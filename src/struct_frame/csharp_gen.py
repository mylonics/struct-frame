#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
C# code generator for struct-frame.

This module generates C# code for struct serialization using
classes with manual Pack/Unpack methods for binary compatibility.
"""

from struct_frame import version, NamingStyleC, camel_to_snake_case, pascal_case, build_enum_leading_comments, build_enum_values, get_discriminator_enum_name, build_discriminator_enum_values, normalize_bytes_type
import os
import time

_style_c = NamingStyleC()

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
    "bytes": "byte[]",
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


def format_xml_summary(comments, indent='    '):
    """
    Format multi-line comments into a single XML summary block.
    
    Args:
        comments: List of comment strings
        indent: Indentation string (default: '    ')
    
    Returns:
        Formatted XML summary string with all comments in a single block
    """
    if not comments:
        return ''
    
    result = f'{indent}/// <summary>\n'
    for comment in comments:
        # Strip leading/trailing slashes and whitespace
        clean_comment = comment.strip('/').strip()
        result += f'{indent}/// {clean_comment}\n'
    result += f'{indent}/// </summary>\n'
    return result


class EnumCSharpGen():
    @staticmethod
    def generate(field):
        # C# uses XML doc comments with different formatting
        result = ''
        if field.comments:
            result += format_xml_summary(field.comments, indent='    ')

        enum_name = field.name
        result += '    public enum %s : byte\n' % enum_name
        result += '    {\n'

        def csharp_comment_formatter(comments):
            if not comments:
                return []
            lines = ['        /// <summary>']
            for c in comments:
                lines.append('        /// %s' % c.strip('/').strip())
            lines.append('        /// </summary>')
            return lines

        enum_values = build_enum_values(
            field, _style_c,
            value_format='        {name} = {value}{comma}',
            comment_formatter=csharp_comment_formatter,
            skip_trailing_comma=True
        )

        result += '\n'.join(enum_values)
        result += '\n    }\n'

        return result

    @staticmethod
    def generate_nested(field, name_override=None):
        """Generate a nested enum inside a C# class body (double-indented)."""
        result = ''
        if field.comments:
            result += format_xml_summary(field.comments, indent='        ')
        enum_name = name_override if name_override else field.name
        result += '        public enum %s : byte\n' % enum_name
        result += '        {\n'
        entries = list(field.data.items())
        for i, (entry_name, (value, comments)) in enumerate(entries):
            if comments:
                result += '            /// <summary>%s</summary>\n' % ' '.join(c.strip('/').strip() for c in comments)
            comma = ',' if i < len(entries) - 1 else ''
            result += '            %s = %d%s\n' % (pascal_case(entry_name), value, comma)
        result += '        }\n'
        return result

    @staticmethod
    def generate_discriminator_enum(oneof, msg_name):
        """Generate a discriminator enum for field_order oneofs in C#."""
        if not oneof.auto_discriminator or oneof.discriminator_type != "field_order":
            return ''

        enum_name = get_discriminator_enum_name(oneof, msg_name)

        def none_entry():
            return '        None = 0,'

        def field_entry(field_name, field_order, is_last):
            comma = '' if is_last else ','
            return f'        {pascal_case(field_name)} = {field_order}{comma}'

        lines = build_discriminator_enum_values(oneof, none_entry, field_entry)
        result = f'    /// <summary>Discriminator enum for {msg_name}.{oneof.name} oneof</summary>\n'
        result += f'    public enum {enum_name} : byte\n'
        result += f'    {{\n'
        result += '\n'.join(lines) + '\n'
        result += f'    }}\n'
        return result

    @staticmethod
    def get_discriminator_enum_name(oneof, msg_name):
        """Get the enum type name for a field_order discriminator."""
        return get_discriminator_enum_name(oneof, msg_name)


class FieldCSharpGen():
    @staticmethod
    def generate_field_declaration(field, renamed_enums=None):
        """Generate C# field declaration"""
        result = ''
        var_name = pascal_case(field.name)
        type_name = normalize_bytes_type(field.field_type)

        # Add leading comments
        leading_comment = field.comments
        if leading_comment:
            result += format_xml_summary(leading_comment, indent='        ')

        # Handle basic type resolution
        if type_name in csharp_types:
            base_type = csharp_types[type_name]
        else:
            # Use the type name directly - namespace/using directives handle scoping
            type_pkg = field.type_package if field.type_package else field.package
            base_type = renamed_enums.get(type_name, type_name) if renamed_enums else type_name

        # Handle arrays
        if field.is_array:
            if type_name == "string":
                # String arrays
                if field.size_option is not None:
                    # Fixed string array
                    result += f'        public byte[] {var_name} {{ get; set; }} = null!;  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars\n'
                elif field.max_size is not None:
                    # Variable string array
                    count_type = "ushort" if field.max_size > 255 else "byte"
                    result += f'        public {count_type} {var_name}Count {{ get; set; }}\n'
                    result += f'        public byte[] {var_name}Data {{ get; set; }} = null!;  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars\n'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array
                    if field.is_enum:
                        result += f'        public byte[] {var_name} {{ get; set; }} = null!;  // Fixed array of {base_type}: {field.size_option} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name} {{ get; set; }} = null!;  // Fixed array: {field.size_option} elements\n'
                elif field.max_size is not None:
                    # Variable array
                    count_type = "ushort" if field.max_size > 255 else "byte"
                    result += f'        public {count_type} {var_name}Count {{ get; set; }}\n'
                    if field.is_enum:
                        result += f'        public byte[] {var_name}Data {{ get; set; }} = null!;  // Variable array of {base_type}: up to {field.max_size} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name}Data {{ get; set; }} = null!;  // Variable array: up to {field.max_size} elements\n'

        # Handle regular strings
        elif type_name == "string":
            if field.size_option is not None:
                # Fixed string
                result += f'        public byte[] {var_name} {{ get; set; }} = null!;  // Fixed string: exactly {field.size_option} chars\n'
            elif field.max_size is not None:
                # Variable string
                length_type = "ushort" if field.max_size > 255 else "byte"
                result += f'        public {length_type} {var_name}Length {{ get; set; }}\n'
                result += f'        public byte[] {var_name}Data {{ get; set; }} = null!;  // Variable string: up to {field.max_size} chars\n'

        # Handle regular fields
        else:
            if type_name not in csharp_types and not field.is_enum:
                # Nested struct - reference type needs null-forgiving operator
                result += f'        public {base_type} {var_name} {{ get; set; }} = null!;\n'
            else:
                # Primitive type or enum - value type doesn't need initializer
                result += f'        public {base_type} {var_name} {{ get; set; }}\n'

        return result

    @staticmethod
    def generate_pack_code(field, base_offset, use_offset_param=False):
        """Generate C# code to pack a field into a byte array buffer.
        
        Handles serialization of:
        - Fixed and variable-length strings
        - Fixed and variable-length arrays of primitives, enums, and nested structs
        - Primitive types (using BinaryPrimitives for endian-correct encoding)
        - Nested message types (using their SerializeTo method)
        
        Args:
            field: The field object containing type, size, and array information
            base_offset: The byte offset where this field starts in the buffer
            use_offset_param: If True, generates code using 'offset + N' syntax
                              for the PackTo() method variant. If False, uses
                              literal offset values for Serialize() method.
        
        Returns:
            List of C# code lines for serializing this field
        """
        lines = []
        var_name = pascal_case(field.name)
        type_name = normalize_bytes_type(field.field_type)
        
        # Local helper to format offset expressions
        def fmt_offset(off):
            if use_offset_param:
                return f'offset + {off}' if off > 0 else 'offset'
            return str(off)

        # IMPORTANT: Check is_array FIRST to handle arrays of primitives correctly
        if field.is_array:
            if type_name == "string":
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
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.field_type, 1)
                array_size = field.size_option if field.size_option else field.max_size
                total_data_size = field.size - (1 if field.max_size else 0)  # subtract count byte if variable
                if field.size_option is not None:
                    # Fixed array
                    if field.is_enum:
                        lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {fmt_offset(base_offset)}, Math.Min({var_name}.Length, {field.size_option}));')
                    elif field.field_type in csharp_type_sizes:
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
                    if field.is_enum:
                        lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {fmt_offset(base_offset + count_size)}, Math.Min({var_name}Data.Length, {field.max_size}));')
                    elif field.field_type in csharp_type_sizes:
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
        elif type_name == "string":
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
        elif field.is_enum:
            # Single enum field - enums are byte values
            lines.append(f'            buffer[{fmt_offset(base_offset)}] = (byte){var_name};')
        else:
            # Nested struct - use SerializeTo for efficiency
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = type_name
            if use_offset_param:
                lines.append(f'            if ({var_name} != null) {var_name}.SerializeTo(buffer, {fmt_offset(base_offset)});')
            else:
                lines.append(f'            if ({var_name} != null) {{ var nestedBytes = {var_name}.Serialize(); Array.Copy(nestedBytes, 0, buffer, {base_offset}, nestedBytes.Length); }}')

        return lines

    @staticmethod
    def generate_unpack_code(field, offset, renamed_enums=None):
        """Generate code to unpack this field from a ReadOnlySpan<byte>."""
        lines = []
        var_name = pascal_case(field.name)
        type_name = normalize_bytes_type(field.field_type)

        # IMPORTANT: Check is_array FIRST to handle arrays of primitives correctly
        if field.is_array:
            if normalize_bytes_type(field.field_type) == "string":
                if field.size_option is not None:
                    # Fixed string array
                    total_size = field.size_option * field.element_size
                    lines.append(f'            msg.{var_name} = new byte[{total_size}];')
                    lines.append(f'            data.Slice({offset}, {total_size}).CopyTo(msg.{var_name}.AsSpan());')
                elif field.max_size is not None:
                    # Variable string array
                    total_size = field.max_size * field.element_size
                    lines.append(f'            msg.{var_name}Count = data[{offset}];')
                    lines.append(f'            msg.{var_name}Data = new byte[{total_size}];')
                    lines.append(f'            data.Slice({offset + 1}, {total_size}).CopyTo(msg.{var_name}Data.AsSpan());')
            else:
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.field_type, 1)
                if field.size_option is not None:
                    # Fixed array
                    if field.is_enum:
                        lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                        lines.append(f'            data.Slice({offset}, {field.size_option}).CopyTo(msg.{var_name}.AsSpan());')
                    elif field.field_type in csharp_type_sizes:
                        base_type = csharp_types.get(field.field_type, field.field_type)
                        total_data_size = field.size
                        lines.append(f'            msg.{var_name} = new {base_type}[{field.size_option}];')
                        lines.append(f'            MemoryMarshal.Cast<byte, {base_type}>(data.Slice({offset}, {total_data_size})).CopyTo(msg.{var_name}.AsSpan());')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = field.field_type
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
                        lines.append(f'            msg.{var_name}Count = BinaryPrimitives.ReadUInt16LittleEndian(data.Slice({offset}, 2));')
                    else:
                        lines.append(f'            msg.{var_name}Count = data[{offset}];')
                    if field.is_enum:
                        lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                        lines.append(f'            data.Slice({offset + count_size}, {field.max_size}).CopyTo(msg.{var_name}Data.AsSpan());')
                    elif field.field_type in csharp_type_sizes:
                        base_type = csharp_types.get(field.field_type, field.field_type)
                        total_data_size = field.size - count_size  # subtract count bytes
                        lines.append(f'            msg.{var_name}Data = new {base_type}[{field.max_size}];')
                        lines.append(f'            MemoryMarshal.Cast<byte, {base_type}>(data.Slice({offset + count_size}, {total_data_size})).CopyTo(msg.{var_name}Data.AsSpan());')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = field.field_type
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
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt16LittleEndian(data.Slice({offset}, 2));')
            elif type_name == "int16":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt16LittleEndian(data.Slice({offset}, 2));')
            elif type_name == "uint32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt32LittleEndian(data.Slice({offset}, 4));')
            elif type_name == "int32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt32LittleEndian(data.Slice({offset}, 4));')
            elif type_name == "uint64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt64LittleEndian(data.Slice({offset}, 8));')
            elif type_name == "int64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt64LittleEndian(data.Slice({offset}, 8));')
            elif type_name == "float":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadSingleLittleEndian(data.Slice({offset}, 4));')
            elif type_name == "double":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadDoubleLittleEndian(data.Slice({offset}, 8));')
            elif type_name == "bool":
                lines.append(f'            msg.{var_name} = data[{offset}] != 0;')
        elif normalize_bytes_type(field.field_type) == "string":
            if field.size_option is not None:
                # Fixed string
                lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                lines.append(f'            data.Slice({offset}, {field.size_option}).CopyTo(msg.{var_name}.AsSpan());')
            elif field.max_size is not None:
                # Variable string
                length_size = 2 if field.max_size > 255 else 1
                if field.max_size > 255:
                    lines.append(f'            msg.{var_name}Length = BinaryPrimitives.ReadUInt16LittleEndian(data.Slice({offset}, 2));')
                else:
                    lines.append(f'            msg.{var_name}Length = data[{offset}];')
                lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                lines.append(f'            data.Slice({offset + length_size}, {field.max_size}).CopyTo(msg.{var_name}Data.AsSpan());')
        elif field.is_enum:
            # Single enum field - enums are byte values, cast to enum type
            type_pkg = field.type_package if field.type_package else field.package
            enum_type = renamed_enums.get(type_name, type_name) if renamed_enums else type_name
            lines.append(f'            msg.{var_name} = ({enum_type})data[{offset}];')
        else:
            # Nested struct
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = type_name
            struct_size = field.size
            lines.append(f'            msg.{var_name} = {nested_type}.Deserialize(data[{offset}..({offset} + {struct_size})]);')

        return lines


