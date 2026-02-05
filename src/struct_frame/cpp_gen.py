#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
C++ code generator for struct-frame.

This module generates C++ code for struct serialization with template-based
Pack/Unpack methods and optional namespace support.
"""

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase, build_enum_leading_comments, build_enum_values
import time

StyleC = NamingStyleC()

cpp_types = {"uint8": "uint8_t",
             "int8": "int8_t",
             "uint16": "uint16_t",
             "int16": "int16_t",
             "uint32": "uint32_t",
             "int32": "int32_t",
             "bool": "bool",
             "float": "float",
             "double": "double",
             "uint64": 'uint64_t',
             "int64":  'int64_t',
             "string": "char",
             }


class EnumCppGen():
    @staticmethod
    def generate(field, use_namespace=False):
        result = build_enum_leading_comments(field.comments)

        # When using namespaces, don't prefix with package name
        if use_namespace:
            enumName = field.name
        else:
            enumName = '%s%s' % (pascalCase(field.package), field.name)
        # Use enum class for C++
        result += 'enum class %s : uint8_t {\n' % (enumName)

        enum_values = build_enum_values(
            field, StyleC,
            value_format='{indent}{name} = {value}{comma}',
            skip_trailing_comma=True
        )

        result += '\n'.join(enum_values)
        result += '\n};\n'

        # Add enum-to-string helper function
        result += f'\n/* Convert {enumName} to string */\n'
        result += f'inline const char* {enumName}_to_string({enumName} value) {{\n'
        result += '    switch (value) {\n'
        for d in field.data:
            result += f'        case {enumName}::{StyleC.enum_entry(d)}: return "{StyleC.enum_entry(d)}";\n'
        result += '        default: return "UNKNOWN";\n'
        result += '    }\n'
        result += '}\n'

        return result


class FieldCppGen():
    @staticmethod
    def generate(field, use_namespace=False):
        result = ''
        var_name = field.name
        type_name = field.fieldType

        # Handle basic type resolution
        if type_name in cpp_types:
            base_type = cpp_types[type_name]
        else:
            if use_namespace:
                # When using namespaces, don't prefix type names
                base_type = type_name
            else:
                # Flat namespace mode: prefix with package name
                if field.isEnum:
                    base_type = '%s%s' % (pascalCase(field.package), type_name)
                else:
                    base_type = '%s%s' % (pascalCase(field.package), type_name)

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                # String arrays need both array size and individual string size
                if field.size_option is not None:
                    # Fixed string array: size_option strings, each element_size chars
                    declaration = f"char {var_name}[{field.size_option}][{field.element_size}];"
                    comment = f"  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars"
                elif field.max_size is not None:
                    # Variable string array: count (uint8_t or uint16_t) + max_size strings of element_size chars each
                    count_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                    declaration = f"struct {{ {count_type} count; char data[{field.max_size}][{field.element_size}]; }} {var_name};"
                    comment = f"  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars"
                else:
                    declaration = f"char {var_name}[1][1];"  # Fallback
                    comment = "  // String array (error in size specification)"
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array: always exact size
                    declaration = f"{base_type} {var_name}[{field.size_option}];"
                    comment = f"  // Fixed array: always {field.size_option} elements"
                elif field.max_size is not None:
                    # Variable array: count (uint8_t or uint16_t) + max elements
                    count_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                    declaration = f"struct {{ {count_type} count; {base_type} data[{field.max_size}]; }} {var_name};"
                    comment = f"  // Variable array: up to {field.max_size} elements"
                else:
                    declaration = f"{base_type} {var_name}[1];"  # Fallback
                    comment = "  // Array (error in size specification)"

            result += f"    {declaration}{comment}"

        # Handle regular strings
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string: exactly size_option characters
                declaration = f"char {var_name}[{field.size_option}];"
                comment = f"  // Fixed string: exactly {field.size_option} chars"
            elif field.max_size is not None:
                # Variable string: length (uint8_t or uint16_t) + max characters
                length_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                declaration = f"struct {{ {length_type} length; char data[{field.max_size}]; }} {var_name};"
                comment = f"  // Variable string: up to {field.max_size} chars"
            else:
                declaration = f"char {var_name}[1];"  # Fallback
                comment = "  // String (error in size specification)"

            result += f"    {declaration}{comment}"

        # Handle regular fields
        else:
            result += f"    {base_type} {var_name};"

        # Add leading comments
        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = c + "\n" + result

        return result



class OneOfCppGen():
    @staticmethod
    def generate_discriminator_enum(oneof, msg_name, use_namespace=False):
        """Generate a discriminator enum for field_order oneofs."""
        if not oneof.auto_discriminator or oneof.discriminator_type != "field_order":
            return ''
        
        result = ''
        enum_name = f'{msg_name}{pascalCase(oneof.name)}Field'
        
        result += f'/* Discriminator enum for {msg_name}::{oneof.name} oneof */\n'
        result += f'enum class {enum_name} : uint8_t {{\n'
        result += f'    NONE = 0,\n'
        
        for idx, (field_name, field) in enumerate(oneof.fields.items()):
            field_order = idx + 1
            # Use SCREAMING_SNAKE_CASE for enum values
            enum_value = CamelToSnakeCase(field_name).upper()
            result += f'    {enum_value} = {field_order},\n'
        
        result += f'}};\n\n'
        return result
    
    @staticmethod
    def get_discriminator_enum_name(oneof, msg_name):
        """Get the enum type name for a field_order discriminator."""
        return f'{msg_name}{pascalCase(oneof.name)}Field'
    
    @staticmethod
    def generate(oneof, use_namespace=False, package=None, msg_name=None):
        """Generate C++ union for a oneof construct."""
        result = ''
        
        # Add comments
        if oneof.comments:
            for c in oneof.comments:
                result += '%s\n' % c
        
        # If discriminator is enabled, add discriminator field first
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                # Use uint16_t since message IDs can be up to 65535
                result += f'    uint16_t {oneof.name}_discriminator;  // Auto-generated message ID discriminator\n'
            else:  # field_order
                # Use the generated enum type for better type safety
                enum_name = OneOfCppGen.get_discriminator_enum_name(oneof, msg_name) if msg_name else 'uint8_t'
                result += f'    {enum_name} {oneof.name}_discriminator;  // Auto-generated field order discriminator\n'
        
        # Generate the union
        result += f'    union {{\n'
        
        # Generate each field in the union
        for key, field in oneof.fields.items():
            field_code = FieldCppGen.generate(field, use_namespace)
            # Indent the field code properly (remove leading spaces and add union indent)
            field_code = field_code.strip()
            result += f'        {field_code}\n'
        
        result += f'    }} {oneof.name};'
        
        return result


class MessageCppGen():
    @staticmethod
    def _mem_compare_expr(var_name):
        """Generate memcmp comparison for fixed-size arrays and structs."""
        return f'(std::memcmp({var_name}, other.{var_name}, sizeof({var_name})) == 0)'
    
    @staticmethod
    def _variable_array_compare_expr(var_name):
        """Generate comparison for variable-length arrays with count field.
        
        Compares count first, then compares the full data buffer. Using sizeof(data)
        compares the entire allocated buffer which is safe for equality checking.
        """
        return f'({var_name}.count == other.{var_name}.count && std::memcmp({var_name}.data, other.{var_name}.data, sizeof({var_name}.data)) == 0)'
    
    @staticmethod
    def _generate_field_comparison(field, use_namespace=False):
        """Generate comparison code for a single field."""
        var_name = field.name
        type_name = field.fieldType
        has_fixed_size = field.size_option is not None
        has_max_size = field.max_size is not None
        
        # Arrays use memcmp-based comparison
        if field.is_array:
            if has_max_size:
                return MessageCppGen._variable_array_compare_expr(var_name)
            return MessageCppGen._mem_compare_expr(var_name)
        
        # String fields need special handling
        if field.fieldType == "string":
            if has_fixed_size:
                return f'(std::strncmp({var_name}, other.{var_name}, {field.size_option}) == 0)'
            if has_max_size:
                return f'({var_name}.length == other.{var_name}.length && std::strncmp({var_name}.data, other.{var_name}.data, {field.max_size}) == 0)'
            return f'(std::strcmp({var_name}, other.{var_name}) == 0)'
        
        # Enums and primitives use direct equality
        if field.isEnum or type_name in cpp_types:
            return f'({var_name} == other.{var_name})'
        
        # Nested structs use memcmp
        return f'(std::memcmp(&{var_name}, &other.{var_name}, sizeof({var_name})) == 0)'
    
    @staticmethod
    def _generate_oneof_comparison(oneof):
        """Generate comparison code for a oneof (union)."""
        comparisons = []
        
        # If auto-discriminator is enabled, compare discriminator first
        if oneof.auto_discriminator:
            comparisons.append(f'({oneof.name}_discriminator == other.{oneof.name}_discriminator)')
        
        # Compare the union as raw bytes (since we don't know which variant is active)
        comparisons.append(f'(std::memcmp(&{oneof.name}, &other.{oneof.name}, sizeof({oneof.name})) == 0)')
        
        return ' && '.join(comparisons)
    
    @staticmethod
    def generate(msg, use_namespace=False, package=None, equality=False, no_packed=False):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '%s\n' % c

        # When using namespaces, don't prefix struct name
        if use_namespace:
            structName = msg.name
            defineName = CamelToSnakeCase(msg.name).upper()
        else:
            structName = '%s%s' % (pascalCase(msg.package), msg.name)
            defineName = '%s_%s' % (CamelToSnakeCase(
                msg.package).upper(), CamelToSnakeCase(msg.name).upper())

        size = 1
        if not msg.fields and not msg.oneofs:
            # Empty structs are allowed in C++ but we add a dummy field
            # for consistency with the C implementation
            size = 1
        else:
            size = msg.size

        # Determine if this message has an ID (for MessageBase inheritance)
        has_msg_id = msg.id is not None
        
        # Compute the message ID value
        msg_id_value = None
        if has_msg_id:
            if package and package.package_id is not None:
                msg_id_value = (package.package_id << 8) | msg.id
            else:
                msg_id_value = msg.id

        # Get magic bytes (default to 0 if not present)
        magic1 = msg.magic_bytes[0] if msg.magic_bytes else 0
        magic2 = msg.magic_bytes[1] if msg.magic_bytes else 0

        # Generate struct with optional MessageBase inheritance
        if has_msg_id:
            result += 'struct %s : FrameParsers::MessageBase<%s, %d, %d, %d, %d> {\n' % (
                structName, structName, msg_id_value, size, magic1, magic2)
        else:
            result += 'struct %s {' % structName

        result += '\n'

        if not msg.fields and not msg.oneofs:
            result += '    char dummy_field;\n'

        # Generate regular fields
        result += '\n'.join([FieldCppGen.generate(f, use_namespace)
                            for key, f in msg.fields.items()])
        
        # Generate oneofs
        if msg.oneofs:
            if msg.fields:
                result += '\n'
            result += '\n'.join([OneOfCppGen.generate(o, use_namespace, package, structName)
                                for key, o in msg.oneofs.items()])
        
        # Ensure newline after fields/oneofs
        if msg.fields or msg.oneofs:
            result += '\n'
        
        # Generate equality operator if requested
        if equality:
            result += '\n'
            result += f'    bool operator==(const {structName}& other) const {{\n'
            
            comparisons = []
            
            # Handle empty structs
            if not msg.fields and not msg.oneofs:
                comparisons.append('(dummy_field == other.dummy_field)')
            else:
                # Generate field comparisons
                for key, field in msg.fields.items():
                    comparisons.append(MessageCppGen._generate_field_comparison(field, use_namespace))
                
                # Generate oneof comparisons
                for key, oneof in msg.oneofs.items():
                    comparisons.append(MessageCppGen._generate_oneof_comparison(oneof))
            
            if comparisons:
                result += '        return ' + ' &&\n               '.join(comparisons) + ';\n'
            else:
                result += '        return true;\n'
            
            result += '    }\n'
            result += f'    bool operator!=(const {structName}& other) const {{ return !(*this == other); }}\n'
        
        # Add variable message constants and methods
        if msg.variable:
            result += MessageCppGen._generate_variable_methods(msg, structName)
        
        # Add unified unpack() method only for messages with MSG_ID (have MessageBase)
        if has_msg_id:
            result += MessageCppGen._generate_unified_unpack(msg, structName, no_packed=no_packed)
        
        # When no_packed is active, generate field-by-field methods for non-variable messages
        if no_packed and not msg.variable and msg.fields:
            result += MessageCppGen._generate_no_packed_methods(msg, structName)
        
        # Add envelope methods if this is an envelope message
        if msg.is_envelope:
            result += MessageCppGen._generate_envelope_methods(msg, structName, use_namespace, package)
        
        result += '};\n'

        return result + '\n'
    
    @staticmethod
    def _generate_variable_methods(msg, structName):
        """Generate variable-length encoding methods for C++ structs."""
        result = ''
        
        # Add MIN_SIZE and IS_VARIABLE constants
        result += f'\n    // Variable-length message constants\n'
        result += f'    static constexpr size_t MIN_SIZE = {msg.min_size};\n'
        result += f'    static constexpr bool IS_VARIABLE = true;\n'
        
        # Generate serialized_size method
        result += f'\n    /**\n'
        result += f'     * Calculate the serialized size using variable-length encoding.\n'
        result += f'     * @return The size in bytes when serialized (between MIN_SIZE and MAX_SIZE)\n'
        result += f'     */\n'
        result += f'    size_t serialized_size() const {{\n'
        result += f'        size_t size = 0;\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.fieldType, (field.size - 1) // field.max_size)
                result += f'        size += 1 + ({var_name}.count * {element_size});  // {var_name}\n'
            elif field.fieldType == "string" and field.max_size is not None:
                # Variable string
                result += f'        size += 1 + {var_name}.length;  // {var_name}\n'
            else:
                result += f'        size += {field.size};  // {var_name}\n'
        
        result += f'        return size;\n'
        result += f'    }}\n'
        
        # Generate serialize method (was pack_variable)
        result += f'\n    /**\n'
        result += f'     * Serialize message using variable-length encoding.\n'
        result += f'     * @param buffer Output buffer (must be at least serialized_size() bytes)\n'
        result += f'     * @return Number of bytes written\n'
        result += f'     */\n'
        result += f'    size_t serialize(uint8_t* buffer) const {{\n'
        result += f'        size_t offset = 0;\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.fieldType, (field.size - 1) // field.max_size)
                result += f'        buffer[offset++] = {var_name}.count;\n'
                result += f'        std::memcpy(buffer + offset, {var_name}.data, {var_name}.count * {element_size});\n'
                result += f'        offset += {var_name}.count * {element_size};\n'
            elif field.fieldType == "string" and field.max_size is not None:
                result += f'        buffer[offset++] = {var_name}.length;\n'
                result += f'        std::memcpy(buffer + offset, {var_name}.data, {var_name}.length);\n'
                result += f'        offset += {var_name}.length;\n'
            else:
                result += f'        std::memcpy(buffer + offset, &{var_name}, {field.size});\n'
                result += f'        offset += {field.size};\n'
        
        result += f'        return offset;\n'
        result += f'    }}\n'
        
        # Generate _deserialize_variable method (was unpack_variable, now private)
        result += f'\n    /**\n'
        result += f'     * Deserialize message from variable-length encoding (internal method).\n'
        result += f'     * @param buffer Input buffer\n'
        result += f'     * @param buffer_size Size of input buffer\n'
        result += f'     * @return Number of bytes read, or 0 if buffer too small\n'
        result += f'     */\n'
        result += f'    size_t _deserialize_variable(const uint8_t* buffer, size_t buffer_size) {{\n'
        result += f'        size_t offset = 0;\n'
        result += f'        std::memset(this, 0, sizeof(*this));\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                else:
                    element_size = type_sizes.get(field.fieldType, (field.size - 1) // field.max_size)
                result += f'        if (offset >= buffer_size) return 0;\n'
                result += f'        {var_name}.count = buffer[offset++];\n'
                result += f'        if ({var_name}.count > {field.max_size}) {var_name}.count = {field.max_size};\n'
                result += f'        if (offset + {var_name}.count * {element_size} > buffer_size) return 0;\n'
                result += f'        std::memcpy({var_name}.data, buffer + offset, {var_name}.count * {element_size});\n'
                result += f'        offset += {var_name}.count * {element_size};\n'
            elif field.fieldType == "string" and field.max_size is not None:
                result += f'        if (offset >= buffer_size) return 0;\n'
                result += f'        {var_name}.length = buffer[offset++];\n'
                result += f'        if ({var_name}.length > {field.max_size}) {var_name}.length = {field.max_size};\n'
                result += f'        if (offset + {var_name}.length > buffer_size) return 0;\n'
                result += f'        std::memcpy({var_name}.data, buffer + offset, {var_name}.length);\n'
                result += f'        offset += {var_name}.length;\n'
            else:
                result += f'        if (offset + {field.size} > buffer_size) return 0;\n'
                result += f'        std::memcpy(&{var_name}, buffer + offset, {field.size});\n'
                result += f'        offset += {field.size};\n'
        
        result += f'        return offset;\n'
        result += f'    }}\n'
        
        return result

    @staticmethod
    def _generate_unified_unpack(msg, structName, no_packed=False):
        """Generate unified deserialize() method that works for both variable and non-variable messages."""
        result = ''
        
        result += f'\n    /**\n'
        result += f'     * Deserialize message from binary data.\n'
        result += f'     * Works for both variable and non-variable messages.\n'
        result += f'     * Uses compile-time dispatch for zero runtime overhead.\n'
        result += f'     * For variable messages with minimal profiles (buffer_size == MAX_SIZE),\n'
        result += f'     * uses direct copy instead of variable-length deserialization.\n'
        result += f'     * @param buffer Input buffer containing serialized message data\n'
        result += f'     * @param buffer_size Size of input buffer\n'
        result += f'     * @return Number of bytes read, or 0 if buffer too small\n'
        result += f'     */\n'
        result += f'    size_t deserialize(const uint8_t* buffer, size_t buffer_size) {{\n'
        
        if msg.variable:
            # Variable message: check if it's minimal profile (buffer_size == MAX_SIZE)
            # If so, use direct copy; otherwise use variable deserialization
            result += f'        // Variable message - check encoding format\n'
            result += f'        if (buffer_size == MAX_SIZE) {{\n'
            result += f'            // Minimal profile format (MAX_SIZE encoding)\n'
            result += f'            std::memcpy(this, buffer, MAX_SIZE);\n'
            result += f'            return MAX_SIZE;\n'
            result += f'        }} else {{\n'
            result += f'            // Variable-length format\n'
            result += f'            return _deserialize_variable(buffer, buffer_size);\n'
            result += f'        }}\n'
        elif no_packed and msg.fields:
            # No-packed mode: use field-by-field deserialization
            result += f'        return _deserialize_fields(buffer, buffer_size);\n'
        else:
            # Non-variable message: simple memcpy with size check
            result += f'        // Fixed-size message - use direct copy\n'
            result += f'        if (buffer_size < MAX_SIZE) return 0;\n'
            result += f'        std::memcpy(this, buffer, MAX_SIZE);\n'
            result += f'        return MAX_SIZE;\n'
        
        result += f'    }}\n'
        
        # Add FrameMsgInfo overload
        result += f'\n    /**\n'
        result += f'     * Deserialize message from FrameMsgInfo (convenience overload).\n'
        result += f'     * @param frame_info Frame information from frame parser\n'
        result += f'     * @return Number of bytes read, or 0 if buffer too small\n'
        result += f'     */\n'
        result += f'    size_t deserialize(const FrameParsers::FrameMsgInfo& frame_info) {{\n'
        result += f'        return deserialize(frame_info.msg_data, frame_info.msg_len);\n'
        result += f'    }}\n'
        
        # Add serialize method for non-variable messages
        if not msg.variable:
            if no_packed and msg.fields:
                result += f'\n    /**\n'
                result += f'     * Serialize message to binary data (field-by-field, no packed struct dependency).\n'
                result += f'     * @param buffer Output buffer (must be at least MAX_SIZE bytes)\n'
                result += f'     * @return Number of bytes written\n'
                result += f'     */\n'
                result += f'    size_t serialize(uint8_t* buffer) const {{\n'
                result += f'        return _serialize_fields(buffer);\n'
                result += f'    }}\n'
            else:
                result += f'\n    /**\n'
                result += f'     * Serialize message to binary data.\n'
                result += f'     * @param buffer Output buffer (must be at least MAX_SIZE bytes)\n'
                result += f'     * @return Number of bytes written\n'
                result += f'     */\n'
                result += f'    size_t serialize(uint8_t* buffer) const {{\n'
                result += f'        std::memcpy(buffer, this, MAX_SIZE);\n'
                result += f'        return MAX_SIZE;\n'
                result += f'    }}\n'
        
        return result

    @staticmethod
    def _generate_no_packed_methods(msg, structName):
        """Generate field-by-field serialize/deserialize methods for non-variable messages without packed structs."""
        result = ''
        
        # Determine how to reference the message size
        # Messages with msg_id inherit MAX_SIZE from MessageBase; others need a literal
        wire_size = 'MAX_SIZE' if msg.id is not None else str(msg.size)
        
        # Internal serialize helper: writes each field individually
        result += f'\n    /**\n'
        result += f'     * Serialize each field individually (no packed struct dependency).\n'
        result += f'     * @param buffer Output buffer (must be at least {wire_size} bytes)\n'
        result += f'     * @return Number of bytes written\n'
        result += f'     */\n'
        result += f'    size_t _serialize_fields(uint8_t* buffer) const {{\n'
        result += f'        size_t pos = 0;\n'
        
        for key, field in msg.fields.items():
            result += f'        std::memcpy(buffer + pos, &{field.name}, {field.size});\n'
            result += f'        pos += {field.size};\n'
        
        result += f'        return pos;\n'
        result += f'    }}\n'
        
        # Internal deserialize helper: reads each field individually
        result += f'\n    /**\n'
        result += f'     * Deserialize each field individually (no packed struct dependency).\n'
        result += f'     * @param buffer Input buffer\n'
        result += f'     * @param buffer_size Size of input buffer\n'
        result += f'     * @return Number of bytes consumed, or 0 if buffer too small\n'
        result += f'     */\n'
        result += f'    size_t _deserialize_fields(const uint8_t* buffer, size_t buffer_size) {{\n'
        result += f'        if (buffer_size < {wire_size}) return 0;\n'
        result += f'        size_t pos = 0;\n'
        result += f'        std::memset(this, 0, sizeof(*this));\n'
        
        for key, field in msg.fields.items():
            result += f'        std::memcpy(&{field.name}, buffer + pos, {field.size});\n'
            result += f'        pos += {field.size};\n'
        
        result += f'        return pos;\n'
        result += f'    }}\n'
        
        return result

    @staticmethod
    def _generate_envelope_methods(msg, structName, use_namespace, package):
        """Generate envelope-specific helper methods for wrapping inner messages."""
        result = ''
        
        # Get the single oneof (validation ensures exactly one exists)
        oneof_name = list(msg.oneofs.keys())[0]
        oneof = msg.oneofs[oneof_name]
        
        result += f'\n    // ========================================\n'
        result += f'    // Envelope message helper methods\n'
        result += f'    // ========================================\n'
        
        # Build list of valid payload types
        payload_types = []
        payload_msg_ids = []
        for field_name, field in oneof.fields.items():
            if use_namespace:
                payload_type = field.fieldType
            else:
                type_pkg = field.type_package if field.type_package else field.package
                payload_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
            payload_types.append((field_name, payload_type))
            if oneof.discriminator_type == "msgid":
                payload_msg_ids.append(f'{payload_type}::MSG_ID')
        
        # Generate parameter list for envelope fields (non-oneof fields)
        param_list = []
        init_list = []
        for f_name, f in msg.fields.items():
            if f.fieldType in cpp_types:
                cpp_type = cpp_types[f.fieldType]
            else:
                if use_namespace:
                    cpp_type = f.fieldType
                else:
                    cpp_type = '%s%s' % (pascalCase(f.package), f.fieldType)
            
            if f.is_array or f.fieldType == "string":
                pass  # Skip arrays/strings for simplicity
            else:
                param_list.append(f'{cpp_type} {f.name}')
                init_list.append(f'        envelope.{f.name} = {f.name};')
        
        if oneof.discriminator_type == "msgid":
            # Generate a single templated wrap method with compile-time constraint using MSG_ID
            result += f'\n    /**\n'
            result += f'     * Create a {structName} envelope wrapping a payload message.\n'
            result += f'     * Only accepts valid payload types: {", ".join([pt[1] for pt in payload_types])}\n'
            result += f'     * @tparam T The payload message type (must be one of the valid types)\n'
            result += f'     * @param payload The message to wrap\n'
            for f_name, f in msg.fields.items():
                if f.is_array or f.fieldType == "string":
                    continue
                result += f'     * @param {f.name} Envelope field value\n'
            result += f'     * @return A fully initialized {structName} envelope\n'
            result += f'     */\n'
            
            # Template constraint: T::MSG_ID must match one of the valid payload MSG_IDs
            valid_ids_check = ' || '.join([f'T::MSG_ID == {msg_id}' for msg_id in payload_msg_ids])
            all_template_params = param_list + ['const T& payload']
            
            result += f'    template<typename T, typename = std::enable_if_t<{valid_ids_check}>>\n'
            result += f'    static {structName} wrap({", ".join(all_template_params)}) {{\n'
            result += f'        {structName} envelope{{}};\n'
            
            # Initialize envelope fields
            for init_line in init_list:
                result += f'{init_line}\n'
            
            # Set the discriminator
            if oneof.auto_discriminator:
                result += f'        envelope.{oneof_name}_discriminator = T::MSG_ID;\n'
            
            # Copy payload based on which type it is
            result += f'        // Copy payload into the correct union field based on MSG_ID\n'
            for field_name, payload_type in payload_types:
                result += f'        if constexpr (T::MSG_ID == {payload_type}::MSG_ID) {{\n'
                result += f'            std::memcpy(&envelope.{oneof_name}.{field_name}, &payload, sizeof(T));\n'
                result += f'        }}\n'
            
            result += f'        return envelope;\n'
            result += f'    }}\n'
            
            # Generate a helper to get the active payload type
            if oneof.auto_discriminator:
                result += f'\n    /**\n'
                result += f'     * Get the message ID of the wrapped payload.\n'
                result += f'     * @return The message ID of the payload in the {oneof_name} union\n'
                result += f'     */\n'
                result += f'    uint16_t getPayloadMessageId() const {{\n'
                result += f'        return {oneof_name}_discriminator;\n'
                result += f'    }}\n'
        
        else:  # field_order discriminator
            # Get the enum type name
            enum_name = OneOfCppGen.get_discriminator_enum_name(oneof, structName)
            
            # Generate separate wrap methods for each payload type
            for idx, (field_name, payload_type) in enumerate(payload_types):
                field_order = idx + 1  # 1-based index
                enum_value = CamelToSnakeCase(field_name).upper()
                all_wrap_params = param_list + [f'const {payload_type}& payload']
                
                result += f'\n    /**\n'
                result += f'     * Create a {structName} envelope wrapping a {payload_type} payload.\n'
                result += f'     * @param payload The {payload_type} message to wrap\n'
                for f_name, f in msg.fields.items():
                    if f.is_array or f.fieldType == "string":
                        continue
                    result += f'     * @param {f.name} Envelope field value\n'
                result += f'     * @return A fully initialized {structName} envelope\n'
                result += f'     */\n'
                result += f'    static {structName} wrap({", ".join(all_wrap_params)}) {{\n'
                result += f'        {structName} envelope{{}};\n'
                
                # Initialize envelope fields
                for init_line in init_list:
                    result += f'{init_line}\n'
                
                # Set the discriminator using enum value
                if oneof.auto_discriminator:
                    result += f'        envelope.{oneof_name}_discriminator = {enum_name}::{enum_value};\n'
                
                # Copy payload
                result += f'        std::memcpy(&envelope.{oneof_name}.{field_name}, &payload, sizeof({payload_type}));\n'
                result += f'        return envelope;\n'
                result += f'    }}\n'
            
            # Generate a helper to get the field order
            if oneof.auto_discriminator:
                result += f'\n    /**\n'
                result += f'     * Get the discriminator value of the wrapped payload.\n'
                result += f'     * @return The {enum_name} enum value for the active payload\n'
                result += f'     */\n'
                result += f'    {enum_name} getPayloadField() const {{\n'
                result += f'        return {oneof_name}_discriminator;\n'
                result += f'    }}\n'
        
        return result


class FileCppGen():
    @staticmethod
    def generate(package, equality=False, no_packed=False):
        yield '/* Automatically generated struct frame header for C++ */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        yield '#pragma once\n'
        yield '#include <cstdint>\n'
        yield '#include <cstddef>\n'
        
        # Include cstring for string comparison, or when no_packed needs field-by-field ops
        if equality or no_packed:
            yield '#include <cstring>\n'
        
        # Always include frame_base.hpp for FrameMsgInfo and MessageBase
        # (needed for deserialize(FrameMsgInfo) overload and message base class)
        yield '#include "frame_base.hpp"\n'
        yield '\n'

        # Check if package has package ID - if so, use namespaces
        use_namespace = package.package_id is not None

        if use_namespace:
            # Convert package name to valid C++ namespace (snake_case)
            namespace_name = CamelToSnakeCase(package.name)
            yield f'namespace {namespace_name} {{\n\n'
            
            # Add package ID constant
            yield f'/* Package ID for extended message IDs */\n'
            yield f'constexpr uint8_t PACKAGE_ID = {package.package_id};\n\n'

        # include additional header files if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumCppGen.generate(enum, use_namespace) + '\n'

        # Generate discriminator enums for field_order oneofs (must come before struct definitions)
        has_discriminator_enums = False
        for key, msg in package.messages.items():
            structName = msg.name if use_namespace else '%s%s' % (pascalCase(msg.package), msg.name)
            for oneof_name, oneof in msg.oneofs.items():
                enum_code = OneOfCppGen.generate_discriminator_enum(oneof, structName, use_namespace)
                if enum_code:
                    if not has_discriminator_enums:
                        yield '/* Oneof discriminator enums */\n'
                        has_discriminator_enums = True
                    yield enum_code

        if package.messages:
            yield '/* Struct definitions */\n'
            if not no_packed:
                yield '#pragma pack(push, 1)\n'
            # Need to sort messages to make sure dependencies are properly met

            for key, msg in package.sortedMessages().items():
                yield MessageCppGen.generate(msg, use_namespace, package, equality, no_packed=no_packed) + '\n'
            if not no_packed:
                yield '#pragma pack(pop)\n\n'
            else:
                yield '\n'

        # Generate get_message_length function
        if package.messages:
            yield 'namespace FrameParsers {\n\n'
            
            if use_namespace:
                # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                yield 'inline bool get_message_length(uint16_t msg_id, size_t* size) {\n'
                yield '    // Extract package ID and message ID from 16-bit message ID\n'
                yield '    uint8_t pkg_id = (msg_id >> 8) & 0xFF;\n'
                yield '    uint8_t local_msg_id = msg_id & 0xFF;\n'
                yield '    \n'
                yield f'    // Check if this is our package\n'
                yield f'    if (pkg_id != PACKAGE_ID) {{\n'
                yield f'        return false;\n'
                yield f'    }}\n'
                yield '    \n'
                yield '    switch (local_msg_id) {\n'
            else:
                # Flat namespace mode: 8-bit message ID
                yield 'inline bool get_message_length(size_t msg_id, size_t* size) {\n'
                yield '    switch (msg_id) {\n'
            
            for key, msg in package.sortedMessages().items():
                if use_namespace:
                    structName = msg.name
                else:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                if msg.id is not None:
                    if use_namespace:
                        # When using package ID, compare against local message ID
                        yield '        case %d: *size = %s::MAX_SIZE; return true;\n' % (msg.id, structName)
                    else:
                        # No package ID, compare against MSG_ID from MessageBase
                        yield '        case %s::MSG_ID: *size = %s::MAX_SIZE; return true;\n' % (structName, structName)

            yield '        default: break;\n'
            yield '    }\n'
            yield '    return false;\n'
            yield '}\n\n'
            
            # Generate unified get_message_info function
            if use_namespace:
                # When using package ID, message ID is 16-bit
                yield 'inline MessageInfo get_message_info(uint16_t msg_id) {\n'
                yield '    // Extract package ID and message ID from 16-bit message ID\n'
                yield '    uint8_t pkg_id = (msg_id >> 8) & 0xFF;\n'
                yield '    uint8_t local_msg_id = msg_id & 0xFF;\n'
                yield '    \n'
                yield f'    // Check if this is our package\n'
                yield f'    if (pkg_id != PACKAGE_ID) {{\n'
                yield f'        return MessageInfo{{}};\n'
                yield f'    }}\n'
                yield '    \n'
                yield '    switch (local_msg_id) {\n'
            else:
                # Flat namespace mode: 8-bit message ID
                yield 'inline MessageInfo get_message_info(uint16_t msg_id) {\n'
                yield '    switch (msg_id) {\n'
            
            for key, msg in package.sortedMessages().items():
                if use_namespace:
                    structName = msg.name
                else:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    
                if msg.id is not None:
                    if use_namespace:
                        # When using package ID, compare against local message ID
                        yield '        case %d: return MessageInfo{%s::MAX_SIZE, %s::MAGIC1, %s::MAGIC2};\n' % (
                            msg.id, structName, structName, structName)
                    else:
                        # No package ID, compare against MSG_ID from MessageBase
                        yield '        case %s::MSG_ID: return MessageInfo{%s::MAX_SIZE, %s::MAGIC1, %s::MAGIC2};\n' % (
                            structName, structName, structName, structName)

            yield '        default: break;\n'
            yield '    }\n'
            yield '    return MessageInfo{};\n'
            yield '}\n\n'
            
            yield '}  // namespace FrameParsers\n'
            
        if use_namespace:
            yield f'\n}}  // namespace {namespace_name}\n'


class TestCppGen():
    """Generator for C++ test code with dummy values for round-trip verification."""
    
    @staticmethod
    def _get_dummy_value(field, use_namespace=False, index=0):
        """Generate a dummy value for a field based on its type."""
        type_name = field.fieldType
        
        # Basic type dummy values - values are computed as Python integers and formatted into C++ literals
        base_uint64 = 9876543210
        base_int64 = 9876543210
        base_float = 3.14159
        
        type_values = {
            "uint8": f"{(42 + index) % 256}",
            "int8": f"{(42 + index) % 128}",
            "uint16": f"{1000 + index}",
            "int16": f"{500 + index}",
            "uint32": f"{123456 + index}U",
            "int32": f"{123456 + index}",
            "uint64": f"{base_uint64 + index}ULL",
            "int64": f"{base_int64 + index}LL",
            "float": f"{base_float + index}f",
            "double": f"{2.718281828 + index}",
            "bool": "true" if index % 2 == 0 else "false",
        }
        
        if type_name in type_values:
            return type_values[type_name]
        elif type_name == "string":
            return f'"test_{index}"'
        elif field.isEnum:
            # Return the first enum value - this is a safe default
            if use_namespace:
                return f"static_cast<{type_name}>(0)"
            else:
                return f"static_cast<{pascalCase(field.package)}{type_name}>(0)"
        else:
            # Nested struct - return empty braces for aggregate init
            return "{}"
        
    @staticmethod
    def _generate_field_init(field, use_namespace=False, prefix="msg", index=0):
        """Generate initialization code for a field."""
        var_name = field.name
        type_name = field.fieldType
        result = ""
        
        # Handle arrays
        if field.is_array:
            if field.size_option is not None:
                # Fixed array
                for i in range(min(field.size_option, 3)):  # Initialize first 3 elements
                    if type_name == "string":
                        result += f'    std::strncpy({prefix}.{var_name}[{i}], "test_{i}", sizeof({prefix}.{var_name}[{i}]) - 1);\n'
                    else:
                        result += f"    {prefix}.{var_name}[{i}] = {TestCppGen._get_dummy_value(field, use_namespace, i)};\n"
            elif field.max_size is not None:
                # Variable array - set count and fill some elements
                num_elements = min(field.max_size, 3)
                result += f"    {prefix}.{var_name}.count = {num_elements};\n"
                for i in range(num_elements):
                    if type_name == "string":
                        result += f'    std::strncpy({prefix}.{var_name}.data[{i}], "test_{i}", sizeof({prefix}.{var_name}.data[{i}]) - 1);\n'
                    else:
                        result += f"    {prefix}.{var_name}.data[{i}] = {TestCppGen._get_dummy_value(field, use_namespace, i)};\n"
        # Handle regular strings
        elif type_name == "string":
            if field.size_option is not None:
                # Fixed string
                result += f'    std::strncpy({prefix}.{var_name}, "test_string", sizeof({prefix}.{var_name}) - 1);\n'
            elif field.max_size is not None:
                # Variable string
                test_str = "test_string"
                result += f'    {prefix}.{var_name}.length = {len(test_str)};\n'
                result += f'    std::strncpy({prefix}.{var_name}.data, "{test_str}", sizeof({prefix}.{var_name}.data) - 1);\n'
        else:
            # Regular field
            result += f"    {prefix}.{var_name} = {TestCppGen._get_dummy_value(field, use_namespace, index)};\n"
        
        return result
    
    @staticmethod
    def generate(package):
        """Generate test code for all messages in a package."""
        yield '/* Automatically generated test code for struct-frame messages */\n'
        yield '/* This file provides round-trip encode/decode verification tests */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())
        
        yield '#pragma once\n\n'
        yield '#include <cstdio>\n'
        yield '#include <cstring>\n'
        yield '#include <cstdint>\n'
        
        # Determine if using namespaces
        use_namespace = package.package_id is not None
        namespace_name = CamelToSnakeCase(package.name) if use_namespace else None
        
        # Include the message definitions
        yield f'#include "{package.name}.structframe.hpp"\n'
        yield '#include "frame_profiles.hpp"\n'
        yield '#include "profiling_tests.hpp"\n'
        yield '\n'
        
        if use_namespace:
            yield f'namespace {namespace_name} {{\n'
            yield f'namespace Tests {{\n\n'
        else:
            yield 'namespace StructFrameTests {\n\n'
        
        # Collect messages with IDs (can be used for round-trip testing)
        testable_messages = [(key, msg) for key, msg in package.sortedMessages().items() 
                            if msg.id is not None]
        
        # Generate message creation functions
        for key, msg in testable_messages:
            if use_namespace:
                structName = msg.name
                fullStructName = msg.name
            else:
                structName = '%s%s' % (pascalCase(msg.package), msg.name)
                fullStructName = structName
            
            yield f'/* Create a test instance of {structName} */\n'
            yield f'inline {fullStructName} create_test_{CamelToSnakeCase(msg.name)}() {{\n'
            yield f'    {fullStructName} msg{{}};\n'
            
            # Generate field initializations (skip oneofs for simplicity)
            field_index = 0
            for field_key, field in msg.fields.items():
                yield TestCppGen._generate_field_init(field, use_namespace, "msg", field_index)
                field_index += 1
            
            yield '    return msg;\n'
            yield '}\n\n'
        
        # Generate test function for a single message
        yield '/* Test result structure */\n'
        yield 'struct TestResult {\n'
        yield '    bool passed;\n'
        yield '    const char* message_name;\n'
        yield '    const char* error_msg;\n'
        yield '};\n\n'
        
        # Generate per-message test functions
        for key, msg in testable_messages:
            if use_namespace:
                structName = msg.name
            else:
                structName = '%s%s' % (pascalCase(msg.package), msg.name)
            
            func_name = f'test_{CamelToSnakeCase(msg.name)}'
            yield f'/* Test round-trip encode/decode for {structName} */\n'
            yield f'template <typename Config>\n'
            yield f'inline TestResult {func_name}() {{\n'
            yield f'    uint8_t buffer[1024];\n'
            yield f'    auto msg = create_test_{CamelToSnakeCase(msg.name)}();\n'
            yield f'    \n'
            if use_namespace:
                yield f'    bool passed = FrameParsers::ProfilingTests::verify_roundtrip<{structName}, Config>(\n'
                yield f'        msg, buffer, sizeof(buffer), FrameParsers::get_message_info);\n'
            else:
                yield f'    bool passed = FrameParsers::ProfilingTests::verify_roundtrip<{structName}, Config>(\n'
                yield f'        msg, buffer, sizeof(buffer), FrameParsers::get_message_info);\n'
            yield f'    \n'
            yield f'    return TestResult{{passed, "{structName}", passed ? nullptr : "Round-trip verification failed"}};\n'
            yield f'}}\n\n'
        
        # Generate master test function that runs all message tests
        yield '/* Number of test messages */\n'
        yield f'static constexpr size_t TEST_MESSAGE_COUNT = {len(testable_messages)};\n\n'
        
        yield '/* Run all message tests with a specific profile */\n'
        yield 'template <typename Config>\n'
        yield 'inline size_t run_all_tests(bool verbose = false) {\n'
        yield '    size_t passed = 0;\n'
        yield '    TestResult results[] = {\n'
        for key, msg in testable_messages:
            func_name = f'test_{CamelToSnakeCase(msg.name)}'
            yield f'        {func_name}<Config>(),\n'
        yield '    };\n'
        yield '    \n'
        yield '    for (size_t i = 0; i < TEST_MESSAGE_COUNT; i++) {\n'
        yield '        if (results[i].passed) {\n'
        yield '            passed++;\n'
        yield '            if (verbose) {\n'
        yield '                std::printf("[PASS] %s\\n", results[i].message_name);\n'
        yield '            }\n'
        yield '        } else {\n'
        yield '            if (verbose) {\n'
        yield '                std::printf("[FAIL] %s: %s\\n", results[i].message_name, \n'
        yield '                           results[i].error_msg ? results[i].error_msg : "Unknown error");\n'
        yield '            }\n'
        yield '        }\n'
        yield '    }\n'
        yield '    \n'
        yield '    if (verbose) {\n'
        yield '        std::printf("\\nTest Results: %zu/%zu passed\\n", passed, TEST_MESSAGE_COUNT);\n'
        yield '    }\n'
        yield '    \n'
        yield '    return passed;\n'
        yield '}\n\n'
        
        # Generate profiling test function
        yield '/* Run profiling tests for all messages with a specific profile */\n'
        yield 'template <typename Config>\n'
        yield 'inline void run_profiling_tests(bool verbose = false) {\n'
        yield '    uint8_t buffer[4096];\n'
        yield '    \n'
        yield '    if (verbose) {\n'
        yield '        std::printf("Running profiling tests (%zu iterations each)...\\n", \n'
        yield '                   FrameParsers::ProfilingTests::PROFILE_ITERATIONS);\n'
        yield '    }\n'
        yield '    \n'
        
        for key, msg in testable_messages:
            if use_namespace:
                structName = msg.name
            else:
                structName = '%s%s' % (pascalCase(msg.package), msg.name)
            
            yield f'    {{\n'
            yield f'        auto msg = create_test_{CamelToSnakeCase(msg.name)}();\n'
            yield f'        auto result = FrameParsers::ProfilingTests::run_packed_profiling<{structName}, Config>(\n'
            yield f'            msg, buffer, sizeof(buffer), FrameParsers::get_message_info);\n'
            yield f'        \n'
            yield f'        if (verbose) {{\n'
            yield f'            std::printf("{structName}:\\n");\n'
            yield f'            std::printf("  Roundtrip: %s\\n", result.roundtrip_verified ? "OK" : "FAIL");\n'
            yield f'            std::printf("  Encode packed:  %zu iterations, %zu bytes\\n", \n'
            yield f'                       result.encode_packed.iterations, result.encode_packed.bytes_total);\n'
            yield f'            std::printf("  Decode packed:  %zu iterations, %zu bytes\\n", \n'
            yield f'                       result.decode_packed.iterations, result.decode_packed.bytes_total);\n'
            yield f'        }}\n'
            yield f'    }}\n'
            yield f'    \n'
        
        yield '}\n\n'
        
        if use_namespace:
            yield f'}}  // namespace Tests\n'
            yield f'}}  // namespace {namespace_name}\n'
        else:
            yield '}  // namespace StructFrameTests\n'
