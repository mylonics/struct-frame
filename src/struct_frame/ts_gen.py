#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
TypeScript code generator for struct-frame.

This module generates TypeScript code for struct serialization using
ES6 module syntax (import/export).
"""

from struct_frame import version, NamingStyleC, pascalCase
from struct_frame.ts_js_base import (
    common_types,
    common_typed_array_methods,
    ts_array_types,
    BaseFieldGen,
    BaseEnumGen,
    # New class-based generation utilities
    TYPE_SIZES,
    TS_TYPE_ANNOTATIONS,
    TS_ARRAY_TYPE_ANNOTATIONS,
    READ_METHODS,
    WRITE_METHODS,
    READ_ARRAY_METHODS,
    WRITE_ARRAY_METHODS,
    calculate_field_layout,
    FieldInfo,
)
import time

StyleC = NamingStyleC()

# Use shared type mappings
ts_types = common_types
ts_typed_array_methods = common_typed_array_methods


class EnumTsGen():
    @staticmethod
    def generate(field, packageName):
        leading_comment = field.comments
        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '%s\n' % c

        # Use PascalCase for both package and enum name (TypeScript convention)
        result += 'export enum %s%s' % (packageName, field.name)

        result += ' {\n'

        enum_length = len(field.data)
        enum_values = []
        for index, (d) in enumerate(field.data):
            leading_comment = field.data[d][1]

            if leading_comment:
                for c in leading_comment:
                    enum_values.append(c)

            comma = ","
            if index == enum_length - 1:
                # last enum member should not end with a comma
                comma = ""

            enum_value = "    %s = %d%s" % (
                StyleC.enum_entry(d), field.data[d][0], comma)

            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        result += '\n}'

        return result


class FieldTsGen():
    """TypeScript field generator using shared base logic."""

    @staticmethod
    def generate(field, packageName):
        """Generate TypeScript field definition using shared base."""
        return BaseFieldGen.generate(
            field, packageName, ts_types, ts_typed_array_methods
        )


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageTsGen():
    @staticmethod
    def generate(msg, packageName, package=None):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        package_msg_name = '%s%s' % (packageName, msg.name)

        result += 'export const %s = new Struct(\'%s\')' % (
            package_msg_name, package_msg_name)
        
        # Add message ID if present
        if msg.id:
            result += '.msgId(%d)' % msg.id
        
        # Add magic numbers if present
        if msg.id is not None and msg.magic_bytes:
            result += '.magic(%d, %d)' % (msg.magic_bytes[0], msg.magic_bytes[1])

        result += '\n'

        size = 1
        if not msg.fields and not msg.oneofs:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += '    .UInt8(\'dummy_field\');'
        else:
            size = msg.size

        # Generate regular fields
        result += '\n'.join([FieldTsGen.generate(f, packageName)
                            for key, f in msg.fields.items()])
        
        # Generate oneofs - add discriminator and allocate union size
        for key, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                # Always use UInt16LE since message IDs can be up to 65535
                result += f'\n    .UInt16LE(\'{oneof.name}_discriminator\')'
            # Allocate space for the union (largest member size)
            # Use a byte array to represent the union storage
            result += f'\n    .ByteArray(\'{oneof.name}_data\', {oneof.size})'
        
        result += '\n    .compile();\n'
        return result + '\n'

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class MessageTsClassGen():
    """Generate TypeScript message classes that extend MessageBase."""
    
    @staticmethod
    def generate(msg, packageName, package, packages, equality=False):
        """Generate a class-based message definition."""
        leading_comment = msg.comments
        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        package_msg_name = '%s%s' % (packageName, msg.name)
        
        # Calculate field layout with offsets
        fields = calculate_field_layout(msg, package, packages)
        total_size = msg.size
        
        # Generate init interface for this message (only if there are fields)
        if fields:
            result += MessageTsClassGen._generate_init_interface(package_msg_name, fields)
        
        # Generate class declaration
        result += f'export class {package_msg_name} extends MessageBase {{\n'
        
        # Static properties
        result += f'  static readonly _size: number = {total_size};\n'
        if msg.id:
            result += f'  static readonly _msgid: number = {msg.id};\n'
        
        # Add magic numbers for checksum
        if msg.id is not None and msg.magic_bytes:
            result += f'  static readonly _magic1: number = {msg.magic_bytes[0]}; // Checksum magic (based on field types and positions)\n'
            result += f'  static readonly _magic2: number = {msg.magic_bytes[1]}; // Checksum magic (based on field types and positions)\n'
        
        # Add variable message constants
        if msg.variable:
            result += f'  static readonly _minSize: number = {msg.min_size}; // Minimum size when all variable fields are empty\n'
            result += f'  static readonly _isVariable: boolean = true; // This message uses variable-length encoding\n'
        
        result += '\n'
        
        # Generate constructor that supports init object (only reference Init type if fields exist)
        if fields:
            result += f'  constructor(bufferOrInit?: Buffer | {package_msg_name}Init) {{\n'
            result += f'    super(Buffer.isBuffer(bufferOrInit) ? bufferOrInit : undefined);\n'
            result += f'    if (bufferOrInit && !Buffer.isBuffer(bufferOrInit)) {{\n'
            result += f'      this._applyInit(bufferOrInit as Record<string, unknown>);\n'
            result += f'    }}\n'
            result += f'  }}\n\n'
        else:
            result += f'  constructor(buffer?: Buffer) {{\n'
            result += f'    super(buffer);\n'
            result += f'  }}\n\n'
        
        # Generate getters and setters for each field
        for field_info in fields:
            result += MessageTsClassGen._generate_field_accessors(field_info, package_msg_name, packages)
        
        # Generate equals method if requested
        if equality:
            result += MessageTsClassGen.generate_equals_method(msg, package_msg_name, fields)
        
        # Generate variable message methods if this is a variable message
        if msg.variable:
            result += MessageTsClassGen._generate_variable_methods(msg, package_msg_name, fields)
        
        # Static getSize method
        result += f'  static getSize(): number {{\n'
        result += f'    return {total_size};\n'
        result += f'  }}\n'
        
        result += '}\n'
        return result + '\n'
    
    @staticmethod
    def _generate_variable_methods(msg, package_msg_name, fields):
        """Generate variable-length encoding methods for TypeScript messages."""
        result = ''
        
        # Generate packSize method
        result += f'\n  /**\n'
        result += f'   * Calculate the packed size using variable-length encoding.\n'
        result += f'   * @returns The size in bytes when packed (between _minSize and _size)\n'
        result += f'   */\n'
        result += f'  packSize(): number {{\n'
        result += f'    let size = 0;\n'
        
        for key, field in msg.fields.items():
            name = field.name
            if field.is_array and field.max_size is not None:
                # Variable array - TypeScript uses name_count
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                count_size = 2 if field.max_size > 255 else 1
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.fieldType, (field.size - count_size) // field.max_size)
                result += f'    size += {count_size} + (this.{name}_count * {element_size}); // {name}\n'
            elif field.fieldType == "string" and field.max_size is not None:
                # Variable string - TypeScript uses name_length
                length_size = 2 if field.max_size > 255 else 1
                result += f'    size += {length_size} + this.{name}_length; // {name}\n'
            else:
                result += f'    size += {field.size}; // {name}\n'
        
        result += f'    return size;\n'
        result += f'  }}\n'
        
        # Generate packVariable method
        result += f'\n  /**\n'
        result += f'   * Pack message using variable-length encoding.\n'
        result += f'   * @returns Buffer with packed data (only used bytes)\n'
        result += f'   */\n'
        result += f'  packVariable(): Buffer {{\n'
        result += f'    const size = this.packSize();\n'
        result += f'    const buffer = Buffer.alloc(size);\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = field.name
            field_type = field.fieldType
            if field.is_array and field.max_size is not None:
                # Variable array - TypeScript uses name_count and name_data
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                max_len = field.max_size
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = this.{name}_count;\n'
                result += f'    buffer.writeUInt8({name}Count, offset++);\n'
                
                if field_type not in type_sizes and field_type != "string" and not field.isEnum:
                    # Nested struct array
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      const nested = this.{name}_data[i];\n'
                    result += f'      nested._buffer.copy(buffer, offset);\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                elif field_type == "string":
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      const str = this.{name}_data[i] || \'\';\n'
                    result += f'      buffer.write(str.slice(0, {element_size}), offset);\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                else:
                    # Map types to Buffer API write methods
                    buffer_write_methods = {
                        "int8": "writeInt8", "uint8": "writeUInt8",
                        "int16": "writeInt16LE", "uint16": "writeUInt16LE",
                        "int32": "writeInt32LE", "uint32": "writeUInt32LE",
                        "int64": "writeBigInt64LE", "uint64": "writeBigUInt64LE",
                        "float": "writeFloatLE", "double": "writeDoubleLE",
                        "bool": "writeUInt8",
                    }
                    write_method_name = buffer_write_methods.get(field_type if not field.isEnum else "uint8", "writeUInt8")
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.{write_method_name}(this.{name}_data[i], offset);\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
            elif field_type == "string" and field.max_size is not None:
                # Variable string - copy from internal buffer (string is stored there)
                max_len = field.max_size
                result += f'    // {name}: variable string\n'
                result += f'    const {name}Len = this.{name}_length;\n'
                result += f'    buffer.writeUInt8({name}Len, offset++);\n'
                # Copy string data from internal buffer
                result += f'    this._buffer.copy(buffer, offset, {msg_offset + 1}, {msg_offset + 1} + {name}Len);\n'
                result += f'    offset += {name}Len;\n'
            else:
                # Fixed field - copy from internal buffer
                result += f'    // {name}: fixed size ({field.size} bytes)\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset + field.size});\n'
                result += f'    offset += {field.size};\n'
            msg_offset += field.size
        
        result += f'    return buffer;\n'
        result += f'  }}\n'
        
        # Generate static unpackVariable method
        result += f'\n  /**\n'
        result += f'   * Unpack message from variable-length encoded buffer.\n'
        result += f'   * @param buffer Input buffer with variable-length encoded data\n'
        result += f'   * @returns New instance with unpacked data\n'
        result += f'   */\n'
        result += f'  static unpackVariable(buffer: Buffer): {package_msg_name} {{\n'
        result += f'    const msg = new {package_msg_name}();\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = field.name
            field_type = field.fieldType
            if field.is_array and field.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                max_len = field.max_size
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = Math.min(buffer.readUInt8(offset++), {max_len});\n'
                
                if field_type not in type_sizes and field_type != "string" and not field.isEnum:
                    # Nested struct array - need to set the internal buffer array elements
                    nested_type = '%s%s' % (pascalCase(field.package), field_type)
                    result += f'    // Write count to internal buffer\n'
                    result += f'    msg._buffer.writeUInt8({name}Count, {msg_offset});\n'
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.copy(msg._buffer, {msg_offset + 1} + i * {element_size}, offset, offset + {element_size});\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                elif field_type == "string":
                    result += f'    // Write count to internal buffer\n'
                    result += f'    msg._buffer.writeUInt8({name}Count, {msg_offset});\n'
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.copy(msg._buffer, {msg_offset + 1} + i * {element_size}, offset, offset + {element_size});\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                else:
                    # Primitive array
                    result += f'    // Write count to internal buffer\n'
                    result += f'    msg._buffer.writeUInt8({name}Count, {msg_offset});\n'
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.copy(msg._buffer, {msg_offset + 1} + i * {element_size}, offset, offset + {element_size});\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
            elif field_type == "string" and field.max_size is not None:
                # Variable string
                max_len = field.max_size
                result += f'    // {name}: variable string\n'
                result += f'    const {name}Len = Math.min(buffer.readUInt8(offset++), {max_len});\n'
                result += f'    // Write length to internal buffer\n'
                result += f'    msg._buffer.writeUInt8({name}Len, {msg_offset});\n'
                result += f'    buffer.copy(msg._buffer, {msg_offset + 1}, offset, offset + {name}Len);\n'
                result += f'    offset += {name}Len;\n'
            else:
                # Fixed field
                result += f'    // {name}: fixed size ({field.size} bytes)\n'
                result += f'    buffer.copy(msg._buffer, {msg_offset}, offset, offset + {field.size});\n'
                result += f'    offset += {field.size};\n'
            msg_offset += field.size
        
        result += f'    return msg;\n'
        result += f'  }}\n'
        
        return result
    
    @staticmethod
    def generate_equals_method(msg, package_msg_name, fields):
        """Generate equals() method for equality comparison."""
        result = f'\n  equals(other: {package_msg_name}): boolean {{\n'
        result += f'    if (!(other instanceof {package_msg_name})) {{\n'
        result += f'      return false;\n'
        result += f'    }}\n'
        
        if not fields:
            result += f'    return true;\n'
        else:
            comparisons = []
            for field_info in fields:
                name = field_info.name
                if field_info.is_array:
                    # Arrays need element-by-element comparison or JSON comparison
                    comparisons.append(f'JSON.stringify(this.{name}) === JSON.stringify(other.{name})')
                elif field_info.field_type == 'string':
                    comparisons.append(f'this.{name} === other.{name}')
                elif field_info.is_nested:
                    # Nested messages need recursive comparison
                    comparisons.append(f'JSON.stringify(this.{name}) === JSON.stringify(other.{name})')
                else:
                    # Primitive types
                    comparisons.append(f'this.{name} === other.{name}')
            
            result += f'    return ' + ' &&\n           '.join(comparisons) + ';\n'
        
        result += f'  }}\n'
        return result
    
    @staticmethod
    def _generate_init_interface(class_name, fields):
        """Generate the Init interface for a message class."""
        result = f'export interface {class_name}Init {{\n'
        
        for field_info in fields:
            ts_type = MessageTsClassGen._get_ts_type_for_field(field_info)
            result += f'  {field_info.name}?: {ts_type};\n'
        
        result += '}\n\n'
        return result
    
    @staticmethod
    def _get_ts_type_for_field(field_info):
        """Get the TypeScript type annotation for a field."""
        field_type = field_info.field_type
        
        if field_info.is_array:
            if field_info.is_nested:
                return f'({field_info.nested_type} | Record<string, unknown>)[]'
            elif field_type == "string":
                return 'string[]'
            else:
                if field_info.is_enum:
                    field_type = "uint8"
                ts_elem_type = TS_ARRAY_TYPE_ANNOTATIONS.get(field_type, "number")
                return f'{ts_elem_type}[]'
        elif field_type == "string":
            return 'string'
        else:
            if field_info.is_enum:
                field_type = "uint8"
            return TS_TYPE_ANNOTATIONS.get(field_type, "number")
    
    @staticmethod
    def _generate_field_accessors(field_info, class_name, packages):
        """Generate getter and setter for a single field."""
        name = field_info.name
        offset = field_info.offset
        field_type = field_info.field_type
        result = ''
        
        # Add comments if present
        for comment in field_info.comments:
            result += f'{comment}\n'
        
        if field_info.is_array:
            result += MessageTsClassGen._generate_array_accessors(field_info)
        elif field_type == "string":
            result += MessageTsClassGen._generate_string_accessors(field_info)
        elif field_info.is_enum or field_type in TYPE_SIZES:
            result += MessageTsClassGen._generate_primitive_accessors(field_info)
        
        return result
    
    @staticmethod
    def _generate_primitive_accessors(field_info):
        """Generate accessors for primitive types."""
        name = field_info.name
        offset = field_info.offset
        field_type = field_info.field_type
        
        # Handle enum as uint8
        if field_info.is_enum:
            field_type = "uint8"
        
        ts_type = TS_TYPE_ANNOTATIONS.get(field_type, "number")
        read_method = READ_METHODS.get(field_type, "_readUInt8")
        write_method = WRITE_METHODS.get(field_type, "_writeUInt8")
        
        result = f'  get {name}(): {ts_type} {{\n'
        result += f'    return this.{read_method}({offset});\n'
        result += f'  }}\n'
        result += f'  set {name}(value: {ts_type}) {{\n'
        result += f'    this.{write_method}({offset}, value);\n'
        result += f'  }}\n\n'
        
        return result
    
    @staticmethod
    def _generate_string_accessors(field_info):
        """Generate accessors for string types."""
        name = field_info.name
        offset = field_info.offset
        size = field_info.element_size or field_info.size
        
        result = f'  get {name}(): string {{\n'
        result += f'    return this._readString({offset}, {size});\n'
        result += f'  }}\n'
        result += f'  set {name}(value: string) {{\n'
        result += f'    this._writeString({offset}, {size}, value);\n'
        result += f'  }}\n\n'
        
        return result
    
    @staticmethod
    def _generate_array_accessors(field_info):
        """Generate accessors for array types."""
        name = field_info.name
        offset = field_info.offset
        field_type = field_info.field_type
        length = field_info.array_length
        elem_size = field_info.element_size
        
        if field_info.is_nested:
            # Struct array
            nested_type = field_info.nested_type
            result = f'  get {name}(): {nested_type}[] {{\n'
            result += f'    return this._readStructArray({offset}, {length}, {nested_type});\n'
            result += f'  }}\n'
            result += f'  set {name}(value: ({nested_type} | Record<string, unknown>)[]) {{\n'
            result += f'    this._writeStructArray({offset}, {length}, {elem_size}, value, {nested_type});\n'
            result += f'  }}\n\n'
        elif field_type == "string":
            # String array using struct array internally (for fixed strings)
            # This is a special case handled by StructArray
            result = f'  get {name}(): string[] {{\n'
            result += f'    // String array - internal struct array representation\n'
            result += f'    const result: string[] = [];\n'
            result += f'    for (let i = 0; i < {length}; i++) {{\n'
            result += f'      result.push(this._readString({offset} + i * {elem_size}, {elem_size}));\n'
            result += f'    }}\n'
            result += f'    return result;\n'
            result += f'  }}\n'
            result += f'  set {name}(value: string[]) {{\n'
            result += f'    const arr = value || [];\n'
            result += f'    for (let i = 0; i < {length}; i++) {{\n'
            result += f'      this._writeString({offset} + i * {elem_size}, {elem_size}, i < arr.length ? arr[i] : \'\');\n'
            result += f'    }}\n'
            result += f'  }}\n\n'
        else:
            # Primitive array
            if field_info.is_enum:
                field_type = "uint8"
            
            ts_elem_type = TS_ARRAY_TYPE_ANNOTATIONS.get(field_type, "number")
            read_method = READ_ARRAY_METHODS.get(field_type, "_readUInt8Array")
            write_method = WRITE_ARRAY_METHODS.get(field_type, "_writeUInt8Array")
            
            result = f'  get {name}(): {ts_elem_type}[] {{\n'
            result += f'    return this.{read_method}({offset}, {length});\n'
            result += f'  }}\n'
            result += f'  set {name}(value: {ts_elem_type}[]) {{\n'
            result += f'    this.{write_method}({offset}, {length}, value);\n'
            result += f'  }}\n\n'
        
        return result


class FileTsGen():
    @staticmethod
    def generate(package, use_class_based=False, packages=None, equality=False):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        # Only import MessageBase/Struct if there are messages
        if package.messages:
            if use_class_based:
                yield "import { MessageBase } from './struct-base';\n"
            else:
                yield "import { Struct, ExtractType } from './struct-base';\n"
        
        # Collect cross-package type dependencies
        external_types = {}  # {package_name: set of type names}
        if package.messages:
            for key, msg in package.messages.items():
                for field_name, field in msg.fields.items():
                    type_package = getattr(field, 'type_package', None)
                    # Only track types from other packages that aren't enums
                    if type_package and type_package != package.name and not field.isEnum:
                        if type_package not in external_types:
                            external_types[type_package] = set()
                        external_types[type_package].add(field.fieldType)
        
        # Generate import statements for cross-package types
        for ext_package, type_names in sorted(external_types.items()):
            # Convert package name to PascalCase for TypeScript conventions
            ext_package_pascal = pascalCase(ext_package)
            imports = ', '.join('%s%s' % (ext_package_pascal, t) for t in sorted(type_names))
            yield "import { %s } from './%s.structframe';\n" % (imports, ext_package)
        
        yield "\n"

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'/* Package ID for extended message IDs */\n'
            yield f'export const PACKAGE_ID = {package.package_id};\n\n'

        # include additional header files here if available in the future

        # Convert package name to PascalCase for TypeScript naming conventions
        package_name_pascal = pascalCase(package.name)
        
        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumTsGen.generate(enum, package_name_pascal) + '\n\n'

        if package.messages:
            if use_class_based:
                yield '/* Message class definitions */\n'
                for key, msg in package.sortedMessages().items():
                    yield MessageTsClassGen.generate(msg, package_name_pascal, package, packages or {}, equality) + '\n'
            else:
                yield '/* Struct definitions */\n'
                for key, msg in package.sortedMessages().items():
                    yield MessageTsGen.generate(msg, package_name_pascal, package) + '\n'
            yield '\n'

        if package.messages:
            # Only generate get_message_info if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                # Import MessageInfo type
                yield 'import { MessageInfo } from \'./frame-profiles\';\n\n'
                
                if package.package_id is not None:
                    # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                    yield 'export function get_message_info(msg_id: number): MessageInfo | undefined {\n'
                    yield '    // Extract package ID and message ID from 16-bit message ID\n'
                    yield '    const pkg_id = (msg_id >> 8) & 0xFF;\n'
                    yield '    const local_msg_id = msg_id & 0xFF;\n'
                    yield '    \n'
                    yield '    // Check if this is our package\n'
                    yield '    if (pkg_id !== PACKAGE_ID) {\n'
                    yield '        return undefined;\n'
                    yield '    }\n'
                    yield '    \n'
                    yield '    switch (local_msg_id) {\n'
                else:
                    # Flat namespace mode: 8-bit message ID
                    yield 'export function get_message_info(msg_id: number): MessageInfo | undefined {\n'
                    yield '    switch (msg_id) {\n'
                
                for msg in messages_with_id:
                    package_msg_name = '%s%s' % (package_name_pascal, msg.name)
                    magic1 = msg.magic_bytes[0] if msg.magic_bytes else 0
                    magic2 = msg.magic_bytes[1] if msg.magic_bytes else 0
                    if use_class_based:
                        yield '        case %s._msgid: return { size: %s._size, magic1: %s._magic1, magic2: %s._magic2 };\n' % (
                            package_msg_name, package_msg_name, package_msg_name, package_msg_name)
                    else:
                        yield '        case %s._msgid: return { size: %s._size, magic1: %d, magic2: %d };\n' % (
                            package_msg_name, package_msg_name, magic1, magic2)

                yield '        default: return undefined;\n'
                yield '    }\n'
                yield '}\n'
            yield '\n'
