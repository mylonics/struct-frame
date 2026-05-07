#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;


import os
import shutil
import hashlib
import json
import time
from struct_frame import FileCGen
from struct_frame import FileTsGen, TestTsGen
from struct_frame import FileJsGen, TestJsGen
from struct_frame import FilePyGen
from struct_frame import FileGqlGen
from struct_frame import FileCppGen
from struct_frame import FileCSharpGen
from struct_frame import FileRustGen
from struct_frame import TestCppGen
from struct_frame import TestPyGen
from struct_frame import TestCGen
from struct_frame import TestCSharpGen
from struct_frame import pascal_case
from struct_frame import camel_to_snake_case
from proto_schema_parser.parser import Parser
from proto_schema_parser import ast
from proto_schema_parser.ast import FieldCardinality

import argparse

current_error_field = ""
current_error_message = ""

default_types = {
    "uint8": {"size": 1},
    "int8": {"size": 1},
    "uint16": {"size": 2},
    "int16": {"size": 2},
    "uint32": {"size": 4},
    "int32": {"size": 4},
    "bool": {"size": 1},
    "float": {"size": 4},
    "double": {"size": 8},
    "int64": {"size": 8},
    "uint64": {"size": 8},
    "string": {"size": 4}  # Variable length, estimated size for length prefix
}

# Type codes for magic number calculation
type_codes = {
    "uint8": 1,
    "int8": 2,
    "uint16": 3,
    "int16": 4,
    "uint32": 5,
    "int32": 6,
    "bool": 7,
    "float": 8,
    "double": 9,
    "int64": 10,
    "uint64": 11,
    "string": 12
}


def calculate_magic_numbers(message):
    """
    Calculate two magic number bytes for a message based on field types and positions.
    This ensures the checksum starts with non-zero values unique to each message structure.

    The magic numbers are calculated using a Fletcher-like algorithm over:
    - Field type codes (not field names)
    - Field positions
    - Field sizes

    Returns: tuple (byte1, byte2)
    """
    magic1 = 0
    magic2 = 0

    position = 0
    for field_name, field in message.fields.items():
        # Get type code
        if field.field_type in type_codes:
            type_code = type_codes[field.field_type]
        else:
            # For custom types (enums, nested messages), use a hash of the type name
            # This ensures different custom types get different codes
            type_code = sum(ord(c) for c in field.field_type) % 256

        # Incorporate type code, position, and size into magic numbers
        # Use Fletcher-like algorithm but ensure non-zero result
        magic1 = (magic1 + type_code + position + 1) & 0xFF
        magic2 = (magic2 + magic1) & 0xFF

        position += 1

    # Handle oneofs
    for oneof_name, oneof in message.oneofs.items():
        for field_name, field in oneof.fields.items():
            if field.field_type in type_codes:
                type_code = type_codes[field.field_type]
            else:
                type_code = sum(ord(c) for c in field.field_type) % 256

            magic1 = (magic1 + type_code + position + 1) & 0xFF
            magic2 = (magic2 + magic1) & 0xFF

            position += 1

    # Ensure magic numbers are non-zero
    # If they are zero, use a default non-zero value
    if magic1 == 0:
        magic1 = 0x5A  # Default non-zero magic byte
    if magic2 == 0:
        magic2 = 0xA5  # Default non-zero magic byte

    return (magic1, magic2)


# Generation hash file name
HASH_FILENAME = ".structframe.hash"


