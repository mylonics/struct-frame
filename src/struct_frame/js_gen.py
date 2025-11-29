#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
JavaScript code generator for struct-frame.

This module generates human-readable JavaScript code for struct serialization.
It reuses the TypeScript generator's type mappings and logic but outputs
JavaScript syntax (CommonJS) instead of TypeScript.
"""

from struct_frame import version, NamingStyleC
import time

StyleC = NamingStyleC()

# Reuse type mappings from TypeScript generator
js_types = {
    "int8":     'Int8',
    "uint8":    'UInt8',
    "int16":    'Int16LE',
    "uint16":   'UInt16LE',
    "bool":     'Boolean8',
    "double":   'Float64LE',
    "float":    'Float32LE',
    "int32":  'Int32LE',
    "uint32": 'UInt32LE',
    "int64":  'BigInt64LE',
    "uint64": 'BigUInt64LE',
    "string":   'String',
}

# JavaScript typed array methods for array fields
js_typed_array_methods = {
    "int8":     'Int8Array',
    "uint8":    'UInt8Array',
    "int16":    'Int16Array',
    "uint16":   'UInt16Array',
    "bool":     'UInt8Array',  # Boolean arrays stored as UInt8Array
    "double":   'Float64Array',
    "float":    'Float32Array',
    "int32":    'Int32Array',
    "uint32":   'UInt32Array',
    "int64":    'BigInt64Array',
    "uint64":   'BigUInt64Array',
    "string":   'StructArray',  # String arrays use StructArray
}


class EnumJsGen():
    @staticmethod
    def generate(field, packageName):
        leading_comment = field.comments
        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '%s\n' % c

        enum_name = '%s%s' % (packageName, StyleC.enum_name(field.name))
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

        return result


class FieldJsGen():
    @staticmethod
    def generate(field, packageName):
        result = ''
        # Check if field is an enum type
        isEnum = field.isEnum if hasattr(field, 'isEnum') else False
        var_name = StyleC.var_name(field.name)
        type_name = field.fieldType

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:  # Fixed size array [size=X]
                    # Fixed string array: string[size] -> StructArray with fixed length
                    result += "    // Fixed string array: %d strings, each exactly %d chars\n" % (field.size_option, field.element_size)
                    # For string arrays, we need to use StructArray with String elements
                    result += "    .StructArray('%s', %d, new Struct().String('value', %d).compile())" % (var_name, field.size_option, field.element_size)
                else:  # Variable size array [max_size=X]
                    # Variable string array: string[max_size=X, element_size=Y] -> count + StructArray
                    result += "    // Variable string array: up to %d strings, each max %d chars\n" % (field.max_size, field.element_size)
                    result += "    .UInt8('%s_count')\n" % var_name
                    result += "    .StructArray('%s_data', %d, new Struct().String('value', %d).compile())" % (var_name, field.max_size, field.element_size)
            else:
                # Regular type arrays
                if type_name in js_types:
                    base_type = js_types[type_name]
                    array_method = js_typed_array_methods.get(type_name, 'StructArray')
                elif isEnum:
                    # Enum arrays are stored as UInt8Array
                    base_type = 'UInt8'
                    array_method = 'UInt8Array'
                else:
                    # Struct arrays - use the original type name (e.g., 'Sensor' not 'sensor')
                    base_type = '%s_%s' % (packageName, type_name)
                    array_method = 'StructArray'

                if field.size_option is not None:  # Fixed size array [size=X]
                    # Fixed array: type[size] -> TypedArray with fixed length
                    array_size = field.size_option
                    result += '    // Fixed array: always %d elements\n' % array_size
                    if array_method == 'StructArray':
                        result += "    .%s('%s', %d, %s)" % (array_method, var_name, array_size, base_type)
                    else:
                        result += "    .%s('%s', %d)" % (array_method, var_name, array_size)
                else:  # Variable size array [max_size=X]
                    # Variable array: type[max_size=X] -> count + TypedArray
                    max_count = field.max_size
                    result += '    // Variable array: up to %d elements\n' % max_count
                    result += "    .UInt8('%s_count')\n" % var_name
                    if array_method == 'StructArray':
                        result += "    .%s('%s_data', %d, %s)" % (array_method, var_name, max_count, base_type)
                    else:
                        result += "    .%s('%s_data', %d)" % (array_method, var_name, max_count)
        else:
            # Non-array fields (existing logic)
            if field.fieldType == "string":
                if hasattr(field, 'size_option') and field.size_option is not None:
                    # Fixed string: string[size] -> fixed length string
                    result += '    // Fixed string: exactly %d chars\n' % field.size_option
                    result += "    .String('%s', %d)" % (var_name, field.size_option)
                elif hasattr(field, 'max_size') and field.max_size is not None:
                    # Variable string: string[max_size=X] -> length + data
                    result += '    // Variable string: up to %d chars\n' % field.max_size
                    result += "    .UInt8('%s_length')\n" % var_name
                    result += "    .String('%s_data', %d)" % (var_name, field.max_size)
                else:
                    # Default string handling (should not occur with new parser)
                    result += "    .String('%s')" % var_name
            else:
                # Regular types
                if type_name in js_types:
                    type_name = js_types[type_name]
                else:
                    type_name = '%s_%s' % (packageName, StyleC.struct_name(type_name))

                if isEnum:
                    # Enums are stored as UInt8 in JavaScript
                    result += "    .UInt8('%s')" % var_name
                else:
                    result += "    .%s('%s')" % (type_name, var_name)

        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = c + "\n" + result

        return result


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageJsGen():
    @staticmethod
    def generate(msg, packageName):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        package_msg_name = '%s_%s' % (packageName, msg.name)

        result += "const %s = new Struct('%s') " % (
            package_msg_name, package_msg_name)

        result += '\n'

        size = 1
        if not msg.fields:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += "    .UInt8('dummy_field');"
        else:
            size = msg.size

        result += '\n'.join([FieldJsGen.generate(f, packageName)
                            for key, f in msg.fields.items()])
        result += '\n    .compile();\n'
        result += 'module.exports.%s = %s;\n\n' % (package_msg_name, package_msg_name)

        result += 'const %s_max_size = %d;\n' % (package_msg_name, size)
        result += 'module.exports.%s_max_size = %s_max_size;\n' % (package_msg_name, package_msg_name)

        if msg.id:
            result += 'const %s_msgid = %d;\n' % (
                package_msg_name, msg.id)
            result += 'module.exports.%s_msgid = %s_msgid;\n' % (package_msg_name, package_msg_name)

            result += 'function %s_encode(buffer, msg) {\n' % (
                package_msg_name)
            result += '  msg_encode(buffer, msg, %s_msgid);\n}\n' % (package_msg_name)
            result += 'module.exports.%s_encode = %s_encode;\n' % (package_msg_name, package_msg_name)

            result += 'function %s_reserve(buffer) {\n' % (
                package_msg_name)
            result += '  const msg_buffer = msg_reserve(buffer, %s_msgid, %s_max_size);\n' % (
                package_msg_name, package_msg_name)
            result += '  if (msg_buffer){\n'
            result += '    return new %s(msg_buffer);\n  }\n  return;\n}\n' % (
                package_msg_name)
            result += 'module.exports.%s_reserve = %s_reserve;\n' % (package_msg_name, package_msg_name)

            result += 'function %s_finish(buffer) {\n' % (
                package_msg_name)
            result += '  msg_finish(buffer);\n}\n'
            result += 'module.exports.%s_finish = %s_finish;\n' % (package_msg_name, package_msg_name)
        return result + '\n'

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class FileJsGen():
    @staticmethod
    def generate(package):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())
        yield '"use strict";\n\n'

        yield "const { Struct } = require('./struct_base');\n"
        yield "const { struct_frame_buffer } = require('./struct_frame_types');\n"
        yield "const { msg_encode, msg_reserve, msg_finish } = require('./struct_frame');\n\n"

        # include additional header files here if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumJsGen.generate(enum, package.name) + '\n\n'

        if package.messages:
            yield '/* Struct definitions */\n'
            for key, msg in package.sortedMessages().items():
                yield MessageJsGen.generate(msg, package.name) + '\n'
            yield '\n'

        if package.messages:
            # Only generate get_message_length if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                yield 'function get_message_length(msg_id) {\n  switch (msg_id) {\n'
                for msg in messages_with_id:
                    package_msg_name = '%s_%s' % (package.name, msg.name)
                    yield '    case %s_msgid: return %s_max_size;\n' % (package_msg_name, package_msg_name)

                yield '    default: break;\n  }\n  return 0;\n}\n'
                yield 'module.exports.get_message_length = get_message_length;\n'
            yield '\n'
