#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
C# code generator for struct-frame.

This module generates C# code for struct serialization using
StructLayout and MarshalAs attributes for binary compatibility.
"""

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase
import time

StyleC = NamingStyleC()

# Mapping from proto types to C# types
csharp_types = {
    "uint8": "byte",
    "int8": "sbyte",
    "uint16": "ushort",
    "int16": "short",
    "uint32": "uint",
    "int32": "int",
    "bool": "bool",
    "float": "float",
    "double": "double",
    "uint64": "ulong",
    "int64": "long",
    "string": "byte",  # Strings are byte arrays in C#
}


class EnumCSharpGen():
    @staticmethod
    def generate(field):
        leading_comment = field.comments

        result = ''
        if leading_comment:
            for c in leading_comment:
                result += '    /// <summary>\n'
                result += '    /// %s\n' % c.strip('/')
                result += '    /// </summary>\n'

        enumName = '%s%s' % (pascalCase(field.package), field.name)
        result += '    public enum %s : byte\n' % enumName
        result += '    {\n'

        enum_length = len(field.data)
        enum_values = []
        for index, (d) in enumerate(field.data):
            leading_comment = field.data[d][1]

            if leading_comment:
                for c in leading_comment:
                    enum_values.append('        /// <summary>')
                    enum_values.append('        /// %s' % c.strip('/'))
                    enum_values.append('        /// </summary>')

            comma = ","
            if index == enum_length - 1:
                comma = ""

            enum_value = "        %s = %d%s" % (
                StyleC.enum_entry(d), field.data[d][0], comma)
            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        result += '\n    }\n'

        return result


class FieldCSharpGen():
    @staticmethod
    def generate(field, field_offset):
        """Generate C# field definition with FieldOffset attribute"""
        result = ''
        var_name = pascalCase(field.name)
        type_name = field.fieldType

        # Add leading comments
        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result += '        /// <summary>\n'
                result += '        /// %s\n' % c.strip('/')
                result += '        /// </summary>\n'

        # Handle basic type resolution
        if type_name in csharp_types:
            base_type = csharp_types[type_name]
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
                    # Fixed string array: size_option strings, each element_size bytes
                    total_size = field.size_option * field.element_size
                    result += f'        [FieldOffset({field_offset})]\n'
                    result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {total_size})]\n'
                    result += f'        public byte[] {var_name};  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars\n'
                elif field.max_size is not None:
                    # Variable string array: count byte + max_size strings of element_size bytes each
                    result += f'        [FieldOffset({field_offset})]\n'
                    result += f'        public byte {var_name}Count;\n'
                    total_size = field.max_size * field.element_size
                    result += f'        [FieldOffset({field_offset + 1})]\n'
                    result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {total_size})]\n'
                    result += f'        public byte[] {var_name}Data;  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars\n'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array
                    result += f'        [FieldOffset({field_offset})]\n'
                    if field.isEnum:
                        result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.size_option})]\n'
                        result += f'        public byte[] {var_name};  // Fixed array of {base_type}: {field.size_option} elements\n'
                    else:
                        result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.size_option})]\n'
                        result += f'        public {base_type}[] {var_name};  // Fixed array: {field.size_option} elements\n'
                elif field.max_size is not None:
                    # Variable array: count byte + max elements
                    result += f'        [FieldOffset({field_offset})]\n'
                    result += f'        public byte {var_name}Count;\n'
                    result += f'        [FieldOffset({field_offset + 1})]\n'
                    if field.isEnum:
                        result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.max_size})]\n'
                        result += f'        public byte[] {var_name}Data;  // Variable array of {base_type}: up to {field.max_size} elements\n'
                    else:
                        result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.max_size})]\n'
                        result += f'        public {base_type}[] {var_name}Data;  // Variable array: up to {field.max_size} elements\n'

        # Handle regular strings
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string: exactly size_option characters
                result += f'        [FieldOffset({field_offset})]\n'
                result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.size_option})]\n'
                result += f'        public byte[] {var_name};  // Fixed string: exactly {field.size_option} chars\n'
            elif field.max_size is not None:
                # Variable string: length byte + max characters
                result += f'        [FieldOffset({field_offset})]\n'
                result += f'        public byte {var_name}Length;\n'
                result += f'        [FieldOffset({field_offset + 1})]\n'
                result += f'        [MarshalAs(UnmanagedType.ByValArray, SizeConst = {field.max_size})]\n'
                result += f'        public byte[] {var_name}Data;  // Variable string: up to {field.max_size} chars\n'

        # Handle regular fields
        else:
            result += f'        [FieldOffset({field_offset})]\n'
            result += f'        public {base_type} {var_name};\n'

        return result


class MessageCSharpGen():
    @staticmethod
    def generate(msg):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '    /// <summary>\n'
                result += '    /// %s\n' % c.strip('/')
                result += '    /// </summary>\n'

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        defineName = '%s_%s' % (CamelToSnakeCase(
            msg.package).upper(), CamelToSnakeCase(msg.name).upper())

        result += '    [StructLayout(LayoutKind.Explicit, Pack = 1, Size = %d)]\n' % msg.size
        result += '    public struct %s\n' % structName
        result += '    {\n'

        result += '        public const int MaxSize = %d;\n' % msg.size
        if msg.id:
            result += '        public const int MsgId = %d;\n' % msg.id
        result += '\n'

        if not msg.fields:
            # Empty structs need a dummy field
            result += '        [FieldOffset(0)]\n'
            result += '        public byte DummyField;\n'
        else:
            # Calculate field offsets
            offset = 0
            for key, f in msg.fields.items():
                result += FieldCSharpGen.generate(f, offset)
                offset += f.size

        result += '    }\n'

        return result + '\n'


class FileCSharpGen():
    @staticmethod
    def generate(package):
        yield '// Automatically generated struct frame code for C#\n'
        yield '// Generated by %s at %s.\n\n' % (version, time.asctime())

        yield 'using System;\n'
        yield 'using System.Runtime.InteropServices;\n\n'

        namespace_name = pascalCase(package.name)
        yield 'namespace StructFrame.%s\n' % namespace_name
        yield '{\n'

        if package.enums:
            yield '    // Enum definitions\n'
            for key, enum in package.enums.items():
                yield EnumCSharpGen.generate(enum) + '\n'

        if package.messages:
            yield '    // Struct definitions\n'
            # Need to sort messages to make sure dependencies are properly met
            for key, msg in package.sortedMessages().items():
                yield MessageCSharpGen.generate(msg)
            yield '\n'

        # Generate helper class with message definitions
        if package.messages:
            yield '    public static class MessageDefinitions\n'
            yield '    {\n'
            yield '        public static bool GetMessageLength(int msgId, out int size)\n'
            yield '        {\n'
            yield '            switch (msgId)\n'
            yield '            {\n'
            for key, msg in package.sortedMessages().items():
                if msg.id:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    yield '                case %s.MsgId: size = %s.MaxSize; return true;\n' % (structName, structName)
            yield '                default: size = 0; return false;\n'
            yield '            }\n'
            yield '        }\n'
            yield '    }\n'

        yield '}\n'