def get_version():
    """Get the struct-frame version from pyproject.toml or package metadata."""
    try:
        # Try to get version from importlib.metadata (Python 3.8+)
        from importlib.metadata import version as get_pkg_version
        return get_pkg_version('struct-frame')
    except Exception:
        pass

    # Fallback: try to read from pyproject.toml
    try:
        import pathlib
        pyproject_path = pathlib.Path(
            __file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('version'):
                        # Parse: version = "0.6.3"
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            return parts[1].strip().strip('"\'')
    except Exception:
        pass

    # Last fallback
    return "unknown"


def compute_generation_hash(args, packages_dict):
    """
    Compute a hash based on CLI parameters, struct-frame version, and parsed message definitions.

    Args:
        args: Parsed argparse arguments
        packages_dict: Dictionary of parsed packages with their messages and enums

    Returns:
        str: SHA256 hash hex string
    """
    hasher = hashlib.sha256()

    # 1. Add struct-frame version
    version = get_version()
    hasher.update(f"version:{version}\n".encode('utf-8'))

    # 2. Add relevant CLI parameters (sorted for consistency)
    cli_params = {
        'build_c': args.build_c,
        'build_ts': args.build_ts,
        'build_js': args.build_js,
        'build_py': args.build_py,
        'build_cpp': args.build_cpp,
        'build_csharp': args.build_csharp,
        'build_gql': args.build_gql,
        'build_rust': args.build_rust,
        'c_path': args.c_path[0] if args.build_c else None,
        'ts_path': args.ts_path[0] if args.build_ts else None,
        'js_path': args.js_path[0] if args.build_js else None,
        'py_path': args.py_path[0] if args.build_py else None,
        'cpp_path': args.cpp_path[0] if args.build_cpp else None,
        'csharp_path': args.csharp_path[0] if args.build_csharp else None,
        'gql_path': args.gql_path[0] if args.build_gql else None,
        'rust_path': args.rust_path[0] if args.build_rust else None,
        'sdk': args.sdk,
        'sdk_embedded': args.sdk_embedded,
        'equality': args.equality,
        'csharp_namespace': args.csharp_namespace[0],
    }
    hasher.update(
        f"cli:{json.dumps(cli_params, sort_keys=True)}\n".encode('utf-8'))

    # 3. Add parsed message definitions (sorted by package name for consistency)
    for pkg_name in sorted(packages_dict.keys()):
        pkg = packages_dict[pkg_name]
        hasher.update(f"package:{pkg_name}\n".encode('utf-8'))

        if pkg.package_id is not None:
            hasher.update(f"  pkgid:{pkg.package_id}\n".encode('utf-8'))

        # Add enums (sorted by name)
        for enum_name in sorted(pkg.enums.keys()):
            enum = pkg.enums[enum_name]
            hasher.update(f"  enum:{enum_name}\n".encode('utf-8'))
            for entry_name in sorted(enum.data.keys()):
                value, _ = enum.data[entry_name]
                hasher.update(f"    {entry_name}={value}\n".encode('utf-8'))

        # Add messages (sorted by name)
        for msg_name in sorted(pkg.messages.keys()):
            msg = pkg.messages[msg_name]
            hasher.update(f"  message:{msg_name}\n".encode('utf-8'))
            if msg.id is not None:
                hasher.update(f"    msgid:{msg.id}\n".encode('utf-8'))
            if msg.variable:
                hasher.update(f"    variable:true\n".encode('utf-8'))
            if msg.is_envelope:
                hasher.update(f"    is_envelope:true\n".encode('utf-8'))

            # Add fields (sorted by name)
            for field_name in sorted(msg.fields.keys()):
                field = msg.fields[field_name]
                field_info = f"    field:{field_name}:{field.field_type}"
                if field.is_array:
                    field_info += ":array"
                if field.size_option is not None:
                    field_info += f":size={field.size_option}"
                if field.max_size is not None:
                    field_info += f":max_size={field.max_size}"
                if field.element_size is not None:
                    field_info += f":element_size={field.element_size}"
                if field.flatten:
                    field_info += ":flatten"
                hasher.update(f"{field_info}\n".encode('utf-8'))

            # Add oneofs (sorted by name)
            for oneof_name in sorted(msg.oneofs.keys()):
                oneof = msg.oneofs[oneof_name]
                hasher.update(f"    oneof:{oneof_name}\n".encode('utf-8'))
                for oneof_field_name in sorted(oneof.fields.keys()):
                    oneof_field = oneof.fields[oneof_field_name]
                    hasher.update(
                        f"      field:{oneof_field_name}:{oneof_field.field_type}\n".encode('utf-8'))

    return hasher.hexdigest()


def get_hash_file_path(args):
    """
    Determine the path for the hash file.

    Args:
        args: Parsed argparse arguments

    Returns:
        str: Path to the hash file
    """
    # Use explicit hash_path if provided
    if args.hash_path[0] is not None:
        hash_dir = args.hash_path[0]
    else:
        # Use the first enabled output path
        if args.build_c:
            hash_dir = args.c_path[0]
        elif args.build_cpp:
            hash_dir = args.cpp_path[0]
        elif args.build_py:
            hash_dir = args.py_path[0]
        elif args.build_ts:
            hash_dir = args.ts_path[0]
        elif args.build_js:
            hash_dir = args.js_path[0]
        elif args.build_csharp:
            hash_dir = args.csharp_path[0]
        elif args.build_gql:
            hash_dir = args.gql_path[0]
        elif args.build_rust:
            hash_dir = args.rust_path[0]
        else:
            # Fallback to current directory
            hash_dir = "."

    return os.path.join(hash_dir, HASH_FILENAME)


def read_previous_hash(hash_file_path):
    """
    Read the previously stored generation hash.

    Args:
        hash_file_path: Path to the hash file

    Returns:
        str or None: The stored hash, or None if file doesn't exist
    """
    try:
        if os.path.exists(hash_file_path):
            with open(hash_file_path, 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def write_generation_hash(hash_file_path, hash_value):
    """
    Write the generation hash to file.

    Args:
        hash_file_path: Path to the hash file
        hash_value: Hash string to write
    """
    dirname = os.path.dirname(hash_file_path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(hash_file_path, 'w') as f:
        f.write(hash_value)


class Enum:
    def __init__(self, package, comments):
        self.name = None
        self.data = {}
        self.size = 1
        self.comments = comments
        self.package = package
        self.is_enum = True
        self.source_file = None
        self.message = None  # Parent message name, or None for package-level enums

    def parse(self, enum):
        self.name = enum.name
        comments = []
        for e in enum.elements:
            if type(e) == ast.Comment:
                comments.append(e.text)
            else:
                if e.name in self.data:
                    print(f"Enum Field Redclaration")
                    return False
                self.data[e.name] = (e.number, comments)
                comments = []

        return True

    def validate(self, current_package, packages, debug=False):
        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"

        output = output + f"Enum: {self.name}\n"

        for key, value in self.data.items():
            output = output + f"Key: {key}, Value: {value}" + "\n"
        return output


class Field:
    def __init__(self, package, comments):
        self.name = None
        self.field_type = None
        self.is_default_type = False
        self.size = 0
        self.validated = False
        self.comments = comments
        self.package = package  # Package where this field is defined
        # Package where the field's type is defined (for cross-package refs)
        self.type_package = None
        self.type_message = None  # Message name if type is a nested enum, else None
        self.is_enum = False
        self.flatten = False
        self.is_array = False
        self.size_option = None   # Fixed size using [size=X]
        self.max_size = None      # Variable size using [max_size=X]
        # Element size for repeated string arrays [element_size=X]
        self.element_size = None

    def parse(self, field):
        self.name = field.name
        self.field_type = field.type

        # Check if this is a repeated field (array)
        if hasattr(field, 'cardinality') and field.cardinality == FieldCardinality.REPEATED:
            self.is_array = True

        if self.field_type in default_types:
            self.is_default_type = True
            self.size = default_types[self.field_type]["size"]
            self.validated = True

        try:
            if hasattr(field, 'options') and field.options:
                # options is typically a list of ast.Option
                for opt in field.options:
                    oname = getattr(opt, 'name', None)
                    ovalue = getattr(opt, 'value', None)
                    if not oname:
                        continue
                    lname = str(oname).strip()
                    # Support unqualified and a couple of qualified names
                    if lname in ('flatten', '(sf.flatten)', '(struct_frame.flatten)'):
                        sval = str(ovalue).strip().lower()
                        if sval in ('true', '1', 'yes', 'on') or ovalue is True:
                            self.flatten = True
                    elif lname in ('size', '(sf.size)', '(struct_frame.size)'):
                        # Fixed size for arrays or strings
                        try:
                            self.size_option = int(ovalue)
                            if self.size_option <= 0 or self.size_option > 65535:
                                print(
                                    f"Invalid size {self.size_option} for field {self.name}, must be 1-65535")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid size value {ovalue} for field {self.name}, must be an integer")
                            return False
                    elif lname in ('max_size', '(sf.max_size)', '(struct_frame.max_size)'):
                        # Variable size for arrays or strings
                        try:
                            self.max_size = int(ovalue)
                            if self.max_size <= 0 or self.max_size > 65535:
                                print(
                                    f"Invalid max_size {self.max_size} for field {self.name}, must be 1-65535")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid max_size value {ovalue} for field {self.name}, must be an integer")
                            return False
                    elif lname in ('element_size', '(sf.element_size)', '(struct_frame.element_size)'):
                        # Individual element size for repeated string arrays
                        try:
                            self.element_size = int(ovalue)
                            if self.element_size <= 0 or self.element_size > 65535:
                                print(
                                    f"Invalid element_size {self.element_size} for field {self.name}, must be 1-65535")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid element_size value {ovalue} for field {self.name}, must be an integer")
                            return False
        except Exception:
            pass
        return True

    def validate(self, current_package, packages, debug=False, current_message=None):

        global current_error_field
        current_error_field = self.name
        if not self.validated:
            # Check for nested enum in the current message first (unqualified name only)
            if (current_message and '.' not in self.field_type
                    and self.field_type in current_message.enums):
                nested_enum = current_message.enums[self.field_type]
                self.is_enum = True
                self.type_message = current_message.name
                self.validated = True
                base_size = nested_enum.size
            else:
                # Handle fully-qualified type names like "pkg_name.TypeName"
                bare_type = self.field_type
                qualified_pkg = None
                if '.' in self.field_type:
                    parts = self.field_type.split('.', 1)
                    qualified_pkg = parts[0]
                    bare_type = parts[1]

                if qualified_pkg:
                    # Qualified name: search only in the named package
                    ret = None
                    source_package = None
                    if qualified_pkg in packages:
                        ret = packages[qualified_pkg].find_field_type(bare_type)
                        if ret:
                            source_package = packages[qualified_pkg]
                else:
                    # First try to find the type in the current package
                    ret = current_package.find_field_type(self.field_type)
                    source_package = current_package

                    # If not found in current package, search in all packages
                    if not ret:
                        for pkg_name, pkg in packages.items():
                            ret = pkg.find_field_type(self.field_type)
                            if ret:
                                source_package = pkg
                                break

                if ret:
                    if ret.validate(current_package, packages, debug):
                        self.is_enum = ret.is_enum
                        self.validated = True
                        base_size = ret.size
                        # Track which package the type comes from
                        self.type_package = source_package.name
                        # Normalize field_type to the bare name (strip package qualifier)
                        self.field_type = bare_type
                    else:
                        print(
                            f"Failed to validate Field: {self.name} of Type: {self.field_type} in Package: {current_package.name}")
                        return False
                else:
                    print(
                        f"Failed to find Field: {self.name} of Type: {self.field_type} in Package: {current_package.name}")
                    return False
        else:
            base_size = self.size

        # Calculate size for arrays and strings
        if self.is_array:
            if self.field_type == "string":
                # String arrays need both array size AND individual element size
                if self.element_size is None:
                    print(
                        f"String array field {self.name} missing required element_size option")
                    return False

                if self.size_option is not None:
                    # Fixed string array: size_option strings, each element_size bytes
                    self.size = self.size_option * self.element_size
                elif self.max_size is not None:
                    # Variable string array: count bytes (1 or 2) + max_size strings of element_size bytes each
                    count_bytes = 2 if self.max_size > 255 else 1
                    self.size = count_bytes + \
                        (self.max_size * self.element_size)
                else:
                    print(
                        f"String array field {self.name} missing required size or max_size option")
                    return False
            else:
                # Non-string arrays
                if self.size_option is not None:
                    # Fixed array: always full, no count byte needed
                    self.size = base_size * self.size_option
                elif self.max_size is not None:
                    # Variable array: count bytes (1 or 2) + max space
                    count_bytes = 2 if self.max_size > 255 else 1
                    self.size = count_bytes + (base_size * self.max_size)
                else:
                    print(
                        f"Array field {self.name} missing required size or max_size option")
                    return False
        elif self.field_type == "string":
            if self.size_option is not None:
                # Fixed string: exactly size_option characters
                self.size = self.size_option
            elif self.max_size is not None:
                # Variable string: length bytes (1 or 2) + max characters
                length_bytes = 2 if self.max_size > 255 else 1
                self.size = length_bytes + self.max_size
            else:
                print(
                    f"String field {self.name} missing required size or max_size option")
                return False
        else:
            self.size = base_size

        # Debug output - only show when debug flag is enabled
        if debug:
            array_info = ""
            if self.is_array:
                if self.field_type == "string":
                    # String arrays show both array size and individual element size
                    if self.size_option is not None:
                        array_info = f", fixed_string_array size={self.size_option}, element_size={self.element_size}"
                    elif self.max_size is not None:
                        array_info = f", bounded_string_array max_size={self.max_size}, element_size={self.element_size}"
                else:
                    # Regular arrays
                    if self.size_option is not None:
                        array_info = f", fixed_array size={self.size_option}"
                    elif self.max_size is not None:
                        array_info = f", bounded_array max_size={self.max_size}"
            elif self.field_type == "string":
                # Regular strings
                if self.size_option is not None:
                    array_info = f", fixed_string size={self.size_option}"
                elif self.max_size is not None:
                    array_info = f", variable_string max_size={self.max_size}"
            print(
                f"  Field {self.name}: type={self.field_type}, is_array={self.is_array}{array_info}, calculated_size={self.size}")

        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        array_info = ""
        if self.is_array:
            if self.size_option is not None:
                array_info = f", Array[size={self.size_option}]"
            elif self.max_size is not None:
                array_info = f", Array[max_size={self.max_size}]"
            else:
                array_info = ", Array[no size specified]"
        elif self.field_type == "string":
            if self.size_option is not None:
                array_info = f", String[size={self.size_option}]"
            elif self.max_size is not None:
                array_info = f", String[max_size={self.max_size}]"
        output = output + \
            f"Field: {self.name}, Type:{self.field_type}, Size:{self.size}{array_info}"
        return output


class OneOf:
    """Represents a oneof (union) construct in a message.

    Discriminator modes:
    - "auto" (default): Use msgid if all fields are messages with msgid, otherwise use field_order
    - "msgid": Force use of message IDs as discriminator (error if any field lacks msgid)
    - "field_order": Force use of field order (1-based index) as discriminator
    - "none": No discriminator generated
    """

    def __init__(self, package, comments):
        self.name = None
        # Fields within this oneof (preserves insertion order in Python 3.7+)
        self.fields = {}
        self.field_order = []  # List of field names in declaration order
        self.size = 0  # Size of the largest field
        self.validated = False
        self.comments = comments
        self.package = package
        self.discriminator_mode = "auto"  # "auto", "msgid", "field_order", "none"
        # True if using msgid, False if using field_order, None if none
        self.auto_discriminator = None
        self.discriminator_type = None  # "msgid" or "field_order" after validation

    def parse(self, oneof_element):
        """Parse a oneof element from the AST."""
        self.name = oneof_element.name
        comments = []

        for e in oneof_element.elements:
            if type(e) == ast.Comment:
                comments.append(e.text)
            elif type(e) == ast.Option:
                if e.name == "discriminator":
                    # Handle both string values and identifier values
                    val = e.value
                    if hasattr(val, 'name'):
                        # It's an Identifier object (unquoted value like 'none')
                        sval = val.name.lower()
                    else:
                        sval = str(val).strip().lower().strip('"\'')
                    if sval in ('auto', 'msgid', 'field_order', 'none', 'false', 'off', 'disabled'):
                        if sval in ('false', 'off', 'disabled'):
                            sval = 'none'
                        self.discriminator_mode = sval
                    else:
                        print(f"Invalid discriminator option '{e.value}' in oneof {self.name}. "
                              f"Valid values: auto, msgid, field_order, none")
                        return False
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"Field Redeclaration in oneof {self.name}")
                    return False
                self.fields[e.name] = Field(self.package, comments)
                self.field_order.append(e.name)  # Track declaration order
                comments = []
                if not self.fields[e.name].parse(e):
                    return False
        return True

    def validate(self, current_package, packages, debug=False, current_message=None):
        """Validate all fields in the oneof and determine size."""
        if self.validated:
            return True

        # Validate each field and track the largest size
        max_size = 0
        all_have_msg_id = True

        for key, field in self.fields.items():
            if not field.validate(current_package, packages, debug, current_message=current_message):
                print(f"Failed to validate field {key} in oneof {self.name}")
                return False
            max_size = max(max_size, field.size)

            # Check if this field's type has a message ID
            if not field.is_default_type and not field.is_enum:
                field_type = current_package.find_field_type(field.field_type)
                # If not found in current package, search in all packages
                if not field_type:
                    for pkg_name, pkg in packages.items():
                        field_type = pkg.find_field_type(field.field_type)
                        if field_type:
                            break

                if field_type and hasattr(field_type, 'id') and field_type.id is not None:
                    # This message type has an ID
                    pass
                else:
                    all_have_msg_id = False
            else:
                # Primitive types or enums don't have message IDs
                all_have_msg_id = False

        self.size = max_size

        # Determine discriminator type based on mode
        if self.discriminator_mode == "none":
            self.auto_discriminator = None
            self.discriminator_type = None
        elif self.discriminator_mode == "msgid":
            if not all_have_msg_id:
                print(
                    f"Error: oneof '{self.name}' has discriminator=msgid but not all fields are messages with msgid")
                return False
            self.auto_discriminator = True
            self.discriminator_type = "msgid"
        elif self.discriminator_mode == "field_order":
            self.auto_discriminator = True  # True means discriminator is present
            self.discriminator_type = "field_order"
        else:  # "auto" - default behavior
            if all_have_msg_id and len(self.fields) > 0:
                self.auto_discriminator = True
                self.discriminator_type = "msgid"
            elif len(self.fields) > 0:
                # Fallback to field_order
                self.auto_discriminator = True
                self.discriminator_type = "field_order"
            else:
                self.auto_discriminator = None
                self.discriminator_type = None

        self.validated = True
        return True

    def get_field_discriminator_value(self, field_name, current_package, packages):
        """Get the discriminator value for a field based on discriminator_type.

        Returns:
            int: The discriminator value (msgid or 1-based field order index)
        """
        if self.discriminator_type == "msgid":
            field = self.fields[field_name]
            field_type = current_package.find_field_type(field.field_type)
            if not field_type:
                for pkg_name, pkg in packages.items():
                    field_type = pkg.find_field_type(field.field_type)
                    if field_type:
                        break
            return field_type.id if field_type else 0
        elif self.discriminator_type == "field_order":
            # 1-based index
            return self.field_order.index(field_name) + 1
        return 0

    def __str__(self):
        output = f"OneOf: {self.name}, Size: {self.size}, Discriminator: {self.discriminator_type}\n"
        for key, value in self.fields.items():
            output += "  " + value.__str__() + "\n"
        return output


class Message:
    def __init__(self, package, comments):
        self.id = None
        self.size = 0
        self.name = None
        self.fields = {}
        self.oneofs = {}  # Dictionary of oneof constructs
        self.enums = {}  # Nested enum definitions (message-scoped)
        self.validated = False
        self.comments = comments
        self.package = package
        self.is_enum = False
        self.magic_bytes = None  # Magic numbers for checksum (byte1, byte2)
        self.variable = False  # Variable length message encoding
        # True if this message is an envelope/container for other messages
        self.is_envelope = False
        self.source_file = None

    def parse(self, msg):
        self.name = msg.name
        comments = []
        for e in msg.elements:
            if type(e) == ast.Option:
                if e.name == "msgid":
                    if self.id:
                        raise Exception(f"Redefinition of msg_id for {e.name}")
                    self.id = e.value
                elif e.name == "variable":
                    sval = str(e.value).strip().lower()
                    if sval in ('true', '1', 'yes', 'on') or e.value is True:
                        self.variable = True
                elif e.name in ("is_envelope", "envelope"):
                    sval = str(e.value).strip().lower()
                    if sval in ('true', '1', 'yes', 'on') or e.value is True:
                        self.is_envelope = True
            elif type(e) == ast.Comment:
                comments.append(e.text)
            elif type(e) == ast.OneOf:
                if e.name in self.oneofs:
                    print(f"OneOf Redeclaration")
                    return False
                self.oneofs[e.name] = OneOf(self.package, comments)
                comments = []
                if not self.oneofs[e.name].parse(e):
                    return False
            elif type(e) == ast.Enum:
                if e.name in self.enums:
                    print(f"Enum Redeclaration in message {self.name}")
                    return False
                self.enums[e.name] = Enum(self.package, comments)
                self.enums[e.name].message = self.name
                comments = []
                if not self.enums[e.name].parse(e):
                    return False
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"Field Redeclaration")
                    return False
                self.fields[e.name] = Field(self.package, comments)
                comments = []
                if not self.fields[e.name].parse(e):
                    return False
        return True

    def validate(self, current_package, packages, debug=False):
        if self.validated:
            return True

        global current_error_message
        current_error_message = self.name

        # Validate regular fields
        for key, value in self.fields.items():
            if not value.validate(current_package, packages, debug, current_message=self):
                print(
                    f"Failed To validate Field: {key}, in Message {self.name}\n")
                return False
            self.size = self.size + value.size

        # Validate oneofs - they contribute their max size to the message
        for key, oneof in self.oneofs.items():
            if not oneof.validate(current_package, packages, debug, current_message=self):
                print(
                    f"Failed To validate OneOf: {key}, in Message {self.name}\n")
                return False
            # Add oneof size (largest field size)
            self.size = self.size + oneof.size
            # If discriminator is enabled, add bytes for the discriminator field
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    self.size = self.size + 2  # uint16_t for message ID
                else:  # field_order
                    self.size = self.size + 1  # uint8_t for field order index

        # Flatten collision detection: if a field is marked as flatten and is a message,
        # ensure none of the child field names collide with fields in this message.
        parent_field_names = set(self.fields.keys())
        for key, value in self.fields.items():
            if getattr(value, 'flatten', False):
                # Only meaningful for non-default, non-enum message types
                if value.is_default_type or value.is_enum:
                    # Flatten has no effect on primitives/enums; skip
                    continue
                child = current_package.find_field_type(value.field_type)
                if not child or getattr(child, 'is_enum', False) or not hasattr(child, 'fields'):
                    # Unknown or non-message type; skip
                    continue
                for ck in child.fields.keys():
                    if ck in parent_field_names:
                        print(
                            f"Flatten collision in Message {self.name}: field '{key}.{ck}' collides with existing field '{ck}'.")
                        return False

        # Array validation
        for key, value in self.fields.items():
            if value.is_array:
                # All arrays must have size or max_size specified
                if value.size_option is None and value.max_size is None:
                    print(
                        f"Array field {key} in Message {self.name}: must specify size or max_size option")
                    return False
            elif value.field_type == "string":
                # Strings must have size or max_size specified
                if value.size_option is None and value.max_size is None:
                    print(
                        f"String field {key} in Message {self.name}: must specify size or max_size option")
                    return False
            elif value.max_size is not None or value.size_option is not None or value.element_size is not None:
                print(
                    f"Field {key} in Message {self.name}: size/max_size/element_size options can only be used with repeated fields or strings")
                return False

        # Envelope message validation
        if self.is_envelope:
            # Envelope messages must have exactly one oneof field
            if len(self.oneofs) != 1:
                print(
                    f"Envelope message {self.name}: must have exactly one oneof field (found {len(self.oneofs)})")
                return False

            # Get the single oneof
            oneof_name = list(self.oneofs.keys())[0]
            oneof = self.oneofs[oneof_name]

            # All fields in the oneof must be message types (not primitives or enums)
            for field_name, field in oneof.fields.items():
                if field.is_default_type:
                    print(
                        f"Envelope message {self.name}: oneof field '{field_name}' must be a message type, not a primitive")
                    return False
                if field.is_enum:
                    print(
                        f"Envelope message {self.name}: oneof field '{field_name}' must be a message type, not an enum")
                    return False

            # If discriminator mode is "msgid" (explicit or auto-determined), all messages must have msgid
            # Note: oneof.validate() is called before message.validate(), so discriminator_type is set
            if oneof.discriminator_type == "msgid":
                for field_name, field in oneof.fields.items():
                    # Find the message type and verify it has a message ID
                    field_type = current_package.find_field_type(
                        field.field_type)
                    if not field_type:
                        for pkg_name, pkg in packages.items():
                            field_type = pkg.find_field_type(field.field_type)
                            if field_type:
                                break

                    if not field_type or not hasattr(field_type, 'id') or field_type.id is None:
                        print(
                            f"Envelope message {self.name}: oneof field '{field_name}' type '{field.field_type}' must have a message ID (option msgid) when using msgid discriminator")
                        return False

        self.validated = True

        # Calculate magic numbers for this message
        self.magic_bytes = calculate_magic_numbers(self)

        # Calculate minimum size for variable messages
        # min_size is the size when all variable-length fields are at their minimum
        if self.variable:
            self.min_size = 0
            for key, value in self.fields.items():
                if value.is_array and value.max_size is not None:
                    # Bounded array: only the count bytes (1 or 2, no data when empty)
                    count_bytes = 2 if value.max_size > 255 else 1
                    self.min_size += count_bytes
                elif value.field_type == "string" and value.max_size is not None:
                    # Variable string: only the length bytes (1 or 2, no data when empty)
                    length_bytes = 2 if value.max_size > 255 else 1
                    self.min_size += length_bytes
                else:
                    # Fixed-size fields use their full size
                    self.min_size += value.size
        else:
            self.min_size = self.size

        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        if self.variable:
            output = output + \
                f"Message: {self.name}, Size: {self.size}, MinSize: {self.min_size}, ID: {self.id}, Variable: True\n"
        else:
            output = output + \
                f"Message: {self.name}, Size: {self.size}, ID: {self.id}\n"

        for key, value in self.fields.items():
            output = output + value.__str__() + "\n"

        for key, value in self.oneofs.items():
            output = output + value.__str__() + "\n"

        return output


class Package:
    def __init__(self, name):
        self.name = name
        self.enums = {}
        self.messages = {}
        self.package_id = None  # Package ID for extended message IDs (0-255)

    def addEnum(self, enum, comments, source_file=None):
        self.comments = comments
        if enum.name in self.enums:
            print(f"Enum Redclaration")
            return False
        self.enums[enum.name] = Enum(self.name, comments)
        self.enums[enum.name].source_file = source_file
        return self.enums[enum.name].parse(enum)

    def addMessage(self, message, comments, source_file=None):
        if message.name in self.messages:
            print(f"Message Redclaration")
            return False
        self.messages[message.name] = Message(self.name, comments)
        self.messages[message.name].source_file = source_file
        return self.messages[message.name].parse(message)

    def validate_package(self, all_packages, debug=False):
        names = []
        for key, value in self.enums.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)
        for key, value in self.messages.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)

        # Validate package ID if specified
        if self.package_id is not None:
            if self.package_id < 0 or self.package_id > 255:
                print(
                    f"Package ID {self.package_id} for package {self.name} out of range (0-255)")
                return False

            # Note: We allow different packages to share the same package ID if one inherited
            # from the other through imports. The package_imports tracking handles this.
            # Only error if the same package NAME has different IDs (checked in validate_package_id).

        # Validate message IDs based on whether package has a package ID
        for key, value in self.messages.items():
            if value.id is not None:
                if self.package_id is not None:
                    # If package has a package ID, message IDs must be < 256
                    if value.id < 0 or value.id >= 256:
                        print(
                            f"Error: Message '{value.name}' in package '{self.name}' has msgid={value.id}")
                        print(
                            f"  When package has 'option pkgid={self.package_id}', all message IDs must be in range [0, 255]")
                        return False
                else:
                    # If no package ID, message IDs must be < 65536
                    if value.id < 0 or value.id >= 65536:
                        print(
                            f"Error: Message '{value.name}' in package '{self.name}' has msgid={value.id}")
                        print(
                            f"  Without package ID, message IDs must be in range [0, 65535]")
                        return False

        for key, value in self.messages.items():
            if not value.validate(self, all_packages, debug):
                print(
                    f"Failed To validate Message: {key}, in Package {self.name}\n")
                return False

        return True

    def find_field_type(self, name):
        for key, value in self.enums.items():
            if value.name == name:
                return value

        for key, value in self.messages.items():
            if value.name == name:
                return value

    def sortedMessages(self):
        # Need to sort messages to ensure no out of order dependencies.
        return self.messages

    def __str__(self):
        output = "Package: " + self.name
        if self.package_id is not None:
            output += f" (ID: {self.package_id})"
        output += "\n"
        for key, value in self.enums.items():
            output = output + value.__str__() + "\n"
        for key, value in self.messages.items():
            output = output + value.__str__() + "\n"
        return output