class MessageCSharpGen():
    @staticmethod
    def generate(msg, package=None, equality=False):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            result += format_xml_summary(leading_comment, indent='    ')

        structName = msg.name

        # Add IEquatable<T> interface if equality is requested
        if equality:
            result += '    public class %s : IStructFrameMessage<%s>, IEquatable<%s>\n' % (structName, structName, structName)
        else:
            result += '    public class %s : IStructFrameMessage<%s>\n' % (structName, structName)
        result += '    {\n'

        result += '        public const int MaxSize = %d;\n' % msg.size

        # Build rename map: nested enum names that collide with a property name get an 'Enum' suffix
        field_property_names = {pascal_case(f.name) for f in msg.fields.values()}
        renamed_enums = {name: f'{name}Enum' for name in msg.enums if name in field_property_names}

        # Emit nested enum definitions inside the class body
        for enum_name, enum in msg.enums.items():
            result += EnumCSharpGen.generate_nested(enum, name_override=renamed_enums.get(enum_name))
            result += '\n'

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
            result += f'        public const int BaseSize = {msg.base_size}; // Non-extension portion size (== MaxSize when no extensions)\n'
        
        # Add variable message constants
        if msg.variable:
            result += f'        public const int MinSize = {msg.min_size}; // Minimum size when all variable fields are empty\n'
            result += f'        public const bool IsVariable = true; // This message uses variable-length encoding\n'
        
        result += '\n'

        # Generate field declarations
        for key, f in msg.fields.items():
            result += FieldCSharpGen.generate_field_declaration(f, renamed_enums=renamed_enums)

        # Generate oneofs - declarations for discriminator and union members
        for key, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'        public ushort {pascal_case(oneof.name)}Discriminator {{ get; set; }}\n'
                else:  # field_order
                    enum_base_name = structName
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, enum_base_name)
                    result += f'        public {enum_name} {pascal_case(oneof.name)}Discriminator {{ get; set; }}\n'
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
                if oneof.discriminator_type == "msgid":
                    result += f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset + {offset}), {pascal_case(oneof_name)}Discriminator);\n'
                    offset += 2
                else:  # field_order
                    result += f'            buffer[offset + {offset}] = (byte){pascal_case(oneof_name)}Discriminator;\n'
                    offset += 1
            
            result += f'            // Oneof {oneof_name} payload (union size: {oneof.size})\n'
            first = True
            for field_name, field in oneof.fields.items():
                type_name = field.field_type
                field_var = pascal_case(field_name)
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
        result += '        /// Deserialize a <see cref="ReadOnlySpan{byte}"/> into this message type.\n'
        result += '        /// This is the primary implementation - the <c>byte[]</c> and\n'
        result += '        /// <see cref="FrameMsgInfo"/> overloads delegate here.\n'
        if msg.variable:
            result += '        /// For variable messages: auto-detects MAX_SIZE vs variable encoding.\n'
        result += '        /// </summary>\n'
        result += f'        public static {structName} Deserialize(ReadOnlySpan<byte> data)\n'
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
            result += f'                return _DeserializeVariable(data.ToArray());\n'
            result += '            }\n'
            result += '        }\n'
            
            # Add _DeserializeMaxSize for variable messages
            result += '\n'
            result += '        /// <summary>\n'
            result += '        /// Deserialize from MAX_SIZE buffer (for minimal profiles)\n'
            result += '        /// </summary>\n'
            result += f'        private static {structName} _DeserializeMaxSize(ReadOnlySpan<byte> data)\n'
            result += '        {\n'
        
        result += f'            var msg = new {structName}();\n'

        offset = 0
        for key, f in msg.fields.items():
            unpack_lines = FieldCSharpGen.generate_unpack_code(f, offset, renamed_enums=renamed_enums)
            for line in unpack_lines:
                result += line + '\n'
            offset += f.size

        # Generate oneof unpacking code
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                if oneof.discriminator_type == "msgid":
                    result += f'            msg.{pascal_case(oneof_name)}Discriminator = BinaryPrimitives.ReadUInt16LittleEndian(data.Slice({offset}));\n'
                    result += f'            var {oneof_name}_discriminator = msg.{pascal_case(oneof_name)}Discriminator;\n'
                    offset += 2
                else:  # field_order
                    enum_base_name = structName
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, enum_base_name)
                    result += f'            msg.{pascal_case(oneof_name)}Discriminator = ({enum_name})data[{offset}];\n'
                    result += f'            var {oneof_name}_discriminator = msg.{pascal_case(oneof_name)}Discriminator;\n'
                    offset += 1
            
            result += f'            // Oneof {oneof_name} payload (union size: {oneof.size})\n'
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    first = True
                    for field_name, field in oneof.fields.items():
                        type_name = field.field_type
                        field_var = pascal_case(field_name)
                        if first:
                            result += f'            if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                            first = False
                        else:
                            result += f'            else if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                        result += '            {\n'
                        result += f'                msg.{field_var} = {type_name}.Deserialize(data[{offset}..({offset} + {type_name}.MaxSize)]);\n'
                        result += '            }\n'
                else:  # field_order
                    enum_base_name = structName
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, enum_base_name)
                    first = True
                    for idx, field_name in enumerate(oneof.field_order):
                        field = oneof.fields[field_name]
                        enum_entry = pascal_case(field_name)
                        field_var = pascal_case(field_name)
                        if field.is_default_type or field.is_enum:
                            # Primitive or enum - we need to handle this differently
                            pass  # Handled below in else case
                        else:
                            type_name = field.field_type
                            if first:
                                result += f'            if ({oneof_name}_discriminator == {enum_name}.{enum_entry})\n'
                                first = False
                            else:
                                result += f'            else if ({oneof_name}_discriminator == {enum_name}.{enum_entry})\n'
                            result += '            {\n'
                            result += f'                msg.{field_var} = {type_name}.Deserialize(data[{offset}..({offset} + {type_name}.MaxSize)]);\n'
                            result += '            }\n'
            offset += oneof.size

        result += '            return msg;\n'
        result += '        }\n'

        # byte[] overload - delegates to the span overload (keeps API compatibility)
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize a byte array. Delegates to <see cref="Deserialize(ReadOnlySpan{byte})"/>.\n'
        result += '        /// </summary>\n'
        result += f'        public static {structName} Deserialize(byte[] data) => Deserialize(data.AsSpan());\n'

        # Add FrameMsgInfo overload
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize message from FrameMsgInfo without allocating.\n'
        result += '        /// Uses <see cref="FrameMsgInfo.GetPayloadSpan"/> to avoid the\n'
        result += '        /// heap allocation that <see cref="FrameMsgInfo.ExtractPayload"/> incurs.\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="frameInfo">Frame information from frame parser</param>\n'
        result += '        /// <returns>Deserialized message</returns>\n'
        result += f'        public static {structName} Deserialize(FrameMsgInfo frameInfo)\n'
        result += '        {\n'
        result += '            if (frameInfo.MsgData == null)\n'
        result += '            {\n'
        result += '                return new ' + structName + '();\n'
        result += '            }\n'
        result += '            return Deserialize(frameInfo.GetPayloadSpan());\n'
        result += '        }\n'

        # Generate interface implementation methods
        result += '\n'
        if msg.id is not None:
            result += '        /// <summary>\n'
            result += '        /// Get the message ID (IStructFrameMessage)\n'
            result += '        /// </summary>\n'
            result += '        public ushort GetMsgId() => MsgId;\n'
        else:
            # Escape the struct name for use in a C# string literal
            escaped_name = structName.replace('\\', '\\\\').replace('"', '\\"')
            result += '        /// <summary>\n'
            result += '        /// Get the message ID (IStructFrameMessage)\n'
            result += '        /// Note: This message does not have a message ID defined.\n'
            result += '        /// </summary>\n'
            result += '        /// <exception cref="System.NotSupportedException">This message type does not have a message ID</exception>\n'
            result += f'        public ushort GetMsgId() => throw new System.NotSupportedException("{escaped_name} does not have a message ID defined");\n'
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
            result += f'        public int GetBaseSize() => BaseSize;\n'
        else:
            result += '        public (byte Magic1, byte Magic2) GetMagicNumbers() => (0, 0);\n'

        # Generate variable message methods if this is a variable message
        if msg.variable:
            result += MessageCSharpGen._generate_variable_methods(msg, structName, renamed_enums=renamed_enums)

        # Generate equality members if requested
        if equality:
            result += MessageCSharpGen._generate_equality_members(msg, structName)
        
        # Generate envelope methods if this is an envelope message
        if msg.is_envelope:
            result += MessageCSharpGen._generate_envelope_methods(msg, structName, package)

        result += '    }\n'

        # Generate NonExtension companion class for messages with extension fields
        if msg.id is not None and msg.base_size < msg.size:
            result += '\n'
            result += MessageCSharpGen._generate_non_extension_class(msg, structName, package)

        return result + '\n'
    
    @staticmethod
    def _generate_variable_methods(msg, structName, renamed_enums=None):
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
            var_name = pascal_case(f.name)
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if f.field_type == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    element_size = type_sizes.get(f.field_type, (f.size - 1) // f.max_size)
                result += f'            size += 1 + ({var_name}Count * {element_size}); // {f.name}\n'
            elif f.field_type == "string" and f.max_size is not None:
                result += f'            size += 1 + {var_name}Length; // {f.name}\n'
            else:
                result += f'            size += {f.size}; // {f.name}\n'
        
        # Oneofs: discriminator + union payload (or length-prefix + variant size for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            oneof_pascal = pascal_case(oneof_name)
            if oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                result += f'            size += {disc_bytes}; // {oneof_name} discriminator\n'
            if oneof.variable:
                result += f'            size += 2; // {oneof_name} variable-length prefix\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    field_var = pascal_case(field_name)
                    effective_size = max(field_size, oneof.min_size_override) if oneof.min_size_override else field_size
                    result += f'            if ((int){oneof_pascal}Discriminator == {disc_val}) size += {effective_size}; // {field_name}\n'
            elif oneof.discriminator_type is not None:
                result += f'            {{\n'
                result += f'                int _{oneof_name}_tlen = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'                if ((int){oneof_pascal}Discriminator == {disc_val}) _{oneof_name}_tlen = {field_size};\n'
                if oneof.min_size_override:
                    result += f'                if (_{oneof_name}_tlen < {oneof.min_size_override}) _{oneof_name}_tlen = {oneof.min_size_override};\n'
                result += f'                size += _{oneof_name}_tlen; // {oneof_name} trimmed union payload\n'
                result += f'            }}\n'
            else:
                result += f'            size += {oneof.size}; // {oneof_name} union payload\n'
        
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
            var_name = pascal_case(f.name)
            type_name = f.field_type
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if normalize_bytes_type(type_name) == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    element_size = type_sizes.get(type_name, (f.size - 1) // f.max_size)
                result += f'            // {f.name}: variable array\n'
                result += f'            buffer[offset++] = {var_name}Count;\n'
                if type_name in type_sizes:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                Buffer.BlockCopy({var_name}Data, 0, buffer, offset, {var_name}Count * {element_size});\n'
                    result += f'            offset += {var_name}Count * {element_size};\n'
                elif f.is_enum:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                Array.Copy({var_name}Data, 0, buffer, offset, {var_name}Count);\n'
                    result += f'            offset += {var_name}Count;\n'
                else:
                    result += f'            if ({var_name}Data != null)\n'
                    result += f'                for (int i = 0; i < {var_name}Count; i++)\n'
                    result += f'                    if ({var_name}Data[i] != null) {{ var bytes = {var_name}Data[i].Serialize(); Array.Copy(bytes, 0, buffer, offset + i * {element_size}, bytes.Length); }}\n'
                    result += f'            offset += {var_name}Count * {element_size};\n'
            elif normalize_bytes_type(type_name) == "string" and f.max_size is not None:
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
                elif normalize_bytes_type(type_name) == "string" and f.size_option is not None:
                    # Fixed string - copy from byte array
                    result += f'            if ({var_name} != null)\n'
                    result += f'                Array.Copy({var_name}, 0, buffer, offset, Math.Min({var_name}.Length, {f.size}));\n'
                    result += f'            offset += {f.size};\n'
                elif f.is_enum:
                    result += f'            buffer[offset++] = (byte){var_name};\n'
                else:
                    # Nested struct
                    result += f'            if ({var_name} != null) {{ var nestedBytes = {var_name}.Serialize(); Array.Copy(nestedBytes, 0, buffer, offset, nestedBytes.Length); }}\n'
                    result += f'            offset += {f.size};\n'
        
        # Oneofs: write discriminator then union payload (or length-prefix + variant bytes for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            oneof_pascal = pascal_case(oneof_name)
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                if oneof.discriminator_type == "msgid":
                    result += f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset, 2), {oneof_pascal}Discriminator);\n'
                    result += f'            offset += 2;\n'
                else:  # field_order
                    result += f'            buffer[offset++] = (byte){oneof_pascal}Discriminator;\n'
            if oneof.variable:
                result += f'            // Oneof {oneof_name} variable-length union payload\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    field_var = pascal_case(field_name)
                    effective_size = max(field_size, oneof.min_size_override) if oneof.min_size_override else field_size
                    result += f'            if ((int){oneof_pascal}Discriminator == {disc_val} && {field_var} != null)\n'
                    result += f'            {{\n'
                    result += f'                var {field_name}Bytes = {field_var}.Serialize();\n'
                    result += f'                BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset, 2), (ushort){effective_size});\n'
                    result += f'                offset += 2;\n'
                    result += f'                Array.Copy({field_name}Bytes, 0, buffer, offset, {field_name}Bytes.Length);\n'
                    result += f'                offset += {effective_size};\n'
                    result += f'            }}\n'
                result += f'            else if ({oneof_pascal}Discriminator == 0 || ({" && ".join(f"(int){oneof_pascal}Discriminator != {dv}" for dv, _, _ in oneof.variant_info)}))\n'
                result += f'            {{\n'
                result += f'                // Unknown or NONE discriminator: write 0-length payload\n'
                result += f'                BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan(offset, 2), 0); offset += 2;\n'
                result += f'            }}\n'
            elif oneof.discriminator_type is not None:
                _trim_label = f'trimmed union (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union'
                result += f'            // Oneof {oneof_name} {_trim_label}\n'
                result += f'            {{\n'
                result += f'                int _{oneof_name}_tlen = 0;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'                if ((int){oneof_pascal}Discriminator == {disc_val}) _{oneof_name}_tlen = {field_size};\n'
                if oneof.min_size_override:
                    result += f'                if (_{oneof_name}_tlen < {oneof.min_size_override}) _{oneof_name}_tlen = {oneof.min_size_override};\n'
                first = True
                for field_name, field in oneof.fields.items():
                    field_var = pascal_case(field_name)
                    if first:
                        result += f'                if ({field_var} != null)\n'
                        first = False
                    else:
                        result += f'                else if ({field_var} != null)\n'
                    result += '                {\n'
                    result += f'                    var {field_name}Bytes = {field_var}.Serialize();\n'
                    result += f'                    Array.Copy({field_name}Bytes, 0, buffer, offset, {field_name}Bytes.Length);\n'
                    result += '                }\n'
                result += f'                offset += _{oneof_name}_tlen;\n'
                result += f'            }}\n'
            else:
                result += f'            // Oneof {oneof_name} union payload\n'
                first = True
                for field_name, field in oneof.fields.items():
                    field_var = pascal_case(field_name)
                    if first:
                        result += f'            if ({field_var} != null)\n'
                        first = False
                    else:
                        result += f'            else if ({field_var} != null)\n'
                    result += '            {\n'
                    result += f'                var {field_name}Bytes = {field_var}.Serialize();\n'
                    result += f'                Array.Copy({field_name}Bytes, 0, buffer, offset, {field_name}Bytes.Length);\n'
                    result += '            }\n'
                result += f'            offset += {oneof.size};\n'
        
        result += '            return buffer;\n'
        result += '        }\n'
        
        # Generate _DeserializeVariable static method (internal method)
        # Keeps byte[] parameter - variable messages receive a freshly-allocated slice
        # from the span dispatch path (data.ToArray()), so no additional allocation occurs.
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Deserialize message from variable-length encoded buffer\n'
        result += '        /// </summary>\n'
        result += f'        private static {structName} _DeserializeVariable(byte[] data)\n'
        result += '        {\n'
        result += f'            var msg = new {structName}();\n'
        result += '            int offset = 0;\n'
        
        for key, f in msg.fields.items():
            var_name = pascal_case(f.name)
            type_name = f.field_type
            if f.is_array and f.max_size is not None:
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if normalize_bytes_type(type_name) == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    count_size = 2 if f.max_size > 255 else 1
                    element_size = type_sizes.get(type_name, (f.size - count_size) // f.max_size)
                result += f'            // {f.name}: variable array\n'
                if f.max_size > 255:
                    result += f'            msg.{var_name}Count = Math.Min(BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset, 2)), (ushort){f.max_size});\n'
                    result += f'            offset += 2;\n'
                else:
                    result += f'            msg.{var_name}Count = Math.Min(data[offset++], (byte){f.max_size});\n'
                if type_name in type_sizes:
                    base_type = csharp_types.get(type_name, type_name)
                    result += f'            msg.{var_name}Data = new {base_type}[{f.max_size}];\n'
                    result += f'            MemoryMarshal.Cast<byte, {base_type}>(data.AsSpan(offset, msg.{var_name}Count * {element_size})).CopyTo(msg.{var_name}Data.AsSpan());\n'
                    result += f'            offset += msg.{var_name}Count * {element_size};\n'
                elif f.is_enum:
                    result += f'            msg.{var_name}Data = new byte[{f.max_size}];\n'
                    result += f'            data.AsSpan(offset, msg.{var_name}Count).CopyTo(msg.{var_name}Data.AsSpan());\n'
                    result += f'            offset += msg.{var_name}Count;\n'
                else:
                    type_pkg = f.type_package if f.type_package else f.package
                    nested_type = type_name
                    result += f'            msg.{var_name}Data = new {nested_type}[{f.max_size}];\n'
                    result += f'            for (int i = 0; i < msg.{var_name}Count; i++)\n'
                    result += f'                msg.{var_name}Data[i] = {nested_type}.Deserialize(data[(offset + i * {element_size})..(offset + (i + 1) * {element_size})]);\n'
                    result += f'            offset += msg.{var_name}Count * {element_size};\n'
            elif normalize_bytes_type(type_name) == "string" and f.max_size is not None:
                result += f'            // {f.name}: variable string\n'
                if f.max_size > 255:
                    result += f'            msg.{var_name}Length = Math.Min(BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset, 2)), (ushort){f.max_size});\n'
                    result += f'            offset += 2;\n'
                else:
                    result += f'            msg.{var_name}Length = Math.Min(data[offset++], (byte){f.max_size});\n'
                result += f'            msg.{var_name}Data = new byte[{f.max_size}];\n'
                result += f'            data.AsSpan(offset, msg.{var_name}Length).CopyTo(msg.{var_name}Data.AsSpan());\n'
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
                elif normalize_bytes_type(type_name) == "string" and f.size_option is not None:
                    # Fixed string - copy into byte array
                    result += f'            msg.{var_name} = new byte[{f.size}];\n'
                    result += f'            data.AsSpan(offset, {f.size}).CopyTo(msg.{var_name}.AsSpan());\n'
                    result += f'            offset += {f.size};\n'
                elif f.is_enum:
                    type_pkg = f.type_package if f.type_package else f.package
                    enum_type = renamed_enums.get(type_name, type_name) if renamed_enums else type_name
                    result += f'            msg.{var_name} = ({enum_type})data[offset++];\n'
                else:
                    type_pkg = f.type_package if f.type_package else f.package
                    nested_type = type_name
                    result += f'            msg.{var_name} = {nested_type}.Deserialize(data[offset..(offset + {nested_type}.MaxSize)]); offset += {nested_type}.MaxSize;\n'
        
        # Oneofs: read discriminator then union payload (or length-prefix + variant bytes for variable oneof)
        for oneof_name, oneof in msg.oneofs.items():
            oneof_pascal = pascal_case(oneof_name)
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                if oneof.discriminator_type == "msgid":
                    result += f'            msg.{oneof_pascal}Discriminator = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset, 2));\n'
                    result += f'            var {oneof_name}_discriminator = msg.{oneof_pascal}Discriminator;\n'
                    result += f'            offset += 2;\n'
                else:  # field_order
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, structName)
                    result += f'            msg.{oneof_pascal}Discriminator = ({enum_name})data[offset++];\n'
                    result += f'            var {oneof_name}_discriminator = msg.{oneof_pascal}Discriminator;\n'
            if oneof.variable:
                result += f'            // Oneof {oneof_name} variable-length union payload\n'
                result += f'            if (offset + 2 > data.Length) return msg;\n'
                result += f'            int _{oneof_name}_len = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset, 2));\n'
                result += f'            offset += 2;\n'
                result += f'            if (offset + _{oneof_name}_len > data.Length) return msg;\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    type_name = oneof.fields[field_name].field_type
                    field_var = pascal_case(field_name)
                    result += f'            if ((int){oneof_name}_discriminator == {disc_val} && _{oneof_name}_len >= {field_size})\n'
                    result += f'                msg.{field_var} = {type_name}.Deserialize(data[offset..(offset + {field_size})]);\n'
                result += f'            offset += _{oneof_name}_len;  // Always skip full payload\n'
            elif oneof.discriminator_type is not None:
                _min_sz = oneof.min_size_override or 0
                _trim_label = f'trimmed union read (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union read'
                result += f'            // Oneof {oneof_name} {_trim_label}\n'
                result += f'            {{\n'
                result += f'                int _{oneof_name}_rlen = {_min_sz};\n'
                for disc_val, field_name, field_size in oneof.variant_info:
                    result += f'                if ((int)msg.{oneof_pascal}Discriminator == {disc_val}) _{oneof_name}_rlen = Math.Max({field_size}, {_min_sz});\n'
                if oneof.discriminator_type == "msgid":
                    first = True
                    for field_name, field_obj in oneof.fields.items():
                        type_name = field_obj.field_type
                        field_var = pascal_case(field_name)
                        if first:
                            result += f'                if (msg.{oneof_pascal}Discriminator == {type_name}.MsgId)\n'
                            first = False
                        else:
                            result += f'                else if (msg.{oneof_pascal}Discriminator == {type_name}.MsgId)\n'
                        result += '                {\n'
                        result += f'                    msg.{field_var} = {type_name}.Deserialize(data[offset..(offset + {type_name}.MaxSize)]);\n'
                        result += '                }\n'
                else:  # field_order
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, structName)
                    first = True
                    for idx, field_name in enumerate(oneof.field_order):
                        field_obj = oneof.fields[field_name]
                        type_name = field_obj.field_type
                        enum_entry = pascal_case(field_name)
                        field_var = pascal_case(field_name)
                        if first:
                            result += f'                if (msg.{oneof_pascal}Discriminator == {enum_name}.{enum_entry})\n'
                            first = False
                        else:
                            result += f'                else if (msg.{oneof_pascal}Discriminator == {enum_name}.{enum_entry})\n'
                        result += '                {\n'
                        result += f'                    msg.{field_var} = {type_name}.Deserialize(data[offset..(offset + {type_name}.MaxSize)]);\n'
                        result += '                }\n'
                result += f'                offset += _{oneof_name}_rlen;\n'
                result += f'            }}\n'
            else:
                result += f'            // Oneof {oneof_name} union payload ({oneof.size} bytes)\n'
                if oneof.auto_discriminator:
                    if oneof.discriminator_type == "msgid":
                        first = True
                        for field_name, field in oneof.fields.items():
                            type_name = field.field_type
                            field_var = pascal_case(field_name)
                            if first:
                                result += f'            if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                                first = False
                            else:
                                result += f'            else if ({oneof_name}_discriminator == {type_name}.MsgId)\n'
                            result += '            {\n'
                            result += f'                msg.{field_var} = {type_name}.Deserialize(data[offset..(offset + {type_name}.MaxSize)]);\n'
                            result += '            }\n'
                    else:  # field_order
                        enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, structName)
                        first = True
                        for idx, field_name in enumerate(oneof.field_order):
                            field = oneof.fields[field_name]
                            type_name = field.field_type
                            enum_entry = pascal_case(field_name)
                            field_var = pascal_case(field_name)
                            if first:
                                result += f'            if ({oneof_name}_discriminator == {enum_name}.{enum_entry})\n'
                                first = False
                            else:
                                result += f'            else if ({oneof_name}_discriminator == {enum_name}.{enum_entry})\n'
                            result += '            {\n'
                            result += f'                msg.{field_var} = {type_name}.Deserialize(data[offset..(offset + {type_name}.MaxSize)]);\n'
                            result += '            }\n'
                result += f'            offset += {oneof.size};\n'
        
        result += '            return msg;\n'
        result += '        }\n'
        
        return result
    
    @staticmethod
    def _generate_non_extension_class(msg, structName, package):
        """Generate a NonExtension companion class for messages with extension fields.

        The companion class serializes only the base (non-extension) portion of
        the message wire format.  It is marked [Obsolete] because it exists only
        to communicate with older firmware that does not understand extensions;
        once all devices are upgraded this class should be removed.
        """
        non_ext_name = f'{structName}NonExtension'
        base_size = msg.base_size

        r = ''
        r += '    /// <summary>\n'
        r += f'    /// Deprecated companion of <see cref="{structName}"/> that omits extension fields.\n'
        r += '    /// Use this only when communicating with older firmware that does not understand\n'
        r += '    /// the extension fields.  Once all devices have been upgraded, switch back to\n'
        r += f'    /// <see cref="{structName}"/> and remove usages of this class.\n'
        r += '    /// </summary>\n'
        r += '    [Obsolete("Use ' + structName + ' for extension-aware devices. ' + non_ext_name + ' is a transitional helper for legacy firmware only.")]\n'
        r += f'    public class {non_ext_name} : IStructFrameMessage\n'
        r += '    {\n'
        r += f'        public const int MaxSize = {structName}.BaseSize;\n'
        r += f'        public const ushort MsgId = {structName}.MsgId;\n'
        r += f'        public const byte Magic1 = {structName}.Magic1;\n'
        r += f'        public const byte Magic2 = {structName}.Magic2;\n'
        r += '\n'
        r += f'        private readonly {structName} _inner;\n'
        r += '\n'
        r += f'        /// <param name="inner">The full {structName} whose base fields will be sent.</param>\n'
        r += f'        public {non_ext_name}({structName} inner)\n'
        r += '        {\n'
        r += '            _inner = inner ?? throw new ArgumentNullException(nameof(inner));\n'
        r += '        }\n'
        r += '\n'
        r += '        /// <summary>Serialize only the base (non-extension) fields.</summary>\n'
        r += '        public byte[] Serialize()\n'
        r += '        {\n'
        r += f'            byte[] full = new byte[{structName}.MaxSize];\n'
        r += '            _inner.SerializeTo(full, 0);\n'
        r += f'            byte[] baseOnly = new byte[{base_size}];\n'
        r += f'            Array.Copy(full, baseOnly, {base_size});\n'
        r += '            return baseOnly;\n'
        r += '        }\n'
        r += '\n'
        r += '        public ushort GetMsgId() => MsgId;\n'
        r += '        public int GetSize() => MaxSize;\n'
        r += '        public (byte Magic1, byte Magic2) GetMagicNumbers() => (Magic1, Magic2);\n'
        r += '    }\n'
        return r

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
            field_name = pascal_case(f.name)
            
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
            elif f.field_type == "string":
                if f.size_option is not None:
                    # Fixed string - use SequenceEqual
                    comparisons.append(f'{field_name}.SequenceEqual(other.{field_name})')
                elif f.max_size is not None:
                    # Variable string - compare length and data
                    comparisons.append(f'{field_name}Length == other.{field_name}Length')
                    comparisons.append(f'{field_name}Data.SequenceEqual(other.{field_name}Data)')
            
            # Handle enums (value types)
            elif f.is_enum:
                comparisons.append(f'{field_name} == other.{field_name}')
            
            # Handle nested messages
            elif f.field_type not in csharp_types:
                comparisons.append(f'({field_name}?.Equals(other.{field_name}) ?? other.{field_name} is null)')
            
            # Handle primitives
            else:
                comparisons.append(f'{field_name} == other.{field_name}')
        
        # Add oneof fields
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                comparisons.append(f'{pascal_case(oneof_name)}Discriminator == other.{pascal_case(oneof_name)}Discriminator')
            for field_name, field in oneof.fields.items():
                field_var = pascal_case(field_name)
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
            field_name = pascal_case(f.name)
            if f.is_array:
                if f.size_option is not None:
                    # Fixed array
                    result += f'            foreach (var b in {field_name}) hash.Add(b);\n'
                elif f.max_size is not None:
                    # Variable array
                    result += f'            hash.Add({field_name}Count);\n'
                    result += f'            foreach (var b in {field_name}Data) hash.Add(b);\n'
            elif f.field_type == "string":
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
                result += f'            hash.Add({pascal_case(oneof_name)}Discriminator);\n'
            for field_name, field in oneof.fields.items():
                result += f'            hash.Add({pascal_case(field_name)});\n'
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
    
    @staticmethod
    def _generate_envelope_methods(msg, structName, package):
        """Generate envelope-specific helper methods for wrapping inner messages."""
        result = '\n'
        
        # Get the single oneof (validation ensures exactly one exists)
        oneof_name = list(msg.oneofs.keys())[0]
        oneof = msg.oneofs[oneof_name]
        
        # Get enum name for field_order discriminators
        enum_name = None
        if oneof.auto_discriminator and oneof.discriminator_type == "field_order":
            enum_base_name = structName
            enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, enum_base_name)
        
        result += '        // ========================================\n'
        result += '        // Envelope message helper methods\n'
        result += '        // ========================================\n'
        
        # Generate Wrap static method for each payload type
        for idx, (field_name, field) in enumerate(oneof.fields.items()):
            # Get the payload type name
            type_pkg = field.type_package if field.type_package else field.package
            payload_type = field.field_type
            
            # Generate parameter list for envelope fields (non-oneof fields)
            field_params = []
            for f_name, f in msg.fields.items():
                csharp_type = csharp_types.get(f.field_type)
                if csharp_type is None:
                    type_pkg = f.type_package if f.type_package else f.package
                    csharp_type = f.field_type
                if f.is_array or f.field_type == "string":
                    # Arrays and strings are complex types
                    continue  # Skip for simplicity, user can set these after wrap
                field_params.append(f'{csharp_type} {f.name}')
            
            # Build parameter list: payload first, then envelope fields
            all_params_list = [f'{payload_type} payload'] + field_params
            
            result += '\n'
            result += '        /// <summary>\n'
            result += f'        /// Create a {structName} envelope wrapping a {payload_type} payload.\n'
            result += '        /// </summary>\n'
            result += f'        /// <param name="payload">The {payload_type} message to wrap</param>\n'
            for f_name, f in msg.fields.items():
                if f.is_array or f.field_type == "string":
                    continue
                result += f'        /// <param name="{f.name}">Envelope field value</param>\n'
            result += f'        /// <returns>A fully initialized {structName} envelope</returns>\n'
            result += f'        public static {structName} Wrap({", ".join(all_params_list)})\n'
            result += '        {\n'
            result += f'            var envelope = new {structName}();\n'
            
            # Initialize envelope fields
            for f_name, f in msg.fields.items():
                if f.is_array or f.field_type == "string":
                    continue
                result += f'            envelope.{pascal_case(f.name)} = {f.name};\n'
            
            # Set the discriminator to the payload's message ID or field order
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'            envelope.{pascal_case(oneof_name)}Discriminator = {payload_type}.MsgId;\n'
                else:  # field_order
                    enum_entry = pascal_case(field_name)
                    result += f'            envelope.{pascal_case(oneof_name)}Discriminator = {enum_name}.{enum_entry};\n'
            
            # Serialize payload and copy to the oneof field
            result += f'            envelope.{pascal_case(field_name)} = payload;\n'
            result += '            return envelope;\n'
            result += '        }\n'
        
        # Generate helper to get the active payload type
        if oneof.auto_discriminator:
            result += '\n'
            result += '        /// <summary>\n'
            result += f'        /// Get the discriminator value of the wrapped payload.\n'
            result += '        /// </summary>\n'
            if oneof.discriminator_type == "msgid":
                result += f'        /// <returns>The message ID of the payload in the {oneof_name} union</returns>\n'
                result += '        public ushort GetPayloadMessageId()\n'
            else:  # field_order
                result += f'        /// <returns>The field discriminator of the payload in the {oneof_name} union</returns>\n'
                result += f'        public {enum_name} GetPayloadFieldDiscriminator()\n'
            result += '        {\n'
            result += f'            return {pascal_case(oneof_name)}Discriminator;\n'
            result += '        }\n'
        
        return result


