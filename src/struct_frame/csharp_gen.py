#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
C# code generator for struct-frame.

This module generates C# code for struct serialization using
classes with manual Pack/Unpack methods for binary compatibility.
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
    "string": "byte[]",
}

# Mapping from proto types to byte sizes
csharp_type_sizes = {
    "uint8": 1,
    "int8": 1,
    "uint16": 2,
    "int16": 2,
    "uint32": 4,
    "int32": 4,
    "bool": 1,
    "float": 4,
    "double": 8,
    "uint64": 8,
    "int64": 8,
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

        # Add enum-to-string extension method
        result += f'\n    /// <summary>\n'
        result += f'    /// Extension methods for {enumName}\n'
        result += f'    /// </summary>\n'
        result += f'    public static class {enumName}Extensions\n'
        result += '    {\n'
        result += f'        /// <summary>\n'
        result += f'        /// Convert {enumName} value to string representation\n'
        result += f'        /// </summary>\n'
        result += f'        public static string ToString(this {enumName} value)\n'
        result += '        {\n'
        result += '            switch (value)\n'
        result += '            {\n'
        for d in field.data:
            result += f'                case {enumName}.{StyleC.enum_entry(d)}: return "{StyleC.enum_entry(d)}";\n'
        result += '                default: return "UNKNOWN";\n'
        result += '            }\n'
        result += '        }\n'
        result += '    }\n'

        return result


class FieldCSharpGen():
    @staticmethod
    def generate_field_declaration(field):
        """Generate C# field declaration"""
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
            # Use the package where the type is defined
            type_pkg = field.type_package if field.type_package else field.package
            base_type = '%s%s' % (pascalCase(type_pkg), type_name)

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                # String arrays
                if field.size_option is not None:
                    # Fixed string array
                    result += f'        public byte[] {var_name} = null!;  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars\n'
                elif field.max_size is not None:
                    # Variable string array
                    count_type = "ushort" if field.max_size > 255 else "byte"
                    result += f'        public {count_type} {var_name}Count;\n'
                    result += f'        public byte[] {var_name}Data = null!;  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars\n'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        result += f'        public byte[] {var_name} = null!;  // Fixed array of {base_type}: {field.size_option} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name} = null!;  // Fixed array: {field.size_option} elements\n'
                elif field.max_size is not None:
                    # Variable array
                    count_type = "ushort" if field.max_size > 255 else "byte"
                    result += f'        public {count_type} {var_name}Count;\n'
                    if field.isEnum:
                        result += f'        public byte[] {var_name}Data = null!;  // Variable array of {base_type}: up to {field.max_size} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name}Data = null!;  // Variable array: up to {field.max_size} elements\n'

        # Handle regular strings
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                result += f'        public byte[] {var_name} = null!;  // Fixed string: exactly {field.size_option} chars\n'
            elif field.max_size is not None:
                # Variable string
                length_type = "ushort" if field.max_size > 255 else "byte"
                result += f'        public {length_type} {var_name}Length;\n'
                result += f'        public byte[] {var_name}Data = null!;  // Variable string: up to {field.max_size} chars\n'

        # Handle regular fields
        else:
            if type_name not in csharp_types and not field.isEnum:
                # Nested struct - reference type needs null-forgiving operator
                result += f'        public {base_type} {var_name} = null!;\n'
            else:
                # Primitive type or enum - value type doesn't need initializer
                result += f'        public {base_type} {var_name};\n'

        return result

    @staticmethod
    def generate_pack_code(field, base_offset, use_offset_param=False):
        """Generate code to pack this field into a byte array.
        
        Args:
            field: The field to pack
            base_offset: The base offset in the message structure
            use_offset_param: If True, generates code using 'offset + N' for PackTo method
        """
        lines = []
        var_name = pascalCase(field.name)
        type_name = field.fieldType
        
        # Helper to format offset (for PackTo method compatibility)
        def fmt_offset(off):
            if use_offset_param:
                return f'offset + {off}' if off > 0 else 'offset'
            return str(off)

        # IMPORTANT: Check is_array FIRST to handle arrays of primitives correctly
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:
                    # Fixed string array
                    total_size = field.size_option * field.element_size
                    lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {fmt_offset(base_offset)}, Math.Min({var_name}.Length, {total_size}));')
                elif field.max_size is not None:
                    # Variable string array
                    total_size = field.max_size * field.element_size
                    lines.append(f'            buffer[{fmt_offset(base_offset)}] = {var_name}Count;')
                    lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {fmt_offset(base_offset + 1)}, Math.Min({var_name}Data.Length, {total_size}));')
            else:
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.fieldType, 1)
                array_size = field.size_option if field.size_option else field.max_size
                total_data_size = field.size - (1 if field.max_size else 0)  # subtract count byte if variable
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {fmt_offset(base_offset)}, Math.Min({var_name}.Length, {field.size_option}));')
                    elif field.fieldType in csharp_type_sizes:
                        # Primitive array - use Buffer.BlockCopy
                        lines.append(f'            if ({var_name} != null)')
                        lines.append(f'                Buffer.BlockCopy({var_name}, 0, buffer, {fmt_offset(base_offset)}, Math.Min({var_name}.Length * {element_size}, {total_data_size}));')
                    else:
                        # Nested struct array - serialize each element using SerializeTo
                        lines.append(f'            if ({var_name} != null)')
                        lines.append(f'                for (int i = 0; i < Math.Min({var_name}.Length, {field.size_option}); i++)')
                        if use_offset_param:
                            lines.append(f'                    if ({var_name}[i] != null) {var_name}[i].SerializeTo(buffer, {fmt_offset(base_offset)} + i * {element_size});')
                        else:
                            lines.append(f'                    if ({var_name}[i] != null) {{ var bytes = {var_name}[i].Serialize(); Array.Copy(bytes, 0, buffer, {base_offset} + i * {element_size}, bytes.Length); }}')
                elif field.max_size is not None:
                    # Variable array
                    count_size = 2 if field.max_size > 255 else 1
                    if field.max_size > 255:
                        lines.append(f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 2), {var_name}Count);')
                    else:
                        lines.append(f'            buffer[{fmt_offset(base_offset)}] = {var_name}Count;')
                    if field.isEnum:
                        lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {fmt_offset(base_offset + count_size)}, Math.Min({var_name}Data.Length, {field.max_size}));')
                    elif field.fieldType in csharp_type_sizes:
                        # Primitive array
                        lines.append(f'            if ({var_name}Data != null)')
                        lines.append(f'                Buffer.BlockCopy({var_name}Data, 0, buffer, {fmt_offset(base_offset + count_size)}, Math.Min({var_name}Data.Length * {element_size}, {total_data_size}));')
                    else:
                        # Nested struct array - serialize each element using SerializeTo
                        lines.append(f'            if ({var_name}Data != null)')
                        lines.append(f'                for (int i = 0; i < Math.Min({var_name}Data.Length, {field.max_size}); i++)')
                        if use_offset_param:
                            lines.append(f'                    if ({var_name}Data[i] != null) {var_name}Data[i].SerializeTo(buffer, {fmt_offset(base_offset + count_size)} + i * {element_size});')
                        else:
                            lines.append(f'                    if ({var_name}Data[i] != null) {{ var bytes = {var_name}Data[i].Serialize(); Array.Copy(bytes, 0, buffer, {base_offset + count_size} + i * {element_size}, bytes.Length); }}')
        elif type_name in csharp_type_sizes:
            # Single primitive field (not array)
            size = csharp_type_sizes[type_name]
            if type_name == "uint8":
                lines.append(f'            buffer[{fmt_offset(base_offset)}] = {var_name};')
            elif type_name == "int8":
                lines.append(f'            buffer[{fmt_offset(base_offset)}] = (byte){var_name};')
            elif type_name == "uint16":
                lines.append(f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 2), {var_name});')
            elif type_name == "int16":
                lines.append(f'            BinaryPrimitives.WriteInt16LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 2), {var_name});')
            elif type_name == "uint32":
                lines.append(f'            BinaryPrimitives.WriteUInt32LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 4), {var_name});')
            elif type_name == "int32":
                lines.append(f'            BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 4), {var_name});')
            elif type_name == "uint64":
                lines.append(f'            BinaryPrimitives.WriteUInt64LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 8), {var_name});')
            elif type_name == "int64":
                lines.append(f'            BinaryPrimitives.WriteInt64LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 8), {var_name});')
            elif type_name == "float":
                lines.append(f'            BinaryPrimitives.WriteSingleLittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 4), {var_name});')
            elif type_name == "double":
                lines.append(f'            BinaryPrimitives.WriteDoubleLittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 8), {var_name});')
            elif type_name == "bool":
                lines.append(f'            buffer[{fmt_offset(base_offset)}] = (byte)({var_name} ? 1 : 0);')
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {fmt_offset(base_offset)}, Math.Min({var_name}.Length, {field.size_option}));')
            elif field.max_size is not None:
                # Variable string
                length_size = 2 if field.max_size > 255 else 1
                if field.max_size > 255:
                    lines.append(f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan({fmt_offset(base_offset)}, 2), {var_name}Length);')
                else:
                    lines.append(f'            buffer[{fmt_offset(base_offset)}] = {var_name}Length;')
                lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {fmt_offset(base_offset + length_size)}, Math.Min({var_name}Data.Length, {field.max_size}));')
        elif field.isEnum:
            # Single enum field - enums are byte values
            lines.append(f'            buffer[{fmt_offset(base_offset)}] = (byte){var_name};')
        else:
            # Nested struct - use SerializeTo for efficiency
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
            if use_offset_param:
                lines.append(f'            if ({var_name} != null) {var_name}.SerializeTo(buffer, {fmt_offset(base_offset)});')
            else:
                lines.append(f'            if ({var_name} != null) {{ var nestedBytes = {var_name}.Serialize(); Array.Copy(nestedBytes, 0, buffer, {base_offset}, nestedBytes.Length); }}')

        return lines

    @staticmethod
    def generate_unpack_code(field, offset):
        """Generate code to unpack this field from a byte array"""
        lines = []
        var_name = pascalCase(field.name)
        type_name = field.fieldType

        # IMPORTANT: Check is_array FIRST to handle arrays of primitives correctly
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:
                    # Fixed string array
                    total_size = field.size_option * field.element_size
                    lines.append(f'            msg.{var_name} = new byte[{total_size}];')
                    lines.append(f'            Array.Copy(data, {offset}, msg.{var_name}, 0, {total_size});')
                elif field.max_size is not None:
                    # Variable string array
                    total_size = field.max_size * field.element_size
                    lines.append(f'            msg.{var_name}Count = data[{offset}];')
                    lines.append(f'            msg.{var_name}Data = new byte[{total_size}];')
                    lines.append(f'            Array.Copy(data, {offset + 1}, msg.{var_name}Data, 0, {total_size});')
            else:
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.fieldType, 1)
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                        lines.append(f'            Array.Copy(data, {offset}, msg.{var_name}, 0, {field.size_option});')
                    elif field.fieldType in csharp_type_sizes:
                        base_type = csharp_types.get(field.fieldType, field.fieldType)
                        total_data_size = field.size
                        lines.append(f'            msg.{var_name} = new {base_type}[{field.size_option}];')
                        lines.append(f'            Buffer.BlockCopy(data, {offset}, msg.{var_name}, 0, {total_data_size});')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                        element_size = field.element_size if field.element_size else (field.size // field.size_option)
                        lines.append(f'            msg.{var_name} = new {nested_type}[{field.size_option}];')
                        lines.append(f'            for (int i = 0; i < {field.size_option}; i++)')
                        lines.append(f'            {{')
                        lines.append(f'                int elemOffset = {offset} + i * {element_size};')
                        lines.append(f'                msg.{var_name}[i] = {nested_type}.Deserialize(data[elemOffset..(elemOffset + {element_size})]);')
                        lines.append(f'            }}')
                elif field.max_size is not None:
                    # Variable array
                    count_size = 2 if field.max_size > 255 else 1
                    if field.max_size > 255:
                        lines.append(f'            msg.{var_name}Count = BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 2));')
                    else:
                        lines.append(f'            msg.{var_name}Count = data[{offset}];')
                    if field.isEnum:
                        lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                        lines.append(f'            Array.Copy(data, {offset + count_size}, msg.{var_name}Data, 0, {field.max_size});')
                    elif field.fieldType in csharp_type_sizes:
                        base_type = csharp_types.get(field.fieldType, field.fieldType)
                        total_data_size = field.size - count_size  # subtract count bytes
                        lines.append(f'            msg.{var_name}Data = new {base_type}[{field.max_size}];')
                        lines.append(f'            Buffer.BlockCopy(data, {offset + count_size}, msg.{var_name}Data, 0, {total_data_size});')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                        element_size = field.element_size if field.element_size else ((field.size - count_size) // field.max_size)
                        lines.append(f'            msg.{var_name}Data = new {nested_type}[{field.max_size}];')
                        lines.append(f'            for (int i = 0; i < {field.max_size}; i++)')
                        lines.append(f'            {{')
                        lines.append(f'                int elemOffset = {offset + count_size} + i * {element_size};')
                        lines.append(f'                msg.{var_name}Data[i] = {nested_type}.Deserialize(data[elemOffset..(elemOffset + {element_size})]);')
                        lines.append(f'            }}')
        elif type_name in csharp_type_sizes:
            # Single primitive field (not array)
            if type_name == "uint8":
                lines.append(f'            msg.{var_name} = data[{offset}];')
            elif type_name == "int8":
                lines.append(f'            msg.{var_name} = (sbyte)data[{offset}];')
            elif type_name == "uint16":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 2));')
            elif type_name == "int16":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt16LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 2));')
            elif type_name == "uint32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt32LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 4));')
            elif type_name == "int32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt32LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 4));')
            elif type_name == "uint64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt64LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 8));')
            elif type_name == "int64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt64LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 8));')
            elif type_name == "float":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadSingleLittleEndian(new ReadOnlySpan<byte>(data, {offset}, 4));')
            elif type_name == "double":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadDoubleLittleEndian(new ReadOnlySpan<byte>(data, {offset}, 8));')
            elif type_name == "bool":
                lines.append(f'            msg.{var_name} = data[{offset}] != 0;')
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                lines.append(f'            Array.Copy(data, {offset}, msg.{var_name}, 0, {field.size_option});')
            elif field.max_size is not None:
                # Variable string
                length_size = 2 if field.max_size > 255 else 1
                if field.max_size > 255:
                    lines.append(f'            msg.{var_name}Length = BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, {offset}, 2));')
                else:
                    lines.append(f'            msg.{var_name}Length = data[{offset}];')
                lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                lines.append(f'            Array.Copy(data, {offset + length_size}, msg.{var_name}Data, 0, {field.max_size});')
        elif field.isEnum:
            # Single enum field - enums are byte values, cast to enum type
            type_pkg = field.type_package if field.type_package else field.package
            enum_type = '%s%s' % (pascalCase(type_pkg), type_name)
            lines.append(f'            msg.{var_name} = ({enum_type})data[{offset}];')
        else:
            # Nested struct
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
            struct_size = field.size
            lines.append(f'            msg.{var_name} = {nested_type}.Deserialize(data[{offset}..({offset} + {struct_size})]);')

        return lines


