#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;


import os
import sys
import shutil
from struct_frame import FileCGen
from struct_frame import FileTsGen
from struct_frame import FileJsGen
from struct_frame import FilePyGen
from struct_frame import FileGqlGen
from struct_frame import FileCppGen
from struct_frame import FileCSharpGen
from proto_schema_parser.parser import Parser
from proto_schema_parser import ast
from proto_schema_parser.ast import FieldCardinality

import argparse

recErrCurrentField = ""
recErrCurrentMessage = ""

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


class Enum:
    def __init__(self, package, comments):
        self.name = None
        self.data = {}
        self.size = 1
        self.comments = comments
        self.package = package
        self.isEnum = True

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

    def validate(self, currentPackage, packages, debug=False):
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
        self.fieldType = None
        self.isDefaultType = False
        self.size = 0
        self.validated = False
        self.comments = comments
        self.package = package
        self.isEnum = False
        self.flatten = False
        self.is_array = False
        self.size_option = None   # Fixed size using [size=X]
        self.max_size = None      # Variable size using [max_size=X]
        # Element size for repeated string arrays [element_size=X]
        self.element_size = None

    def parse(self, field):
        self.name = field.name
        self.fieldType = field.type

        # Check if this is a repeated field (array)
        if hasattr(field, 'cardinality') and field.cardinality == FieldCardinality.REPEATED:
            self.is_array = True

        if self.fieldType in default_types:
            self.isDefaultType = True
            self.size = default_types[self.fieldType]["size"]
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
                            if self.size_option <= 0 or self.size_option > 255:
                                print(
                                    f"Invalid size {self.size_option} for field {self.name}, must be 1-255")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid size value {ovalue} for field {self.name}, must be an integer")
                            return False
                    elif lname in ('max_size', '(sf.max_size)', '(struct_frame.max_size)'):
                        # Variable size for arrays or strings
                        try:
                            self.max_size = int(ovalue)
                            if self.max_size <= 0 or self.max_size > 255:
                                print(
                                    f"Invalid max_size {self.max_size} for field {self.name}, must be 1-255")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid max_size value {ovalue} for field {self.name}, must be an integer")
                            return False
                    elif lname in ('element_size', '(sf.element_size)', '(struct_frame.element_size)'):
                        # Individual element size for repeated string arrays
                        try:
                            self.element_size = int(ovalue)
                            if self.element_size <= 0 or self.element_size > 255:
                                print(
                                    f"Invalid element_size {self.element_size} for field {self.name}, must be 1-255")
                                return False
                        except (ValueError, TypeError):
                            print(
                                f"Invalid element_size value {ovalue} for field {self.name}, must be an integer")
                            return False
        except Exception:
            pass
        return True

    def validate(self, currentPackage, packages, debug=False):

        global recErrCurrentField
        recErrCurrentField = self.name
        if not self.validated:
            ret = currentPackage.findFieldType(self.fieldType, packages)

            if ret:
                if ret.validate(currentPackage, packages, debug):
                    self.isEnum = ret.isEnum
                    self.validated = True
                    base_size = ret.size
                else:
                    print(
                        f"Failed to validate Field: {self.name} of Type: {self.fieldType} in Package: {currentPackage.name}")
                    return False
            else:
                print(
                    f"Failed to find Field: {self.name} of Type: {self.fieldType} in Package: {currentPackage.name}")
                return False
        else:
            base_size = self.size

        # Calculate size for arrays and strings
        if self.is_array:
            if self.fieldType == "string":
                # String arrays need both array size AND individual element size
                if self.element_size is None:
                    print(
                        f"String array field {self.name} missing required element_size option")
                    return False

                if self.size_option is not None:
                    # Fixed string array: size_option strings, each element_size bytes
                    self.size = self.size_option * self.element_size
                elif self.max_size is not None:
                    # Variable string array: 1 byte count + max_size strings of element_size bytes each
                    self.size = 1 + (self.max_size * self.element_size)
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
                    # Variable array: 1 byte for count + max space
                    self.size = 1 + (base_size * self.max_size)
                else:
                    print(
                        f"Array field {self.name} missing required size or max_size option")
                    return False
        elif self.fieldType == "string":
            if self.size_option is not None:
                # Fixed string: exactly size_option characters
                self.size = self.size_option
            elif self.max_size is not None:
                # Variable string: 1 byte length + max characters
                self.size = 1 + self.max_size
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
                if self.fieldType == "string":
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
            elif self.fieldType == "string":
                # Regular strings
                if self.size_option is not None:
                    array_info = f", fixed_string size={self.size_option}"
                elif self.max_size is not None:
                    array_info = f", variable_string max_size={self.max_size}"
            print(
                f"  Field {self.name}: type={self.fieldType}, is_array={self.is_array}{array_info}, calculated_size={self.size}")

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
        elif self.fieldType == "string":
            if self.size_option is not None:
                array_info = f", String[size={self.size_option}]"
            elif self.max_size is not None:
                array_info = f", String[max_size={self.max_size}]"
        output = output + \
            f"Field: {self.name}, Type:{self.fieldType}, Size:{self.size}{array_info}"
        return output