class FileCSharpGen():
    @staticmethod
    def _file_header(package, equality=False, needs_collections=False, include_timestamp=False):
        """Generate the standard file header (auto-gen comment, usings, namespace open)."""
        result = '// Automatically generated struct frame code for C#\n'
        result += '// Generated by struct-frame %s.\n\n' % version
        result += '#nullable enable\n\n'
        result += 'using System;\n'
        if needs_collections:
            result += 'using System.Collections.Generic;\n'
        if equality:
            result += 'using System.Linq;\n'
        result += 'using System.Buffers.Binary;\n'
        result += 'using System.Runtime.InteropServices;\n'
        result += 'using StructFrame;\n'

        # Collect referenced packages for using directives
        referenced_packages = set()
        for key, msg in package.messages.items():
            for field_name, field in msg.fields.items():
                if field.type_package and field.type_package != package.name:
                    referenced_packages.add(field.type_package)

        if referenced_packages:
            for ref_pkg in sorted(referenced_packages):
                result += f'using StructFrame.{pascal_case(ref_pkg)};\n'

        result += '\n'
        namespace_name = pascal_case(package.name)
        result += 'namespace StructFrame.%s\n' % namespace_name
        result += '{\n'
        return result

    @staticmethod
    def _file_footer():
        return '}\n'

    @staticmethod
    def generate_per_file(package, equality=False):
        """Generate one file per enum/message/utility class.
        
        Returns a dict of {relative_filename: content_string} where
        filenames are relative to the package folder (e.g. 'BasicTypesMessage.cs').
        """
        files = {}

        def header(needs_collections=False):
            return FileCSharpGen._file_header(package, equality=equality, needs_collections=needs_collections)

        footer = FileCSharpGen._file_footer()

        # PackageInfo (if package_id is set)
        if package.package_id is not None:
            content = header()
            content += f'    // Package ID for extended message IDs\n'
            content += f'    public static class PackageInfo\n'
            content += f'    {{\n'
            content += f'        public const byte PackageId = {package.package_id};\n'
            content += f'    }}\n'
            content += footer
            files['PackageInfo.cs'] = content

        # One file per enum (in Enums/ subfolder)
        if package.enums:
            for key, enum in package.enums.items():
                content = header()
                content += EnumCSharpGen.generate(enum)
                content += footer
                files[os.path.join('Enums', f'{enum.name}.cs')] = content

        # One file per discriminator enum
        for key, msg in package.messages.items():
            struct_name = msg.name
            enum_base_name = struct_name
            for oneof_name, oneof in msg.oneofs.items():
                if oneof.auto_discriminator and oneof.discriminator_type == 'field_order':
                    enum_name = EnumCSharpGen.get_discriminator_enum_name(oneof, enum_base_name)
                    content = header()
                    content += EnumCSharpGen.generate_discriminator_enum(oneof, enum_base_name)
                    content += footer
                    files[os.path.join('Enums', f'{enum_name}.cs')] = content

        # One file per message (in Messages/ subfolder)
        if package.messages:
            for key, msg in package.sortedMessages().items():
                content = header()
                content += MessageCSharpGen.generate(msg, package, equality)
                content += footer
                # Strip the package prefix from the class name for the filename
                files[os.path.join('Messages', f'{msg.name}.cs')] = content

        # MessageDefinitions in its own file (includes timestamp since it's the single aggregation file)
        if package.messages:
            content = FileCSharpGen._file_header(package, equality=equality, needs_collections=True, include_timestamp=True)
            content += FileCSharpGen._generate_message_definitions(package)
            content += footer
            files['MessageDefinitions.cs'] = content

        return files

    @staticmethod
    def _generate_message_definitions(package):
        """Generate the MessageDefinitions static class content."""
        result = ''
        namespace_name_local = pascal_case(package.name)
        result += '    /// <summary>\n'
        result += '    /// Message registry and utilities for automatic message lookup and deserialization.\n'
        result += '    /// </summary>\n'
        result += '    public static class MessageDefinitions\n'
        result += '    {\n'

        # Generate MessageEntry record for the registry
        result += '        /// <summary>\n'
        result += '        /// Information about a registered message type.\n'
        result += '        /// </summary>\n'
        result += '        public record MessageEntry(\n'
        result += '            ushort Id,\n'
        result += '            string Name,\n'
        result += '            Type PayloadType,\n'
        result += '            Func<byte[], IStructFrameMessage?> Deserializer,\n'
        result += '            int MaxSize,\n'
        result += '            byte Magic1,\n'
        result += '            byte Magic2\n'
        result += '        );\n\n'

        # Generate the static registry
        result += '        /// <summary>\n'
        result += '        /// Static registry of all message types.\n'
        result += '        /// </summary>\n'
        result += '        private static readonly Dictionary<ushort, MessageEntry> _registryById = new()\n'
        result += '        {\n'

        for key, msg in package.sortedMessages().items():
            if msg.id:
                structName = msg.name
                magic1 = '0'
                magic2 = '0'
                if msg.magic_bytes:
                    magic1 = f'{structName}.Magic1'
                    magic2 = f'{structName}.Magic2'
                if package.package_id is not None:
                    combined_msg_id = (package.package_id << 8) | msg.id
                    result += f'            {{ {combined_msg_id}, new MessageEntry({combined_msg_id}, "{msg.name}", typeof({structName}), data => {structName}.Deserialize(data), {structName}.MaxSize, {magic1}, {magic2}) }},\n'
                else:
                    result += f'            {{ {structName}.MsgId, new MessageEntry({structName}.MsgId, "{msg.name}", typeof({structName}), data => {structName}.Deserialize(data), {structName}.MaxSize, {magic1}, {magic2}) }},\n'

        result += '        };\n\n'

        # Generate name lookup dictionary
        result += '        /// <summary>\n'
        result += '        /// Static registry for name-based lookup.\n'
        result += '        /// </summary>\n'
        result += '        private static readonly Dictionary<string, MessageEntry> _registryByName = new(StringComparer.OrdinalIgnoreCase)\n'
        result += '        {\n'

        for key, msg in package.sortedMessages().items():
            if msg.id:
                structName = msg.name
                if package.package_id is not None:
                    combined_msg_id = (package.package_id << 8) | msg.id
                    result += f'            {{ "{msg.name}", _registryById[{combined_msg_id}] }},\n'
                else:
                    result += f'            {{ "{msg.name}", _registryById[{structName}.MsgId] }},\n'

        result += '        };\n\n'

        # Generate type lookup dictionary
        result += '        /// <summary>\n'
        result += '        /// Static registry for type-based lookup (O(1) generic deserialization).\n'
        result += '        /// </summary>\n'
        result += '        private static readonly Dictionary<Type, MessageEntry> _registryByType = new()\n'
        result += '        {\n'

        for key, msg in package.sortedMessages().items():
            if msg.id:
                structName = msg.name
                if package.package_id is not None:
                    combined_msg_id = (package.package_id << 8) | msg.id
                    result += f'            {{ typeof({structName}), _registryById[{combined_msg_id}] }},\n'
                else:
                    result += f'            {{ typeof({structName}), _registryById[{structName}.MsgId] }},\n'

        result += '        };\n\n'

        # GetMessageInfo by ID
        result += '        /// <summary>\n'
        result += '        /// Get message info (size and magic numbers) for a given message ID.\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="msgId">The message ID</param>\n'
        result += '        /// <returns>MessageInfo if found, null otherwise</returns>\n'

        if package.package_id is not None:
            result += '        public static MessageInfo? GetMessageInfo(int msgId)\n'
            result += '        {\n'
            result += '            byte pkgId = (byte)((msgId >> 8) & 0xFF);\n'
            result += '            byte localMsgId = (byte)(msgId & 0xFF);\n'
            result += '            \n'
            result += f'            if (pkgId != PackageInfo.PackageId)\n'
            result += '            {\n'
            result += '                return null;\n'
            result += '            }\n'
            result += '            \n'
            result += '            switch (localMsgId)\n'
            result += '            {\n'
        else:
            result += '        public static MessageInfo? GetMessageInfo(int msgId)\n'
            result += '        {\n'
            result += '            switch (msgId)\n'
            result += '            {\n'

        for key, msg in package.sortedMessages().items():
            if msg.id:
                structName = msg.name
                magic1 = '0'
                magic2 = '0'
                if msg.magic_bytes:
                    magic1 = f'{structName}.Magic1'
                    magic2 = f'{structName}.Magic2'
                if package.package_id is not None:
                    result += '                case %d: return new MessageInfo(%s.MaxSize, %s, %s, %s.BaseSize);\n' % (msg.id, structName, magic1, magic2, structName)
                else:
                    result += '                case %s.MsgId: return new MessageInfo(%s.MaxSize, %s, %s, %s.BaseSize);\n' % (structName, structName, magic1, magic2, structName)
        result += '                default: return null;\n'
        result += '            }\n'
        result += '        }\n\n'

        # GetMessageEntry by ID
        result += '        /// <summary>\n'
        result += '        /// Get full message entry (including deserializer) for a given message ID.\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="msgId">The message ID</param>\n'
        result += '        /// <returns>MessageEntry if found, null otherwise</returns>\n'
        result += '        public static MessageEntry? GetMessageEntry(ushort msgId)\n'
        result += '        {\n'
        result += '            return _registryById.TryGetValue(msgId, out var entry) ? entry : null;\n'
        result += '        }\n\n'

        # GetMessageEntry by name
        result += '        /// <summary>\n'
        result += '        /// Get message entry by name (case-insensitive).\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="name">The message name</param>\n'
        result += '        /// <returns>MessageEntry if found, null otherwise</returns>\n'
        result += '        public static MessageEntry? GetMessageEntry(string name)\n'
        result += '        {\n'
        result += '            return _registryByName.TryGetValue(name, out var entry) ? entry : null;\n'
        result += '        }\n\n'

        # GetAllMessages
        result += '        /// <summary>\n'
        result += '        /// Get all registered message entries.\n'
        result += '        /// </summary>\n'
        result += '        /// <returns>Collection of all message entries</returns>\n'
        result += '        public static IEnumerable<MessageEntry> GetAllMessages()\n'
        result += '        {\n'
        result += '            return _registryById.Values;\n'
        result += '        }\n\n'

        # Deserialize method
        result += '        /// <summary>\n'
        result += '        /// Deserialize a message payload by message ID.\n'
        result += '        /// Automatically dispatches to the correct deserializer based on msgId.\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="msgId">The message ID</param>\n'
        result += '        /// <param name="payload">The serialized payload bytes</param>\n'
        result += '        /// <returns>Deserialized message object, or null if unknown message ID</returns>\n'
        result += '        public static IStructFrameMessage? Deserialize(ushort msgId, byte[] payload)\n'
        result += '        {\n'
        result += '            if (_registryById.TryGetValue(msgId, out var entry))\n'
        result += '            {\n'
        result += '                return entry.Deserializer(payload);\n'
        result += '            }\n'
        result += '            return null;\n'
        result += '        }\n\n'

        # Deserialize from FrameMsgInfo
        result += '        /// <summary>\n'
        result += '        /// Deserialize a message from FrameMsgInfo.\n'
        result += '        /// Automatically dispatches to the correct deserializer based on msgId.\n'
        result += '        /// </summary>\n'
        result += '        /// <param name="frameInfo">Frame info from parser</param>\n'
        result += '        /// <returns>Deserialized message object, or null if unknown message ID</returns>\n'
        result += '        public static IStructFrameMessage? Deserialize(FrameMsgInfo frameInfo)\n'
        result += '        {\n'
        result += '            if (!frameInfo.Valid || frameInfo.MsgData == null)\n'
        result += '            {\n'
        result += '                return null;\n'
        result += '            }\n'
        result += '            \n'
        result += '            return Deserialize(frameInfo.MsgId, frameInfo.ExtractPayload());\n'
        result += '        }\n\n'

        # Generic Deserialize<T>
        result += '        /// <summary>\n'
        result += '        /// Deserialize a message payload to a specific type.\n'
        result += '        /// </summary>\n'
        result += '        /// <typeparam name="T">The expected message type</typeparam>\n'
        result += '        /// <param name="payload">The serialized payload bytes</param>\n'
        result += '        /// <returns>Deserialized message, or null if type mismatch or invalid</returns>\n'
        result += '        public static T? Deserialize<T>(byte[] payload) where T : class, IStructFrameMessage\n'
        result += '        {\n'
        result += '            if (_registryByType.TryGetValue(typeof(T), out var entry))\n'
        result += '            {\n'
        result += '                return entry.Deserializer(payload) as T;\n'
        result += '            }\n'
        result += '            return null;\n'
        result += '        }\n'

        result += '    }\n'
        return result

    @staticmethod
    def generate(package, equality=False):
        yield '// Automatically generated struct frame code for C#\n'
        yield '// Generated by struct-frame %s.\n\n' % version

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
                yield f'using StructFrame.{pascal_case(ref_pkg)};\n'
        
        yield '\n'

        namespace_name = pascal_case(package.name)
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

        # Generate discriminator enums for field_order oneofs
        discriminator_enums_generated = False
        for key, msg in package.messages.items():
            struct_name = msg.name
            enum_base_name = struct_name
            for oneof_name, oneof in msg.oneofs.items():
                if oneof.auto_discriminator and oneof.discriminator_type == 'field_order':
                    if not discriminator_enums_generated:
                        yield '    // Discriminator enums\n'
                        discriminator_enums_generated = True
                    enum_code = EnumCSharpGen.generate_discriminator_enum(oneof, enum_base_name)
                    yield enum_code + '\n'

        if package.messages:
            yield '    // Message definitions\n'
            for key, msg in package.sortedMessages().items():
                yield MessageCSharpGen.generate(msg, package, equality)
            yield '\n'

        # Generate helper class with message definitions
        if package.messages:
            yield FileCSharpGen._generate_message_definitions(package)

        yield '}\n'