packages = {}
processed_file = []
required_file = []
# Track which package imports which other packages: {importing_pkg: [imported_pkg1, imported_pkg2, ...]}
package_imports = {}

parser = argparse.ArgumentParser(
    prog='struct_frame',
    description='Message serialization and header generation program')

parser.add_argument('filename', nargs='?', default=None,
                    help='Proto file to process')
parser.add_argument('--debug', action='store_true')
parser.add_argument('--validate', action='store_true',
                    help='Validate the proto file without generating any output files')
parser.add_argument('--build_c', action='store_true')
parser.add_argument('--build_ts', action='store_true')
parser.add_argument('--build_js', action='store_true')
parser.add_argument('--build_py', action='store_true')
parser.add_argument('--build_cpp', action='store_true')
parser.add_argument('--build_csharp', action='store_true')
parser.add_argument('--c_path', nargs=1, type=str, default=['generated/c/'])
parser.add_argument('--ts_path', nargs=1, type=str, default=['generated/ts/'])
parser.add_argument('--js_path', nargs=1, type=str, default=['generated/js/'])
parser.add_argument('--py_path', nargs=1, type=str, default=['generated/py/'])
parser.add_argument('--cpp_path', nargs=1, type=str,
                    default=['generated/cpp/'])
parser.add_argument('--csharp_path', nargs=1, type=str,
                    default=['generated/csharp/'])
