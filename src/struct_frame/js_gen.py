#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
JavaScript code generator for struct-frame.

This module generates human-readable JavaScript code for struct serialization.
It reuses the shared TypeScript/JavaScript base module for common logic
but outputs JavaScript syntax (CommonJS) instead of TypeScript.
"""

from struct_frame import version, NamingStyleC
from struct_frame.ts_js_base import (
    common_types,
    common_typed_array_methods,
    BaseFieldGen,
    BaseEnumGen,
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