class TestCSharpGen():
    """Generator for C# round-trip test code with deterministic dummy values.

    Emits a single ``test_roundtrip_<pkg>.cs`` file inside the package folder
    containing a ``Program`` class with ``Main()`` that exercises every message
    across all 5 frame profiles.
    """

    @staticmethod
    def _dummy_value(field, index=0):
        """Return a C# literal for *field*'s scalar type, or None for nested
        struct (caller must instantiate via ``new``)."""
        type_name = field.field_type
        type_values = {
            "uint8":  f"(byte){(42 + index) % 256}",
            "int8":   f"(sbyte){(42 + index) % 128}",
            "uint16": f"(ushort){1000 + index}",
            "int16":  f"(short){500 + index}",
            "uint32": f"{123456 + index}u",
            "int32":  f"{123456 + index}",
            "uint64": f"{9876543210 + index}UL",
            "int64":  f"{9876543210 + index}L",
            "float":  f"{3.14159 + index}f",
            "double": f"{2.718281828 + index}",
            "bool":   "true" if index % 2 == 0 else "false",
        }
        if type_name in type_values:
            return type_values[type_name]
        if field.is_enum:
            # Enum properties default to 0 (the first value). Avoid emitting an
            # explicit cast because nested enums may be renamed to *Enum when
            # they collide with property names, and they live inside the
            # parent class (e.g. ``MyMsg.MyEnumEnum``). Returning ``None``
            # tells the caller to skip the assignment.
            return None
        return None  # nested struct

    @staticmethod
    def _bytes_literal(s, fixed_size=None):
        """Return a C# expression yielding a byte[] containing *s* (UTF-8),
        optionally padded/truncated to *fixed_size* bytes."""
        data = s.encode('utf-8')
        if fixed_size is not None:
            data = data[:fixed_size].ljust(fixed_size, b'\x00')
        return 'new byte[] { ' + ', '.join(str(b) for b in data) + ' }'

    @staticmethod
    def _generate_field_init(field, prefix="msg", index=0):
        """Generate C# field init lines for a deterministic test value."""
        var_name = pascal_case(field.name)
        type_name = field.field_type
        out = ""

        if field.is_array:
            if normalize_bytes_type(type_name) == "string":
                if field.size_option is not None:
                    # Fixed string array: byte[] flattened, size_option strings * element_size bytes
                    total = field.size_option * field.element_size
                    elem_bytes = b''.join(
                        f"test_{i}".encode('utf-8')[:field.element_size].ljust(field.element_size, b'\x00')
                        for i in range(field.size_option)
                    )
                    out += f'        {prefix}.{var_name} = new byte[] {{ ' + ', '.join(str(b) for b in elem_bytes) + ' };\n'
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    elem_bytes = b''.join(
                        f"test_{i}".encode('utf-8')[:field.element_size].ljust(field.element_size, b'\x00')
                        for i in range(count)
                    )
                    out += f'        {prefix}.{var_name}Count = {count};\n'
                    out += f'        {prefix}.{var_name}Data = new byte[] {{ ' + ', '.join(str(b) for b in elem_bytes) + ' };\n'
            else:
                # Determine element type name in C#
                if type_name in csharp_types:
                    elem_type = csharp_types[type_name]
                else:
                    elem_type = type_name
                if field.size_option is not None:
                    count = field.size_option
                    if field.is_enum:
                        out += f'        {prefix}.{var_name} = new byte[{count}];\n'
                    elif type_name not in csharp_types:
                        out += f'        {prefix}.{var_name} = new {elem_type}[{count}];\n'
                        out += f'        for (int _i = 0; _i < {count}; _i++) {prefix}.{var_name}[_i] = new {elem_type}();\n'
                    else:
                        n = min(count, 3)
                        out += f'        {prefix}.{var_name} = new {elem_type}[{count}];\n'
                        for i in range(n):
                            out += f'        {prefix}.{var_name}[{i}] = {TestCSharpGen._dummy_value(field, i)};\n'
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    out += f'        {prefix}.{var_name}Count = {count};\n'
                    if field.is_enum:
                        bytes_ = ', '.join(str(i) for i in range(count))
                        out += f'        {prefix}.{var_name}Data = new byte[] {{ {bytes_} }};\n'
                    elif type_name not in csharp_types:
                        out += f'        {prefix}.{var_name}Data = new {elem_type}[{count}];\n'
                        out += f'        for (int _i = 0; _i < {count}; _i++) {prefix}.{var_name}Data[_i] = new {elem_type}();\n'
                    else:
                        out += f'        {prefix}.{var_name}Data = new {elem_type}[] {{ '
                        out += ', '.join(TestCSharpGen._dummy_value(field, i) for i in range(count))
                        out += ' };\n'
        elif normalize_bytes_type(type_name) == "string":
            if field.size_option is not None:
                out += f'        {prefix}.{var_name} = {TestCSharpGen._bytes_literal("test_string", field.size_option)};\n'
            elif field.max_size is not None:
                test_str = "test_string"
                out += f'        {prefix}.{var_name}Length = {len(test_str)};\n'
                out += f'        {prefix}.{var_name}Data = {TestCSharpGen._bytes_literal(test_str)};\n'
        else:
            dummy = TestCSharpGen._dummy_value(field, index)
            if dummy is not None:
                out += f'        {prefix}.{var_name} = {dummy};\n'
            elif field.is_enum:
                pass  # enum left at default 0 value
            else:
                # Nested message - default-construct
                out += f'        {prefix}.{var_name} = new {type_name}();\n'
        return out

    @staticmethod
    def generate(package, namespace='StructFrame.Generated'):
        """Generate the ``test_roundtrip_<pkg>.cs`` file content."""
        pkg_pascal = pascal_case(package.name)
        # Skip oneof messages and messages without IDs
        testable_messages = [(key, msg) for key, msg in package.sortedMessages().items()
                             if msg.id is not None and not getattr(msg, 'oneofs', {})]

        # Collect referenced packages for using directives (for nested-message field types)
        referenced_packages = set()
        for key, msg in testable_messages:
            for fkey, field in msg.fields.items():
                if field.type_package and field.type_package != package.name:
                    referenced_packages.add(field.type_package)

        yield '// Automatically generated round-trip test runner for struct-frame messages.\n'
        yield f'// Generated by struct-frame {version}.\n\n'
        yield '#nullable enable\n\n'
        yield 'using System;\n'
        yield 'using System.Collections.Generic;\n'
        yield 'using System.Linq;\n'
        yield 'using StructFrame;\n'
        yield 'using StructFrame.Framing;\n'
        yield 'using StructFrame.Profiles;\n'
        yield f'using StructFrame.{pkg_pascal};\n'
        for ref_pkg in sorted(referenced_packages):
            yield f'using StructFrame.{pascal_case(ref_pkg)};\n'
        yield '\n'
        yield f'namespace StructFrame.{pkg_pascal}\n'
        yield '{\n'
        yield f'    public static class TestRoundtrip{pkg_pascal}\n'
        yield '    {\n'

        # Profile descriptor
        yield '        private class ProfileEntry\n'
        yield '        {\n'
        yield '            public string Name = "";\n'
        yield '            public Func<BufferWriter> CreateWriter = () => null!;\n'
        yield '            public Func<Func<int, MessageInfo?>, AccumulatingReader> CreateReader = (_) => null!;\n'
        yield '            public bool HasPkgId;\n'
        yield '            public bool HasLength;\n'
        yield '            public int MaxPayload; // -1 == unlimited\n'
        yield '        }\n\n'

        yield '        private static readonly ProfileEntry[] Profiles = new[]\n'
        yield '        {\n'
        yield '            new ProfileEntry { Name = "ProfileStandard", CreateWriter = () => new ProfileStandardWriter(),\n'
        yield '                CreateReader = (g) => new ProfileStandardAccumulatingReader(2048, g), HasPkgId = false, HasLength = true,  MaxPayload = 255 },\n'
        yield '            new ProfileEntry { Name = "ProfileSensor",   CreateWriter = () => new ProfileSensorWriter(),\n'
        yield '                CreateReader = (g) => new ProfileSensorAccumulatingReader(2048, g), HasPkgId = false, HasLength = false, MaxPayload = -1 },\n'
        yield '            new ProfileEntry { Name = "ProfileIPC",      CreateWriter = () => new ProfileIPCWriter(),\n'
        yield '                CreateReader = (g) => new ProfileIPCAccumulatingReader(2048, g),    HasPkgId = false, HasLength = false, MaxPayload = -1 },\n'
        yield '            new ProfileEntry { Name = "ProfileBulk",     CreateWriter = () => new ProfileBulkWriter(),\n'
        yield '                CreateReader = (g) => new ProfileBulkAccumulatingReader(8192, g),   HasPkgId = true,  HasLength = true,  MaxPayload = 65535 },\n'
        yield '            new ProfileEntry { Name = "ProfileNetwork",  CreateWriter = () => new ProfileNetworkWriter(),\n'
        yield '                CreateReader = (g) => new ProfileNetworkAccumulatingReader(8192, g),HasPkgId = true,  HasLength = true,  MaxPayload = 65535 },\n'
        yield '        };\n\n'

        # Per-message create + roundtrip method
        for key, msg in testable_messages:
            structName = msg.name
            yield f'        private static {structName} Create{structName}()\n'
            yield '        {\n'
            yield f'            var msg = new {structName}();\n'
            field_index = 0
            for fkey, field in msg.fields.items():
                yield TestCSharpGen._generate_field_init(field, "msg", field_index)
                field_index += 1
            yield '            return msg;\n'
            yield '        }\n\n'

            yield f'        private static bool Roundtrip{structName}(ProfileEntry p, bool verbose)\n'
            yield '        {\n'
            yield f'            if (!p.HasPkgId && {structName}.MsgId > 255)\n'
            yield '            {\n'
            yield f'                if (verbose) Console.WriteLine($"[SKIP] {structName} ({{p.Name}}): msg_id > 255 needs HasPkgId");\n'
            yield '                return true;\n'
            yield '            }\n'
            yield f'            if (p.MaxPayload >= 0 && {structName}.MaxSize > p.MaxPayload)\n'
            yield '            {\n'
            yield f'                if (verbose) Console.WriteLine($"[SKIP] {structName} ({{p.Name}}): exceeds MaxPayload");\n'
            yield '                return true;\n'
            yield '            }\n'
            yield '            try\n'
            yield '            {\n'
            yield f'                var orig = Create{structName}();\n'
            yield '                var writer = p.CreateWriter();\n'
            yield f'                writer.SetBuffer(new byte[{structName}.MaxSize + 256]);\n'
            yield '                writer.Write(orig);\n'
            yield '                var data = writer.GetData();\n\n'
            yield f'                var reader = p.CreateReader((id) => MessageDefinitions.GetMessageInfo(id));\n'
            yield '                reader.AddData(data);\n'
            yield '                var info = reader.Next();\n'
            yield '                if (!info.Valid)\n'
            yield '                {\n'
            yield f'                    Console.WriteLine($"[FAIL] {structName} ({{p.Name}}): parse failed");\n'
            yield '                    return false;\n'
            yield '                }\n'
            yield f'                if (info.MsgId != {structName}.MsgId)\n'
            yield '                {\n'
            yield f'                    Console.WriteLine($"[FAIL] {structName} ({{p.Name}}): msg_id mismatch (expected {{(int){structName}.MsgId}}, got {{(int)info.MsgId}})");\n'
            yield '                    return false;\n'
            yield '                }\n'
            yield f'                var decoded = {structName}.Deserialize(info);\n'
            yield '                var origBytes = orig.Serialize();\n'
            yield '                var decBytes = decoded.Serialize();\n'
            yield '                if (!origBytes.SequenceEqual(decBytes))\n'
            yield '                {\n'
            yield f'                    Console.WriteLine($"[FAIL] {structName} ({{p.Name}}): decoded data differs from original");\n'
            yield '                    return false;\n'
            yield '                }\n'
            yield f'                if (verbose) Console.WriteLine($"[PASS] {structName} ({{p.Name}})");\n'
            yield '                return true;\n'
            yield '            }\n'
            yield '            catch (Exception ex)\n'
            yield '            {\n'
            yield f'                Console.WriteLine($"[FAIL] {structName} ({{p.Name}}): exception: {{ex.Message}}");\n'
            yield '                return false;\n'
            yield '            }\n'
            yield '        }\n\n'

        # Master runner
        yield f'        private const int MessageCount = {len(testable_messages)};\n\n'
        yield '        public static bool RunAll(bool verbose)\n'
        yield '        {\n'
        yield '            bool allOk = true;\n'
        yield '            foreach (var p in Profiles)\n'
        yield '            {\n'
        yield '                if (verbose) Console.WriteLine($"\\n--- {p.Name} ---");\n'
        yield '                int passed = 0;\n'
        for key, msg in testable_messages:
            yield f'                if (Roundtrip{msg.name}(p, verbose)) passed++;\n'
        yield '                if (verbose) Console.WriteLine($"  -> {passed}/{MessageCount} passed");\n'
        yield '                if (passed != MessageCount)\n'
        yield '                {\n'
        yield '                    allOk = false;\n'
        yield '                    Console.WriteLine($"[FAIL] {p.Name}: {passed}/{MessageCount} passed");\n'
        yield '                }\n'
        yield '                else if (verbose)\n'
        yield '                {\n'
        yield '                    Console.WriteLine($"[OK] {p.Name}: {passed}/{MessageCount} passed");\n'
        yield '                }\n'
        yield '            }\n'
        yield '            return allOk;\n'
        yield '        }\n\n'

        yield '        public static int Main(string[] args)\n'
        yield '        {\n'
        yield '            bool verbose = args.Any(a => a == "-v" || a == "--verbose");\n'
        yield f'            Console.WriteLine("Running round-trip tests for package \'{package.name}\' across 5 profiles...");\n'
        yield '            bool ok = RunAll(verbose);\n'
        yield '            if (ok)\n'
        yield '            {\n'
        yield f'                Console.WriteLine("[TEST PASSED] All round-trip tests for \'{package.name}\' succeeded.");\n'
        yield '                return 0;\n'
        yield '            }\n'
        yield f'            Console.WriteLine("[TEST FAILED] Round-trip tests for \'{package.name}\' had failures.");\n'
        yield '            return 1;\n'
        yield '        }\n'
        yield '    }\n'
        yield '}\n'