class Message:
    def __init__(self, package, comments):
        self.id = None
        self.size = 0
        self.name = None
        self.fields = {}
        self.validated = False
        self.comments = comments
        self.package = package
        self.isEnum = False

    def parse(self, msg):
        self.name = msg.name
        comments = []
        for e in msg.elements:
            if type(e) == ast.Option:
                if e.name == "msgid":
                    if self.id:
                        raise Exception(f"Redefinition of msg_id for {e.name}")
                    self.id = e.value
            elif type(e) == ast.Comment:
                comments.append(e.text)
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"Field Redclaration")
                    return False
                self.fields[e.name] = Field(self.package, comments)
                comments = []
                if not self.fields[e.name].parse(e):
                    return False
        return True

    def validate(self, currentPackage, packages, debug=False):
        if self.validated:
            return True

        global recErrCurrentMessage
        recErrCurrentMessage = self.name
        for key, value in self.fields.items():
            if not value.validate(currentPackage, packages, debug):
                print(
                    f"Failed To validate Field: {key}, in Message {self.name}\n")
                return False
            self.size = self.size + value.size

        # Flatten collision detection: if a field is marked as flatten and is a message,
        # ensure none of the child field names collide with fields in this message.
        parent_field_names = set(self.fields.keys())
        for key, value in self.fields.items():
            if getattr(value, 'flatten', False):
                # Only meaningful for non-default, non-enum message types
                if value.isDefaultType or value.isEnum:
                    # Flatten has no effect on primitives/enums; skip
                    continue
                child = currentPackage.findFieldType(value.fieldType)
                if not child or getattr(child, 'isEnum', False) or not hasattr(child, 'fields'):
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
            elif value.fieldType == "string":
                # Strings must have size or max_size specified
                if value.size_option is None and value.max_size is None:
                    print(
                        f"String field {key} in Message {self.name}: must specify size or max_size option")
                    return False
            elif value.max_size is not None or value.size_option is not None or value.element_size is not None:
                print(
                    f"Field {key} in Message {self.name}: size/max_size/element_size options can only be used with repeated fields or strings")
                return False

        self.validated = True
        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        output = output + \
            f"Message: {self.name}, Size: {self.size}, ID: {self.id}\n"

        for key, value in self.fields.items():
            output = output + value.__str__() + "\n"
        return output


class Package:
    def __init__(self, name):
        self.name = name
        self.enums = {}
        self.messages = {}
        self.package_id = None  # Optional package ID for multi-package support
        self.imported_packages = []  # List of package names this package imports

    def addEnum(self, enum, comments):
        self.comments = comments
        if enum.name in self.enums:
            print(f"Enum Redclaration")
            return False
        self.enums[enum.name] = Enum(self.name, comments)
        return self.enums[enum.name].parse(enum)

    def addMessage(self, message, comments):
        if message.name in self.messages:
            print(f"Message Redclaration")
            return False
        self.messages[message.name] = Message(self.name, comments)
        return self.messages[message.name].parse(message)

    def validatePackage(self, allPackages, debug=False):
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

        for key, value in self.messages.items():
            if not value.validate(self, allPackages, debug):
                print(
                    f"Failed To validate Message: {key}, in Package {self.name}\n")
                return False

        return True

    def findFieldType(self, name, allPackages=None):
        # First search in this package
        for key, value in self.enums.items():
            if value.name == name:
                return value

        for key, value in self.messages.items():
            if value.name == name:
                return value
        
        # Then search in imported packages
        if allPackages:
            for imported_pkg_name in self.imported_packages:
                if imported_pkg_name in allPackages:
                    imported_pkg = allPackages[imported_pkg_name]
                    result = imported_pkg.findFieldType(name, None)  # Don't recurse imports
                    if result:
                        return result
        
        return None

    def sortedMessages(self):
        # Need to sort messages to ensure no out of order dependencies.
        return self.messages

    def __str__(self):
        output = "Package: " + self.name + "\n"
        for key, value in self.enums.items():
            output = output + value.__str__() + "\n"
        for key, value in self.messages.items():
            output = output + value.__str__() + "\n"
        return output