parser.add_argument('--build_gql', action='store_true')
parser.add_argument('--gql_path', nargs=1, type=str,
                    default=['generated/gql/'])
parser.add_argument('--build_rust', action='store_true')
parser.add_argument('--rust_path', nargs=1, type=str,
                    default=['generated/rust/'])
parser.add_argument('--catalog_path', nargs=1, type=str, default=['generated/'],
                    help='Directory for the LSP type catalog file (sf_compile.json)')
parser.add_argument('--sdk', action='store_true',
                    help='Include full SDK with all transports (UDP, TCP, WebSocket, Serial)')
parser.add_argument('--sdk_embedded', action='store_true',
                    help='Include embedded SDK (serial transport only, no ASIO dependencies)')
parser.add_argument('--equality', action='store_true',
                    help='Generate equality comparison operators/methods for messages')
parser.add_argument('--csharp_namespace', nargs=1, type=str, default=['StructFrame'],
                    help='Root namespace for generated C# code (default: StructFrame)')
parser.add_argument('--force', action='store_true',
                    help='Force regeneration even if hash matches previous generation')
parser.add_argument('--hash_path', nargs=1, type=str, default=[None],
                    help='Path to store the generation hash file (default: first output path)')
parser.add_argument('--generate_tests', action='store_true',
                    help='Generate test code with dummy values for all messages (round-trip encode/decode verification)')


def parseFile(filename, base_path=None, importing_package=None):
    """Parse a proto file and handle imports recursively.

    Args:
        filename: Path to the proto file to parse
        base_path: Base directory for resolving relative imports (defaults to filename's directory)
        importing_package: Name of the package that is importing this file (for tracking imports)

    Returns:
        bool: True if parsing succeeded, False otherwise
    """
    # Convert to absolute path for circular import detection
    abs_filename = os.path.abspath(filename)

    # Avoid circular imports
    if abs_filename in processed_file:
        return True

    processed_file.append(abs_filename)

    # Set base path for resolving imports
    if base_path is None:
        base_path = os.path.dirname(abs_filename)

    try:
        with open(abs_filename, "r") as f:
            result = Parser().parse(f.read())
    except FileNotFoundError:
        print(f"Error: Could not find file {filename}")
        return False
    except Exception as e:
        print(f"Error parsing file {filename}: {e}")
        return False

    foundPackage = False
    package_name = ""
    comments = []

    for e in result.file_elements:
        if (type(e) == ast.Package):
            if foundPackage:
                print(
                    f"Multiple Package declaration found in file {filename} - {package_name}")
                return False
            foundPackage = True
            package_name = e.name
            if package_name not in packages:
                packages[package_name] = Package(package_name)
            # Track import relationship if this file was imported
            if importing_package and importing_package != package_name:
                if importing_package not in package_imports:
                    package_imports[importing_package] = []
                if package_name not in package_imports[importing_package]:
                    package_imports[importing_package].append(package_name)

        elif (type(e) == ast.Import):
            # Handle import statements
            import_file = e.name

            # Try to resolve import path relative to base_path first
            import_path_base = os.path.join(base_path, import_file)
            import_path_current = os.path.join(
                os.path.dirname(abs_filename), import_file)

            if os.path.exists(import_path_base):
                import_path = import_path_base
            elif os.path.exists(import_path_current):
                import_path = import_path_current
            else:
                print(
                    f"Error: Could not find imported file '{import_file}' from {filename}")
                print(f"  Tried: {import_path_base}")
                print(f"  Tried: {import_path_current}")
                return False

            # Recursively parse the imported file, passing current package as importer
            if not parseFile(import_path, base_path, package_name):
                print(f"Error: Failed to parse imported file {import_file}")
                return False

        elif (type(e) == ast.Option):
            # Handle file-level options (like pkgid)
            if not foundPackage:
                print(
                    f"Option {e.name} found before package declaration in {filename}")
                return False
            if e.name == "pkgid":
                if not validate_package_id(package_name, e.value, filename):
                    return False

        elif (type(e) == ast.Enum):
            if not foundPackage:
                print(f"Enum found before package declaration in {filename}")
                return False
            if not packages[package_name].addEnum(e, comments, source_file=abs_filename):
                print(
                    f"Enum Error in Package: {package_name}  FileName: {filename} EnumName: {e.name}")
                return False
            comments = []

        elif (type(e) == ast.Message):
            if not foundPackage:
                print(
                    f"Message found before package declaration in {filename}")
                return False
            if not packages[package_name].addMessage(e, comments, source_file=abs_filename):
                print(
                    f"Message Error in Package: {package_name}  FileName: {filename} MessageName: {e.name}")
                return False
            comments = []

        elif (type(e) == ast.Comment):
            comments.append(e.text)

    return True


