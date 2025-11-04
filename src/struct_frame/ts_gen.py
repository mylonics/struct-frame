#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from struct_frame import version, NamingStyleC
import time

StyleC = NamingStyleC()

ts_types = {
    "int8":     'Int8',
    "uint8":    'UInt8',
    "int16":    'Int16LE',
    "uint16":   'UInt16LE',
    "bool":     'Boolean8',
    "double":   'Float64LE',
    "float":    'Float32LE',
    "int32":  'Int32LE',
    "uint32": 'UInt32LE',
    "uint64": 'BigInt64LE',
    "int64":  'BigUInt64LE',
    "string":   'String',
}

# TypeScript type mappings for array declarations
ts_array_types = {
    "int8":     'number',
    "uint8":    'number',
    "int16":    'number',
    "uint16":   'number',
    "bool":     'boolean',
    "double":   'number',
    "float":    'number',
    "int32":    'number',
    "uint32":   'number',
    "uint64":   'bigint',
    "int64":    'bigint',
    "string":   'string',
}


class EnumTsGen():
    @staticmethod
    def generate(field, packageName):
        leading_comment = field.comments
        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '%s\n' % c

        result += 'export enum %s%s' % (packageName,
                                        StyleC.enum_name(field.name))

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
    @staticmethod
    def generate(field, packageName):
        result = ''
        isEnum = False
        var_name = StyleC.var_name(field.name)
        type_name = field.fieldType

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:  # Fixed size array [size=X]
                    # Fixed string array: string[size] -> Array<string> with fixed length
                    result += f'    // Fixed string array: {field.size_option} strings, each exactly {field.element_size} chars\n'
                    result += f'    .Array(\'{var_name}\', \'String\', {field.size_option})'
                else:  # Variable size array [max_size=X]
                    # Variable string array: string[max_size=X, element_size=Y] -> Array<string> with count
                    result += f'    // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars\n'
                    result += f'    .UInt8(\'{var_name}_count\')\n'
                    result += f'    .Array(\'{var_name}_data\', \'String\', {field.max_size})'
            else:
                # Regular type arrays
                if type_name in ts_types:
                    base_type = ts_types[type_name]
                else:
                    base_type = f'{packageName.lower()}_{StyleC.struct_name(type_name).lower()}'

                if field.size_option is not None:  # Fixed size array [size=X]
                    # Fixed array: type[size] -> Array<type> with fixed length
                    # For fixed arrays, size_option contains the exact size
                    array_size = field.size_option
                    result += f'    // Fixed array: always {array_size} elements\n'
                    result += f'    .Array(\'{var_name}\', \'{base_type}\', {array_size})'
                else:  # Variable size array [max_size=X]
                    # Variable array: type[max_size=X] -> count + Array<type>
                    max_count = field.max_size  # For variable arrays, max_size is the maximum count
                    result += f'    // Variable array: up to {max_count} elements\n'
                    result += f'    .UInt8(\'{var_name}_count\')\n'
                    result += f'    .Array(\'{var_name}_data\', \'{base_type}\', {max_count})'
        else:
            # Non-array fields (existing logic)
            if field.fieldType == "string":
                if hasattr(field, 'size_option') and field.size_option is not None:
                    # Fixed string: string[size] -> fixed length string
                    result += f'    // Fixed string: exactly {field.size_option} chars\n'
                    result += f'    .String(\'{var_name}\', {field.size_option})'
                elif hasattr(field, 'max_size') and field.max_size is not None:
                    # Variable string: string[max_size=X] -> length + data
                    result += f'    // Variable string: up to {field.max_size} chars\n'
                    result += f'    .UInt8(\'{var_name}_length\')\n'
                    result += f'    .String(\'{var_name}_data\', {field.max_size})'
                else:
                    # Default string handling (should not occur with new parser)
                    result += f'    .String(\'{var_name}\')'
            else:
                # Regular types
                if type_name in ts_types:
                    type_name = ts_types[type_name]
                else:
                    type_name = f'{packageName}_{StyleC.struct_name(type_name)}'

                if isEnum:
                    result += f'    .UInt8(\'{var_name}\', typed<{type_name}>())'
                else:
                    result += f'    .{type_name}(\'{var_name}\')'

        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = c + "\n" + result

        return result


# ---------------------------------------------------------------------------
#                   Generation of messages (structures)
# ---------------------------------------------------------------------------


class MessageTsGen():
    @staticmethod
    def generate(msg, packageName):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        package_msg_name = '%s_%s' % (packageName, msg.name)

        result += 'export const %s = new typed_struct.Struct(\'%s\') ' % (
            package_msg_name, package_msg_name)

        result += '\n'

        size = 1
        if not msg.fields:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += '    .UInt8(\'dummy_field\');'
        else:
            size = msg.size

        result += '\n'.join([FieldTsGen.generate(f, packageName)
                            for key, f in msg.fields.items()])
        result += '\n    .compile();\n\n'

        result += 'export const %s_max_size = %d;\n' % (package_msg_name, size)

        if msg.id:
            result += 'export const %s_msgid = %d\n' % (
                package_msg_name, msg.id)

            result += 'export function %s_encode(buffer: struct_frame_buffer, msg: any) {\n' % (
                package_msg_name)
            result += '    msg_encode(buffer, msg, %s_msgid)\n}\n' % (package_msg_name)

            result += 'export function %s_reserve(buffer: struct_frame_buffer) {\n' % (
                package_msg_name)
            result += '    const msg_buffer = msg_reserve(buffer, %s_msgid, %s_max_size);\n' % (
                package_msg_name, package_msg_name)
            result += '    if (msg_buffer){\n'
            result += '        return new %s(msg_buffer)\n    }\n    return;\n}\n' % (
                package_msg_name)

            result += 'export function %s_finish(buffer: struct_frame_buffer) {\n' % (
                package_msg_name)
            result += '    msg_finish(buffer);\n}\n'
        return result + '\n'

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class FileTsGen():
    @staticmethod
    def generate(package):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        yield 'const typed_struct = require(\'typed-struct\')\n'
        yield 'const ExtractType = typeof typed_struct.ExtractType;\n'
        yield 'const type = typeof typed_struct.ExtractType;\n\n'

        yield "import { struct_frame_buffer } from './struct_frame_types';\n"

        yield "import { msg_encode, msg_reserve, msg_finish } from './struct_frame';\n\n"

        # include additional header files here if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumTsGen.generate(enum, package.name) + '\n\n'

        if package.messages:
            yield '/* Struct definitions */\n'
            for key, msg in package.sortedMessages().items():
                yield MessageTsGen.generate(msg, package.name) + '\n'
            yield '\n'

        if package.messages:
            # Only generate get_message_length if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                yield 'export function get_message_length(msg_id : number){\n switch (msg_id)\n {\n'
                for msg in messages_with_id:
                    package_msg_name = '%s_%s' % (package.name, msg.name)
                    yield '  case %s_msgid: return %s_max_size;\n' % (package_msg_name, package_msg_name)

                yield '  default: break;\n } return 0;\n}'
            yield '\n'
