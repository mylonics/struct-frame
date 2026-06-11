#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
TypeScript code generator for struct-frame.

This module generates TypeScript code for struct serialization using
ES6 module syntax (import/export).
"""

from struct_frame import version, NamingStyleC, pascal_case, build_enum_leading_comments, build_enum_values, get_discriminator_enum_name, build_discriminator_enum_values
from struct_frame.ts_js_base import (
    common_types,
    common_typed_array_methods,
    ts_array_types,
    BaseFieldGen,
    BaseEnumGen,
    to_camel_case,
    # New class-based generation utilities
    TYPE_SIZES,
    TS_TYPE_ANNOTATIONS,
    TS_ARRAY_TYPE_ANNOTATIONS,
    READ_METHODS,
    WRITE_METHODS,
    READ_ARRAY_METHODS,
    WRITE_ARRAY_METHODS,
    BUFFER_READ_METHODS,
    BUFFER_WRITE_METHODS,
    calculate_field_layout,
    FieldInfo,
)
import time

_style_c = NamingStyleC()

# Use shared type mappings
ts_types = common_types
ts_typed_array_methods = common_typed_array_methods


class EnumTsGen():
    @staticmethod
    def generate(field, package_name):
        result = build_enum_leading_comments(field.comments)

        # Use short name without package prefix (TypeScript convention)
        result += 'export enum %s' % field.name
        result += ' {\n'

        enum_values = build_enum_values(
            field, _style_c,
            value_generator=lambda d, _, val, comma: f'    {pascal_case(d)} = {val}{comma}',
            skip_trailing_comma=True
        )

        result += '\n'.join(enum_values)
        result += '\n}'

        return result
    
    @staticmethod
    def generate_for_message(field, msg_name):
        """Generate a prefixed enum for a message-nested enum.

        TypeScript can't nest enums inside classes/consts, so the enum is emitted
        at module scope with a prefixed name: MsgNameEnumName.
        """
        result = build_enum_leading_comments(field.comments)
        enum_name = f'{msg_name}{field.name}'
        result += f'export enum {enum_name} {{\n'

        entries = list(field.data.items())
        for i, (entry_name, (value, comments)) in enumerate(entries):
            for c in comments:
                result += f'    // {c}\n'
            comma = ',' if i < len(entries) - 1 else ''
            result += f'    {pascal_case(entry_name)} = {value}{comma}\n'

        result += '}'
        return result

    @staticmethod
    def generate_discriminator_enum(oneof, msg_name):
        """Generate a discriminator enum for field_order oneofs in TypeScript."""
        if not oneof.auto_discriminator or oneof.discriminator_type != "field_order":
            return ''

        enum_name = get_discriminator_enum_name(oneof, msg_name)

        def none_entry():
            return '    None = 0,'

        def field_entry(field_name, field_order, is_last):
            comma = '' if is_last else ','
            return f'    {pascal_case(field_name)} = {field_order}{comma}'

        lines = build_discriminator_enum_values(oneof, none_entry, field_entry)
        result = f'/** Discriminator enum for {msg_name}.{oneof.name} oneof */\n'
        result += f'export enum {enum_name} {{\n'
        result += '\n'.join(lines) + '\n'
        result += f'}}\n'
        return result

    @staticmethod
    def get_discriminator_enum_name(oneof, msg_name):
        """Get the enum type name for a field_order discriminator."""
        return get_discriminator_enum_name(oneof, msg_name)


class FieldTsGen():
    """TypeScript field generator using shared base logic."""

    @staticmethod
    def generate(field, package_name):
        """Generate TypeScript field definition using shared base."""
        return BaseFieldGen.generate(
            field, package_name, ts_types, ts_typed_array_methods
        )


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageTsGen():
    @staticmethod
    def generate(msg, package_name, package=None):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '%s\n' % c

        package_msg_name = msg.name

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
        result += '\n'.join([FieldTsGen.generate(f, package_name)
                            for key, f in msg.fields.items()])
        
        # Generate oneofs - add discriminator and allocate union size
        for key, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    # Use UInt16LE since message IDs can be up to 65535
                    result += f'\n    .UInt16LE(\'{to_camel_case(oneof.name)}Discriminator\')'
                else:  # field_order
                    # Use UInt8 since field order is 1-based index
                    result += f'\n    .UInt8(\'{to_camel_case(oneof.name)}Discriminator\')'
            # Allocate space for the union (largest member size)
            # Use a byte array to represent the union storage
            result += f'\n    .ByteArray(\'{to_camel_case(oneof.name)}Data\', {oneof.size})'
        
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
    def generate(msg, package_name, package, packages, equality=False):
        """Generate a class-based message definition."""
        leading_comment = msg.comments
        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '%s\n' % c

        package_msg_name = msg.name
        
        # Calculate field layout with offsets
        fields = calculate_field_layout(msg, package, packages)
        total_size = msg.size
        
        # Generate init interface for this message (only if there are fields)
        if fields:
            result += MessageTsClassGen._generate_init_interface(package_msg_name, fields)
            result += MessageTsClassGen._generate_object_interface(package_msg_name, fields)
        
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
            result += f'  static readonly _baseSize: number = {msg.base_size}; // Non-extension portion size (== _size when no extensions)\n'
        
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
        else:
            # For non-variable messages, add a serialize() method that returns the buffer
            result += f'\n  /**\n'
            result += f'   * Serialize message to binary data.\n'
            result += f'   * Returns a copy of the internal buffer.\n'
            result += f'   * @returns Buffer with serialized message data\n'
            result += f'   */\n'
            result += f'  serialize(): Buffer {{\n'
            result += f'    return Buffer.from(this._buffer);\n'
            result += f'  }}\n'
        
        # Generate unified deserialize method for messages with MSG_ID
        if msg.id is not None:
            result += MessageTsClassGen._generate_unified_unpack(msg, package_msg_name)
        
        # Generate envelope methods if this is an envelope message
        if msg.is_envelope:
            result += MessageTsClassGen._generate_envelope_methods(msg, package_msg_name, package_name, packages)
        
        # toObject() for efficient repeated field reads
        if fields:
            result += MessageTsClassGen._generate_to_object_method(package_msg_name, fields)

        # Static getSize method
        result += f'  static getSize(): number {{\n'
        result += f'    return {total_size};\n'
        result += f'  }}\n'
        
        result += '}\n'
        return result + '\n'
    
    @staticmethod
    def _generate_unified_unpack(msg, package_msg_name):
        """Generate unified deserialize() method that works for both variable and non-variable messages."""
        result = ''
        
        result += f'\n  /**\n'
        result += f'   * Deserialize message from binary data.\n'
        result += f'   * Works for both variable and non-variable messages.\n'
        result += f'   * For variable messages with minimal profiles (buffer.length == _size),\n'
        result += f'   * uses fixed-size deserialization instead of variable-length deserialization.\n'
        result += f'   * @param buffer Input buffer containing serialized message data, or FrameMsgInfo from frame parser\n'
        result += f'   * @returns New instance with deserialized data\n'
        result += f'   */\n'
        result += f'  static deserialize(buffer: Buffer | any): {package_msg_name} {{\n'
        result += f'    // Check if buffer is FrameMsgInfo (has msgData property)\n'
        result += f'    if (buffer && typeof buffer === "object" && "msgData" in buffer) {{\n'
        result += f'      buffer = Buffer.from(buffer.msgData);\n'
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
    def _generate_envelope_methods(msg, package_msg_name, package_name, packages):
        """Generate envelope-specific helper methods for wrapping inner messages."""
        result = ''
        
        # Get the single oneof (validation ensures exactly one exists)
        oneof_name = list(msg.oneofs.keys())[0]
        oneof = msg.oneofs[oneof_name]
        
        result += f'\n  // ========================================\n'
        result += f'  // Envelope message helper methods\n'
        result += f'  // ========================================\n'
        
        # Build list of valid payload types
        payload_types = []
        for field_name, field in oneof.fields.items():
            payload_type = field.field_type
            payload_types.append((field_name, payload_type))
        
        # Create union type for valid payloads
        payload_union = ' | '.join([pt[1] for pt in payload_types])
        
        # Generate parameter list for envelope fields (non-oneof fields)
        field_params = []
        for f_name, f in msg.fields.items():
            # Lookup type annotation once and reuse
            base_ts_type = TS_TYPE_ANNOTATIONS.get(f.field_type, 'number')
            if f.field_type in ("string", "bytes"):
                ts_type = "string"
            elif f.is_array:
                ts_type = f'{base_ts_type}[]'
            else:
                ts_type = base_ts_type
            field_params.append(f'{to_camel_case(f.name)}?: {ts_type}')
        
        # Build parameter list: payload first, then optional envelope fields
        all_params_list = [f'payload: {payload_union}'] + field_params
        
        result += f'\n  /**\n'
        result += f'   * Create a {package_msg_name} envelope wrapping a payload message.\n'
        result += f'   * @param payload The message to wrap (must be one of: {payload_union})\n'
        for f_name, f in msg.fields.items():
            result += f'   * @param {to_camel_case(f.name)} Envelope field value\n'
        result += f'   * @returns A fully initialized {package_msg_name} envelope\n'
        result += f'   */\n'
        result += f'  static wrap({", ".join(all_params_list)}): {package_msg_name} {{\n'
        result += f'    const envelope = new {package_msg_name}();\n'
        
        # Initialize envelope fields
        for f_name, f in msg.fields.items():
            camel_fname = to_camel_case(f.name)
            result += f'    if ({camel_fname} !== undefined) envelope.{camel_fname} = {camel_fname};\n'
        
        # Set the discriminator to the payload's message ID or field order
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                result += f'    envelope.{to_camel_case(oneof_name)}Discriminator = (payload.constructor as any)._msgid;\n'
            else:  # field_order - use enum values
                enum_name = EnumTsGen.get_discriminator_enum_name(oneof, package_msg_name)
                result += f'    // Set discriminator based on payload type\n'
                for idx, (field_name, payload_type) in enumerate(payload_types):
                    enum_value = pascal_case(field_name)
                    if idx == 0:
                        result += f'    if (payload instanceof {payload_type}) envelope.{to_camel_case(oneof_name)}Discriminator = {enum_name}.{enum_value};\n'
                    else:
                        result += f'    else if (payload instanceof {payload_type}) envelope.{to_camel_case(oneof_name)}Discriminator = {enum_name}.{enum_value};\n'
        
        # Copy the payload into the union data area
        result += f'    // Copy payload into union data area\n'
        result += f'    payload._buffer.copy(envelope._buffer, envelope._getUnionOffset("{to_camel_case(oneof_name)}"), 0, payload._buffer.length);\n'
        result += f'    return envelope;\n'
        result += f'  }}\n'
        
        # Generate helper to get the active payload type
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                result += f'\n  /**\n'
                result += f'   * Get the message ID of the wrapped payload.\n'
                result += f'   * @returns The message ID of the payload in the {oneof_name} union\n'
                result += f'   */\n'
                result += f'  getPayloadMessageId(): number {{\n'
                result += f'    return this.{to_camel_case(oneof_name)}Discriminator;\n'
                result += f'  }}\n'
            else:  # field_order - return enum type
                enum_name = EnumTsGen.get_discriminator_enum_name(oneof, package_msg_name)
                result += f'\n  /**\n'
                result += f'   * Get the discriminator enum value for the wrapped payload.\n'
                result += f'   * @returns The {enum_name} enum value for the active payload\n'
                result += f'   */\n'
                result += f'  getPayloadField(): {enum_name} {{\n'
                result += f'    return this.{to_camel_case(oneof_name)}Discriminator;\n'
                result += f'  }}\n'
        
        # Generate helper to get the union offset (needed for envelope operations)
        result += f'\n  private _getUnionOffset(name: string): number {{\n'
        # Calculate offset to oneof data area
        offset = sum(f.size for f in msg.fields.values())
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                offset += 2  # uint16 discriminator size
            else:  # field_order
                offset += 1  # uint8 discriminator size
        result += f'    if (name === "{to_camel_case(oneof_name)}") return {offset}; // After discriminator\n'
        result += f'    return 0;\n'
        result += f'  }}\n'
        
        return result

    @staticmethod
    def _generate_variable_methods(msg, package_msg_name, fields):
        """Generate variable-length encoding methods for TypeScript messages."""
        result = ''
        
        # Add isVariable() instance method
        result += f'\n  /**\n'
        result += f'   * Check if this message uses variable-length encoding.\n'
        result += f'   * @returns true (this message is variable-length)\n'
        result += f'   */\n'
        result += f'  isVariable(): boolean {{\n'
        result += f'    return true;\n'
        result += f'  }}\n'
        
        # Generate serializedSize method (formerly packSize)
        result += f'\n  /**\n'
        result += f'   * Calculate the serialized size using variable-length encoding.\n'
        result += f'   * @returns The size in bytes when serialized (between _minSize and _size)\n'
        result += f'   */\n'
        result += f'  serializedSize(): number {{\n'
        result += f'    let size = 0;\n'
        
        for key, field in msg.fields.items():
            name = to_camel_case(field.name)
            if field.is_array and field.max_size is not None:
                # Variable array - TypeScript uses name_count
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                count_size = 2 if field.max_size > 255 else 1
                if field.field_type in ("string", "bytes"):
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.field_type, (field.size - count_size) // field.max_size)
                result += f'    size += {count_size} + (this.{name}Count * {element_size}); // {name}\n'
            elif field.field_type in ("string", "bytes") and field.max_size is not None:
                # Variable string - TypeScript uses name_length
                length_size = 2 if field.max_size > 255 else 1
                result += f'    size += {length_size} + this.{name}Length; // {name}\n'
            else:
                result += f'    size += {field.size}; // {name}\n'
        
        # Track _buffer offset for oneof discriminator reads
        sz_msg_offset = sum(f.size for f in msg.fields.values())
        # Oneofs: discriminator + union payload (or length-prefix + variant size for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                result += f'    size += {disc_bytes}; // {oneof_name} discriminator\n'
            if oneof.variable:
                result += f'    size += 2; // {oneof_name} variable-length prefix\n'
                if oneof.auto_discriminator:
                    disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                    disc_read_method = 'readUInt16LE' if oneof.discriminator_type == "msgid" else 'readUInt8'
                    result += f'    const _{oneof_name}Disc = this._buffer.{disc_read_method}({sz_msg_offset});\n'
                    sz_msg_offset += disc_bytes
                else:
                    result += f'    const _{oneof_name}Disc = 0;\n'
                result += f'    let _{oneof_name}VSize = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'    if (_{oneof_name}Disc === {disc_val}) _{oneof_name}VSize = {field_size};  // {field_name}\n'
                if oneof.min_size_override:
                    result += f'    if (_{oneof_name}VSize < {oneof.min_size_override}) _{oneof_name}VSize = {oneof.min_size_override};\n'
                result += f'    size += _{oneof_name}VSize; // {oneof_name} variant\n'
                sz_msg_offset += oneof.size
            elif oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                disc_read_method = 'readUInt16LE' if oneof.discriminator_type == "msgid" else 'readUInt8'
                result += f'    const _{oneof_name}TrimDisc = this._buffer.{disc_read_method}({sz_msg_offset});\n'
                sz_msg_offset += disc_bytes
                result += f'    let _{oneof_name}TLen = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'    if (_{oneof_name}TrimDisc === {disc_val}) _{oneof_name}TLen = {field_size};\n'
                if oneof.min_size_override:
                    result += f'    if (_{oneof_name}TLen < {oneof.min_size_override}) _{oneof_name}TLen = {oneof.min_size_override};\n'
                result += f'    size += _{oneof_name}TLen; // {oneof_name} trimmed union payload\n'
                sz_msg_offset += oneof.size
            else:
                if oneof.auto_discriminator:
                    disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                    sz_msg_offset += disc_bytes
                result += f'    size += {oneof.size}; // {oneof_name} union payload\n'
                sz_msg_offset += oneof.size
        
        result += f'    return size;\n'
        result += f'  }}\n'
        
        # Generate serialize method (was packVariable)
        result += f'\n  /**\n'
        result += f'   * Serialize message using variable-length encoding.\n'
        result += f'   * @returns Buffer with serialized data (only used bytes)\n'
        result += f'   */\n'
        result += f'  serialize(): Buffer {{\n'
        result += f'    const size = this.serializedSize();\n'
        result += f'    const buffer = Buffer.alloc(size);\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = to_camel_case(field.name)
            field_type = field.field_type
            if field.is_array and field.max_size is not None:
                # Variable array - TypeScript uses name_count and name_data
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type in ("string", "bytes"):
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                max_len = field.max_size
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = this.{name}Count;\n'
                result += f'    buffer.writeUInt8({name}Count, offset++);\n'
                
                if field_type not in type_sizes and field_type != "string" and not field.is_enum:
                    # Nested struct array
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      const nested = this.{name}Data[i];\n'
                    result += f'      nested._buffer.copy(buffer, offset);\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                elif field_type in ("string", "bytes"):
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      const str = this.{name}Data[i] || \'\';\n'
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
                    write_method_name = buffer_write_methods.get(field_type if not field.is_enum else "uint8", "writeUInt8")
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.{write_method_name}(this.{name}Data[i], offset);\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
            elif field_type in ("string", "bytes") and field.max_size is not None:
                # Variable string - copy from internal buffer (string is stored there)
                max_len = field.max_size
                result += f'    // {name}: variable string\n'
                result += f'    const {name}Len = this.{name}Length;\n'
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
        
        # Oneofs: copy discriminator bytes + union payload (or length-prefix + variant bytes for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                result += f'    // {oneof_name}: discriminator ({disc_bytes} bytes)\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset + disc_bytes});\n'
                result += f'    offset += {disc_bytes};\n'
                msg_offset += disc_bytes
            if oneof.variable:
                disc_read = f'this._buffer.readUInt16LE({msg_offset - 2})' if oneof.discriminator_type == "msgid" else f'this._buffer.readUInt8({msg_offset - 1})'
                result += f'    // {oneof_name}: variable-length union payload\n'
                result += f'    const _{oneof_name}SerDisc = {disc_read};\n'
                result += f'    let _{oneof_name}SerLen = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'    if (_{oneof_name}SerDisc === {disc_val}) _{oneof_name}SerLen = {field_size};  // {field_name}\n'
                if oneof.min_size_override:
                    result += f'    if (_{oneof_name}SerLen < {oneof.min_size_override}) _{oneof_name}SerLen = {oneof.min_size_override};\n'
                result += f'    buffer.writeUInt16LE(_{oneof_name}SerLen, offset); offset += 2;\n'
                result += f'    if (_{oneof_name}SerLen > 0) {{\n'
                result += f'      this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset} + _{oneof_name}SerLen);\n'
                result += f'      offset += _{oneof_name}SerLen;\n'
                result += f'    }}\n'
                msg_offset += oneof.size
            elif oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                disc_offset = msg_offset - disc_bytes
                disc_read_method = 'readUInt16LE' if oneof.discriminator_type == "msgid" else 'readUInt8'
                _trim_label = f'trimmed union (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union'
                result += f'    // {oneof_name}: {_trim_label}\n'
                result += f'    const _{oneof_name}TrimDisc = this._buffer.{disc_read_method}({disc_offset});\n'
                result += f'    let _{oneof_name}TrimLen = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'    if (_{oneof_name}TrimDisc === {disc_val}) _{oneof_name}TrimLen = {field_size};\n'
                if oneof.min_size_override:
                    result += f'    if (_{oneof_name}TrimLen < {oneof.min_size_override}) _{oneof_name}TrimLen = {oneof.min_size_override};\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset} + _{oneof_name}TrimLen);\n'
                result += f'    offset += _{oneof_name}TrimLen;\n'
                msg_offset += oneof.size
            else:
                result += f'    // {oneof_name}: union payload ({oneof.size} bytes)\n'
                result += f'    this._buffer.copy(buffer, offset, {msg_offset}, {msg_offset + oneof.size});\n'
                result += f'    offset += {oneof.size};\n'
                msg_offset += oneof.size
        result += f'    return buffer;\n'
        result += f'  }}\n'
        result += f'\n  /**\n'
        result += f'   * Deserialize message from variable-length encoded buffer.\n'
        result += f'   * Internal method used by deserialize().\n'
        result += f'   * @param buffer Input buffer with variable-length encoded data\n'
        result += f'   * @returns New instance with deserialized data\n'
        result += f'   */\n'
        result += f'  static _deserializeVariable(buffer: Buffer): {package_msg_name} {{\n'
        result += f'    const msg = new {package_msg_name}();\n'
        result += f'    let offset = 0;\n'
        
        msg_offset = 0
        for key, field in msg.fields.items():
            name = to_camel_case(field.name)
            field_type = field.field_type
            if field.is_array and field.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field_type in ("string", "bytes"):
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field_type, (field.size - 1) // field.max_size)
                max_len = field.max_size
                result += f'    // {name}: variable array\n'
                result += f'    const {name}Count = Math.min(buffer.readUInt8(offset++), {max_len});\n'
                
                if field_type not in type_sizes and field_type != "string" and not field.is_enum:
                    # Nested struct array - need to set the internal buffer array elements
                    nested_type = '%s%s' % (pascal_case(field.package), field_type)
                    result += f'    // Write count to internal buffer\n'
                    result += f'    msg._buffer.writeUInt8({name}Count, {msg_offset});\n'
                    result += f'    for (let i = 0; i < {name}Count; i++) {{\n'
                    result += f'      buffer.copy(msg._buffer, {msg_offset + 1} + i * {element_size}, offset, offset + {element_size});\n'
                    result += f'      offset += {element_size};\n'
                    result += f'    }}\n'
                elif field_type in ("string", "bytes"):
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
            elif field_type in ("string", "bytes") and field.max_size is not None:
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
        
        # Oneofs: read discriminator bytes + union payload (or length-prefix + variant bytes for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                result += f'    // {oneof_name}: discriminator ({disc_bytes} bytes)\n'
                result += f'    buffer.copy(msg._buffer, {msg_offset}, offset, offset + {disc_bytes});\n'
                result += f'    offset += {disc_bytes};\n'
                msg_offset += disc_bytes
            if oneof.variable:
                disc_read = f'msg._buffer.readUInt16LE({msg_offset - 2})' if oneof.discriminator_type == "msgid" else f'msg._buffer.readUInt8({msg_offset - 1})'
                result += f'    // {oneof_name}: variable-length union payload\n'
                result += f'    const _{oneof_name}DeserLen = buffer.readUInt16LE(offset); offset += 2;\n'
                result += f'    if (_{oneof_name}DeserLen > 0 && offset + _{oneof_name}DeserLen <= buffer.length) {{\n'
                result += f'      buffer.copy(msg._buffer, {msg_offset}, offset, offset + Math.min(_{oneof_name}DeserLen, {oneof.size}));\n'
                result += f'    }}\n'
                result += f'    offset += _{oneof_name}DeserLen;\n'
                msg_offset += oneof.size
            elif oneof.auto_discriminator:
                _min_sz = oneof.min_size_override or 0
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                disc_offset = msg_offset - disc_bytes
                disc_read_method = 'readUInt16LE' if oneof.discriminator_type == "msgid" else 'readUInt8'
                _trim_label = f'trimmed union read (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union read'
                result += f'    // {oneof_name}: {_trim_label}\n'
                result += f'    const _{oneof_name}TRDisc = msg._buffer.{disc_read_method}({disc_offset});\n'
                result += f'    let _{oneof_name}TRLen = {_min_sz};\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'    if (_{oneof_name}TRDisc === {disc_val}) _{oneof_name}TRLen = Math.max({field_size}, {_min_sz});\n'
                result += f'    if (offset + _{oneof_name}TRLen <= buffer.length) {{\n'
                result += f'      buffer.copy(msg._buffer, {msg_offset}, offset, offset + Math.min(_{oneof_name}TRLen, {oneof.size}));\n'
                result += f'    }}\n'
                result += f'    offset += _{oneof_name}TRLen;\n'
                msg_offset += oneof.size
            else:
                result += f'    // {oneof_name}: union payload ({oneof.size} bytes)\n'
                result += f'    buffer.copy(msg._buffer, {msg_offset}, offset, offset + {oneof.size});\n'
                result += f'    offset += {oneof.size};\n'
                msg_offset += oneof.size
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
    def _generate_object_interface(class_name, fields):
        """Generate the Object interface returned by toObject()."""
        result = f'export interface {class_name}Object {{\n'
        for field_info in fields:
            ts_type = MessageTsClassGen._get_ts_type_for_field(field_info)
            result += f'  {field_info.name}: {ts_type};\n'
        result += '}\n\n'
        return result

    @staticmethod
    def _generate_to_object_method(class_name, fields):
        """Generate a toObject() method that decodes all fields into a plain POJO.

        Scalar primitive reads are inlined directly to this._buffer.readXxx(offset)
        to eliminate the getter-to-wrapper call chain on the hot read path.
        String and array fields delegate to their getters.
        """
        result = '\n  /**\n'
        result += '   * Decode all fields into a plain object for efficient repeated reads.\n'
        result += '   * Call this once at parse/store time, then read from the returned POJO\n'
        result += '   * in render loops — plain property reads hit V8 inline caches directly.\n'
        result += '   * Scalar reads are inlined (no getter or wrapper call overhead).\n'
        result += '   * @returns Plain object with all field values decoded\n'
        result += '   */\n'
        result += f'  toObject(): {class_name}Object {{\n'
        result += '    return {\n'
        for field_info in fields:
            name = field_info.name
            field_type = field_info.field_type
            offset = field_info.offset
            if field_info.is_array or field_info.is_nested:
                # Arrays and nested structs: delegate to getter
                result += f'      {name}: this.{name},\n'
            elif field_type in ("string", "bytes"):
                # Strings: delegate to wrapper (UTF-8 decode cannot be trivially inlined)
                size = field_info.element_size or field_info.size
                result += f'      {name}: this._readString({offset}, {size}),\n'
            elif field_type == "bool":
                result += f'      {name}: this._buffer.readUInt8({offset}) !== 0,\n'
            else:
                # Scalar primitive: inline the Buffer read directly
                actual_type = "uint8" if field_info.is_enum else field_type
                buf_read = BUFFER_READ_METHODS.get(actual_type, "readUInt8")
                result += f'      {name}: this._buffer.{buf_read}({offset}),\n'
        result += '    };\n'
        result += '  }\n'
        return result
    
    @staticmethod
    def _get_ts_type_for_field(field_info):
        """Get the TypeScript type annotation for a field."""
        field_type = field_info.field_type
        
        if field_info.is_array:
            if field_info.is_nested:
                return f'({field_info.nested_type} | Record<string, unknown>)[]'
            elif field_type in ("string", "bytes"):
                return 'string[]'
            else:
                if field_info.is_enum:
                    field_type = "uint8"
                ts_elem_type = TS_ARRAY_TYPE_ANNOTATIONS.get(field_type, "number")
                return f'{ts_elem_type}[]'
        elif field_type in ("string", "bytes"):
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
        elif field_type in ("string", "bytes"):
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
        
        # Boolean needs special transforms (readUInt8 + !== 0, writeUInt8 + ternary)
        if field_type == "bool":
            result = f'  get {name}(): {ts_type} {{\n'
            result += f'    return this._buffer.readUInt8({offset}) !== 0;\n'
            result += f'  }}\n'
            result += f'  set {name}(value: {ts_type}) {{\n'
            result += f'    this._buffer.writeUInt8(value ? 1 : 0, {offset});\n'
            result += f'  }}\n\n'
        else:
            # Inline the Buffer method call directly — eliminates the MessageBase
            # wrapper hop on the hot read path (getter → Buffer, not getter → wrapper → Buffer).
            # Note: Buffer.readXxx(offset) but Buffer.writeXxx(value, offset) — different arg order.
            buf_read = BUFFER_READ_METHODS.get(field_type, "readUInt8")
            buf_write = BUFFER_WRITE_METHODS.get(field_type, "writeUInt8")
            result = f'  get {name}(): {ts_type} {{\n'
            result += f'    return this._buffer.{buf_read}({offset});\n'
            result += f'  }}\n'
            result += f'  set {name}(value: {ts_type}) {{\n'
            result += f'    this._buffer.{buf_write}(value, {offset});\n'
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
        elif field_type in ("string", "bytes"):
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
        yield '/* Generated by struct-frame %s. */\n\n' % version

        # Only import MessageBase/Struct if there are messages
        if package.messages:
            if use_class_based:
                yield "import { MessageBase } from './struct-base';\n"
            else:
                yield "import { Struct, ExtractType } from './struct-base';\n"
        
        # Collect cross-package type dependencies (messages and enums)
        external_types = {}  # {package_name: set of type names}
        if package.messages:
            for key, msg in package.messages.items():
                for field_name, field in msg.fields.items():
                    type_package = getattr(field, 'type_package', None)
                    # Track all types (including enums) from other packages
                    if type_package and type_package != package.name:
                        if type_package not in external_types:
                            external_types[type_package] = set()
                        external_types[type_package].add(field.field_type)
        
        # Generate import statements for cross-package types
        for ext_package, type_names in sorted(external_types.items()):
            imports = ', '.join(sorted(type_names))
            yield "import { %s } from './%s.structframe';\n" % (imports, ext_package.replace('_', '-'))
        
        yield "\n"

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'/* Package ID for extended message IDs */\n'
            yield f'export const PACKAGE_ID = {package.package_id};\n\n'

        # include additional header files here if available in the future

        # Convert package name to PascalCase for TypeScript naming conventions
        package_name_pascal = pascal_case(package.name)
        
        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumTsGen.generate(enum, package_name_pascal) + '\n\n'

        # Generate nested message enums (prefixed at module scope)
        has_nested_enums = False
        for key, msg in package.messages.items():
            structName = msg.name
            if msg.enums:
                if not has_nested_enums:
                    yield '/* Nested message enums (prefixed at module scope) */\n'
                    has_nested_enums = True
                for enum_name, enum in msg.enums.items():
                    yield EnumTsGen.generate_for_message(enum, structName) + '\n\n'

        # Generate discriminator enums for field_order oneofs (must come before message definitions)
        has_discriminator_enums = False
        for key, msg in package.messages.items():
            structName = msg.name
            for oneof_name, oneof in msg.oneofs.items():
                enum_code = EnumTsGen.generate_discriminator_enum(oneof, structName)
                if enum_code:
                    if not has_discriminator_enums:
                        yield '/* Oneof discriminator enums */\n'
                        has_discriminator_enums = True
                    yield enum_code + '\n'

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
            # Only generate getMessageInfo if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                # Import MessageInfo type
                yield 'import { MessageInfo } from \'./frame-profiles\';\n\n'
                
                if package.package_id is not None:
                    # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                    yield 'export function getMessageInfo(msgId: number): MessageInfo | undefined {\n'
                    yield '    // Extract package ID and message ID from 16-bit message ID\n'
                    yield '    const pkg_id = (msgId >> 8) & 0xFF;\n'
                    yield '    const local_msg_id = msgId & 0xFF;\n'
                    yield '    \n'
                    yield '    // Check if this is our package\n'
                    yield '    if (pkg_id !== PACKAGE_ID) {\n'
                    yield '        return undefined;\n'
                    yield '    }\n'
                    yield '    \n'
                    yield '    switch (local_msg_id) {\n'
                else:
                    # Flat namespace mode: 8-bit message ID
                    yield 'export function getMessageInfo(msgId: number): MessageInfo | undefined {\n'
                    yield '    switch (msgId) {\n'
                
                for msg in messages_with_id:
                    package_msg_name = msg.name
                    magic1 = msg.magic_bytes[0] if msg.magic_bytes else 0
                    magic2 = msg.magic_bytes[1] if msg.magic_bytes else 0
                    if use_class_based:
                        yield '        case %s._msgid: return { size: %s._size, magic1: %s._magic1, magic2: %s._magic2, baseSize: %s._baseSize };\n' % (
                            package_msg_name, package_msg_name, package_msg_name, package_msg_name, package_msg_name)
                    else:
                        yield '        case %s._msgid: return { size: %s._size, magic1: %d, magic2: %d, baseSize: %d };\n' % (
                            package_msg_name, package_msg_name, magic1, magic2, msg.base_size)

                yield '        default: return undefined;\n'
                yield '    }\n'
                yield '}\n'
            yield '\n'


# =============================================================================
# Round-trip test code generator
# =============================================================================

# Field type set for primitives (used by the test generator below).
_TS_PRIM_TYPES = {"uint8", "int8", "uint16", "int16", "uint32", "int32",
                  "uint64", "int64", "float", "double", "bool"}


class TestTsGen():
    """Generator for TypeScript test code with dummy values for round-trip verification."""

    @staticmethod
    def _get_dummy_value(field, index=0):
        """Generate a dummy literal for a primitive/enum/string field."""
        type_name = field.field_type
        type_values = {
            "uint8": str((42 + index) % 256),
            "int8": str((42 + index) % 128),
            "uint16": str(1000 + index),
            "int16": str(500 + index),
            "uint32": str(123456 + index),
            "int32": str(123456 + index),
            "uint64": f"{9876543210 + index}n",
            "int64": f"{9876543210 + index}n",
            "float": str(round(3.14159 + index, 5)),
            "double": str(round(2.718281828 + index, 9)),
            "bool": "true" if index % 2 == 0 else "false",
        }
        if type_name in type_values:
            return type_values[type_name]
        if type_name in ("string", "bytes"):
            return f'"test_{index}"'
        if field.is_enum:
            return "0"
        # Nested struct - empty plain object accepted by the init applier
        return "{}"

    @staticmethod
    def _generate_field_init(field, prefix="msg", index=0):
        """Generate setter assignment code for a single field."""
        var_name = to_camel_case(field.name)
        type_name = field.field_type
        result = ""

        # Variable arrays / nested struct fields are modelled as arrays in TS.
        if field.is_array:
            if field.size_option is not None:
                count = min(field.size_option, 3)
                if type_name in ("string", "bytes"):
                    items = [f'"test_{i}"' for i in range(count)]
                    pad = ['""' for _ in range(field.size_option - count)]
                elif type_name == "bool":
                    # Setters for primitive bool arrays accept ``number[]``.
                    items = [str((42 + i) % 2) for i in range(count)]
                    pad = ["0" for _ in range(field.size_option - count)]
                elif type_name not in _TS_PRIM_TYPES and not field.is_enum:
                    # Nested struct array - use empty object literals
                    items = ["{}" for _ in range(count)]
                    pad = ["{}" for _ in range(field.size_option - count)]
                else:
                    items = [TestTsGen._get_dummy_value(field, i) for i in range(count)]
                    pad = ["0" for _ in range(field.size_option - count)]
                arr_literal = "[" + ", ".join(items + pad) + "]"
                result += f"    {prefix}.{var_name} = {arr_literal};\n"
            elif field.max_size is not None:
                num_elements = min(field.max_size, 3)
                if type_name in ("string", "bytes"):
                    items = [f'"test_{i}"' for i in range(num_elements)]
                elif type_name == "bool":
                    items = [str((42 + i) % 2) for i in range(num_elements)]
                elif type_name not in _TS_PRIM_TYPES and not field.is_enum:
                    items = ["{}" for _ in range(num_elements)]
                else:
                    items = [TestTsGen._get_dummy_value(field, i) for i in range(num_elements)]
                arr_literal = "[" + ", ".join(items) + "]"
                result += f"    {prefix}.{var_name}Count = {num_elements};\n"
                result += f"    {prefix}.{var_name}Data = {arr_literal};\n"
        elif type_name in ("string", "bytes"):
            if field.size_option is not None:
                result += f'    {prefix}.{var_name} = "test_string";\n'
            elif field.max_size is not None:
                test_str = "test_string"
                result += f'    {prefix}.{var_name}Length = {len(test_str)};\n'
                result += f'    {prefix}.{var_name}Data = "{test_str}";\n'
            else:
                result += f'    {prefix}.{var_name} = "test_string";\n'
        elif type_name not in _TS_PRIM_TYPES and not field.is_enum:
            # Single nested struct - the TS layout wraps it as a 1-element
            # struct array, so the setter accepts ``[{}]``.
            result += f"    {prefix}.{var_name} = [{{}}];\n"
        else:
            result += f"    {prefix}.{var_name} = {TestTsGen._get_dummy_value(field, index)};\n"

        return result

    @staticmethod
    def generate(package, imported_packages=None):
        """Generate TypeScript round-trip test code for a package."""
        package_kebab = package.name.replace('_', '-')

        yield '/**\n'
        yield ' * Automatically generated round-trip test code for struct-frame messages.\n'
        yield ' * For every message in the package this file populates fields with\n'
        yield ' * deterministic dummy values, encodes via BufferWriter, decodes back via\n'
        yield ' * AccumulatingReader and verifies that the decoded message matches the\n'
        yield ' * original. Every message is exercised against all five frame profiles.\n'
        yield f' * Generated by struct-frame {version}.\n'
        yield ' */\n\n'

        yield "import {\n"
        yield "    ProfileStandardWriter, ProfileStandardAccumulatingReader,\n"
        yield "    ProfileSensorWriter,   ProfileSensorAccumulatingReader,\n"
        yield "    ProfileIPCWriter,      ProfileIPCAccumulatingReader,\n"
        yield "    ProfileBulkWriter,     ProfileBulkAccumulatingReader,\n"
        yield "    ProfileNetworkWriter,  ProfileNetworkAccumulatingReader,\n"
        yield "} from './frame-profiles';\n"
        yield f"import * as Pkg from './{package_kebab}.structframe';\n"
        yield f"import {{ getMessageInfo }} from './{package_kebab}.structframe';\n"
        if imported_packages:
            for imp in imported_packages:
                imp_kebab = imp.replace('_', '-')
                yield f"import * as {pascal_case(imp)}Pkg from './{imp_kebab}.structframe';\n"
        yield "\n"

        # Profile name -> writer/reader/has_pkg_id/max_payload table.
        # Profiles without ``has_pkg_id`` cannot encode messages with msg_id > 255.
        # Profiles with a finite ``maxPayload`` reject messages whose ``_size`` exceeds it.
        yield "interface ProfileEntry {\n"
        yield "    name: string;\n"
        yield "    WriterCls: any;\n"
        yield "    ReaderCls: any;\n"
        yield "    hasPkgId: boolean;\n"
        yield "    maxPayload: number | null;\n"
        yield "}\n\n"

        yield "const PROFILES: ProfileEntry[] = [\n"
        yield "    { name: 'ProfileStandard', WriterCls: ProfileStandardWriter, ReaderCls: ProfileStandardAccumulatingReader, hasPkgId: false, maxPayload: 255 },\n"
        yield "    { name: 'ProfileSensor',   WriterCls: ProfileSensorWriter,   ReaderCls: ProfileSensorAccumulatingReader,   hasPkgId: false, maxPayload: null },\n"
        yield "    { name: 'ProfileIPC',      WriterCls: ProfileIPCWriter,      ReaderCls: ProfileIPCAccumulatingReader,      hasPkgId: false, maxPayload: null },\n"
        yield "    { name: 'ProfileBulk',     WriterCls: ProfileBulkWriter,     ReaderCls: ProfileBulkAccumulatingReader,     hasPkgId: true,  maxPayload: 65535 },\n"
        yield "    { name: 'ProfileNetwork',  WriterCls: ProfileNetworkWriter,  ReaderCls: ProfileNetworkAccumulatingReader,  hasPkgId: true,  maxPayload: 65535 },\n"
        yield "];\n\n"

        # Collect testable messages (skip oneof/variant messages).
        testable_messages = [(key, msg) for key, msg in package.sortedMessages().items()
                             if msg.id is not None and not getattr(msg, 'oneofs', {})]

        # Per-message factory functions.
        for key, msg in testable_messages:
            struct_name = msg.name
            func_name = f'createTest{struct_name}'
            yield f'export function {func_name}(): Pkg.{struct_name} {{\n'
            yield f'    const msg = new Pkg.{struct_name}();\n'
            field_index = 0
            for field_key, field in msg.fields.items():
                yield TestTsGen._generate_field_init(field, "msg", field_index)
                field_index += 1
            yield '    return msg;\n'
            yield '}\n\n'

        # Result + helper types.
        yield 'interface TestResult { passed: boolean; name: string; error: string; }\n\n'

        yield 'function verifyRoundtrip(msg: any, MsgCls: any, WriterCls: any, ReaderCls: any, getInfoFn: any): [boolean, string] {\n'
        yield '    try {\n'
        yield '        const bufSize = Math.max(2048, (MsgCls._size || 0) + 128);\n'
        yield '        const writer = new WriterCls(bufSize);\n'
        yield '        const written = writer.write(msg);\n'
        yield '        if (!written) return [false, "encode failed"];\n'
        yield '        const encoded = writer.data();\n'
        yield '        if (!encoded || encoded.length === 0) return [false, "empty encoded buffer"];\n'
        yield '\n'
        yield '        const reader = new ReaderCls(getInfoFn, Math.max(4096, bufSize * 2));\n'
        yield '        reader.addData(Buffer.from(encoded));\n'
        yield '        const result = reader.next();\n'
        yield '        if (!result || !result.valid) return [false, "parse failed"];\n'
        yield '        if (result.msgId !== MsgCls._msgid) {\n'
        yield '            return [false, `msg_id mismatch: expected ${MsgCls._msgid}, got ${result.msgId}`];\n'
        yield '        }\n'
        yield '\n'
        yield '        const decoded = MsgCls.deserialize(result);\n'
        yield '        if (!decoded) return [false, "deserialize returned null"];\n'
        yield '\n'
        yield '        const a = msg.serialize();\n'
        yield '        const b = decoded.serialize();\n'
        yield '        if (a.length !== b.length || !Buffer.from(a).equals(Buffer.from(b))) {\n'
        yield '            return [false, "decoded data differs from original"];\n'
        yield '        }\n'
        yield '        return [true, ""];\n'
        yield '    } catch (e: any) {\n'
        yield '        return [false, `exception: ${e && e.message ? e.message : e}`];\n'
        yield '    }\n'
        yield '}\n\n'

        yield 'function isCompatible(MsgCls: any, hasPkgId: boolean, maxPayload: number | null, getInfoFn: any): string | null {\n'
        yield '    if (!hasPkgId && (MsgCls._msgid > 255)) {\n'
        yield '        return "msg_id > 255 requires has_pkg_id profile";\n'
        yield '    }\n'
        yield '    if (maxPayload !== null && (MsgCls._size || 0) > maxPayload) {\n'
        yield '        return "message exceeds profile max_payload";\n'
        yield '    }\n'
        yield '    if (getInfoFn(MsgCls._msgid) === undefined) {\n'
        yield '        return "msg_id not registered for this profile (likely cross-package mismatch)";\n'
        yield '    }\n'
        yield '    return null;\n'
        yield '}\n\n'

        # Per-message test wrappers.
        for key, msg in testable_messages:
            struct_name = msg.name
            create_func = f'createTest{struct_name}'
            test_func = f'test{struct_name}'
            yield f'function {test_func}(WriterCls: any, ReaderCls: any, getInfoFn: any): TestResult {{\n'
            yield f'    const msg = {create_func}();\n'
            yield f'    const [passed, reason] = verifyRoundtrip(msg, Pkg.{struct_name}, WriterCls, ReaderCls, getInfoFn);\n'
            yield f'    return {{ passed, name: "{struct_name}", error: passed ? "" : reason }};\n'
            yield '}\n\n'

        yield f'export const TEST_MESSAGE_COUNT = {len(testable_messages)};\n\n'

        # Driver that runs all messages for one profile.
        yield '// Runs all message tests for one profile. Skipped (profile-incompatible)\n'
        yield '// messages are tracked separately from passes (NOT counted as passes);\n'
        yield '// tested[i] is set true when message i round-trips under this profile.\n'
        yield '// Returns [passed, skipped].\n'
        yield 'function runAllTests(WriterCls: any, ReaderCls: any, getInfoFn: any, hasPkgId: boolean, maxPayload: number | null, tested: boolean[], verbose: boolean): [number, number] {\n'
        yield '    let passed = 0;\n'
        yield '    let skipped = 0;\n'
        for idx, (key, msg) in enumerate(testable_messages):
            struct_name = msg.name
            test_func = f'test{struct_name}'
            yield f'    {{\n'
            yield f'        const skip = isCompatible(Pkg.{struct_name}, hasPkgId, maxPayload, getInfoFn);\n'
            yield f'        if (skip !== null) {{\n'
            yield f'            skipped += 1;\n'
            yield f'            if (verbose) console.log(`[SKIP] {struct_name}: ${{skip}}`);\n'
            yield f'        }} else {{\n'
            yield f'            const r = {test_func}(WriterCls, ReaderCls, getInfoFn);\n'
            yield f'            if (r.passed) {{\n'
            yield f'                passed += 1;\n'
            yield f'                tested[{idx}] = true;\n'
            yield f'                if (verbose) console.log(`[PASS] ${{r.name}}`);\n'
            yield f'            }} else if (verbose) {{\n'
            yield f'                console.log(`[FAIL] ${{r.name}}: ${{r.error}}`);\n'
            yield f'            }}\n'
            yield f'        }}\n'
            yield f'    }}\n'
        yield '    if (verbose) console.log(`  -> ${passed}/${TEST_MESSAGE_COUNT - skipped} passed (${skipped} skipped)`);\n'
        yield '    return [passed, skipped];\n'
        yield '}\n\n'

        yield 'export function runRoundtripAllProfiles(verbose: boolean = false): boolean {\n'
        yield '    let allOk = true;\n'
        yield '    const tested: boolean[] = new Array(TEST_MESSAGE_COUNT).fill(false);\n'
        yield '    for (const p of PROFILES) {\n'
        yield '        if (verbose) console.log(`\\n--- ${p.name} ---`);\n'
        yield '        const [passed, skipped] = runAllTests(p.WriterCls, p.ReaderCls, getMessageInfo, p.hasPkgId, p.maxPayload, tested, verbose);\n'
        yield '        const expected = TEST_MESSAGE_COUNT - skipped;\n'
        yield '        if (passed !== expected) {\n'
        yield '            allOk = false;\n'
        yield '            console.log(`[FAIL] ${p.name}: ${passed}/${expected} passed (${skipped} skipped)`);\n'
        yield '        } else if (verbose) {\n'
        yield '            console.log(`[OK] ${p.name}: ${passed}/${expected} passed (${skipped} skipped)`);\n'
        yield '        }\n'
        yield '    }\n'
        yield '    // Messages skipped under every profile are not exercised by this\n'
        yield '    // generated suite (e.g. cross-package messages the per-package registry\n'
        yield '    // cannot resolve). Reported loudly but non-fatally -- a profile that\n'
        yield '    // *attempts* a message and fails is already caught above.\n'
        yield '    const neverTested: number[] = [];\n'
        yield '    for (let i = 0; i < TEST_MESSAGE_COUNT; i++) { if (!tested[i]) neverTested.push(i); }\n'
        yield '    if (neverTested.length > 0) {\n'
        yield '        console.log(`[WARN] ${neverTested.length} message(s) skipped under every profile, not exercised by this suite (indices ${JSON.stringify(neverTested)})`);\n'
        yield '    }\n'
        yield '    return allOk;\n'
        yield '}\n\n'

        # Module-as-script entrypoint.
        yield 'if (require.main === module) {\n'
        yield '    const verbose = process.argv.includes("-v") || process.argv.includes("--verbose");\n'
        yield f'    console.log("Running round-trip tests for package \'{package.name}\' across 5 profiles...");\n'
        yield '    const ok = runRoundtripAllProfiles(verbose);\n'
        yield '    if (ok) {\n'
        yield f'        console.log("[TEST PASSED] All round-trip tests for \'{package.name}\' succeeded.");\n'
        yield '        process.exit(0);\n'
        yield '    } else {\n'
        yield f'        console.log("[TEST FAILED] Round-trip tests for \'{package.name}\' had failures.");\n'
        yield '        process.exit(1);\n'
        yield '    }\n'
        yield '}\n'



