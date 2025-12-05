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
    def generate(field):
        leading_comment = field.comments

        result = ''
        if leading_comment:
            for c in leading_comment:
                result += '%s\n' % c

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
    def generate(field):
        result = ''
        var_name = field.name
        type_name = field.fieldType

        # Handle basic type resolution
        if type_name in cpp_types:
            base_type = cpp_types[type_name]
        else:
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


class MessageCppGen():
    @staticmethod
    def generate(msg):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '%s\n' % c

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        result += 'struct %s {' % structName

        result += '\n'

        size = 1
        if not msg.fields:
            # Empty structs are allowed in C++ but we add a dummy field
            # for consistency with the C implementation
            result += '    char dummy_field;\n'
        else:
            size = msg.size

        result += '\n'.join([FieldCppGen.generate(f)
                            for key, f in msg.fields.items()])
        result += '\n};\n\n'

        defineName = '%s_%s' % (CamelToSnakeCase(
            msg.package).upper(), CamelToSnakeCase(msg.name).upper())
        result += 'constexpr size_t %s_MAX_SIZE = %d;\n' % (defineName, size)

        if msg.id:
            result += 'constexpr size_t %s_MSG_ID = %d;\n' % (
                defineName, msg.id)

        return result + '\n'


class FileCppGen():
    @staticmethod
    def generate(package):
        yield '/* Automatically generated struct frame header for C++ */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        yield '#pragma once\n'
        yield '#include <cstdint>\n'
        yield '#include <cstddef>\n\n'

        # include additional header files if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumCppGen.generate(enum) + '\n'

        if package.messages:
            yield '/* Struct definitions */\n'
            yield '#pragma pack(push, 1)\n'
            # Need to sort messages to make sure dependencies are properly met

            for key, msg in package.sortedMessages().items():
                yield MessageCppGen.generate(msg) + '\n'
            yield '#pragma pack(pop)\n\n'

        # Generate get_message_length function
        if package.messages:
            yield 'namespace FrameParsers {\n\n'
            yield 'inline bool get_message_length(size_t msg_id, size_t* size) {\n'
            yield '    switch (msg_id) {\n'
            for key, msg in package.sortedMessages().items():
                name = '%s_%s' % (CamelToSnakeCase(
                    msg.package).upper(), CamelToSnakeCase(msg.name).upper())
                if msg.id:
                    yield '        case %s_MSG_ID: *size = %s_MAX_SIZE; return true;\n' % (name, name)

            yield '        default: break;\n'
            yield '    }\n'
            yield '    return false;\n'
            yield '}\n\n'
            yield '}  // namespace FrameParsers\n'
