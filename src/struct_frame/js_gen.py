#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
JavaScript code generator for struct-frame.

This module generates human-readable JavaScript code for struct serialization.
It reuses the shared TypeScript/JavaScript base module for common logic
but outputs JavaScript syntax (CommonJS) instead of TypeScript.
"""

from struct_frame import version, NamingStyleC, pascalCase
from struct_frame.ts_js_base import (
    common_types,
    common_typed_array_methods,
    BaseFieldGen,
    BaseEnumGen,
    # New class-based generation utilities
    TYPE_SIZES,
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
js_types = common_types
js_typed_array_methods = common_typed_array_methods


class EnumJsGen():
    @staticmethod
    def generate(field, packageName):
        leading_comment = field.comments
        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '%s\n' % c

        # Use PascalCase for both package and enum name (JavaScript convention)
        enum_name = '%s%s' % (packageName, field.name)
        result += 'const %s = Object.freeze({' % enum_name

        result += '\n'

        enum_length = len(field.data)
        enum_values = []
        for index, (d) in enumerate(field.data):
            leading_comment = field.data[d][1]

            if leading_comment:
                for c in leading_comment:
                    enum_values.append('  ' + c)

            comma = ","
            if index == enum_length - 1:
                # last enum member should not end with a comma
                comma = ""

            enum_value = "  %s: %d%s" % (
                StyleC.enum_entry(d), field.data[d][0], comma)

            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        result += '\n});\n'
        result += 'module.exports.%s = %s;' % (enum_name, enum_name)

        # Add enum-to-string helper function
        result += f'\n\n/* Convert {enum_name} to string */\n'
        result += f'function {enum_name}_to_string(value) {{\n'
        result += '  switch (value) {\n'
        for d in field.data:
            result += f'    case {enum_name}.{StyleC.enum_entry(d)}: return "{StyleC.enum_entry(d)}";\n'
        result += '    default: return "UNKNOWN";\n'
        result += '  }\n'
        result += '}\n'
        result += f'module.exports.{enum_name}_to_string = {enum_name}_to_string;\n'

        return result


class FieldJsGen():
    """JavaScript field generator using shared base logic."""

    @staticmethod
    def generate(field, packageName):
        """Generate JavaScript field definition using shared base."""
        return BaseFieldGen.generate(
            field, packageName, js_types, js_typed_array_methods
        )


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageJsGen():
    @staticmethod
    def generate(msg, packageName, package=None):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        package_msg_name = '%s%s' % (packageName, msg.name)

        result += "const %s = new Struct('%s')" % (
            package_msg_name, package_msg_name)
        
        # Add message ID if present
        if msg.id:
            result += '.msgId(%d)' % msg.id

        result += '\n'

        size = 1
        if not msg.fields and not msg.oneofs:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += "    .UInt8('dummy_field');"
        else:
            size = msg.size

        # Generate regular fields
        result += '\n'.join([FieldJsGen.generate(f, packageName)
                            for key, f in msg.fields.items()])
        
        # Generate oneofs - add discriminator and allocate union size
        for key, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                # Always use UInt16LE since message IDs can be up to 65535
                result += f"\n    .UInt16LE('{oneof.name}_discriminator')"
            # Allocate space for the union (largest member size)
            # Use a byte array to represent the union storage
            result += f"\n    .ByteArray('{oneof.name}_data', {oneof.size})"
        
        result += '\n    .compile();\n'
        result += 'module.exports.%s = %s;\n' % (package_msg_name, package_msg_name)

        return result + '\n'

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class MessageJsClassGen():
    """Generate JavaScript message classes that extend MessageBase."""
    
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
        
        # Generate class declaration
        result += f'class {package_msg_name} extends MessageBase {{\n'
        
        # Static properties
        result += f'  static _size = {total_size};\n'
        if msg.id:
            result += f'  static _msgid = {msg.id};\n'
        
        # Add magic numbers for checksum
        if msg.id is not None and msg.magic_bytes:
            result += f'  static _magic1 = {msg.magic_bytes[0]}; // Checksum magic (based on field types and positions)\n'
            result += f'  static _magic2 = {msg.magic_bytes[1]}; // Checksum magic (based on field types and positions)\n'
        
        # Add variable message constants
        if msg.variable:
            result += f'  static _minSize = {msg.min_size}; // Minimum size when all variable fields are empty\n'
            result += f'  static _isVariable = true; // This message uses variable-length encoding\n'
        
        result += '\n'
        
        # Generate constructor that supports init object
        result += f'  /**\n'
        result += f'   * Create a new {package_msg_name} instance.\n'
        result += f'   * @param {{Buffer|Object}} [bufferOrInit] - Buffer to wrap or init object with field values\n'
        result += f'   */\n'
        result += f'  constructor(bufferOrInit) {{\n'
        result += f'    super(Buffer.isBuffer(bufferOrInit) ? bufferOrInit : undefined);\n'
        result += f'    if (bufferOrInit && !Buffer.isBuffer(bufferOrInit)) {{\n'
        result += f'      this._applyInit(bufferOrInit);\n'
        result += f'    }}\n'
        result += f'  }}\n\n'
        
        # Generate getters and setters for each field
        for field_info in fields:
            result += MessageJsClassGen._generate_field_accessors(field_info, package_msg_name, packages)
        
        # Generate equals method if requested
        if equality:
            result += MessageJsClassGen.generate_equals_method(msg, package_msg_name, fields)
        
        # Generate variable message methods if this is a variable message
        if msg.variable:
            result += MessageJsClassGen._generate_variable_methods(msg, package_msg_name)
        else:
            # For non-variable messages, add a serialize() method that returns the buffer
            result += f'\n  /**\n'
            result += f'   * Serialize message to binary data.\n'
            result += f'   * Returns a copy of the internal buffer.\n'
            result += f'   * @returns {{Buffer}} Buffer with serialized message data\n'
            result += f'   */\n'
            result += f'  serialize() {{\n'
            result += f'    return Buffer.from(this._buffer);\n'
            result += f'  }}\n'
        
        # Generate unified deserialize method for messages with MSG_ID
        if msg.id is not None:
            result += MessageJsClassGen._generate_unified_unpack(msg, package_msg_name)
        
        # Static getSize method
        result += f'  static getSize() {{\n'
        result += f'    return {total_size};\n'
        result += f'  }}\n'
        
        result += '}\n'
        result += f'module.exports.{package_msg_name} = {package_msg_name};\n'
        return result + '\n'
    
    @staticmethod
    def _generate_unified_unpack(msg, package_msg_name):
        """Generate unified deserialize() method that works for both variable and non-variable messages."""
        result = ''
        
        result += f'\n  /**\n'
        result += f'   * Deserialize message from binary data.\n'
        result += f'   * Works for both variable and non-variable messages.\n'
        result += f'   * For variable messages with minimal profiles (buffer.length === _size),\n'
        result += f'   * uses fixed-size deserialization instead of variable-length deserialization.\n'
        result += f'   * @param {{Buffer|Object}} buffer Input buffer or FrameMsgInfo from frame parser\n'
        result += f'   * @returns {{{package_msg_name}}} New instance with deserialized data\n'
        result += f'   */\n'
        result += f'  static deserialize(buffer) {{\n'
        result += f'    // Check if buffer is FrameMsgInfo (has msg_data property)\n'
        result += f'    if (buffer && typeof buffer === "object" && "msg_data" in buffer) {{\n'
        result += f'      buffer = Buffer.from(buffer.msg_data);\n'
        result += f'    }} else if (buffer instanceof Uint8Array && !(buffer instanceof Buffer)) {{\n'
        result += f'      buffer = Buffer.from(buffer);\n'
        result += f'    }}\n'
        result += f'    \n'
        
        if msg.variable:
            result += f'    // Variable message - check encoding format\n'
            result += f'    if (buffer.length === {package_msg_name}._size) {{\n'
            result += f'      // Minimal profile format (MAX_SIZE encoding)\n'
            result += f'      const msg = new {package_msg_name}();\n'
            result += f'      buffer.copy(msg._buffer);\n'
            result += f'      return msg;\n'
            result += f'    }} else {{\n'
            result += f'      // Variable-length format\n'
            result += f'      return {package_msg_name}._deserializeVariable(buffer);\n'
            result += f'    }}\n'
        else:
            result += f'    // Fixed-size message - use direct copy\n'
            result += f'    const msg = new {package_msg_name}();\n'
            result += f'    buffer.copy(msg._buffer);\n'
            result += f'    return msg;\n'
        
        result += f'  }}\n'
        
        return result
    
    @staticmethod
    def _generate_variable_methods(msg, package_msg_name):
        """Generate variable-length encoding methods for JavaScript messages."""
        result = ''
        
        # Add isVariable() instance method
        result += f'\n  /**\n'
        result += f'   * Check if this message uses variable-length encoding.\n'
        result += f'   * @returns {{boolean}} true (this message is variable-length)\n'
        result += f'   */\n'
        result += f'  isVariable() {{\n'
        result += f'    return true;\n'
        result += f'  }}\n'
        
        # Generate serializedSize method (was packSize)
        result += f'\n  /**\n'
        result += f'   * Calculate the serialized size using variable-length encoding.\n'
        result += f'   * @returns {{number}} The size in bytes when serialized\n'
        result += f'   */\n'
        result += f'  serializedSize() {{\n'
        result += f'    let size = 0;\n'
        
        for key, field in msg.fields.items():
            name = field.name
            if field.is_array and field.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.fieldType, (field.size - 1) // field.max_size)
                result += f'    size += 1 + (this.{name}_count * {element_size}); // {name}\n'
            elif field.fieldType == "string" and field.max_size is not None:
                result += f'    size += 1 + this.{name}_length; // {name}\n'
            else:
                result += f'    size += {field.size}; // {name}\n'
        
        result += f'    return size;\n'
        result += f'  }}\n'
        
        # Generate serialize method (was packVariable)
        result += f'\n  /**\n'
        result += f'   * Serialize message using variable-length encoding.\n'
        result += f'   * @returns {{Buffer}} Buffer with serialized data (only used bytes)\n'
        result += f'   */\n'
        result += f'  serialize() {{\n'
        result += f'    const size = this.serializedSize();\n'
        result += f'    const buffer = Buffer.alloc(size);\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = field.name
            field_type = field.fieldType
            if field.is_array and field.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = this.{name}_count;\n'
                result += f'    buffer.writeUInt8({name}Count, offset++);\n'
                
                write_method = WRITE_METHODS.get(field_type if not field.isEnum else "uint8", "_writeUInt8")
                write_method_name = write_method.replace("_write", "write")
                result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                result += f'      buffer.{write_method_name}(this.{name}_data[i], offset);\n'
                result += f'      offset += {element_size};\n'
                result += f'    }}\n'
            elif field_type == "string" and field.max_size is not None:
                result += f'    // {name}: variable string\n'
                result += f'    const {name}Len = this.{name}_length;\n'
                result += f'    buffer.writeUInt8({name}Len, offset++);\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset + 1}, {msg_offset + 1} + {name}Len);\n'
                result += f'    offset += {name}Len;\n'
            else:
                result += f'    // {name}: fixed size ({field.size} bytes)\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset + field.size});\n'
                result += f'    offset += {field.size};\n'
            msg_offset += field.size
        
        result += f'    return buffer;\n'
        result += f'  }}\n'
        
        # Generate static _deserializeVariable method (was unpackVariable)
        result += f'\n  /**\n'
        result += f'   * Deserialize message from variable-length encoded buffer.\n'
        result += f'   * Internal method used by deserialize().\n'
        result += f'   * @param {{Buffer}} buffer Input buffer with variable-length encoded data\n'
        result += f'   * @returns {{{package_msg_name}}} New instance with deserialized data\n'
        result += f'   */\n'
        result += f'  static _deserializeVariable(buffer) {{\n'
        result += f'    const msg = new {package_msg_name}();\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = field.name
            field_type = field.fieldType
            if field.is_array and field.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = Math.min(buffer.readUInt8(offset++), {field.max_size});\n'
                result += f'    msg._buffer.writeUInt8({name}Count, {msg_offset});\n'
                result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                result += f'      buffer.copy(msg._buffer, {msg_offset + 1} + i * {element_size}, offset, offset + {element_size});\n'
                result += f'      offset += {element_size};\n'
                result += f'    }}\n'
            elif field_type == "string" and field.max_size is not None:
                result += f'    // {name}: variable string\n'
                result += f'    const {name}Len = Math.min(buffer.readUInt8(offset++), {field.max_size});\n'
                result += f'    msg._buffer.writeUInt8({name}Len, {msg_offset});\n'
                result += f'    buffer.copy(msg._buffer, {msg_offset + 1}, offset, offset + {name}Len);\n'
                result += f'    offset += {name}Len;\n'
            else:
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
        result = f'\n  /**\n'
        result += f'   * Compare this message with another for equality.\n'
        result += f'   * @param {{{package_msg_name}}} other - The other message to compare with\n'
        result += f'   * @returns {{boolean}} - True if the messages are equal\n'
        result += f'   */\n'
        result += f'  equals(other) {{\n'
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
            result += MessageJsClassGen._generate_array_accessors(field_info)
        elif field_type == "string":
            result += MessageJsClassGen._generate_string_accessors(field_info)
        elif field_info.is_enum or field_type in TYPE_SIZES:
            result += MessageJsClassGen._generate_primitive_accessors(field_info)
        
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
        
        read_method = READ_METHODS.get(field_type, "_readUInt8")
        write_method = WRITE_METHODS.get(field_type, "_writeUInt8")
        
        result = f'  get {name}() {{\n'
        result += f'    return this.{read_method}({offset});\n'
        result += f'  }}\n'
        result += f'  set {name}(value) {{\n'
        result += f'    this.{write_method}({offset}, value);\n'
        result += f'  }}\n\n'
        
        return result
    
    @staticmethod
    def _generate_string_accessors(field_info):
        """Generate accessors for string types."""
        name = field_info.name
        offset = field_info.offset
        size = field_info.element_size or field_info.size
        
        result = f'  get {name}() {{\n'
        result += f'    return this._readString({offset}, {size});\n'
        result += f'  }}\n'
        result += f'  set {name}(value) {{\n'
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
            result = f'  get {name}() {{\n'
            result += f'    return this._readStructArray({offset}, {length}, {nested_type});\n'
            result += f'  }}\n'
            result += f'  set {name}(value) {{\n'
            result += f'    this._writeStructArray({offset}, {length}, {elem_size}, value, {nested_type});\n'
            result += f'  }}\n\n'
        elif field_type == "string":
            # String array
            result = f'  get {name}() {{\n'
            result += f'    const result = [];\n'
            result += f'    for (let i = 0; i < {length}; i++) {{\n'
            result += f'      result.push(this._readString({offset} + i * {elem_size}, {elem_size}));\n'
            result += f'    }}\n'
            result += f'    return result;\n'
            result += f'  }}\n'
            result += f'  set {name}(value) {{\n'
            result += f'    const arr = value || [];\n'
            result += f'    for (let i = 0; i < {length}; i++) {{\n'
            result += f'      this._writeString({offset} + i * {elem_size}, {elem_size}, i < arr.length ? arr[i] : \'\');\n'
            result += f'    }}\n'
            result += f'  }}\n\n'
        else:
            # Primitive array
            if field_info.is_enum:
                field_type = "uint8"
            
            read_method = READ_ARRAY_METHODS.get(field_type, "_readUInt8Array")
            write_method = WRITE_ARRAY_METHODS.get(field_type, "_writeUInt8Array")
            
            result = f'  get {name}() {{\n'
            result += f'    return this.{read_method}({offset}, {length});\n'
            result += f'  }}\n'
            result += f'  set {name}(value) {{\n'
            result += f'    this.{write_method}({offset}, {length}, value);\n'
            result += f'  }}\n\n'
        
        return result


class FileJsGen():
    @staticmethod
    def generate(package, use_class_based=False, packages=None, equality=False):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())
        yield '"use strict";\n\n'

        # Only import MessageBase/Struct if there are messages
        if package.messages:
            if use_class_based:
                yield "const { MessageBase } = require('./struct-base');\n"
            else:
                yield "const { Struct } = require('./struct-base');\n"
        
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
        
        # Generate require statements for cross-package types
        for ext_package, type_names in sorted(external_types.items()):
            # Convert package name to PascalCase for JavaScript conventions
            ext_package_pascal = pascalCase(ext_package)
            for t in sorted(type_names):
                type_var = '%s%s' % (ext_package_pascal, t)
                yield "const { %s } = require('./%s.structframe');\n" % (type_var, ext_package)
        
        if external_types:
            yield "\n"

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'/* Package ID for extended message IDs */\n'
            yield f'const PACKAGE_ID = {package.package_id};\n'
            yield f'module.exports.PACKAGE_ID = PACKAGE_ID;\n\n'

        # include additional header files here if available in the future

        # Convert package name to PascalCase for JavaScript naming conventions
        package_name_pascal = pascalCase(package.name)
        
        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumJsGen.generate(enum, package_name_pascal) + '\n\n'

        if package.messages:
            if use_class_based:
                yield '/* Message class definitions */\n'
                for key, msg in package.sortedMessages().items():
                    yield MessageJsClassGen.generate(msg, package_name_pascal, package, packages or {}, equality) + '\n'
            else:
                yield '/* Struct definitions */\n'
                for key, msg in package.sortedMessages().items():
                    yield MessageJsGen.generate(msg, package_name_pascal, package) + '\n'
            yield '\n'

        if package.messages:
            # Only generate get_message_info if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                # Generate unified get_message_info function
                # Returns { size, magic1, magic2 } for a given message ID
                if package.package_id is not None:
                    # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                    yield '/**\n'
                    yield ' * Get message info (size and magic numbers) for a message ID.\n'
                    yield ' * @param {number} msg_id - 16-bit message ID (pkg_id << 8 | local_msg_id)\n'
                    yield ' * @returns {{size: number, magic1: number, magic2: number}|undefined}\n'
                    yield ' */\n'
                    yield 'function get_message_info(msg_id) {\n'
                    yield '  // Extract package ID and message ID from 16-bit message ID\n'
                    yield '  const pkg_id = (msg_id >> 8) & 0xFF;\n'
                    yield '  const local_msg_id = msg_id & 0xFF;\n'
                    yield '  \n'
                    yield '  // Check if this is our package\n'
                    yield '  if (pkg_id !== PACKAGE_ID) {\n'
                    yield '    return undefined;\n'
                    yield '  }\n'
                    yield '  \n'
                    yield '  switch (local_msg_id) {\n'
                else:
                    # Flat namespace mode: 8-bit message ID
                    yield '/**\n'
                    yield ' * Get message info (size and magic numbers) for a message ID.\n'
                    yield ' * @param {number} msg_id - Message ID\n'
                    yield ' * @returns {{size: number, magic1: number, magic2: number}|undefined}\n'
                    yield ' */\n'
                    yield 'function get_message_info(msg_id) {\n'
                    yield '  switch (msg_id) {\n'
                
                for msg in messages_with_id:
                    package_msg_name = '%s%s' % (package_name_pascal, msg.name)
                    yield '    case %s._msgid: return { size: %s._size, magic1: %s._magic1, magic2: %s._magic2 };\n' % (
                        package_msg_name, package_msg_name, package_msg_name, package_msg_name)

                yield '    default: break;\n'
                yield '  }\n'
                yield '  return undefined;\n'
                yield '}\n'
                yield 'module.exports.get_message_info = get_message_info;\n'
            yield '\n'
