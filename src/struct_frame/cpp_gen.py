#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase
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
        leading_comment = field.comments

        result = ''
        if leading_comment:
            for c in leading_comment:
                result += '%s\n' % c

        # When using namespaces, don't prefix with package name
        if use_namespace:
            enumName = field.name
        else:
            enumName = '%s%s' % (pascalCase(field.package), field.name)
        # Use enum class for C++
        result += 'enum class %s : uint8_t' % (enumName)

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
        result += '\n};\n'

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
                    # Variable string array: count byte + max_size strings of element_size chars each
                    declaration = f"struct {{ uint8_t count; char data[{field.max_size}][{field.element_size}]; }} {var_name};"
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
                    # Variable array: count byte + max elements
                    declaration = f"struct {{ uint8_t count; {base_type} data[{field.max_size}]; }} {var_name};"
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
                # Variable string: length byte + max characters
                declaration = f"struct {{ uint8_t length; char data[{field.max_size}]; }} {var_name};"
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
    def generate(oneof, use_namespace=False, package=None):
        """Generate C++ union for a oneof construct."""
        result = ''
        
        # Add comments
        if oneof.comments:
            for c in oneof.comments:
                result += '%s\n' % c
        
        # If auto-discriminator is enabled, add discriminator field first
        if oneof.auto_discriminator:
            # Always use uint16_t since message IDs can be up to 65535
            result += f'    uint16_t {oneof.name}_discriminator;  // Auto-generated message ID discriminator\n'
        
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
    def _generate_field_comparison(field, use_namespace=False):
        """Generate comparison code for a single field."""
        var_name = field.name
        type_name = field.fieldType
        
        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:
                    # Fixed string array: compare each string with strncmp
                    return f'(std::memcmp({var_name}, other.{var_name}, sizeof({var_name})) == 0)'
                elif field.max_size is not None:
                    # Variable string array: compare count and data
                    return f'({var_name}.count == other.{var_name}.count && std::memcmp({var_name}.data, other.{var_name}.data, sizeof({var_name}.data)) == 0)'
                else:
                    return f'(std::memcmp({var_name}, other.{var_name}, sizeof({var_name})) == 0)'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array: compare with memcmp
                    return f'(std::memcmp({var_name}, other.{var_name}, sizeof({var_name})) == 0)'
                elif field.max_size is not None:
                    # Variable array: compare count and data
                    return f'({var_name}.count == other.{var_name}.count && std::memcmp({var_name}.data, other.{var_name}.data, sizeof({var_name}.data)) == 0)'
                else:
                    return f'(std::memcmp({var_name}, other.{var_name}, sizeof({var_name})) == 0)'
        
        # Handle regular strings
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string: compare with strncmp
                return f'(std::strncmp({var_name}, other.{var_name}, {field.size_option}) == 0)'
            elif field.max_size is not None:
                # Variable string: compare length and data
                return f'({var_name}.length == other.{var_name}.length && std::strncmp({var_name}.data, other.{var_name}.data, {field.max_size}) == 0)'
            else:
                return f'(std::strcmp({var_name}, other.{var_name}) == 0)'
        
        # Handle enums - compare with ==
        elif field.isEnum:
            return f'({var_name} == other.{var_name})'
        
        # Handle nested messages (compare as byte memory since they're packed)
        elif type_name not in cpp_types:
            # Nested struct - compare with memcmp for packed structs
            return f'(std::memcmp(&{var_name}, &other.{var_name}, sizeof({var_name})) == 0)'
        
        # Handle regular fields (primitives)
        else:
            return f'({var_name} == other.{var_name})'
    
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
    def generate(msg, use_namespace=False, package=None, equality=False):
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

        # Generate struct with optional MessageBase inheritance
        if has_msg_id:
            result += 'struct %s : FrameParsers::MessageBase<%s, %d, %d> {' % (
                structName, structName, msg_id_value, size)
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
            result += '\n'.join([OneOfCppGen.generate(o, use_namespace, package)
                                for key, o in msg.oneofs.items()])
        
        # Generate equality operator if requested
        if equality:
            result += '\n\n'
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
        
        # Add magic number constants inside the class (for checksum initialization)
        if has_msg_id and msg.magic_bytes:
            result += f'\n    // Magic numbers for checksum (based on field types and positions)\n'
            result += f'    static constexpr uint8_t MAGIC1 = {msg.magic_bytes[0]};\n'
            result += f'    static constexpr uint8_t MAGIC2 = {msg.magic_bytes[1]};\n'
        
        result += '};\n'

        return result + '\n'


class FileCppGen():
    @staticmethod
    def generate(package, equality=False):
        yield '/* Automatically generated struct frame header for C++ */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        yield '#pragma once\n'
        yield '#include <cstdint>\n'
        yield '#include <cstddef>\n'
        
        # Include cstring for string comparison if equality is enabled
        if equality:
            yield '#include <cstring>\n'
        
        # Check if any message has an ID (needs MessageBase from frame_base.hpp)
        has_msg_with_id = any(msg.id is not None for msg in package.messages.values()) if package.messages else False
        if has_msg_with_id:
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

        if package.messages:
            yield '/* Struct definitions */\n'
            yield '#pragma pack(push, 1)\n'
            # Need to sort messages to make sure dependencies are properly met

            for key, msg in package.sortedMessages().items():
                yield MessageCppGen.generate(msg, use_namespace, package, equality) + '\n'
            yield '#pragma pack(pop)\n\n'

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
            
            # Generate get_magic_numbers function (legacy support)
            if use_namespace:
                # When using package ID, message ID is 16-bit
                yield 'inline bool get_magic_numbers(uint16_t msg_id, uint8_t* magic1, uint8_t* magic2) {\n'
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
                yield 'inline bool get_magic_numbers(size_t msg_id, uint8_t* magic1, uint8_t* magic2) {\n'
                yield '    switch (msg_id) {\n'
            
            for key, msg in package.sortedMessages().items():
                if use_namespace:
                    structName = msg.name
                    defineName = CamelToSnakeCase(msg.name).upper()
                else:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    defineName = '%s_%s' % (CamelToSnakeCase(
                        msg.package).upper(), CamelToSnakeCase(msg.name).upper())
                    
                if msg.id is not None and msg.magic_bytes:
                    if use_namespace:
                        # When using package ID, compare against local message ID
                        yield '        case %d: *magic1 = %s::MAGIC1; *magic2 = %s::MAGIC2; return true;\n' % (
                            msg.id, structName, structName)
                    else:
                        # No package ID, compare against MSG_ID from MessageBase
                        yield '        case %s::MSG_ID: *magic1 = %s::MAGIC1; *magic2 = %s::MAGIC2; return true;\n' % (
                            structName, structName, structName)

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