class MessageCSharpGen():
    @staticmethod
    def generate(msg, package=None, equality=False):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result += '    /// <summary>\n'
                result += '    /// %s\n' % c.strip('/')
                result += '    /// </summary>\n'

        structName = '%s%s' % (pascalCase(msg.package), msg.name)

        # Add IEquatable<T> interface if equality is requested
        if equality:
            result += '    public class %s : IStructFrameMessage<%s>, IEquatable<%s>\n' % (structName, structName, structName)
        else:
            result += '    public class %s : IStructFrameMessage<%s>\n' % (structName, structName)
        result += '    {\n'

        result += '        public const int MaxSize = %d;\n' % msg.size
        if msg.id:
            if package and package.package_id is not None:
                combined_msg_id = (package.package_id << 8) | msg.id
                result += '        public const ushort MsgId = %d;\n' % combined_msg_id
            else:
                result += '        public const ushort MsgId = %d;\n' % msg.id
        
        # Add magic numbers for checksum
        if msg.id is not None and msg.magic_bytes:
            result += f'        public const byte Magic1 = {msg.magic_bytes[0]}; // Checksum magic (based on field types and positions)\n'
            result += f'        public const byte Magic2 = {msg.magic_bytes[1]}; // Checksum magic (based on field types and positions)\n'
        
        # Add variable message constants
        if msg.variable:
            result += f'        public const int MinSize = {msg.min_size}; // Minimum size when all variable fields are empty\n'
            result += f'        public const bool IsVariable = true; // This message uses variable-length encoding\n'
        
        result += '\n'

        # Generate field declarations
        for key, f in msg.fields.items():
            result += FieldCSharpGen.generate_field_declaration(f)

        # Generate oneofs - declarations for discriminator and union members
        for key, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'        public ushort {pascalCase(oneof.name)}Discriminator;\n'
            for field_name, field in oneof.fields.items():
                result += f'        // Union member: {field_name}\n'
                result += FieldCSharpGen.generate_field_declaration(field)

        # Generate Serialize() method
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Serialize this message into a byte array\n'
        if msg.variable:
            result += '        /// For variable messages: returns variable-length encoding by default\n'
            result += '        /// Use SerializeMaxSize() for MAX_SIZE encoding (needed for minimal profiles)\n'
        result += '        /// </summary>\n'
        result += '        public byte[] Serialize()\n'
        result += '        {\n'
        if msg.variable:
            # Variable messages return variable-length encoding by default
            result += '            return _SerializeVariable();\n'
        else:
            result += '            byte[] buffer = new byte[MaxSize];\n'
            result += '            SerializeTo(buffer, 0);\n'
            result += '            return buffer;\n'
        result += '        }\n'
        
        # For variable messages, add SerializeMaxSize() method
        if msg.variable:
            result += '\n'
            result += '        /// <summary>\n'
            result += '        /// Serialize this message to MAX_SIZE (for minimal profiles without length field)\n'
            result += '        /// </summary>\n'
            result += '        public byte[] SerializeMaxSize()\n'
            result += '        {\n'
            result += '            byte[] buffer = new byte[MaxSize];\n'
            result += '            SerializeTo(buffer, 0);\n'
            result += '            return buffer;\n'
            result += '        }\n'
        
        # Generate SerializeTo() method for zero-allocation serialization
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Serialize this message into an existing buffer (zero allocation).\n'
        result += '        /// Returns the number of bytes written.\n'
        result += '        /// </summary>\n'
        result += '        public int SerializeTo(byte[] buffer, int offset)\n'
        result += '        {\n'

        offset = 0
        for key, f in msg.fields.items():
            pack_lines = FieldCSharpGen.generate_pack_code(f, offset, use_offset_param=True)
            for line in pack_lines:
                result += line + '\n'
            offset += f.size

        # Generate oneof packing code
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                result += f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset + {offset}), {pascalCase(oneof_name)}Discriminator);\n'
                offset += 2
            
            result += f'            // Oneof {oneof_name} payload (union size: {oneof.size})\n'
            first = True
            for field_name, field in oneof.fields.items():
                type_name = '%s%s' % (pascalCase(field.package), field.fieldType)
                field_var = pascalCase(field_name)
                if first:
                    result += f'            if ({field_var} != null)\n'
                    first = False
                else:
                    result += f'            else if ({field_var} != null)\n'
                result += '            {\n'
                result += f'                {field_var}.SerializeTo(buffer, offset + {offset});\n'
                result += '            }\n'
            offset += oneof.size

        result += f'            return MaxSize;\n'
        result += '        }\n'

        # Generate Deserialize() static method
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize a byte array into this message type\n'
        if msg.variable:
            result += '        /// For variable messages: auto-detects MAX_SIZE vs variable encoding\n'
        result += '        /// </summary>\n'
        result += f'        public static {structName} Deserialize(byte[] data)\n'
        result += '        {\n'
        
        # For variable messages, detect format based on size
        if msg.variable:
            result += f'            // Variable message - detect encoding format\n'
            result += f'            if (data.Length == MaxSize)\n'
            result += '            {\n'
            result += f'                // MAX_SIZE encoding (minimal profiles)\n'
            result += f'                return _DeserializeMaxSize(data);\n'
            result += '            }\n'
            result += '            else\n'
            result += '            {\n'
            result += f'                // Variable-length encoding\n'
            result += f'                return _DeserializeVariable(data);\n'
            result += '            }\n'
            result += '        }\n'
            
            # Add _DeserializeMaxSize for variable messages
            result += '\n'
            result += '        /// <summary>\n'
            result += '        /// Deserialize from MAX_SIZE buffer (for minimal profiles)\n'
            result += '        /// </summary>\n'
            result += f'        private static {structName} _DeserializeMaxSize(byte[] data)\n'
            result += '        {\n'
        
        result += f'            var msg = new {structName}();\n'

        offset = 0
        for key, f in msg.fields.items():
            unpack_lines = FieldCSharpGen.generate_unpack_code(f, offset)
            for line in unpack_lines:
                result += line + '\n'
            offset += f.size

        # Generate oneof unpacking code
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                result += f'            msg.{pascalCase(oneof_name)}Discriminator = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan({offset}));\n'
                result += f'            var {oneof_name}_discriminator = msg.{pascalCase(oneof_name)}Discriminator;\n'
                offset += 2
            
            result += f'            // Oneof {oneof_name} payload (union size: {oneof.size})\n'
            if oneof.auto_discriminator:
                first = True
                for field_name, field in oneof.fields.items():
                    type_name = '%s%s' % (pascalCase(field.package), field.fieldType)
                    field_var = pascalCase(field_name)
                    if first:
                        result += f'            if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                        first = False
                    else:
                        result += f'            else if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                    result += '            {\n'
                    result += f'                msg.{field_var} = {type_name}.Deserialize(data[{offset}..({offset} + {type_name}.MaxSize)]);\n'
                    result += '            }\n'
            offset += oneof.size

        result += '            return msg;\n'
        result += '        }\n'

        # Add FrameMsgInfo overload
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize message from FrameMsgInfo (convenience overload)\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="frameInfo">Frame information from frame parser</param>\n'
        result += '        /// <returns>Deserialized message</returns>\n'
        result += f'        public static {structName} Deserialize(FrameMsgInfo frameInfo)\n'
        result += '        {\n'
        result += '            // Extract payload from frame info\n'
        result += '            if (frameInfo.MsgData == null)\n'
        result += '            {\n'
        result += '                return new ' + structName + '();\n'
        result += '            }\n'
        result += '            byte[] payload;\n'
        result += '            if (frameInfo.MsgDataOffset > 0)\n'
        result += '            {\n'
        result += '                // Copy from offset to new array\n'
        result += '                payload = new byte[frameInfo.MsgLen];\n'
        result += '                Array.Copy(frameInfo.MsgData, frameInfo.MsgDataOffset, payload, 0, frameInfo.MsgLen);\n'
        result += '            }\n'
        result += '            else\n'
        result += '            {\n'
        result += '                payload = frameInfo.MsgData;\n'
        result += '            }\n'
        result += '            return Deserialize(payload);\n'
        result += '        }\n'

        # Generate interface implementation methods
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Get the message ID (IStructFrameMessage)\n'
        result += '        /// </summary>\n'
        if msg.id is not None:
            result += '        public ushort GetMsgId() => MsgId;\n'
        else:
            result += '        public ushort GetMsgId() => 0;\n'
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Get the message size (IStructFrameMessage)\n'
        result += '        /// </summary>\n'
        result += '        public int GetSize() => MaxSize;\n'
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Get the magic numbers for checksum (IStructFrameMessage)\n'
        result += '        /// </summary>\n'
        if msg.id is not None and msg.magic_bytes:
            result += f'        public (byte Magic1, byte Magic2) GetMagicNumbers() => (Magic1, Magic2);\n'
        else:
            result += '        public (byte Magic1, byte Magic2) GetMagicNumbers() => (0, 0);\n'

        # Generate variable message methods if this is a variable message
        if msg.variable:
            result += MessageCSharpGen._generate_variable_methods(msg, structName)

        # Generate equality members if requested
        if equality:
            result += MessageCSharpGen._generate_equality_members(msg, structName)

        result += '    }\n'

        return result + '\n'
    
    @staticmethod
    def _generate_variable_methods(msg, structName):
        """Generate SerializedSize, _SerializeVariable, and _DeserializeVariable methods for variable messages."""
        result = '\n'
        
        # Generate SerializedSize method
        result += '        /// <summary>\n'
        result += '        /// Calculate the serialized size using variable-length encoding\n'
        result += '        /// </summary>\n'
        result += '        public int SerializedSize()\n'
        result += '        {\n'
        result += '            int size = 0;\n'
        
        for key, f in msg.fields.items():
            var_name = pascalCase(f.name)
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if f.fieldType == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    element_size = type_sizes.get(f.fieldType, (f.size - 1) // f.max_size)
                result += f'            size += 1 + ({var_name}Count * {element_size}); // {f.name}\n'
            elif f.fieldType == "string" and f.max_size is not None:
                result += f'            size += 1 + {var_name}Length; // {f.name}\n'
            else:
                result += f'            size += {f.size}; // {f.name}\n'
        
        result += '            return size;\n'
        result += '        }\n'
        
        # Generate _SerializeVariable method (internal method)
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Serialize message using variable-length encoding (only serializes used bytes)\n'
        result += '        /// </summary>\n'
        result += '        private byte[] _SerializeVariable()\n'
        result += '        {\n'
        result += '            int size = SerializedSize();\n'
        result += '            byte[] buffer = new byte[size];\n'
        result += '            int offset = 0;\n'
        
        for key, f in msg.fields.items():
            var_name = pascalCase(f.name)
            type_name = f.fieldType
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if type_name == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    element_size = type_sizes.get(type_name, (f.size - 1) // f.max_size)
                result += f'            // {f.name}: variable array\n'
                result += f'            buffer[offset++] = {var_name}Count;\n'
                if type_name in type_sizes:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                Buffer.BlockCopy({var_name}Data, 0, buffer, offset, {var_name}Count * {element_size});\n'
                    result += f'            offset += {var_name}Count * {element_size};\n'
                elif f.isEnum:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                Array.Copy({var_name}Data, 0, buffer, offset, {var_name}Count);\n'
                    result += f'            offset += {var_name}Count;\n'
                else:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                for (int i = 0; i < {var_name}Count; i++)\n'
                    result += f'                    if ({var_name}Data[i] != null) {{ var bytes = {var_name}Data[i].Pack(); Array.Copy(bytes, 0, buffer, offset + i * {element_size}, bytes.Length); }}\n'
                    result += f'            offset += {var_name}Count * {element_size};\n'
            elif type_name == "string" and f.max_size is not None:
                result += f'            // {f.name}: variable string\n'
                result += f'            buffer[offset++] = {var_name}Length;\n'
                result += f'            if ({var_name}Data != null)\n'
                result += f'                Array.Copy({var_name}Data, 0, buffer, offset, {var_name}Length);\n'
                result += f'            offset += {var_name}Length;\n'
            else:
                # Fixed field - generate pack code inline
                if type_name in csharp_type_sizes:
                    size = csharp_type_sizes[type_name]
                    if type_name == "uint8":
                        result += f'            buffer[offset++] = {var_name};\n'
                    elif type_name == "int8":
                        result += f'            buffer[offset++] = (byte){var_name};\n'
                    elif type_name == "uint16":
                        result += f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset, 2), {var_name}); offset += 2;\n'
                    elif type_name == "int16":
                        result += f'            BinaryPrimitives.WriteInt16LittleEndian(buffer.AsSpan(offset, 2), {var_name}); offset += 2;\n'
                    elif type_name == "uint32":
                        result += f'            BinaryPrimitives.WriteUInt32LittleEndian(buffer.AsSpan(offset, 4), {var_name}); offset += 4;\n'
                    elif type_name == "int32":
                        result += f'            BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan(offset, 4), {var_name}); offset += 4;\n'
                    elif type_name == "uint64":
                        result += f'            BinaryPrimitives.WriteUInt64LittleEndian(buffer.AsSpan(offset, 8), {var_name}); offset += 8;\n'
                    elif type_name == "int64":
                        result += f'            BinaryPrimitives.WriteInt64LittleEndian(buffer.AsSpan(offset, 8), {var_name}); offset += 8;\n'
                    elif type_name == "float":
                        result += f'            BinaryPrimitives.WriteSingleLittleEndian(buffer.AsSpan(offset, 4), {var_name}); offset += 4;\n'
                    elif type_name == "double":
                        result += f'            BinaryPrimitives.WriteDoubleLittleEndian(buffer.AsSpan(offset, 8), {var_name}); offset += 8;\n'
                    elif type_name == "bool":
                        result += f'            buffer[offset++] = (byte)({var_name} ? 1 : 0);\n'
                elif type_name == "string" and f.size_option is not None:
                    # Fixed string - copy from byte array
                    result += f'            if ({var_name} != null)\n'
                    result += f'                Array.Copy({var_name}, 0, buffer, offset, Math.Min({var_name}.Length, {f.size}));\n'
                    result += f'            offset += {f.size};\n'
                elif f.isEnum:
                    result += f'            buffer[offset++] = (byte){var_name};\n'
                else:
                    # Nested struct
                    result += f'            if ({var_name} != null) {{ var nestedBytes = {var_name}.Pack(); Array.Copy(nestedBytes, 0, buffer, offset, nestedBytes.Length); }}\n'
                    result += f'            offset += {f.size};\n'
        
        result += '            return buffer;\n'
        result += '        }\n'
        
        # Generate _DeserializeVariable static method (internal method)
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize message from variable-length encoded buffer\n'
        result += '        /// </summary>\n'
        result += f'        private static {structName} _DeserializeVariable(byte[] data)\n'
        result += '        {\n'
        result += f'            var msg = new {structName}();\n'
        result += '            int offset = 0;\n'
        
        for key, f in msg.fields.items():
            var_name = pascalCase(f.name)
            type_name = f.fieldType
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if type_name == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    count_size = 2 if f.max_size > 255 else 1
                    element_size = type_sizes.get(type_name, (f.size - count_size) // f.max_size)
                result += f'            // {f.name}: variable array\n'
                if f.max_size > 255:
                    result += f'            msg.{var_name}Count = Math.Min(BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, offset, 2)), (ushort){f.max_size});\n'
                    result += f'            offset += 2;\n'
                else:
                    result += f'            msg.{var_name}Count = Math.Min(data[offset++], (byte){f.max_size});\n'
                if type_name in type_sizes:
                    base_type = csharp_types.get(type_name, type_name)
                    result += f'            msg.{var_name}Data = new {base_type}[{f.max_size}];\n'
                    result += f'            Buffer.BlockCopy(data, offset, msg.{var_name}Data, 0, msg.{var_name}Count * {element_size});\n'
                    result += f'            offset += msg.{var_name}Count * {element_size};\n'
                elif f.isEnum:
                    result += f'            msg.{var_name}Data = new byte[{f.max_size}];\n'
                    result += f'            Array.Copy(data, offset, msg.{var_name}Data, 0, msg.{var_name}Count);\n'
                    result += f'            offset += msg.{var_name}Count;\n'
                else:
                    type_pkg = f.type_package if f.type_package else f.package
                    nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
                    result += f'            msg.{var_name}Data = new {nested_type}[{f.max_size}];\n'
                    result += f'            for (int i = 0; i < msg.{var_name}Count; i++)\n'
                    result += f'                msg.{var_name}Data[i] = {nested_type}.Deserialize(data[(offset + i * {element_size})..(offset + (i + 1) * {element_size})]);\n'
                    result += f'            offset += msg.{var_name}Count * {element_size};\n'
            elif type_name == "string" and f.max_size is not None:
                result += f'            // {f.name}: variable string\n'
                if f.max_size > 255:
                    result += f'            msg.{var_name}Length = Math.Min(BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, offset, 2)), (ushort){f.max_size});\n'
                    result += f'            offset += 2;\n'
                else:
                    result += f'            msg.{var_name}Length = Math.Min(data[offset++], (byte){f.max_size});\n'
                result += f'            msg.{var_name}Data = new byte[{f.max_size}];\n'
                result += f'            Array.Copy(data, offset, msg.{var_name}Data, 0, msg.{var_name}Length);\n'
                result += f'            offset += msg.{var_name}Length;\n'
            else:
                # Fixed field
                if type_name in csharp_type_sizes:
                    if type_name == "uint8":
                        result += f'            msg.{var_name} = data[offset++];\n'
                    elif type_name == "int8":
                        result += f'            msg.{var_name} = (sbyte)data[offset++];\n'
                    elif type_name == "uint16":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset, 2)); offset += 2;\n'
                    elif type_name == "int16":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadInt16LittleEndian(data.AsSpan(offset, 2)); offset += 2;\n'
                    elif type_name == "uint32":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(offset, 4)); offset += 4;\n'
                    elif type_name == "int32":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(offset, 4)); offset += 4;\n'
                    elif type_name == "uint64":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadUInt64LittleEndian(data.AsSpan(offset, 8)); offset += 8;\n'
                    elif type_name == "int64":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadInt64LittleEndian(data.AsSpan(offset, 8)); offset += 8;\n'
                    elif type_name == "float":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(offset, 4)); offset += 4;\n'
                    elif type_name == "double":
                        result += f'            msg.{var_name} = BinaryPrimitives.ReadDoubleLittleEndian(data.AsSpan(offset, 8)); offset += 8;\n'
                    elif type_name == "bool":
                        result += f'            msg.{var_name} = data[offset++] != 0;\n'
                elif type_name == "string" and f.size_option is not None:
                    # Fixed string - copy into byte array
                    result += f'            msg.{var_name} = new byte[{f.size}];\n'
                    result += f'            Array.Copy(data, offset, msg.{var_name}, 0, {f.size});\n'
                    result += f'            offset += {f.size};\n'
                elif f.isEnum:
                    type_pkg = f.type_package if f.type_package else f.package
                    enum_type = '%s%s' % (pascalCase(type_pkg), type_name)
                    result += f'            msg.{var_name} = ({enum_type})data[offset++];\n'
                else:
                    type_pkg = f.type_package if f.type_package else f.package
                    nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
                    result += f'            msg.{var_name} = {nested_type}.Deserialize(data[offset..(offset + {nested_type}.MaxSize)]); offset += {nested_type}.MaxSize;\n'
        
        result += '            return msg;\n'
        result += '        }\n'
        
        return result
    
    @staticmethod
    def _generate_equality_members(msg, structName):
        """Generate Equals, GetHashCode, and equality operators."""
        result = '\n'
        
        # Generate Equals method
        result += '        /// <summary>\n'
        result += '        /// Compare this message with another for equality\n'
        result += '        /// </summary>\n'
        result += f'        public bool Equals({structName}? other)\n'
        result += '        {\n'
        result += '            if (other is null) return false;\n'
        result += '            if (ReferenceEquals(this, other)) return true;\n'
        
        comparisons = []
        for key, f in msg.fields.items():
            field_name = pascalCase(f.name)
            
            # Handle arrays
            if f.is_array:
                if f.size_option is not None:
                    # Fixed array - use SequenceEqual
                    comparisons.append(f'{field_name}.SequenceEqual(other.{field_name})')
                elif f.max_size is not None:
                    # Variable array - compare count and data
                    comparisons.append(f'{field_name}Count == other.{field_name}Count')
                    comparisons.append(f'{field_name}Data.SequenceEqual(other.{field_name}Data)')
            
            # Handle strings
            elif f.fieldType == "string":
                if f.size_option is not None:
                    # Fixed string - use SequenceEqual
                    comparisons.append(f'{field_name}.SequenceEqual(other.{field_name})')
                elif f.max_size is not None:
                    # Variable string - compare length and data
                    comparisons.append(f'{field_name}Length == other.{field_name}Length')
                    comparisons.append(f'{field_name}Data.SequenceEqual(other.{field_name}Data)')
            
            # Handle enums (value types)
            elif f.isEnum:
                comparisons.append(f'{field_name} == other.{field_name}')
            
            # Handle nested messages
            elif f.fieldType not in csharp_types:
                comparisons.append(f'({field_name}?.Equals(other.{field_name}) ?? other.{field_name} is null)')
            
            # Handle primitives
            else:
                comparisons.append(f'{field_name} == other.{field_name}')
        
        # Add oneof fields
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                comparisons.append(f'{pascalCase(oneof_name)}Discriminator == other.{pascalCase(oneof_name)}Discriminator')
            for field_name, field in oneof.fields.items():
                field_var = pascalCase(field_name)
                comparisons.append(f'({field_var}?.Equals(other.{field_var}) ?? other.{field_var} is null)')
        
        if comparisons:
            result += '            return ' + ' &&\n                   '.join(comparisons) + ';\n'
        else:
            result += '            return true;\n'
        
        result += '        }\n\n'
        
        # Generate override Equals(object)
        result += '        /// <summary>\n'
        result += '        /// Compare this message with an object for equality\n'
        result += '        /// </summary>\n'
        result += '        public override bool Equals(object? obj)\n'
        result += '        {\n'
        result += f'            return obj is {structName} other && Equals(other);\n'
        result += '        }\n\n'
        
        # Generate GetHashCode
        result += '        /// <summary>\n'
        result += '        /// Get hash code for this message\n'
        result += '        /// </summary>\n'
        result += '        public override int GetHashCode()\n'
        result += '        {\n'
        result += '            var hash = new HashCode();\n'
        for key, f in msg.fields.items():
            field_name = pascalCase(f.name)
            if f.is_array:
                if f.size_option is not None:
                    # Fixed array
                    result += f'            foreach (var b in {field_name}) hash.Add(b);\n'
                elif f.max_size is not None:
                    # Variable array
                    result += f'            hash.Add({field_name}Count);\n'
                    result += f'            foreach (var b in {field_name}Data) hash.Add(b);\n'
            elif f.fieldType == "string":
                if f.size_option is not None:
                    # Fixed string
                    result += f'            foreach (var b in {field_name}) hash.Add(b);\n'
                elif f.max_size is not None:
                    # Variable string
                    result += f'            hash.Add({field_name}Length);\n'
                    result += f'            foreach (var b in {field_name}Data) hash.Add(b);\n'
            else:
                result += f'            hash.Add({field_name});\n'
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'            hash.Add({pascalCase(oneof_name)}Discriminator);\n'
            for field_name, field in oneof.fields.items():
                result += f'            hash.Add({pascalCase(field_name)});\n'
        result += '            return hash.ToHashCode();\n'
        result += '        }\n\n'
        
        # Generate equality operators
        result += '        /// <summary>\n'
        result += '        /// Equality operator\n'
        result += '        /// </summary>\n'
        result += f'        public static bool operator ==({structName}? left, {structName}? right)\n'
        result += '        {\n'
        result += '            if (left is null) return right is null;\n'
        result += '            return left.Equals(right);\n'
        result += '        }\n\n'
        
        result += '        /// <summary>\n'
        result += '        /// Inequality operator\n'
        result += '        /// </summary>\n'
        result += f'        public static bool operator !=({structName}? left, {structName}? right)\n'
        result += '        {\n'
        result += '            return !(left == right);\n'
        result += '        }\n'
        
        return result