packages = {}
processed_file = []
required_file = []

parser = argparse.ArgumentParser(
    prog='struct_frame',
    description='Message serialization and header generation program')

parser.add_argument('filename', nargs='?', default=None,
                    help='Proto file to process (required unless --regenerate_boiler_plate is used)')
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
parser.add_argument('--frame_formats', nargs=1, type=str,
                    help='Proto file containing frame format definitions to generate frame parsers')
parser.add_argument('--regenerate_boiler_plate', action='store_true',
                    help='Regenerate boilerplate code. Uses --frame_formats file if provided, '
                         'otherwise uses default frame_formats.proto')


def parseFile(filename):
    # Avoid processing the same file twice
    abs_filename = os.path.abspath(filename)
    if abs_filename in processed_file:
        return True
    
    processed_file.append(abs_filename)
    
    # Get the directory of the current file for resolving relative imports
    file_dir = os.path.dirname(abs_filename)
    
    with open(filename, "r") as f:
        result = Parser().parse(f.read())

        foundPackage = False
        package_name = ""
        comments = []
        imports = []  # Track imports for this file

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

            elif (type(e) == ast.Import):
                # Handle import statements
                imports.append(e.name)
                
            elif (type(e) == ast.Option):
                # Handle file-level options like package_id
                if e.name == "package_id":
                    if foundPackage and package_name in packages:
                        if packages[package_name].package_id is not None:
                            print(f"Warning: package_id redefined for package {package_name}")
                        packages[package_name].package_id = e.value

            elif (type(e) == ast.Enum):
                if not packages[package_name].addEnum(e, comments):
                    print(
                        f"Enum Error in Package: {package_name}  FileName: {filename} EnumName: {e.name}")
                    return False
                comments = []

            elif (type(e) == ast.Message):
                if not packages[package_name].addMessage(e, comments):
                    print(
                        f"Message Error in Package: {package_name}  FileName: {filename} MessageName: {e.name}")
                    return False
                comments = []

            elif (type(e) == ast.Comment):
                comments.append(e.text)
        
        # Process imports after we know the package name
        if foundPackage and imports:
            for import_name in imports:
                # Resolve import path relative to current file
                import_path = os.path.join(file_dir, import_name)
                if not os.path.exists(import_path):
                    print(f"Error: Cannot find imported file '{import_name}' (looked at {import_path})")
                    return False
                
                # Parse the imported file
                if not parseFile(import_path):
                    print(f"Error: Failed to parse imported file '{import_name}'")
                    return False
                
                # Find the package name of the imported file and add to imports list
                # We need to read the imported file to find its package name
                with open(import_path, "r") as import_file:
                    import_result = Parser().parse(import_file.read())
                    for elem in import_result.file_elements:
                        if type(elem) == ast.Package:
                            imported_pkg_name = elem.name
                            if imported_pkg_name not in packages[package_name].imported_packages:
                                packages[package_name].imported_packages.append(imported_pkg_name)
                            break
        
        return True


def validatePackages(debug=False):
    # Check if multiple packages exist and ensure they have package IDs
    if len(packages) > 1:
        package_ids = {}
        for key, value in packages.items():
            if value.package_id is None:
                print(f"Error: Package '{key}' does not have a package_id assigned. "
                      f"When compiling multiple packages, each package must have a unique package_id.")
                return False
            
            # Check for duplicate package IDs
            if value.package_id in package_ids:
                print(f"Error: Duplicate package_id {value.package_id} found in packages "
                      f"'{key}' and '{package_ids[value.package_id]}'")
                return False
            
            package_ids[value.package_id] = key
    
    for key, value in packages.items():
        if not value.validatePackage(packages, debug):
            print(f"Failed To Validate Package: {key}")
            return False

    return True


def printPackages():
    for key, value in packages.items():
        print(value)


def generateCFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.h")
        data = ''.join(FileCGen.generate(value))
        out[name] = data

    return out


def generateTsFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.ts")
        data = ''.join(FileTsGen.generate(value))
        out[name] = data
    return out


def generateJsFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.js")
        data = ''.join(FileJsGen.generate(value))
        out[name] = data
    return out


def generatePyFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + "_sf.py")
        data = ''.join(FilePyGen.generate(value))
        out[name] = data
    return out


def generateCppFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.hpp")
        data = ''.join(FileCppGen.generate(value))
        out[name] = data
    return out


def generateCSharpFileStrings(path):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".sf.cs")
        data = ''.join(FileCSharpGen.generate(value))
        out[name] = data
    return out


def generateFrameParserFiles(frame_formats_file, c_path, ts_path, js_path, py_path, cpp_path, csharp_path,
                             build_c, build_ts, build_js, build_py, build_cpp, build_csharp):
    """Generate frame parser files from frame format definitions"""
    from struct_frame.frame_format import parse_frame_formats
    from struct_frame.frame_parser_c_gen import generate_c_frame_parsers
    from struct_frame.frame_parser_py_gen import generate_py_frame_parsers
    from struct_frame.frame_parser_ts_gen import generate_ts_frame_parsers, generate_js_frame_parsers
    from struct_frame.frame_parser_cpp_gen import generate_cpp_frame_parsers
    from struct_frame.frame_parser_csharp_gen import generate_csharp_frame_parsers

    formats = parse_frame_formats(frame_formats_file)
    files = {}

    if build_c:
        name = os.path.join(c_path, "frame_parsers_gen.h")
        files[name] = generate_c_frame_parsers(formats)

    if build_ts:
        name = os.path.join(ts_path, "frame_parsers_gen.ts")
        files[name] = generate_ts_frame_parsers(formats)

    if build_js:
        name = os.path.join(js_path, "frame_parsers_gen.js")
        files[name] = generate_js_frame_parsers(formats)

    if build_py:
        name = os.path.join(py_path, "frame_parsers_gen.py")
        files[name] = generate_py_frame_parsers(formats)

    if build_cpp:
        name = os.path.join(cpp_path, "frame_parsers_gen.hpp")
        files[name] = generate_cpp_frame_parsers(formats)

    if build_csharp:
        name = os.path.join(csharp_path, "FrameParsersGen.cs")
        files[name] = generate_csharp_frame_parsers(formats)

    return files