def validate_package_id(package_name, new_id, filename):
    """Validate package ID assignment.

    Args:
        package_name: Name of the package
        new_id: Package ID being assigned
        filename: File where the assignment occurs

    Returns:
        bool: True if valid, False if conflict detected
    """
    current_id = packages[package_name].package_id

    if current_id is not None:
        # Check if this is a conflicting value
        if current_id != new_id:
            print(
                f"Error: Package '{package_name}' has conflicting package IDs:")
            print(f"  Already defined as: {current_id}")
            print(f"  Trying to redefine as: {new_id} in {filename}")
            return False
        # Same value - this is OK (multiple files in same package)
    else:
        # First assignment
        packages[package_name].package_id = new_id

    return True


def apply_package_id_inheritance():
    """Apply package ID inheritance rules.

    After all files are parsed, if an imported package has no package ID,
    it inherits the package ID from the importing package.

    Returns:
        bool: True if successful, False if conflicts detected
    """
    # Iterate through import relationships
    for importing_pkg, imported_pkgs in package_imports.items():
        importing_pkg_id = packages[importing_pkg].package_id

        for imported_pkg in imported_pkgs:
            imported_pkg_id = packages[imported_pkg].package_id

            # If imported package has no ID, inherit from importing package
            if imported_pkg_id is None:
                if importing_pkg_id is not None:
                    # Inheritance: imported package gets the importing package's ID
                    packages[imported_pkg].package_id = importing_pkg_id
                # else: Neither package has an ID - this will be caught by validatePackages if needed
            # If both packages have IDs, they are validated separately
            # Note: Same package name with different IDs is caught by validate_package_id()
            # during parsing, not here

    return True


def validate_packages(debug=False):
    """Validate all packages and enforce multi-package rules."""

    # Apply package ID inheritance first
    if not apply_package_id_inheritance():
        return False

    # Check if multiple packages exist
    if len(packages) > 1:
        # When multiple packages are being compiled, they must have package IDs
        packages_without_ids = [
            name for name, pkg in packages.items() if pkg.package_id is None]
        if packages_without_ids:
            print(f"Error: Multiple packages are being compiled, but the following packages do not have package IDs assigned:")
            for pkg_name in packages_without_ids:
                print(f"  - {pkg_name}")
            print(f"\nWhen compiling multiple packages, each package must specify 'option pkgid = N;' where N is 0-255.")
            print(f"This ensures unique message IDs across all packages using the format: (package_id << 8) | msg_id")
            return False

    # Validate each package
    for key, value in packages.items():
        if not value.validate_package(packages, debug):
            print(f"Failed To Validate Package: {key}")
            return False

    return True


def needs_extended_payload_types():
    """
    Determine if only Extended* payload types should be used.

    Returns True if:
    - Any package has a package ID, OR
    - Any message ID is >= 256

    When this returns True, only Extended* payload types should be generated:
    - ExtendedMsgIds, Extended, ExtendedMinimal, ExtendedMultiSystemStream, ExtendedLength

    Standard payload types (Minimal, Default, SysComp, Seq, MultiSystemStream)
    and their profiles (ProfileStandard, ProfileSensor, ProfileIPC) should not be generated.
    """
    for pkg_name, pkg in packages.items():
        # Check if package has package ID
        if pkg.package_id is not None:
            return True

        # Check if any message ID >= 256
        for msg_name, msg in pkg.messages.items():
            if msg.id is not None and msg.id >= 256:
                return True

    return False


def printPackages():
    for key, value in packages.items():
        print(value)


def topological_sort_packages(pkgs, pkg_imports):
    """Return package names in dependency-first topological order (Kahn's BFS).

    Packages with no dependencies come first so that an aggregate include file
    can list them in the order a compiler needs to see them.

    Args:
        pkgs:        dict {pkg_name: Package}
        pkg_imports: dict {pkg_name: [imported_pkg_name, ...]}

    Returns:
        list of package names in topological order
    """
    from collections import deque

    # Build in-degree count and adjacency list (dependency → dependant)
    in_degree = {name: 0 for name in pkgs}
    dependants = {name: [] for name in pkgs}

    for pkg_name, deps in pkg_imports.items():
        if pkg_name not in pkgs:
            continue
        for dep in deps:
            if dep not in pkgs:
                continue
            in_degree[pkg_name] += 1
            dependants[dep].append(pkg_name)

    # Start with packages that have no dependencies
    queue = deque(name for name, deg in in_degree.items() if deg == 0)
    # Sort for determinism when multiple packages have the same degree
    queue = deque(sorted(queue))
    result = []

    while queue:
        pkg_name = queue.popleft()
        result.append(pkg_name)
        for dep in sorted(dependants[pkg_name]):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    # Append any remaining packages (handles cycles or disconnected nodes)
    for name in sorted(pkgs):
        if name not in result:
            result.append(name)

    return result