class FileCSharpGen():
    @staticmethod
    def generate(package, equality=False):
        yield '// Automatically generated struct frame code for C#\n'
        yield '// Generated by %s at %s.\n\n' % (version, time.asctime())

        yield '#nullable enable\n\n'
        yield 'using System;\n'
        yield 'using System.Collections.Generic;\n'
        
        # Add LINQ for SequenceEqual when equality is enabled
        if equality:
            yield 'using System.Linq;\n'
        yield 'using System.Buffers.Binary;\n'
        yield 'using System.Runtime.InteropServices;\n'
        yield 'using StructFrame;\n'
        
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
            yield '    // Message definitions\n'
            for key, msg in package.sortedMessages().items():
                yield MessageCSharpGen.generate(msg, package, equality)
            yield '\n'

        # Generate helper class with message definitions
        if package.messages:
            namespace_name_local = pascalCase(package.name)
            yield '    /// <summary>\n'
            yield '    /// Message registry and utilities for automatic message lookup and deserialization.\n'
            yield '    /// </summary>\n'
            yield '    public static class MessageDefinitions\n'
            yield '    {\n'
            
            # Generate MessageEntry record for the registry
            yield '        /// <summary>\n'
            yield '        /// Information about a registered message type.\n'
            yield '        /// </summary>\n'
            yield '        public record MessageEntry(\n'
            yield '            ushort Id,\n'
            yield '            string Name,\n'
            yield '            Type PayloadType,\n'
            yield '            Func<byte[], IStructFrameMessage?> Deserializer,\n'
            yield '            int MaxSize,\n'
            yield '            byte Magic1,\n'
            yield '            byte Magic2\n'
            yield '        );\n\n'
            
            # Generate the static registry
            yield '        /// <summary>\n'
            yield '        /// Static registry of all message types.\n'
            yield '        /// </summary>\n'
            yield '        private static readonly Dictionary<ushort, MessageEntry> _registryById = new()\n'
            yield '        {\n'
            
            for key, msg in package.sortedMessages().items():
                if msg.id:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    magic1 = '0'
                    magic2 = '0'
                    if msg.magic_bytes:
                        magic1 = f'{structName}.Magic1'
                        magic2 = f'{structName}.Magic2'
                    if package.package_id is not None:
                        combined_msg_id = (package.package_id << 8) | msg.id
                        yield f'            {{ {combined_msg_id}, new MessageEntry({combined_msg_id}, "{msg.name}", typeof({structName}), data => {structName}.Deserialize(data), {structName}.MaxSize, {magic1}, {magic2}) }},\n'
                    else:
                        yield f'            {{ {structName}.MsgId, new MessageEntry({structName}.MsgId, "{msg.name}", typeof({structName}), data => {structName}.Deserialize(data), {structName}.MaxSize, {magic1}, {magic2}) }},\n'
            
            yield '        };\n\n'
            
            # Generate name lookup dictionary
            yield '        /// <summary>\n'
            yield '        /// Static registry for name-based lookup.\n'
            yield '        /// </summary>\n'
            yield '        private static readonly Dictionary<string, MessageEntry> _registryByName = new(StringComparer.OrdinalIgnoreCase)\n'
            yield '        {\n'
            
            for key, msg in package.sortedMessages().items():
                if msg.id:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    if package.package_id is not None:
                        combined_msg_id = (package.package_id << 8) | msg.id
                        yield f'            {{ "{msg.name}", _registryById[{combined_msg_id}] }},\n'
                    else:
                        yield f'            {{ "{msg.name}", _registryById[{structName}.MsgId] }},\n'
            
            yield '        };\n\n'
            
            # GetMessageInfo by ID
            yield '        /// <summary>\n'
            yield '        /// Get message info (size and magic numbers) for a given message ID.\n'
            yield '        /// </summary>\n'
            yield '        /// <param name="msgId">The message ID</param>\n'
            yield '        /// <returns>MessageInfo if found, null otherwise</returns>\n'
            
            if package.package_id is not None:
                yield '        public static MessageInfo? GetMessageInfo(int msgId)\n'
                yield '        {\n'
                yield '            byte pkgId = (byte)((msgId >> 8) & 0xFF);\n'
                yield '            byte localMsgId = (byte)(msgId & 0xFF);\n'
                yield '            \n'
                yield f'            if (pkgId != PackageInfo.PackageId)\n'
                yield '            {\n'
                yield '                return null;\n'
                yield '            }\n'
                yield '            \n'
                yield '            switch (localMsgId)\n'
                yield '            {\n'
            else:
                yield '        public static MessageInfo? GetMessageInfo(int msgId)\n'
                yield '        {\n'
                yield '            switch (msgId)\n'
                yield '            {\n'
            
            for key, msg in package.sortedMessages().items():
                if msg.id:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    magic1 = '0'
                    magic2 = '0'
                    if msg.magic_bytes:
                        magic1 = f'{structName}.Magic1'
                        magic2 = f'{structName}.Magic2'
                    if package.package_id is not None:
                        yield '                case %d: return new MessageInfo(%s.MaxSize, %s, %s);\n' % (msg.id, structName, magic1, magic2)
                    else:
                        yield '                case %s.MsgId: return new MessageInfo(%s.MaxSize, %s, %s);\n' % (structName, structName, magic1, magic2)
            yield '                default: return null;\n'
            yield '            }\n'
            yield '        }\n\n'
            
            # GetMessageEntry by ID
            yield '        /// <summary>\n'
            yield '        /// Get full message entry (including deserializer) for a given message ID.\n'
            yield '        /// </summary>\n'
            yield '        /// <param name="msgId">The message ID</param>\n'
            yield '        /// <returns>MessageEntry if found, null otherwise</returns>\n'
            yield '        public static MessageEntry? GetMessageEntry(ushort msgId)\n'
            yield '        {\n'
            yield '            return _registryById.TryGetValue(msgId, out var entry) ? entry : null;\n'
            yield '        }\n\n'
            
            # GetMessageEntry by name
            yield '        /// <summary>\n'
            yield '        /// Get message entry by name (case-insensitive).\n'
            yield '        /// </summary>\n'
            yield '        /// <param name="name">The message name</param>\n'
            yield '        /// <returns>MessageEntry if found, null otherwise</returns>\n'
            yield '        public static MessageEntry? GetMessageEntry(string name)\n'
            yield '        {\n'
            yield '            return _registryByName.TryGetValue(name, out var entry) ? entry : null;\n'
            yield '        }\n\n'
            
            # GetAllMessages
            yield '        /// <summary>\n'
            yield '        /// Get all registered message entries.\n'
            yield '        /// </summary>\n'
            yield '        /// <returns>Collection of all message entries</returns>\n'
            yield '        public static IEnumerable<MessageEntry> GetAllMessages()\n'
            yield '        {\n'
            yield '            return _registryById.Values;\n'
            yield '        }\n\n'
            
            # Deserialize method
            yield '        /// <summary>\n'
            yield '        /// Deserialize a message payload by message ID.\n'
            yield '        /// Automatically dispatches to the correct deserializer based on msgId.\n'
            yield '        /// </summary>\n'
            yield '        /// <param name="msgId">The message ID</param>\n'
            yield '        /// <param name="payload">The serialized payload bytes</param>\n'
            yield '        /// <returns>Deserialized message object, or null if unknown message ID</returns>\n'
            yield '        public static IStructFrameMessage? Deserialize(ushort msgId, byte[] payload)\n'
            yield '        {\n'
            yield '            if (_registryById.TryGetValue(msgId, out var entry))\n'
            yield '            {\n'
            yield '                return entry.Deserializer(payload);\n'
            yield '            }\n'
            yield '            return null;\n'
            yield '        }\n\n'
            
            # Deserialize from FrameMsgInfo
            yield '        /// <summary>\n'
            yield '        /// Deserialize a message from FrameMsgInfo.\n'
            yield '        /// Automatically dispatches to the correct deserializer based on msgId.\n'
            yield '        /// </summary>\n'
            yield '        /// <param name="frameInfo">Frame info from parser</param>\n'
            yield '        /// <returns>Deserialized message object, or null if unknown message ID</returns>\n'
            yield '        public static IStructFrameMessage? Deserialize(FrameMsgInfo frameInfo)\n'
            yield '        {\n'
            yield '            if (!frameInfo.Valid || frameInfo.MsgData == null)\n'
            yield '            {\n'
            yield '                return null;\n'
            yield '            }\n'
            yield '            \n'
            yield '            // Extract payload from frame info\n'
            yield '            byte[] payload;\n'
            yield '            if (frameInfo.MsgDataOffset > 0)\n'
            yield '            {\n'
            yield '                payload = new byte[frameInfo.MsgLen];\n'
            yield '                Array.Copy(frameInfo.MsgData, frameInfo.MsgDataOffset, payload, 0, frameInfo.MsgLen);\n'
            yield '            }\n'
            yield '            else if (frameInfo.MsgData.Length == frameInfo.MsgLen)\n'
            yield '            {\n'
            yield '                payload = frameInfo.MsgData;\n'
            yield '            }\n'
            yield '            else\n'
            yield '            {\n'
            yield '                payload = new byte[frameInfo.MsgLen];\n'
            yield '                Array.Copy(frameInfo.MsgData, 0, payload, 0, frameInfo.MsgLen);\n'
            yield '            }\n'
            yield '            \n'
            yield '            return Deserialize(frameInfo.MsgId, payload);\n'
            yield '        }\n\n'
            
            # Generic Deserialize<T>
            yield '        /// <summary>\n'
            yield '        /// Deserialize a message payload to a specific type.\n'
            yield '        /// </summary>\n'
            yield '        /// <typeparam name="T">The expected message type</typeparam>\n'
            yield '        /// <param name="payload">The serialized payload bytes</param>\n'
            yield '        /// <returns>Deserialized message, or null if type mismatch or invalid</returns>\n'
            yield '        public static T? Deserialize<T>(byte[] payload) where T : class, IStructFrameMessage\n'
            yield '        {\n'
            yield '            // Find the entry for type T\n'
            yield '            foreach (var entry in _registryById.Values)\n'
            yield '            {\n'
            yield '                if (entry.PayloadType == typeof(T))\n'
            yield '                {\n'
            yield '                    return entry.Deserializer(payload) as T;\n'
            yield '                }\n'
            yield '            }\n'
            yield '            return null;\n'
            yield '        }\n'
            
            yield '    }\n'

        yield '}\n'