def main():
    from struct_frame.generate_boilerplate import update_src_boilerplate, generate_boilerplate_to_paths, get_default_frame_formats_path

    # Reset global state at the start
    global packages, processed_file, required_file
    packages = {}
    processed_file = []
    required_file = []

    args = parser.parse_args()

    # Handle --regenerate_boiler_plate mode
    if args.regenerate_boiler_plate:
        # Determine which frame_formats file to use
        if args.frame_formats:
            frame_formats_file = args.frame_formats[0]
            print(f"Regenerating boilerplate from: {frame_formats_file}")
            # Generate to boilerplate directory using custom frame_formats file
            from struct_frame.generate_boilerplate import get_boilerplate_dir, write_file
            boilerplate_dir = get_boilerplate_dir()

            if not os.path.exists(frame_formats_file):
                print(
                    f"Error: frame_formats file not found at {frame_formats_file}")
                return

            files = generate_boilerplate_to_paths(
                frame_formats_file,
                c_path=os.path.join(boilerplate_dir, 'c'),
                ts_path=os.path.join(boilerplate_dir, 'ts'),
                js_path=os.path.join(boilerplate_dir, 'js'),
                py_path=os.path.join(boilerplate_dir, 'py'),
                cpp_path=os.path.join(boilerplate_dir, 'cpp')
            )

            for path, content in files.items():
                write_file(path, content)

            print(f"Successfully regenerated {len(files)} boilerplate files")
        else:
            # Use default frame_formats.proto
            print("Regenerating boilerplate from default frame_formats.proto")
            success = update_src_boilerplate()
            if not success:
                print("Failed to regenerate boilerplate")
                return
        return

    # Normal mode requires a filename
    if not args.filename:
        print("Error: filename is required unless --regenerate_boiler_plate is used")
        parser.print_help()
        return

    parseFile(args.filename)

    # If validate mode is specified, skip build argument check and file generation
    if args.validate:
        print("Running in validate mode - no files will be generated")
    elif (not args.build_c and not args.build_ts and not args.build_js and not args.build_py and not args.build_cpp and not args.build_csharp and not args.build_gql):
        print("Select at least one build argument")
        return

    valid = False
    try:
        valid = validatePackages(args.debug)
    except RecursionError as err:
        print(
            f'Recursion Error. Messages most likely have a cyclical dependancy. Check Message: {recErrCurrentMessage} and Field: {recErrCurrentField}')
        sys.exit(1)

    if not valid:
        print("Validation failed")
        sys.exit(1)

    if args.validate:
        # In validate mode, only perform validation - no file generation
        print("Validation successful")
        if args.debug:
            printPackages()
        return

    # Normal mode: generate files
    files = {}
    if (args.build_c):
        files.update(generateCFileStrings(args.c_path[0]))

    if (args.build_ts):
        files.update(generateTsFileStrings(args.ts_path[0]))

    if (args.build_js):
        files.update(generateJsFileStrings(args.js_path[0]))

    if (args.build_py):
        files.update(generatePyFileStrings(args.py_path[0]))

    if (args.build_cpp):
        files.update(generateCppFileStrings(args.cpp_path[0]))

    if (args.build_csharp):
        files.update(generateCSharpFileStrings(args.csharp_path[0]))

    if (args.build_gql):
        for key, value in packages.items():
            name = os.path.join(args.gql_path[0], value.name + '.graphql')
            data = ''.join(FileGqlGen.generate(value))
            files[name] = data

    # Generate frame parsers if frame_formats proto is provided
    if args.frame_formats:
        frame_parser_files = generateFrameParserFiles(
            args.frame_formats[0],
            args.c_path[0], args.ts_path[0], args.js_path[0],
            args.py_path[0], args.cpp_path[0], args.csharp_path[0],
            args.build_c, args.build_ts, args.build_js,
            args.build_py, args.build_cpp, args.build_csharp
        )
        files.update(frame_parser_files)

    for filename, filedata in files.items():
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(filedata)

    dir_path = os.path.dirname(os.path.realpath(__file__))

    # When --frame_formats is provided, the frame parser boilerplate files are
    # replaced by the generated frame parsers, so we only copy utility files.
    # Otherwise, copy all boilerplate files (now multi-file structure).
    
    # Utility files that should be copied even when generating custom frame parsers
    # (files that are not frame format specific)
    utility_files = {
        'c': ['frame_base.h'],
        'cpp': ['frame_base.hpp'],
        'ts': ['struct_base.ts', 'struct_frame.ts', 'struct_frame_types.ts', 'frame_base.ts'],
        'js': ['struct_base.js', 'struct_frame.js', 'struct_frame_types.js', 'frame_base.js'],
        'py': [],  # __init__.py will be generated with the custom frame formats
        'csharp': ['FrameBase.cs']
    }
    
    def copy_files_list(src_dir, dst_dir, files_to_copy):
        """Copy specified files from src_dir to dst_dir"""
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for item in files_to_copy:
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(dst_dir, item)
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)

    def copy_all_files(src_dir, dst_dir):
        """Copy all files from src_dir to dst_dir"""
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        if os.path.exists(src_dir):
            for item in os.listdir(src_dir):
                src_path = os.path.join(src_dir, item)
                dst_path = os.path.join(dst_dir, item)
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)

    if args.frame_formats:
        # When generating custom frame parsers, only copy utility files
        # (the generated frame parsers will be written separately)
        if args.build_c:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/c"),
                args.c_path[0], utility_files['c'])

        if args.build_ts:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/ts"),
                args.ts_path[0], utility_files['ts'])

        if args.build_js:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/js"),
                args.js_path[0], utility_files['js'])

        if args.build_py:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/py"),
                args.py_path[0], utility_files['py'])

        if args.build_cpp:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/cpp"),
                args.cpp_path[0], utility_files['cpp'])

        if args.build_csharp:
            copy_files_list(
                os.path.join(dir_path, "boilerplate/csharp"),
                args.csharp_path[0], utility_files['csharp'])
    else:
        # Copy all boilerplate files (multi-file structure)
        if (args.build_c):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/c"),
                args.c_path[0])

        if (args.build_ts):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/ts"),
                args.ts_path[0])

        if (args.build_js):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/js"),
                args.js_path[0])

        if (args.build_py):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/py"),
                args.py_path[0])

        if (args.build_cpp):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/cpp"),
                args.cpp_path[0])

        if (args.build_csharp):
            copy_all_files(
                os.path.join(dir_path, "boilerplate/csharp"),
                args.csharp_path[0])

    # No boilerplate for GraphQL currently

    if args.debug:
        printPackages()
    print("Struct Frame successfully completed")


if __name__ == '__main__':
    main()