def generate_lsp_file_strings(catalog_path, build_flags=None, paths=None):
    """Generate a single JSON catalog file for language-server navigation.

    Produces one language-agnostic ``sf_compile.json`` that lists
    every message, nested message, and enum defined across all packages,
    together with the source ``.proto`` file, generated file path, and
    language-specific element name for each enabled language.

    Args:
        catalog_path: Directory where ``sf_compile.json`` will be written.
        build_flags:  dict {lang: bool}  e.g. {'c': True, 'cpp': False, ...}
        paths:        dict {lang: str}   absolute output directory for each language

    Returns:
        dict {filename: content}
    """
    if build_flags is None:
        build_flags = {}
    if paths is None:
        paths = {}

    abs_catalog = os.path.abspath(catalog_path)

    def _relpath(abs_file):
        """Return a forward-slash relative path from catalog_path to abs_file."""
        try:
            rel = os.path.relpath(abs_file, abs_catalog)
        except ValueError:
            # Different drives on Windows — fall back to absolute path
            rel = abs_file
        return rel.replace(os.sep, '/')

    def _pkg_generated_files(pkg_name):
        """Return {lang: relative_path} for package-level generated files."""
        result = {}
        if build_flags.get('c'):
            result['c'] = _relpath(os.path.join(os.path.abspath(paths['c']),
                                                f'{pkg_name}.structframe.h'))
        if build_flags.get('cpp'):
            result['cpp'] = _relpath(os.path.join(os.path.abspath(paths['cpp']),
                                                  f'{pkg_name}.structframe.hpp'))
        if build_flags.get('ts'):
            result['ts'] = _relpath(os.path.join(os.path.abspath(paths['ts']),
                                                 f'{pkg_name.replace("_", "-")}.structframe.ts'))
        if build_flags.get('js'):
            result['js'] = _relpath(os.path.join(os.path.abspath(paths['js']),
                                                 f'{pkg_name.replace("_", "-")}.structframe.js'))
        if build_flags.get('py'):
            result['py'] = _relpath(os.path.join(os.path.abspath(paths['py']),
                                                 'struct_frame', 'generated',
                                                 f'{pkg_name}.py'))
        if build_flags.get('gql'):
            result['gql'] = _relpath(os.path.join(os.path.abspath(paths['gql']),
                                                  f'{pkg_name}.graphql'))
        if build_flags.get('rust'):
            result['rust'] = _relpath(os.path.join(os.path.abspath(paths['rust']),
                                                   f'{pkg_name}.structframe.rs'))
        return result

    def _lang_symbol_info(lang, pkg, symbol_name):
        """Return language-specific namespace, element, and qualified element."""
        pkg_name = pkg.name
        pkg_pascal = pascal_case(pkg_name)

        if lang == 'c':
            element = f'{pkg_pascal}{symbol_name}'
            return None, element, element

        if lang == 'cpp':
            # C++ always uses structframe::<pkg_name> nested namespace
            namespace = f'structframe::{camel_to_snake_case(pkg_name)}'
            element = symbol_name
            return namespace, element, f'{namespace}::{element}'

        if lang in ('ts', 'js'):
            element = symbol_name
            return None, element, element

        if lang == 'gql':
            element = f'{pkg_pascal}{symbol_name}'
            return None, element, element

        if lang == 'py':
            namespace = f'struct_frame.generated.{pkg_name}'
            element = symbol_name
            return namespace, element, f'{namespace}.{element}'

        if lang == 'rust':
            namespace = pkg_name
            element = symbol_name
            return namespace, element, f'{namespace}::{element}'

        if lang == 'csharp':
            namespace = f'StructFrame.{pkg_pascal}'
            element = symbol_name
            return namespace, element, f'{namespace}.{element}'

        return None, symbol_name, symbol_name

    def _generated_file_entries(pkg, symbol_name, base_generated_files):
        """Return {lang: {path, namespace, element, qualified_element}} catalog entries."""
        entries = {}
        for lang, rel_path in base_generated_files.items():
            namespace, element, qualified_element = _lang_symbol_info(
                lang, pkg, symbol_name)
            entries[lang] = {
                "path": rel_path,
                "namespace": namespace,
                "element": element,
                "qualified_element": qualified_element,
            }
        return entries

    ordered = topological_sort_packages(packages, package_imports)

    messages = []
    enums = []

    for pkg_name in ordered:
        if pkg_name not in packages:
            continue
        pkg = packages[pkg_name]
        pkg_files = _pkg_generated_files(pkg_name)
        pkg_pascal = pascal_case(pkg_name)

        for msg_name, msg in pkg.messages.items():
            gen_files = dict(pkg_files)
            # C#: one file per message — {PascalPkg}/Messages/{MsgName}.cs
            if build_flags.get('csharp'):
                gen_files['csharp'] = _relpath(
                    os.path.join(os.path.abspath(paths['csharp']),
                                 pkg_pascal, 'Messages', f'{msg_name}.cs'))
            messages.append({
                "name": msg_name,
                "package": pkg_name,
                "source_file": os.path.basename(msg.source_file) if msg.source_file else None,
                "generated_files": _generated_file_entries(
                    pkg, msg_name, gen_files
                ),
            })

            # Nested enums (message-scoped): appear in the same file as the parent message
            for nested_enum_name, nested_enum in msg.enums.items():
                nested_gen_files = {}
                for lang, rel_path in gen_files.items():
                    # Nested enums share the parent message's generated file
                    nested_gen_files[lang] = rel_path

                def _nested_enum_symbol_info(lang, pkg_, msg_name_, enum_name_):
                    pkg_name_ = pkg_.name
                    pkg_pascal_ = pascal_case(pkg_name_)
                    flat_name = f'{pkg_pascal_}{msg_name_}{enum_name_}'

                    if lang == 'c':
                        return None, flat_name, flat_name

                    if lang == 'cpp':
                        # C++ always uses structframe::<pkg_name> nested namespace
                        ns = f'structframe::{camel_to_snake_case(pkg_name_)}'
                        element = f'{msg_name_}::{enum_name_}'
                        return ns, element, f'{ns}::{msg_name_}::{enum_name_}'

                    if lang == 'py':
                        ns = f'struct_frame.generated.{pkg_name_}'
                        return ns, enum_name_, f'{ns}.{msg_name_}.{enum_name_}'

                    if lang in ('ts', 'js'):
                        element = f'{msg_name_}{enum_name_}'
                        return None, element, element

                    if lang == 'rust':
                        element = f'{msg_name_}{enum_name_}'
                        ns = pkg_name_
                        return ns, element, f'{ns}::{element}'

                    if lang == 'csharp':
                        ns = f'StructFrame.{pkg_pascal_}'
                        return ns, enum_name_, f'{ns}.{msg_name_}.{enum_name_}'

                    return None, enum_name_, enum_name_

                nested_entries = {}
                for lang, rel_path in nested_gen_files.items():
                    namespace_, element_, qualified_ = _nested_enum_symbol_info(
                        lang, pkg, msg_name, nested_enum_name)
                    nested_entries[lang] = {
                        "path": rel_path,
                        "namespace": namespace_,
                        "element": element_,
                        "qualified_element": qualified_,
                    }

                enums.append({
                    "name": nested_enum_name,
                    "package": pkg_name,
                    "parent_message": msg_name,
                    "source_file": os.path.basename(msg.source_file) if msg.source_file else None,
                    "generated_files": nested_entries,
                })

        for enum_name, enum in pkg.enums.items():
            gen_files = dict(pkg_files)
            # C#: one file per enum — {PascalPkg}/Enums/{EnumName}.cs
            if build_flags.get('csharp'):
                gen_files['csharp'] = _relpath(
                    os.path.join(os.path.abspath(paths['csharp']),
                                 pkg_pascal, 'Enums', f'{enum_name}.cs'))
            enums.append({
                "name": enum_name,
                "package": pkg_name,
                "source_file": os.path.basename(enum.source_file) if enum.source_file else None,
                "generated_files": _generated_file_entries(
                    pkg, enum_name, gen_files
                ),
            })

    catalog = {
        "messages": messages,
        "enums": enums,
    }

    catalog_file = os.path.join(catalog_path, "sf_compile.json")
    return {catalog_file: json.dumps(catalog, indent=2) + "\n"}


def generateCFileStrings(path, equality=False, generate_tests=False):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.h")
        imported = package_imports.get(value.name, [])
        data = ''.join(FileCGen.generate(
            value, imported_packages=imported, equality=equality))
        out[name] = data

        if generate_tests:
            test_name = os.path.join(path, value.name + ".tests.h")
            out[test_name] = ''.join(TestCGen.generate(value))
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".c")
            out[roundtrip_name] = ''.join(TestCGen.generate_roundtrip_main(value))

    return out


def generateTsFileStrings(path, equality=False, generate_tests=False):
    import json as _json
    out = {}
    pkg_names = []
    for key, value in packages.items():
        kebab_name = value.name.replace('_', '-')
        name = os.path.join(path, kebab_name + ".structframe.ts")
        data = ''.join(FileTsGen.generate(
            value, use_class_based=True, packages=packages, equality=equality))
        out[name] = data
        pkg_names.append(kebab_name)

        # Generate test file alongside the package output if requested.
        # Mirrors the Python/C++ generator pattern: emit a runnable
        # ``test_roundtrip_<package>.ts`` containing dummy-value factories,
        # round-trip verifier, and a ``main`` entrypoint.
        if generate_tests:
            imported = package_imports.get(value.name, [])
            test_name = os.path.join(path, "test_roundtrip_" + value.name + ".ts")
            test_data = ''.join(TestTsGen.generate(value, imported_packages=imported))
            out[test_name] = test_data

    # Generate index.ts barrel so the output folder is a self-contained ESM package
    if pkg_names:
        sf_ver = get_version()
        lines = [
            '/* Auto-generated barrel index — re-exports all generated packages */',
            f'/* Generated by struct-frame {sf_ver} */\n',
        ]
        for pkg in sorted(pkg_names):
            lines.append(f"export * from './{pkg}.structframe';")
        out[os.path.join(path, 'index.ts')] = '\n'.join(lines) + '\n'

        pkg_json = {
            "exports": {
                ".": {
                    "import": "./index.ts",
                    "types": "./index.ts"
                }
            }
        }
        out[os.path.join(path, 'package.json')] = _json.dumps(
            pkg_json, indent=2) + '\n'

    return out


def generateJsFileStrings(path, equality=False, generate_tests=False):
    import json as _json
    out = {}
    pkg_names = []
    for key, value in packages.items():
        kebab_name = value.name.replace('_', '-')
        name = os.path.join(path, kebab_name + ".structframe.js")
        data = ''.join(FileJsGen.generate(
            value, use_class_based=True, packages=packages, equality=equality))
        out[name] = data
        pkg_names.append(kebab_name)

        # Generate test file alongside the package output if requested.
        # Mirrors the Python/C++ generator pattern: emit a runnable
        # ``test_roundtrip_<package>.js`` containing dummy-value factories,
        # round-trip verifier, and a ``main`` entrypoint.
        if generate_tests:
            imported = package_imports.get(value.name, [])
            test_name = os.path.join(path, "test_roundtrip_" + value.name + ".js")
            test_data = ''.join(TestJsGen.generate(value, imported_packages=imported))
            out[test_name] = test_data

    # Generate index.js barrel so the output folder is a self-contained CJS package
    if pkg_names:
        sf_ver = get_version()
        lines = [
            '/* Auto-generated barrel index — re-exports all generated packages */',
            f'/* Generated by struct-frame {sf_ver} */\n',
        ]
        for pkg in sorted(pkg_names):
            lines.append(
                f"Object.assign(module.exports, require('./{pkg}.structframe'));")
        out[os.path.join(path, 'index.js')] = '\n'.join(lines) + '\n'

    return out


def generatePyFileStrings(path, equality=False, generate_tests=False):
    out = {}

    # Create package structure: struct_frame/generated/
    generated_path = os.path.join(path, "struct_frame", "generated")

    # Create __init__.py for struct_frame package
    struct_frame_init = os.path.join(path, "struct_frame", "__init__.py")
    out[struct_frame_init] = '"""StructFrame generated code package."""\n'

    # Create __init__.py for generated subpackage
    generated_init = os.path.join(generated_path, "__init__.py")
    out[generated_init] = '"""StructFrame generated message definitions."""\n'

    # Generate message files in the generated package
    for key, value in packages.items():
        name = os.path.join(generated_path, value.name + ".py")
        imported_pkg_names = package_imports.get(value.name, [])
        imported_pkg_objects = {n: packages[n]
                                for n in imported_pkg_names if n in packages}
        data = ''.join(FilePyGen.generate(value, imported_packages=imported_pkg_names,
                                          imported_package_objects=imported_pkg_objects, equality=equality))
        out[name] = data

        # Generate test file if requested
        if generate_tests:
            test_name = os.path.join(generated_path, value.name + "_tests.py")
            test_data = ''.join(TestPyGen.generate(value, imported_packages=imported_pkg_names))
            out[test_name] = test_data
            # Standalone round-trip runner: a tiny wrapper that just imports the
            # tests module and invokes its ``__main__`` entry point. Generated
            # alongside as ``test_roundtrip_<package>.py`` so the test runner
            # can launch it directly per .sf file.
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".py")
            out[roundtrip_name] = (
                '#!/usr/bin/env python3\n'
                '"""Standalone round-trip test runner for package \'%s\'.\n'
                'Generated by struct-frame %s. Exercises every message across all 5 frame profiles."""\n'
                'import os, runpy, sys\n'
                'HERE = os.path.dirname(os.path.abspath(__file__))\n'
                'sys.path.insert(0, os.path.join(HERE, "struct_frame", "generated"))\n'
                'sys.path.insert(0, HERE)\n'
                'runpy.run_module("struct_frame.generated.%s_tests", run_name="__main__")\n'
            ) % (value.name, get_version(), value.name)

    return out


