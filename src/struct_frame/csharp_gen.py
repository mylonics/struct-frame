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
            # Use the package where the type is defined, not where the field is defined
            type_pkg = field.type_package if field.type_package else field.package
            if field.isEnum:
                base_type = '%s%s' % (pascalCase(type_pkg), type_name)
            else:
                base_type = '%s%s' % (pascalCase(type_pkg), type_name)

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
    def generate(msg, package=None):
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
            # When package has a package ID, generate 16-bit message ID as (pkg_id << 8) | msg_id
            if package and package.package_id is not None:
                # Compute combined 16-bit message ID
                combined_msg_id = (package.package_id << 8) | msg.id
                result += '        public const ushort MsgId = %d;\n' % combined_msg_id
            else:
                # No package ID, use plain message ID (also ushort for consistency)
                result += '        public const ushort MsgId = %d;\n' % msg.id
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
        yield 'using System.Runtime.InteropServices;\n'
        
        # Collect referenced packages for using directives
        referenced_packages = set()
        for key, msg in package.messages.items():
            for field_name, field in msg.fields.items():
                if field.type_package and field.type_package != package.name:
                    referenced_packages.add(field.type_package)
        
        # Add using directives for referenced packages
        if referenced_packages:
            for ref_pkg in sorted(referenced_packages):
                yield f'using StructFrame.{pascalCase(ref_pkg)};\n'
        
        yield '\n'

        namespace_name = pascalCase(package.name)
        yield 'namespace StructFrame.%s\n' % namespace_name
        yield '{\n'

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'    // Package ID for extended message IDs\n'
            yield f'    public static class PackageInfo\n'
            yield f'    {{\n'
            yield f'        public const byte PackageId = {package.package_id};\n'
            yield f'    }}\n\n'

        if package.enums:
            yield '    // Enum definitions\n'
            for key, enum in package.enums.items():
                yield EnumCSharpGen.generate(enum) + '\n'

        if package.messages:
            yield '    // Struct definitions\n'
            # Need to sort messages to make sure dependencies are properly met
            for key, msg in package.sortedMessages().items():
                yield MessageCSharpGen.generate(msg, package)
            yield '\n'

        # Generate helper class with message definitions
        if package.messages:
            yield '    public static class MessageDefinitions\n'
            yield '    {\n'
            
            if package.package_id is not None:
                # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                yield '        public static bool GetMessageLength(ushort msgId, out int size)\n'
                yield '        {\n'
                yield '            // Extract package ID and message ID from 16-bit message ID\n'
                yield '            byte pkgId = (byte)((msgId >> 8) & 0xFF);\n'
                yield '            byte localMsgId = (byte)(msgId & 0xFF);\n'
                yield '            \n'
                yield '            // Check if this is our package\n'
                yield f'            if (pkgId != PackageInfo.PackageId)\n'
                yield '            {\n'
                yield '                size = 0;\n'
                yield '                return false;\n'
                yield '            }\n'
                yield '            \n'
                yield '            switch (localMsgId)\n'
                yield '            {\n'
            else:
                # Flat namespace mode: 8-bit message ID
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
