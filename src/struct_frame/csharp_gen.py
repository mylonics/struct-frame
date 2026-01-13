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
                    result += f'        public byte[] {var_name};  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars\n'
                elif field.max_size is not None:
                    # Variable string array
                    result += f'        public byte {var_name}Count;\n'
                    result += f'        public byte[] {var_name}Data;  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars\n'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        result += f'        public byte[] {var_name};  // Fixed array of {base_type}: {field.size_option} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name};  // Fixed array: {field.size_option} elements\n'
                elif field.max_size is not None:
                    # Variable array
                    result += f'        public byte {var_name}Count;\n'
                    if field.isEnum:
                        result += f'        public byte[] {var_name}Data;  // Variable array of {base_type}: up to {field.max_size} elements\n'
                    else:
                        result += f'        public {base_type}[] {var_name}Data;  // Variable array: up to {field.max_size} elements\n'

        # Handle regular strings
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                result += f'        public byte[] {var_name};  // Fixed string: exactly {field.size_option} chars\n'
            elif field.max_size is not None:
                # Variable string
                result += f'        public byte {var_name}Length;\n'
                result += f'        public byte[] {var_name}Data;  // Variable string: up to {field.max_size} chars\n'

        # Handle regular fields
        else:
            result += f'        public {base_type} {var_name};\n'

        return result

    @staticmethod
    def generate_pack_code(field, offset):
        """Generate code to pack this field into a byte array"""
        lines = []
        var_name = pascalCase(field.name)
        type_name = field.fieldType

        # IMPORTANT: Check is_array FIRST to handle arrays of primitives correctly
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:
                    # Fixed string array
                    total_size = field.size_option * field.element_size
                    lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {offset}, Math.Min({var_name}.Length, {total_size}));')
                elif field.max_size is not None:
                    # Variable string array
                    total_size = field.max_size * field.element_size
                    lines.append(f'            buffer[{offset}] = {var_name}Count;')
                    lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {offset + 1}, Math.Min({var_name}Data.Length, {total_size}));')
            else:
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.fieldType, 1)
                array_size = field.size_option if field.size_option else field.max_size
                total_data_size = field.size - (1 if field.max_size else 0)  # subtract count byte if variable
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {offset}, Math.Min({var_name}.Length, {field.size_option}));')
                    elif field.fieldType in csharp_type_sizes:
                        # Primitive array - use Buffer.BlockCopy
                        lines.append(f'            if ({var_name} != null)')
                        lines.append(f'                Buffer.BlockCopy({var_name}, 0, buffer, {offset}, Math.Min({var_name}.Length * {element_size}, {total_data_size}));')
                    else:
                        # Nested struct array - pack each element
                        lines.append(f'            if ({var_name} != null)')
                        lines.append(f'                for (int i = 0; i < Math.Min({var_name}.Length, {field.size_option}); i++)')
                        lines.append(f'                    if ({var_name}[i] != null) {{ var bytes = {var_name}[i].Pack(); Array.Copy(bytes, 0, buffer, {offset} + i * {element_size}, bytes.Length); }}')
                elif field.max_size is not None:
                    # Variable array
                    lines.append(f'            buffer[{offset}] = {var_name}Count;')
                    if field.isEnum:
                        lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {offset + 1}, Math.Min({var_name}Data.Length, {field.max_size}));')
                    elif field.fieldType in csharp_type_sizes:
                        # Primitive array
                        lines.append(f'            if ({var_name}Data != null)')
                        lines.append(f'                Buffer.BlockCopy({var_name}Data, 0, buffer, {offset + 1}, Math.Min({var_name}Data.Length * {element_size}, {total_data_size}));')
                    else:
                        # Nested struct array - pack each element
                        lines.append(f'            if ({var_name}Data != null)')
                        lines.append(f'                for (int i = 0; i < Math.Min({var_name}Data.Length, {field.max_size}); i++)')
                        lines.append(f'                    if ({var_name}Data[i] != null) {{ var bytes = {var_name}Data[i].Pack(); Array.Copy(bytes, 0, buffer, {offset + 1} + i * {element_size}, bytes.Length); }}')
        elif type_name in csharp_type_sizes:
            # Single primitive field (not array)
            size = csharp_type_sizes[type_name]
            if type_name == "uint8":
                lines.append(f'            buffer[{offset}] = {var_name};')
            elif type_name == "int8":
                lines.append(f'            buffer[{offset}] = (byte){var_name};')
            elif type_name == "uint16":
                lines.append(f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan({offset}, 2), {var_name});')
            elif type_name == "int16":
                lines.append(f'            BinaryPrimitives.WriteInt16LittleEndian(buffer.AsSpan({offset}, 2), {var_name});')
            elif type_name == "uint32":
                lines.append(f'            BinaryPrimitives.WriteUInt32LittleEndian(buffer.AsSpan({offset}, 4), {var_name});')
            elif type_name == "int32":
                lines.append(f'            BinaryPrimitives.WriteInt32LittleEndian(buffer.AsSpan({offset}, 4), {var_name});')
            elif type_name == "uint64":
                lines.append(f'            BinaryPrimitives.WriteUInt64LittleEndian(buffer.AsSpan({offset}, 8), {var_name});')
            elif type_name == "int64":
                lines.append(f'            BinaryPrimitives.WriteInt64LittleEndian(buffer.AsSpan({offset}, 8), {var_name});')
            elif type_name == "float":
                lines.append(f'            BinaryPrimitives.WriteSingleLittleEndian(buffer.AsSpan({offset}, 4), {var_name});')
            elif type_name == "double":
                lines.append(f'            BinaryPrimitives.WriteDoubleLittleEndian(buffer.AsSpan({offset}, 8), {var_name});')
            elif type_name == "bool":
                lines.append(f'            buffer[{offset}] = (byte)({var_name} ? 1 : 0);')
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                lines.append(f'            if ({var_name} != null) Array.Copy({var_name}, 0, buffer, {offset}, Math.Min({var_name}.Length, {field.size_option}));')
            elif field.max_size is not None:
                # Variable string
                lines.append(f'            buffer[{offset}] = {var_name}Length;')
                lines.append(f'            if ({var_name}Data != null) Array.Copy({var_name}Data, 0, buffer, {offset + 1}, Math.Min({var_name}Data.Length, {field.max_size}));')
        elif field.isEnum:
            # Single enum field - enums are byte values
            lines.append(f'            buffer[{offset}] = (byte){var_name};')
        else:
            # Nested struct - would need recursive handling
            # For now, copy the whole struct as bytes
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
            lines.append(f'            if ({var_name} != null) {{ var nestedBytes = {var_name}.Pack(); Array.Copy(nestedBytes, 0, buffer, {offset}, nestedBytes.Length); }}')

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
                    lines.append(f'            Array.Copy(data, offset + {offset}, msg.{var_name}, 0, {total_size});')
                elif field.max_size is not None:
                    # Variable string array
                    total_size = field.max_size * field.element_size
                    lines.append(f'            msg.{var_name}Count = data[offset + {offset}];')
                    lines.append(f'            msg.{var_name}Data = new byte[{total_size}];')
                    lines.append(f'            Array.Copy(data, offset + {offset + 1}, msg.{var_name}Data, 0, {total_size});')
            else:
                element_size = field.element_size if field.element_size else csharp_type_sizes.get(field.fieldType, 1)
                if field.size_option is not None:
                    # Fixed array
                    if field.isEnum:
                        lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                        lines.append(f'            Array.Copy(data, offset + {offset}, msg.{var_name}, 0, {field.size_option});')
                    elif field.fieldType in csharp_type_sizes:
                        base_type = csharp_types.get(field.fieldType, field.fieldType)
                        total_data_size = field.size
                        lines.append(f'            msg.{var_name} = new {base_type}[{field.size_option}];')
                        lines.append(f'            Buffer.BlockCopy(data, offset + {offset}, msg.{var_name}, 0, {total_data_size});')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                        element_size = field.element_size if field.element_size else (field.size // field.size_option)
                        lines.append(f'            msg.{var_name} = new {nested_type}[{field.size_option}];')
                        lines.append(f'            for (int i = 0; i < {field.size_option}; i++)')
                        lines.append(f'                msg.{var_name}[i] = {nested_type}.Unpack(data, offset + {offset} + i * {element_size});')
                elif field.max_size is not None:
                    # Variable array
                    lines.append(f'            msg.{var_name}Count = data[offset + {offset}];')
                    if field.isEnum:
                        lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                        lines.append(f'            Array.Copy(data, offset + {offset + 1}, msg.{var_name}Data, 0, {field.max_size});')
                    elif field.fieldType in csharp_type_sizes:
                        base_type = csharp_types.get(field.fieldType, field.fieldType)
                        total_data_size = field.size - 1  # subtract count byte
                        lines.append(f'            msg.{var_name}Data = new {base_type}[{field.max_size}];')
                        lines.append(f'            Buffer.BlockCopy(data, offset + {offset + 1}, msg.{var_name}Data, 0, {total_data_size});')
                    else:
                        # Nested struct array
                        type_pkg = field.type_package if field.type_package else field.package
                        nested_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                        element_size = field.element_size if field.element_size else ((field.size - 1) // field.max_size)
                        lines.append(f'            msg.{var_name}Data = new {nested_type}[{field.max_size}];')
                        lines.append(f'            for (int i = 0; i < {field.max_size}; i++)')
                        lines.append(f'                msg.{var_name}Data[i] = {nested_type}.Unpack(data, offset + {offset + 1} + i * {element_size});')
        elif type_name in csharp_type_sizes:
            # Single primitive field (not array)
            if type_name == "uint8":
                lines.append(f'            msg.{var_name} = data[offset + {offset}];')
            elif type_name == "int8":
                lines.append(f'            msg.{var_name} = (sbyte)data[offset + {offset}];')
            elif type_name == "uint16":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt16LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 2));')
            elif type_name == "int16":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt16LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 2));')
            elif type_name == "uint32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt32LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 4));')
            elif type_name == "int32":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt32LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 4));')
            elif type_name == "uint64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadUInt64LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 8));')
            elif type_name == "int64":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadInt64LittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 8));')
            elif type_name == "float":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadSingleLittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 4));')
            elif type_name == "double":
                lines.append(f'            msg.{var_name} = BinaryPrimitives.ReadDoubleLittleEndian(new ReadOnlySpan<byte>(data, offset + {offset}, 8));')
            elif type_name == "bool":
                lines.append(f'            msg.{var_name} = data[offset + {offset}] != 0;')
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string
                lines.append(f'            msg.{var_name} = new byte[{field.size_option}];')
                lines.append(f'            Array.Copy(data, offset + {offset}, msg.{var_name}, 0, {field.size_option});')
            elif field.max_size is not None:
                # Variable string
                lines.append(f'            msg.{var_name}Length = data[offset + {offset}];')
                lines.append(f'            msg.{var_name}Data = new byte[{field.max_size}];')
                lines.append(f'            Array.Copy(data, offset + {offset + 1}, msg.{var_name}Data, 0, {field.max_size});')
        elif field.isEnum:
            # Single enum field - enums are byte values, cast to enum type
            type_pkg = field.type_package if field.type_package else field.package
            enum_type = '%s%s' % (pascalCase(type_pkg), type_name)
            lines.append(f'            msg.{var_name} = ({enum_type})data[offset + {offset}];')
        else:
            # Nested struct
            type_pkg = field.type_package if field.type_package else field.package
            nested_type = '%s%s' % (pascalCase(type_pkg), type_name)
            lines.append(f'            msg.{var_name} = {nested_type}.Unpack(data, offset + {offset});')

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

        result += '    public class %s : IStructFrameMessage\n' % structName
        result += '    {\n'

        result += '        public const int MaxSize = %d;\n' % msg.size
        if msg.id:
            if package and package.package_id is not None:
                combined_msg_id = (package.package_id << 8) | msg.id
                result += '        public const ushort MsgId = %d;\n' % combined_msg_id
            else:
                result += '        public const ushort MsgId = %d;\n' % msg.id
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

        # Generate Pack() method
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Pack this message into a byte array\n'
        result += '        /// </summary>\n'
        result += '        public byte[] Pack()\n'
        result += '        {\n'
        result += '            byte[] buffer = new byte[MaxSize];\n'

        offset = 0
        for key, f in msg.fields.items():
            pack_lines = FieldCSharpGen.generate_pack_code(f, offset)
            for line in pack_lines:
                result += line + '\n'
            offset += f.size

        # Generate oneof packing code
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                result += f'            // Oneof {oneof_name} discriminator\n'
                result += f'            BinaryPrimitives.WriteUInt16LittleEndian(buffer.AsSpan({offset}), {pascalCase(oneof_name)}Discriminator);\n'
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
                result += f'                var unionBytes = {field_var}.Pack();\n'
                result += f'                Array.Copy(unionBytes, 0, buffer, {offset}, Math.Min(unionBytes.Length, {oneof.size}));\n'
                result += '            }\n'
            offset += oneof.size

        result += '            return buffer;\n'
        result += '        }\n'

        # Generate Unpack() static method
        result += '\n'
        result += '        /// <summary>\n'
        result += '        /// Unpack a byte array into this message type\n'
        result += '        /// </summary>\n'
        result += f'        public static {structName} Unpack(byte[] data, int offset = 0)\n'
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
                result += f'            msg.{pascalCase(oneof_name)}Discriminator = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(offset + {offset}));\n'
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
                    result += f'                msg.{field_var} = {type_name}.Unpack(data, offset + {offset});\n'
                    result += '            }\n'
            offset += oneof.size

        result += '            return msg;\n'
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

        # Generate equality members if requested
        if equality:
            result += MessageCSharpGen._generate_equality_members(msg, structName)

        result += '    }\n'

        return result + '\n'
    
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

        yield 'using System;\n'
        
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
            yield '    public static class MessageDefinitions\n'
            yield '    {\n'
            
            if package.package_id is not None:
                yield '        public static bool GetMessageLength(ushort msgId, out int size)\n'
                yield '        {\n'
                yield '            byte pkgId = (byte)((msgId >> 8) & 0xFF);\n'
                yield '            byte localMsgId = (byte)(msgId & 0xFF);\n'
                yield '            \n'
                yield f'            if (pkgId != PackageInfo.PackageId)\n'
                yield '            {\n'
                yield '                size = 0;\n'
                yield '                return false;\n'
                yield '            }\n'
                yield '            \n'
                yield '            switch (localMsgId)\n'
                yield '            {\n'
            else:
                yield '        public static bool GetMessageLength(int msgId, out int size)\n'
                yield '        {\n'
                yield '            switch (msgId)\n'
                yield '            {\n'
            
            for key, msg in package.sortedMessages().items():
                if msg.id:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    if package.package_id is not None:
                        yield '                case %d: size = %s.MaxSize; return true;\n' % (msg.id, structName)
                    else:
                        yield '                case %s.MsgId: size = %s.MaxSize; return true;\n' % (structName, structName)
            yield '                default: size = 0; return false;\n'
            yield '            }\n'
            yield '        }\n'
            yield '    }\n'

        yield '}\n'