def generateCppFileStrings(path, equality=False, generate_tests=False):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.hpp")
        imported = package_imports.get(value.name, [])
        data = ''.join(FileCppGen.generate(
            value, imported_packages=imported, equality=equality))
        out[name] = data

        # Generate test file if requested
        if generate_tests:
            test_name = os.path.join(path, value.name + ".tests.hpp")
            test_data = ''.join(TestCppGen.generate(value))
            out[test_name] = test_data
            # Standalone round-trip main file with full ``main()``: compile this
            # single .cpp (with -I<gen_dir>) to get a binary that runs
            # round-trip tests for every message across all 5 profiles.
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".cpp")
            roundtrip_data = ''.join(TestCppGen.generate_roundtrip_main(value))
            out[roundtrip_name] = roundtrip_data
    return out


def generateRustFileStrings(path, equality=False):
    out = {}
    # Collect all packages being generated now
    new_package_names = []
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.rs")
        data = ''.join(FileRustGen.generate(value, equality=equality))
        out[name] = data
        new_package_names.append(value.name)

    # Discover ALL .structframe.rs files in the output directory (from previous runs)
    all_package_names = list(new_package_names)
    if os.path.exists(path):
        for fname in sorted(os.listdir(path)):
            if fname.endswith('.structframe.rs'):
                pkg_name = fname[:-len('.structframe.rs')]
                if pkg_name not in all_package_names:
                    all_package_names.append(pkg_name)

    # Generate lib.rs and Cargo.toml for the generated crate
    out[os.path.join(path, "lib.rs")] = FileRustGen.generate_lib_rs(
        sorted(all_package_names))
    out[os.path.join(path, "Cargo.toml")] = FileRustGen.generate_cargo_toml()
    return out


def generateCSharpFileStrings(path, equality=False, namespace='StructFrame.Generated', generate_tests=False):
    out = {}
    for key, value in packages.items():
        # Generate per-file output into a package subfolder
        pkg_folder = os.path.join(path, pascal_case(value.name))
        per_file = FileCSharpGen.generate_per_file(value, equality=equality)
        for filename, content in per_file.items():
            out[os.path.join(pkg_folder, filename)] = content

        # Always generate SDK interface (inside package folder)
        from struct_frame.csharp_sdk_interface_gen import generate_csharp_sdk_interface
        sdk_name = os.path.join(pkg_folder, "SdkInterface.cs")
        sdk_data = generate_csharp_sdk_interface(value)
        out[sdk_name] = sdk_data

        if generate_tests:
            test_name = os.path.join(pkg_folder, "test_roundtrip_" + value.name + ".cs")
            out[test_name] = ''.join(TestCSharpGen.generate(value, namespace=namespace))

    # Always generate .csproj so consumers can use <ProjectReference>
    csproj_name = os.path.join(path, "StructFrame.csproj")
    csproj_data = _generateCSharpProjectFile(namespace)
    out[csproj_name] = csproj_data

    return out


def _generateCSharpProjectFile(namespace):
    """Generate a .csproj file for the generated C# code.

    Produces an SDK-style class library project that auto-includes all .cs files.
    Consumers can reference this via <ProjectReference> instead of listing
    individual generated files.

    The Framework folder (Types, Framing, Profiles, Sdk core) and all generated
    message/SdkInterface files are always included. The Transports/ folder is
    always copied; transport implementations are excluded from compilation by
    default and enabled individually at build time:

      dotnet build -p:IncludeSerialTransport=true    # Serial (System.IO.Ports)
      dotnet build -p:IncludeNetCoreServer=true      # TCP, UDP, WebSocket (NetCoreServer)

    Both flags can be combined. The target framework defaults to net8.0 and can
    be overridden via a Directory.Build.props file in the consuming project:

      <Project>
        <PropertyGroup>
          <TargetFramework>net6.0</TargetFramework>
        </PropertyGroup>
      </Project>
    """
    project_content = f'''<Project Sdk="Microsoft.NET.Sdk">

  <!-- Core library settings -->
  <PropertyGroup>
    <TargetFrameworks>net8.0;net9.0;net10.0</TargetFrameworks>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>{namespace}</RootNamespace>
    <LangVersion>latest</LangVersion>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <IncludeSerialTransport Condition="'$(IncludeSerialTransport)' == ''">false</IncludeSerialTransport>
    <IncludeNetCoreServer Condition="'$(IncludeNetCoreServer)' == ''">false</IncludeNetCoreServer>
  </PropertyGroup>

  <!-- NuGet package metadata
       Override these at pack time:  dotnet pack -p:Version=1.2.3 -p:PackageId=MyMessages
       Or set them in a Directory.Build.props in the consuming repository. -->
  <PropertyGroup>
    <IsPackable>true</IsPackable>
    <PackageId Condition="'$(PackageId)' == ''">{namespace}</PackageId>
    <Version Condition="'$(Version)' == ''">1.0.0</Version>
    <Authors Condition="'$(Authors)' == ''">{namespace}</Authors>
    <Description Condition="'$(Description)' == ''">Generated message serialization library produced by struct-frame.</Description>
    <PackageTags Condition="'$(PackageTags)' == ''">struct-frame;serialization;generated</PackageTags>
    <PackageLicenseExpression Condition="'$(PackageLicenseExpression)' == ''">MIT</PackageLicenseExpression>
    <RepositoryType Condition="'$(RepositoryType)' == ''">git</RepositoryType>
  </PropertyGroup>

  <!-- Reproducible builds and symbol packages -->
  <PropertyGroup>
    <Deterministic>true</Deterministic>
    <ContinuousIntegrationBuild Condition="'$(CI)' == 'true'">true</ContinuousIntegrationBuild>
    <IncludeSymbols>true</IncludeSymbols>
    <SymbolPackageFormat>snupkg</SymbolPackageFormat>
    <EmbedUntrackedSources>true</EmbedUntrackedSources>
    <PublishRepositoryUrl>true</PublishRepositoryUrl>
  </PropertyGroup>

  <!-- Define NETCORESERVER_AVAILABLE when NetCoreServer is enabled -->
  <PropertyGroup Condition="'$(IncludeNetCoreServer)' == 'true'">
    <DefineConstants>$(DefineConstants);NETCORESERVER_AVAILABLE</DefineConstants>
  </PropertyGroup>

  <!-- Source Link: enables IDE/debugger to navigate to source at the exact commit.
       Set $(RepositoryUrl) (e.g. https://github.com/org/repo) to activate. -->
  <ItemGroup Condition="'$(RepositoryUrl)' != '' and '$(RepositoryType)' == 'git'">
    <PackageReference Include="Microsoft.SourceLink.GitHub" Version="8.*" PrivateAssets="All" />
  </ItemGroup>

  <!-- Exclude all transports by default -->
  <ItemGroup>
    <Compile Remove="Framework\\Sdk\\Transports\\**" />
  </ItemGroup>

  <!-- Serial transport: SerialTransport.cs + System.IO.Ports package -->
  <ItemGroup Condition="'$(IncludeSerialTransport)' == 'true'">
    <Compile Include="Framework\\Sdk\\Transports\\SerialTransport.cs" />
    <PackageReference Include="System.IO.Ports" Version="8.*" />
  </ItemGroup>

  <!-- Network transports: TCP, UDP, WebSocket + NetCoreServer package -->
  <ItemGroup Condition="'$(IncludeNetCoreServer)' == 'true'">
    <Compile Include="Framework\\Sdk\\Transports\\TcpTransport.cs" />
    <Compile Include="Framework\\Sdk\\Transports\\UdpTransport.cs" />
    <Compile Include="Framework\\Sdk\\Transports\\WebSocketTransport.cs" />
    <PackageReference Include="NetCoreServer" Version="8.*" />
  </ItemGroup>

</Project>
'''
    return project_content


