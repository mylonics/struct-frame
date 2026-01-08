#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
TypeScript code generator for struct-frame.

This module generates TypeScript code for struct serialization using
ES6 module syntax (import/export).
"""

from struct_frame import version, NamingStyleC
from struct_frame.ts_js_base import (
    common_types,
    common_typed_array_methods,
    ts_array_types,
    BaseFieldGen,
    BaseEnumGen,
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

        package_msg_name = '%s_%s' % (packageName, msg.name)

        result += 'export const %s = new Struct(\'%s\') ' % (
            package_msg_name, package_msg_name)

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

        yield "import { Struct, ExtractType } from './struct_base';\n"
        yield "import { struct_frame_buffer } from './struct_frame_types';\n"
        yield "import { msg_encode, msg_reserve, msg_finish } from './struct_frame';\n"
        
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
            # Use the type name directly (as it appears in msg.name) - don't convert case
            imports = ', '.join('%s_%s' % (ext_package, t) for t in sorted(type_names))
            yield "import { %s } from './%s.sf';\n" % (imports, ext_package)
        
        yield "\n"

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'/* Package ID for extended message IDs */\n'
            yield f'export const PACKAGE_ID = {package.package_id};\n\n'

        # include additional header files here if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumTsGen.generate(enum, package.name) + '\n\n'

        if package.messages:
            yield '/* Struct definitions */\n'
            for key, msg in package.sortedMessages().items():
                yield MessageTsGen.generate(msg, package.name, package) + '\n'
            yield '\n'

        if package.messages:
            # Only generate get_message_length if there are messages with IDs
            messages_with_id = [
                msg for key, msg in package.sortedMessages().items() if msg.id]
            if messages_with_id:
                if package.package_id is not None:
                    # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                    yield 'export function get_message_length(msg_id: number) {\n'
                    yield '    // Extract package ID and message ID from 16-bit message ID\n'
                    yield '    const pkg_id = (msg_id >> 8) & 0xFF;\n'
                    yield '    const local_msg_id = msg_id & 0xFF;\n'
                    yield '    \n'
                    yield '    // Check if this is our package\n'
                    yield '    if (pkg_id !== PACKAGE_ID) {\n'
                    yield '        return 0;\n'
                    yield '    }\n'
                    yield '    \n'
                    yield '    switch (local_msg_id) {\n'
                else:
                    # Flat namespace mode: 8-bit message ID
                    yield 'export function get_message_length(msg_id: number) {\n'
                    yield '    switch (msg_id) {\n'
                
                for msg in messages_with_id:
                    package_msg_name = '%s_%s' % (package.name, msg.name)
                    yield '        case %s_msgid: return %s_max_size;\n' % (package_msg_name, package_msg_name)

                yield '        default: break;\n'
                yield '    }\n'
                yield '    return 0;\n'
                yield '}\n'
            yield '\n'