def main():

    args = parser.parse_args()

    # Normal mode requires a filename
    if not args.filename:
        print("Error: filename is required")
        parser.print_help()
        return

    parseFile(args.filename)

    # If validate mode is specified, skip build argument check and file generation
    if args.validate:
        print("Running in validate mode - no files will be generated")
    elif (not args.build_c and not args.build_ts and not args.build_js and not args.build_py and not args.build_cpp and not args.build_csharp and not args.build_gql and not args.build_rust):
        print("Select at least one build argument")
        return

    valid = False
    try:
        valid = validate_packages(args.debug)
    except RecursionError as err:
        print(
            f'Recursion Error. Messages most likely have a cyclical dependancy. Check Message: {current_error_message} and Field: {current_error_field}')
        return

    if not valid:
        print("Validation failed")
        return

    if args.validate:
        # In validate mode, only perform validation - no file generation
        print("Validation successful")
        if args.debug:
            printPackages()
        return

    # Compute generation hash and check if regeneration is needed
    current_hash = compute_generation_hash(args, packages)
    hash_file_path = get_hash_file_path(args)
    previous_hash = read_previous_hash(hash_file_path)

    if not args.force and previous_hash == current_hash:
        print("Generation skipped: no changes detected (hash matches previous generation)")
        print(f"  Hash file: {hash_file_path}")
        print("  Use --force to regenerate anyway")
        return

    if args.debug:
        if previous_hash is None:
            print(f"No previous hash found at {hash_file_path}")
        elif previous_hash != current_hash:
            print(
                f"Hash changed: {previous_hash[:16]}... -> {current_hash[:16]}...")

    # Normal mode: generate files
    files = {}
    if (args.build_c):
        files.update(generateCFileStrings(
            args.c_path[0], equality=args.equality, generate_tests=args.generate_tests))

    if (args.build_ts):
        files.update(generateTsFileStrings(
            args.ts_path[0], equality=args.equality, generate_tests=args.generate_tests))

    if (args.build_js):
        files.update(generateJsFileStrings(
            args.js_path[0], equality=args.equality, generate_tests=args.generate_tests))

    if (args.build_py):
        files.update(generatePyFileStrings(
            args.py_path[0], equality=args.equality, generate_tests=args.generate_tests))

    if (args.build_cpp):
        files.update(generateCppFileStrings(
            args.cpp_path[0], equality=args.equality, generate_tests=args.generate_tests))

    if (args.build_csharp):
        files.update(generateCSharpFileStrings(args.csharp_path[0],
                                               equality=args.equality,
                                               namespace=args.csharp_namespace[0],
                                               generate_tests=args.generate_tests))

    if (args.build_gql):
        from struct_frame.gql_gen import _PACKAGE_DIRECTIVE_DEF
        for key, value in packages.items():
            name = os.path.join(args.gql_path[0], value.name + '.graphql')
            data = ''.join(FileGqlGen.generate(value))
            files[name] = data

        # Generate a stitched schema.graphql that combines all packages into
        # one document with extend-based merging.  Each per-package file is
        # included via a comment header so tooling can trace provenance.
        stitched_parts = [
            f'# Stitched schema — generated by struct-frame {get_version()}\n',
            f'# Contains all packages: {", ".join(sorted(packages.keys()))}\n\n',
            _PACKAGE_DIRECTIVE_DEF + '\n\n',
        ]
        query_fields = []
        for key, value in packages.items():
            stitched_parts.append(f'# --- Package: {value.name} ---\n')
            # Re-emit enum and message types (without the per-file directive def)
            from struct_frame.gql_gen import EnumGqlGen, MessageGqlGen, pascal_case as _pc
            for _, enum in value.enums.items():
                stitched_parts.append(
                    EnumGqlGen.generate(enum).rstrip() + '\n\n')
            for _, msg in value.sortedMessages().items():
                stitched_parts.append(MessageGqlGen.generate(
                    value, msg).rstrip() + '\n\n')
            for _, msg in value.sortedMessages().items():
                type_name = f'{_pc(value.name)}{msg.name}'
                query_fields.append(f'  {msg.name}: {type_name}')
        if query_fields:
            stitched_parts.append('type Query {\n')
            stitched_parts.append('\n'.join(query_fields) + '\n')
            stitched_parts.append('}\n')
        files[os.path.join(args.gql_path[0], 'schema.graphql')
              ] = ''.join(stitched_parts)

    if (args.build_rust):
        files.update(generateRustFileStrings(
            args.rust_path[0], equality=args.equality))

    # Generate LSP type catalog (single language-agnostic JSON file)
    lsp_build_flags = {
        'c':      args.build_c,
        'cpp':    args.build_cpp,
        'ts':     args.build_ts,
        'js':     args.build_js,
        'py':     args.build_py,
        'gql':    args.build_gql,
        'csharp': args.build_csharp,
        'rust':   args.build_rust,
    }
    lsp_paths = {
        'c':      args.c_path[0],
        'cpp':    args.cpp_path[0],
        'ts':     args.ts_path[0],
        'js':     args.js_path[0],
        'py':     args.py_path[0],
        'gql':    args.gql_path[0],
        'csharp': args.csharp_path[0],
        'rust':   args.rust_path[0],
    }
    files.update(generate_lsp_file_strings(
        args.catalog_path[0], lsp_build_flags, lsp_paths))

    for filename, filedata in files.items():
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        # Retry on transient PermissionError (e.g. Windows file lock from
        # the .NET build server or an IDE holding the .csproj open briefly).
        for _attempt in range(5):
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(filedata)
                break
            except PermissionError:
                if _attempt == 4:
                    raise
                time.sleep(0.5)

    dir_path = os.path.dirname(os.path.realpath(__file__))

    def copy_all_files(src_dir, dst_dir, exclude_dirs=None):
        """Copy all files and directories from src_dir to dst_dir

        Args:
            src_dir: Source directory
            dst_dir: Destination directory  
            exclude_dirs: List of directory names to exclude at any level (e.g., ['struct_frame_sdk', 'Transports'])
        """
        if exclude_dirs is None:
            exclude_dirs = []

        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        if os.path.exists(src_dir):
            ignore_fn = shutil.ignore_patterns(
                *exclude_dirs) if exclude_dirs else None
            for item in os.listdir(src_dir):
                # Skip excluded directories
                if item in exclude_dirs:
                    continue

                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                if os.path.isdir(src_path):
                    # Recursively copy directories
                    shutil.copytree(src_path, dst_path,
                                    dirs_exist_ok=True, ignore=ignore_fn)
                elif os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)

    def copy_sdk_files(src_dir, dst_dir, embedded=False, include_asio=False):
        """Copy SDK files (struct_frame_sdk directory)

        Args:
            src_dir: Source boilerplate directory
            dst_dir: Destination directory
            embedded: If True, copy only embedded-safe files (no ASIO)
            include_asio: If True, include ASIO files for full SDK (default: False)
        """
        sdk_src = os.path.join(src_dir, "struct_frame_sdk")
        sdk_dst = os.path.join(dst_dir, "struct_frame_sdk")

        # Handle PascalCase naming for C# boilerplate
        if not os.path.exists(sdk_src):
            sdk_src = os.path.join(src_dir, "Sdk")
            sdk_dst = os.path.join(dst_dir, "Sdk")

        if not os.path.exists(sdk_src):
            return

        if not os.path.exists(sdk_dst):
            os.makedirs(sdk_dst)

        # Determine which files to exclude
        exclude_items = []

        # For C++, handle embedded vs full SDK differently
        if 'cpp' in src_dir:
            if embedded or not include_asio:
                # Exclude ASIO and network transports for embedded SDK or when ASIO not requested
                exclude_items = ['asio.hpp', 'asio', 'asio-repo',
                                 'network_transports.hpp', 'sdk.hpp']

        # Copy SDK files with exclusions
        for item in os.listdir(sdk_src):
            if item in exclude_items:
                continue
            src_path = os.path.join(sdk_src, item)
            dst_path = os.path.join(sdk_dst, item)

            # Skip broken symlinks
            if os.path.islink(src_path) and not os.path.exists(os.path.realpath(src_path)):
                continue

            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

    # Copy all boilerplate files (excluding SDK by default)
    # SDK is handled separately below based on --sdk or --sdk_embedded flags
    exclude_sdk = ['struct_frame_sdk', 'Sdk']

    if (args.build_c):
        copy_all_files(
            os.path.join(dir_path, "boilerplate/c"),
            args.c_path[0], exclude_sdk)

    if (args.build_ts):
        copy_all_files(
            os.path.join(dir_path, "boilerplate/ts"),
            args.ts_path[0], exclude_sdk)

    if (args.build_js):
        copy_all_files(
            os.path.join(dir_path, "boilerplate/js"),
            args.js_path[0], exclude_sdk)

    if (args.build_py):
        copy_all_files(
            os.path.join(dir_path, "boilerplate/py"),
            args.py_path[0], exclude_sdk)

    if (args.build_cpp):
        copy_all_files(
            os.path.join(dir_path, "boilerplate/cpp"),
            args.cpp_path[0], exclude_sdk)

    if (args.build_csharp):
        # C# boilerplate uses Framework/ structure.
        # Transports/ is always copied; the .csproj controls conditional
        # compilation of transport implementations at build time:
        #   -p:IncludeSerialTransport=true   → Serial (System.IO.Ports)
        #   -p:IncludeNetCoreServer=true     → TCP, UDP, WebSocket (NetCoreServer)
        copy_all_files(
            os.path.join(dir_path, "boilerplate/csharp"),
            args.csharp_path[0], [])

    if (args.build_rust):
        # Exclude lib.rs and Cargo.toml from boilerplate copy - they are generated
        copy_all_files(
            os.path.join(dir_path, "boilerplate/rust"),
            args.rust_path[0], exclude_sdk + ['lib.rs', 'Cargo.toml'])

    # Copy SDK files if requested
    if args.sdk or args.sdk_embedded:
        embedded_only = args.sdk_embedded and not args.sdk

        if args.build_c:
            # C doesn't have SDK yet
            pass

        if args.build_ts:
            copy_sdk_files(
                os.path.join(dir_path, "boilerplate/ts"),
                args.ts_path[0], embedded_only)

        if args.build_js:
            copy_sdk_files(
                os.path.join(dir_path, "boilerplate/js"),
                args.js_path[0], embedded_only)

        if args.build_py:
            copy_sdk_files(
                os.path.join(dir_path, "boilerplate/py"),
                args.py_path[0], embedded_only)

        if args.build_cpp:
            # ASIO is only included for C++ when full SDK is requested (not embedded)
            include_asio = args.sdk and not args.sdk_embedded
            copy_sdk_files(
                os.path.join(dir_path, "boilerplate/cpp"),
                args.cpp_path[0], embedded_only, include_asio=include_asio)

    # No boilerplate for GraphQL currently

    # Write generation hash after successful generation
    write_generation_hash(hash_file_path, current_hash)
    if args.debug:
        print(f"Generation hash written to {hash_file_path}")

    if args.debug:
        printPackages()
    print("Struct Frame successfully completed")


if __name__ == '__main__':
    main()
