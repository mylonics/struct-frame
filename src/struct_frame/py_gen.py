#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
Python code generator for struct-frame.

This module generates Python code for struct serialization using the struct
module for binary packing/unpacking with dataclass-style message definitions.
"""

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase, build_enum_leading_comments, build_enum_values
import time

StyleC = NamingStyleC()

# Mapping from proto types to Python struct format characters
py_struct_format = {
    "uint8": "B",
    "int8": "b",
    "uint16": "H",
    "int16": "h",
    "uint32": "I",
    "int32": "i",
    "bool": "?",
    "float": "f",
    "double": "d",
    "uint64": "Q",
    "int64": "q",
}

# Mapping from struct format characters to their sizes in bytes
struct_format_sizes = {
    'b': 1, 'B': 1,
    'h': 2, 'H': 2,
    'i': 4, 'I': 4,
    'q': 8, 'Q': 8,
    'f': 4, 'd': 8,
    '?': 1
}

# Python type hints for fields
py_type_hints = {
    "uint8": "int",
    "int8": "int",
    "uint16": "int",
    "int16": "int",
    "uint32": "int",
    "int32": "int",
    "bool": "bool",
    "float": "float",
    "double": "float",
    "uint64": "int",
    "int64": "int",
    "string": "bytes",
}


class EnumPyGen():
    @staticmethod
    def generate(field):
        result = build_enum_leading_comments(field.comments, comment_prefix='#')

        enumName = '%s%s' % (pascalCase(field.package), field.name)
        result += 'class %s(Enum):\n' % (enumName)

        def py_comment_formatter(comments):
            return ['#' + c for c in comments]

        enum_values = build_enum_values(
            field, StyleC,
            value_format='{indent}{name} = {value}',
            comment_formatter=py_comment_formatter,
            skip_trailing_comma=False  # Python doesn't need comma handling
        )

        result += '\n'.join(enum_values)
        
        return result
    
    @staticmethod
    def generate_discriminator_enum(oneof, msg_name):
        """Generate a discriminator enum for field_order oneofs in Python."""
        if not oneof.auto_discriminator or oneof.discriminator_type != "field_order":
            return ''
        
        enum_name = f'{msg_name}{pascalCase(oneof.name)}Field'
        result = f'class {enum_name}(Enum):\n'
        result += f'    """Discriminator enum for {msg_name}.{oneof.name} oneof"""\n'
        result += f'    NONE = 0\n'
        
        for idx, (field_name, field) in enumerate(oneof.fields.items()):
            field_order = idx + 1
            # Use SCREAMING_SNAKE_CASE for enum values
            enum_value = CamelToSnakeCase(field_name).upper()
            result += f'    {enum_value} = {field_order}\n'
        
        return result
    
    @staticmethod
    def get_discriminator_enum_name(oneof, msg_name):
        """Get the enum type name for a field_order discriminator."""
        return f'{msg_name}{pascalCase(oneof.name)}Field'


class FieldPyGen():
    @staticmethod
    def get_type_hint(field):
        """Get Python type hint for a field"""
        type_name = field.fieldType
        
        if type_name in py_type_hints:
            base_hint = py_type_hints[type_name]
        elif field.isEnum:
            base_hint = "int"  # Enums are stored as uint8
        else:
            # Nested message
            base_hint = '%s%s' % (pascalCase(field.package), type_name)
        
        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                return "List[bytes]"
            else:
                return f"List[{base_hint}]"
        elif field.fieldType == "string":
            return "bytes"
        else:
            return base_hint
    
    @staticmethod
    def generate(field):
        """Generate field definition with type hint"""
        result = ''
        
        var_name = field.name
        type_hint = FieldPyGen.get_type_hint(field)
        
        result += f'    {var_name}: {type_hint}'
        
        # Add comments about special handling
        if field.is_array:
            if field.size_option is not None:
                result += f'  # Fixed array: {field.size_option} elements'
            elif field.max_size is not None:
                result += f'  # Bounded array: max {field.max_size} elements'
        elif field.fieldType == "string":
            if field.size_option is not None:
                result += f'  # Fixed string: {field.size_option} bytes'
            elif field.max_size is not None:
                result += f'  # Variable string: max {field.max_size} bytes'
        
        if field.isEnum:
            enum_class_name = '%s%s' % (pascalCase(field.package), field.fieldType)
            result += f'  # Enum: {enum_class_name}'
        
        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = "#" + c + "\n" + result
        
        return result


class MessagePyGen():
    @staticmethod
    def get_struct_format(field):
        """Get struct format string for a field"""
        type_name = field.fieldType
        
        # Get base format character
        if type_name in py_struct_format:
            base_fmt = py_struct_format[type_name]
        elif field.isEnum:
            base_fmt = "B"  # Enums are uint8
        elif type_name == "string":
            # Strings need special handling
            if field.size_option is not None:
                return f"{field.size_option}s"
            else:
                return None  # Variable strings handled separately
        else:
            # Nested message - no direct format
            return None
        
        # Handle arrays
        if field.is_array:
            if field.size_option is not None:
                # Fixed array
                return f"{field.size_option}{base_fmt}"
            else:
                # Bounded/variable array - handled separately
                return None
        
        return base_fmt
    
    @staticmethod
    def generate_eq_method(msg, structName):
        """Generate the __eq__ method for equality comparison"""
        result = '\n    def __eq__(self, other) -> bool:\n'
        result += '        """Compare two messages for equality"""\n'
        result += f'        if not isinstance(other, {structName}):\n'
        result += '            return False\n'
        
        comparisons = []
        
        # Generate field comparisons
        for key, f in msg.fields.items():
            comparisons.append(f'self.{f.name} == other.{f.name}')
        
        # Generate oneof comparisons
        for oneof_name, oneof in msg.oneofs.items():
            comparisons.append(f'self.{oneof_name} == other.{oneof_name}')
            comparisons.append(f'self.{oneof_name}_which == other.{oneof_name}_which')
            if oneof.auto_discriminator:
                comparisons.append(f'self.{oneof_name}_discriminator == other.{oneof_name}_discriminator')
        
        if comparisons:
            result += '        return (' + ' and\n                '.join(comparisons) + ')\n'
        else:
            result += '        return True\n'
        
        result += '\n    def __ne__(self, other) -> bool:\n'
        result += '        """Compare two messages for inequality"""\n'
        result += '        return not self.__eq__(other)\n'
        
        return result
    
    @staticmethod
    def generate_pack_method(msg):
        """Generate the serialize() method"""
        result = '\n    def serialize(self) -> bytes:\n'
        if msg.variable:
            result += '        """Serialize the message into binary format (variable-length encoding by default)\n'
            result += '        \n'
            result += '        For variable messages: returns variable-length encoding.\n'
            result += '        Use serialize_max_size() for MAX_SIZE encoding (needed for minimal profiles).\n'
            result += '        """\n'
            result += '        return self._serialize_variable()\n'
            result += '\n'
            result += '    def serialize_max_size(self) -> bytes:\n'
            result += '        """Serialize the message to MAX_SIZE (for minimal profiles without length field)"""\n'
        else:
            result += '        """Serialize the message into binary format"""\n'
        result += '        data = b""\n'
        
        # Pack regular fields
        for key, f in msg.fields.items():
            if f.fieldType == "string" and not f.is_array:
                # String field
                if f.size_option is not None:
                    # Fixed string
                    result += f'        # Fixed string: {f.name}\n'
                    result += f'        data += struct.pack("<{f.size_option}s", self.{f.name}[:{f.size_option}])\n'
                elif f.max_size is not None:
                    # Variable string with length prefix
                    count_fmt = "H" if f.max_size > 255 else "B"
                    result += f'        # Variable string: {f.name}\n'
                    result += f'        str_data = self.{f.name}[:{f.max_size}]\n'
                    result += f'        data += struct.pack("<{count_fmt}", len(str_data))\n'
                    result += f'        data += struct.pack("<{f.max_size}s", str_data)\n'
            elif f.is_array:
                # Array field
                if f.fieldType == "string":
                    # String array
                    if f.size_option is not None:
                        # Fixed string array
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Fixed string array: {f.name}\n'
                        result += f'        for i in range({f.size_option}):\n'
                        result += f'            if i < len(self.{f.name}):\n'
                        result += f'                data += struct.pack("<{element_size}s", self.{f.name}[i][:{element_size}])\n'
                        result += f'            else:\n'
                        result += f'                data += struct.pack("<{element_size}s", b"")\n'
                    elif f.max_size is not None:
                        # Bounded string array
                        count_fmt = "H" if f.max_size > 255 else "B"
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Bounded string array: {f.name}\n'
                        result += f'        data += struct.pack("<{count_fmt}", min(len(self.{f.name}), {f.max_size}))\n'
                        result += f'        for i in range({f.max_size}):\n'
                        result += f'            if i < len(self.{f.name}):\n'
                        result += f'                data += struct.pack("<{element_size}s", self.{f.name}[i][:{element_size}])\n'
                        result += f'            else:\n'
                        result += f'                data += struct.pack("<{element_size}s", b"")\n'
                else:
                    # Numeric/enum/struct array
                    fmt = MessagePyGen.get_struct_format(f)
                    if f.size_option is not None:
                        # Fixed array
                        if fmt:
                            # Fixed array of primitives/enums
                            result += f'        # Fixed array: {f.name}\n'
                            result += f'        for i in range({f.size_option}):\n'
                            result += f'            val = self.{f.name}[i] if i < len(self.{f.name}) else 0\n'
                            if f.isEnum:
                                result += f'            data += struct.pack("<B", int(val))\n'
                            else:
                                base_fmt = py_struct_format[f.fieldType]
                                result += f'            data += struct.pack("<{base_fmt}", val)\n'
                        else:
                            # Fixed array of nested messages
                            type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                            result += f'        # Fixed nested message array: {f.name}\n'
                            result += f'        for i in range({f.size_option}):\n'
                            result += f'            if i < len(self.{f.name}):\n'
                            result += f'                data += self.{f.name}[i].serialize()\n'
                            result += f'            else:\n'
                            result += f'                data += {type_name}().serialize()\n'
                    elif f.max_size is not None:
                        # Bounded array
                        count_fmt = "H" if f.max_size > 255 else "B"
                        if f.isDefaultType or f.isEnum:
                            # Primitives/enums
                            result += f'        # Bounded array: {f.name}\n'
                            result += f'        data += struct.pack("<{count_fmt}", min(len(self.{f.name}), {f.max_size}))\n'
                            result += f'        for i in range({f.max_size}):\n'
                            result += f'            val = self.{f.name}[i] if i < len(self.{f.name}) else 0\n'
                            if f.isEnum:
                                result += f'            data += struct.pack("<B", int(val))\n'
                            else:
                                base_fmt = py_struct_format[f.fieldType]
                                result += f'            data += struct.pack("<{base_fmt}", val)\n'
                        else:
                            # Nested messages
                            result += f'        # Bounded nested message array: {f.name}\n'
                            result += f'        data += struct.pack("<{count_fmt}", min(len(self.{f.name}), {f.max_size}))\n'
                            result += f'        for i in range({f.max_size}):\n'
                            result += f'            if i < len(self.{f.name}):\n'
                            result += f'                data += self.{f.name}[i].serialize()\n'
                            result += f'            else:\n'
                            # Need to create empty instance
                            type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                            result += f'                data += {type_name}().serialize()\n'
            else:
                # Regular field
                fmt = MessagePyGen.get_struct_format(f)
                if fmt:
                    # Simple type
                    result += f'        data += struct.pack("<{fmt}", self.{f.name})\n'
                else:
                    # Nested message
                    result += f'        data += self.{f.name}.serialize()\n'
        
        # Pack oneofs
        for oneof_name, oneof in msg.oneofs.items():
            # Discriminator if enabled
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'        # Oneof {oneof_name} auto-discriminator (uint16 - message ID)\n'
                    result += f'        if self.{oneof_name}_which is not None:\n'
                    result += f'            data += struct.pack("<H", self.{oneof_name}[self.{oneof_name}_which].__class__.msg_id)\n'
                    result += f'        else:\n'
                    result += f'            data += struct.pack("<H", 0)\n'
                else:  # field_order
                    result += f'        # Oneof {oneof_name} discriminator (uint8 - field order, 1-based)\n'
                    field_order_map = {field_name: idx + 1 for idx, field_name in enumerate(oneof.field_order)}
                    result += f'        _field_order_map = {field_order_map}\n'
                    result += f'        if self.{oneof_name}_which is not None:\n'
                    result += f'            data += struct.pack("<B", _field_order_map[self.{oneof_name}_which])\n'
                    result += f'        else:\n'
                    result += f'            data += struct.pack("<B", 0)\n'
            
            # Pack the union field (whichever is active)
            result += f'        # Oneof {oneof_name} payload\n'
            # We need to allocate the full size for the union
            result += f'        union_data = b""\n'
            result += f'        if self.{oneof_name}_which is not None:\n'
            result += f'            union_data = self.{oneof_name}[self.{oneof_name}_which].serialize()\n'
            result += f'        # Pad to union size\n'
            result += f'        union_data = union_data.ljust({oneof.size}, b"\\x00")\n'
            result += f'        data += union_data\n'
        
        result += '        return data\n'
        return result
    
    @staticmethod
    def generate_unpack_method(msg):
        """Generate the _deserialize_fixed() class method"""
        result = '\n    @classmethod\n'
        result += '    def _deserialize_fixed(cls, data: bytes):\n'
        result += '        """Deserialize binary data into a message instance (fixed-size format)"""\n'
        result += '        offset = 0\n'
        result += '        fields = {}\n'
        
        for key, f in msg.fields.items():
            if f.fieldType == "string" and not f.is_array:
                # String field
                if f.size_option is not None:
                    # Fixed string
                    result += f'        # Fixed string: {f.name}\n'
                    result += f'        fields["{f.name}"] = struct.unpack_from("<{f.size_option}s", data, offset)[0]\n'
                    result += f'        offset += {f.size_option}\n'
                elif f.max_size is not None:
                    # Variable string with length prefix
                    count_fmt = "H" if f.max_size > 255 else "B"
                    count_size = 2 if f.max_size > 255 else 1
                    result += f'        # Variable string: {f.name}\n'
                    result += f'        str_len = struct.unpack_from("<{count_fmt}", data, offset)[0]\n'
                    result += f'        offset += {count_size}\n'
                    result += f'        str_data = struct.unpack_from("<{f.max_size}s", data, offset)[0]\n'
                    result += f'        fields["{f.name}"] = str_data[:str_len]\n'
                    result += f'        offset += {f.max_size}\n'
            elif f.is_array:
                # Array field
                if f.fieldType == "string":
                    # String array
                    if f.size_option is not None:
                        # Fixed string array
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Fixed string array: {f.name}\n'
                        result += f'        fields["{f.name}"] = []\n'
                        result += f'        for i in range({f.size_option}):\n'
                        result += f'            s = struct.unpack_from("<{element_size}s", data, offset)[0]\n'
                        result += f'            fields["{f.name}"].append(s)\n'
                        result += f'            offset += {element_size}\n'
                    elif f.max_size is not None:
                        # Bounded string array
                        count_fmt = "H" if f.max_size > 255 else "B"
                        count_size = 2 if f.max_size > 255 else 1
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Bounded string array: {f.name}\n'
                        result += f'        count = struct.unpack_from("<{count_fmt}", data, offset)[0]\n'
                        result += f'        offset += {count_size}\n'
                        result += f'        fields["{f.name}"] = []\n'
                        result += f'        for i in range({f.max_size}):\n'
                        result += f'            s = struct.unpack_from("<{element_size}s", data, offset)[0]\n'
                        result += f'            if i < count:\n'
                        result += f'                fields["{f.name}"].append(s)\n'
                        result += f'            offset += {element_size}\n'
                else:
                    # Numeric/enum/struct array
                    fmt = MessagePyGen.get_struct_format(f)
                    if f.size_option is not None:
                        # Fixed array
                        if fmt:
                            # Fixed array of primitives/enums
                            result += f'        # Fixed array: {f.name}\n'
                            result += f'        fields["{f.name}"] = []\n'
                            result += f'        for i in range({f.size_option}):\n'
                            if f.isEnum:
                                result += f'            val = struct.unpack_from("<B", data, offset)[0]\n'
                                result += f'            offset += 1\n'
                            else:
                                base_fmt = py_struct_format[f.fieldType]
                                size = struct_format_sizes[base_fmt]
                                result += f'            val = struct.unpack_from("<{base_fmt}", data, offset)[0]\n'
                                result += f'            offset += {size}\n'
                            result += f'            fields["{f.name}"].append(val)\n'
                        else:
                            # Fixed array of nested messages
                            type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                            result += f'        # Fixed nested message array: {f.name}\n'
                            result += f'        fields["{f.name}"] = []\n'
                            result += f'        for i in range({f.size_option}):\n'
                            result += f'            msg = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.msg_size])\n'
                            result += f'            fields["{f.name}"].append(msg)\n'
                            result += f'            offset += {type_name}.msg_size\n'
                    elif f.max_size is not None:
                        # Bounded array
                        count_fmt = "H" if f.max_size > 255 else "B"
                        count_size = 2 if f.max_size > 255 else 1
                        if f.isDefaultType or f.isEnum:
                            # Primitives/enums
                            result += f'        # Bounded array: {f.name}\n'
                            result += f'        count = struct.unpack_from("<{count_fmt}", data, offset)[0]\n'
                            result += f'        offset += {count_size}\n'
                            result += f'        fields["{f.name}"] = []\n'
                            result += f'        for i in range({f.max_size}):\n'
                            if f.isEnum:
                                result += f'            val = struct.unpack_from("<B", data, offset)[0]\n'
                                result += f'            offset += 1\n'
                            else:
                                base_fmt = py_struct_format[f.fieldType]
                                size = struct_format_sizes[base_fmt]
                                result += f'            val = struct.unpack_from("<{base_fmt}", data, offset)[0]\n'
                                result += f'            offset += {size}\n'
                            result += f'            if i < count:\n'
                            result += f'                fields["{f.name}"].append(val)\n'
                        else:
                            # Nested messages
                            type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                            result += f'        # Bounded nested message array: {f.name}\n'
                            result += f'        count = struct.unpack_from("<{count_fmt}", data, offset)[0]\n'
                            result += f'        offset += {count_size}\n'
                            result += f'        fields["{f.name}"] = []\n'
                            result += f'        for i in range({f.max_size}):\n'
                            result += f'            msg = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.msg_size])\n'
                            result += f'            if i < count:\n'
                            result += f'                fields["{f.name}"].append(msg)\n'
                            result += f'            offset += {type_name}.msg_size\n'
            else:
                # Regular field
                fmt = MessagePyGen.get_struct_format(f)
                if fmt:
                    # Simple type
                    # Handle multi-character struct formats like '16s'
                    if fmt.endswith('s') and len(fmt) > 1 and fmt[:-1].isdigit():
                        size = int(fmt[:-1])
                    else:
                        size = struct_format_sizes.get(fmt, 0)
                    result += f'        fields["{f.name}"] = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                    result += f'        offset += {size}\n'
                else:
                    # Nested message
                    type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                    result += f'        fields["{f.name}"] = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.msg_size])\n'
                    result += f'        offset += {type_name}.msg_size\n'
        
        # Unpack oneofs
        for oneof_name, oneof in msg.oneofs.items():
            # Discriminator if enabled
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'        # Oneof {oneof_name} auto-discriminator (uint16 - message ID)\n'
                    result += f'        discriminator = struct.unpack_from("<H", data, offset)[0]\n'
                    result += f'        offset += 2\n'
                else:  # field_order
                    result += f'        # Oneof {oneof_name} discriminator (uint8 - field order, 1-based)\n'
                    result += f'        discriminator = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
                result += f'        fields["{oneof_name}_discriminator"] = discriminator\n'
            
            # Unpack the union payload
            result += f'        # Oneof {oneof_name} payload\n'
            result += f'        fields["{oneof_name}"] = {{}}\n'
            result += f'        fields["{oneof_name}_which"] = None\n'
            
            # Try to unpack based on discriminator if available
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'        # Determine which field is active based on message ID\n'
                    for field_name, field in oneof.fields.items():
                        type_name = '%s%s' % (pascalCase(field.package), field.fieldType)
                        result += f'        if discriminator == {type_name}.msg_id:\n'
                        result += f'            fields["{oneof_name}"]["{field_name}"] = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.msg_size])\n'
                        result += f'            fields["{oneof_name}_which"] = "{field_name}"\n'
                else:  # field_order
                    result += f'        # Determine which field is active based on field order (1-based index)\n'
                    for idx, field_name in enumerate(oneof.field_order):
                        field = oneof.fields[field_name]
                        field_idx = idx + 1  # 1-based index
                        if field.isDefaultType or field.isEnum:
                            # Primitive or enum type
                            pack_format = py_struct_format.get(field.fieldType, 'B')
                            result += f'        if discriminator == {field_idx}:\n'
                            result += f'            fields["{oneof_name}"]["{field_name}"] = struct.unpack_from("<{pack_format}", data, offset)[0]\n'
                            result += f'            fields["{oneof_name}_which"] = "{field_name}"\n'
                        else:
                            # Nested message
                            type_name = '%s%s' % (pascalCase(field.package), field.fieldType)
                            result += f'        if discriminator == {field_idx}:\n'
                            result += f'            fields["{oneof_name}"]["{field_name}"] = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.msg_size])\n'
                            result += f'            fields["{oneof_name}_which"] = "{field_name}"\n'
            
            result += f'        offset += {oneof.size}\n'
        
        result += '        return cls(**fields)\n'
        return result
    
    @staticmethod
    def generate_data_method(msg):
        """Generate the data() method that returns packed bytes (C++ compatible API)"""
        result = '\n    def data(self) -> bytes:\n'
        result += '        """Return packed message bytes (C++ MessageBase compatible API)"""\n'
        result += '        return self.serialize()\n'
        return result
    
    @staticmethod
    def generate(msg, equality=False):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '#%s\n' % c

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        result += 'class %s:\n' % structName
        # Add both old and new naming for compatibility
        result += '    msg_size = %s\n' % msg.size
        result += '    MAX_SIZE = %s  # C++ compatible alias\n' % msg.size
        if msg.id != None:
            result += '    msg_id = %s\n' % msg.id
            result += '    MSG_ID = %s  # C++ compatible alias\n' % msg.id
        
        # Add magic numbers for checksum
        if msg.id is not None and msg.magic_bytes:
            result += f'    MAGIC1 = {msg.magic_bytes[0]}  # Checksum magic number (based on field types and positions)\n'
            result += f'    MAGIC2 = {msg.magic_bytes[1]}  # Checksum magic number (based on field types and positions)\n'
        
        # Add variable message constants
        if msg.variable:
            result += f'    MIN_SIZE = {msg.min_size}  # Minimum size when all variable fields are empty\n'
            result += f'    IS_VARIABLE = True  # This message uses variable-length encoding\n'
        
        result += '\n'

        # Generate __init__ method
        result += '    def __init__(self'
        init_params = []
        for key, f in msg.fields.items():
            type_hint = FieldPyGen.get_type_hint(f)
            init_params.append(f'{f.name}: {type_hint} = None')
        
        # Add oneof parameters
        for oneof_name, oneof in msg.oneofs.items():
            init_params.append(f'{oneof_name}: dict = None')
            init_params.append(f'{oneof_name}_which: str = None')
            if oneof.auto_discriminator:
                init_params.append(f'{oneof_name}_discriminator: int = None')
        
        if init_params:
            result += ', ' + ', '.join(init_params)
        result += '):\n'
        
        for key, f in msg.fields.items():
            # Initialize with defaults
            if f.is_array:
                # For float32 arrays, truncate each element to 32-bit precision
                if f.fieldType == "float":
                    result += f'        self.{f.name} = [_truncate_float32(v) for v in {f.name}] if {f.name} is not None else []\n'
                else:
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else []\n'
            elif f.fieldType == "string":
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else b""\n'
            elif f.fieldType in py_type_hints:
                if f.fieldType == "bool":
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else False\n'
                elif f.fieldType == "float":
                    # Truncate float32 to 32-bit precision
                    result += f'        self.{f.name} = _truncate_float32({f.name}) if {f.name} is not None else 0.0\n'
                elif f.fieldType == "double":
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0.0\n'
                else:
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0\n'
            elif f.isEnum:
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0\n'
            else:
                # Nested message
                type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else {type_name}()\n'

        # Initialize oneofs
        for oneof_name, oneof in msg.oneofs.items():
            result += f'        self.{oneof_name} = {oneof_name} if {oneof_name} is not None else {{}}\n'
            result += f'        self.{oneof_name}_which = {oneof_name}_which\n'
            if oneof.auto_discriminator:
                result += f'        self.{oneof_name}_discriminator = {oneof_name}_discriminator\n'

        # Generate pack method
        result += MessagePyGen.generate_pack_method(msg)

        # Generate unpack method
        result += MessagePyGen.generate_unpack_method(msg)

        # Generate data() method (C++ compatible API)
        result += MessagePyGen.generate_data_method(msg)

        # Generate __str__ method
        result += '\n    def __str__(self):\n'
        result += f'        out = "{msg.name} Msg, ID {msg.id}, Size {msg.size} \\n"\n'
        for key, f in msg.fields.items():
            result += f'        out += f"{key} = '
            result += '{self.' + key + '}\\n"\n'
        for oneof_name, oneof in msg.oneofs.items():
            result += f'        out += f"{oneof_name} = '
            result += '{self.' + oneof_name + '}\\n"\n'
        result += f'        out += "\\n"\n'
        result += f'        return out'

        # Generate to_dict method
        result += '\n\n    def to_dict(self, include_name = True, include_id = True):\n'
        result += '        out = {}\n'
        for key, f in msg.fields.items():
            if f.is_array:
                if f.isDefaultType or f.isEnum or f.fieldType == "string":
                    result += f'        out["{key}"] = self.{key}\n'
                else:
                    result += f'        out["{key}"] = [item.to_dict(False, False) for item in self.{key}]\n'
            elif f.isDefaultType or f.isEnum or f.fieldType == "string":
                result += f'        out["{key}"] = self.{key}\n'
            else:
                if getattr(f, 'flatten', False):
                    result += f'        out.update(self.{key}.to_dict(False, False))\n'
                else:
                    result += f'        out["{key}"] = self.{key}.to_dict(False, False)\n'
        
        # Add oneofs to dict
        for oneof_name, oneof in msg.oneofs.items():
            result += f'        if self.{oneof_name}_which:\n'
            result += f'            out["{oneof_name}"] = self.{oneof_name}[self.{oneof_name}_which].to_dict(False, False)\n'
        
        result += '        if include_name:\n'
        result += f'            out["name"] = "{msg.name}"\n'
        result += '        if include_id:\n'
        result += f'            out["msg_id"] = "{msg.id}"\n'
        result += '        return out\n'

        # Generate __eq__ method if requested
        if equality:
            result += MessagePyGen.generate_eq_method(msg, structName)

        # Generate variable message methods if this is a variable message
        if msg.variable:
            result += MessagePyGen.generate_variable_methods(msg)
        
        # Add unified unpack() method for messages with MSG_ID
        if msg.id is not None:
            result += MessagePyGen.generate_unified_unpack(msg)
        
        # Add envelope methods if this is an envelope message
        if msg.is_envelope:
            result += MessagePyGen.generate_envelope_methods(msg, structName)

        return result
    
    @staticmethod
    def generate_unified_unpack(msg):
        """Generate unified deserialize() method that works for both variable and non-variable messages."""
        result = ''
        
        result += '\n    @classmethod\n'
        result += '    def deserialize(cls, data: bytes):\n'
        result += '        """Deserialize message from binary data.\n'
        result += '        Works for both variable and non-variable messages.\n'
        result += '        For variable messages with minimal profiles (len(data) == MAX_SIZE),\n'
        result += '        uses fixed-size deserialization instead of variable-length deserialization.\n'
        result += '        """\n'
        
        if msg.variable:
            result += '        # Variable message - check encoding format\n'
            result += '        if len(data) == cls.MAX_SIZE:\n'
            result += '            # Minimal profile format (MAX_SIZE encoding)\n'
            result += '            return cls._deserialize_fixed(data)\n'
            result += '        else:\n'
            result += '            # Variable-length format\n'
            result += '            return cls._deserialize_variable(data)\n'
        else:
            result += '        # Fixed-size message - use standard deserialization\n'
            result += '        return cls._deserialize_fixed(data)\n'
        
        # Add convenience overload for FrameMsgInfo
        result += '\n    @classmethod\n'
        result += '    def deserialize(cls, data):\n'
        result += '        """Deserialize message from binary data or FrameMsgInfo.\n'
        result += '        \n'
        result += '        Args:\n'
        result += '            data: Either bytes to deserialize, or FrameMsgInfo from frame parser\n'
        result += '        \n'
        result += '        Returns:\n'
        result += '            Deserialized message instance\n'
        result += '        """\n'
        result += '        # Check if data is FrameMsgInfo (duck typing - has msg_data attribute)\n'
        result += '        if hasattr(data, "msg_data"):\n'
        result += '            data = data.msg_data\n'
        result += '        \n'
        
        if msg.variable:
            result += '        # Variable message - check encoding format\n'
            result += '        if len(data) == cls.MAX_SIZE:\n'
            result += '            # Minimal profile format (MAX_SIZE encoding)\n'
            result += '            return cls._deserialize_fixed(data)\n'
            result += '        else:\n'
            result += '            # Variable-length format\n'
            result += '            return cls._deserialize_variable(data)\n'
        else:
            result += '        # Fixed-size message - use standard deserialization\n'
            result += '        return cls._deserialize_fixed(data)\n'
        
        return result
    
    @staticmethod
    def generate_variable_methods(msg):
        """Generate pack_size, pack_variable, and unpack_variable methods for variable messages."""
        result = ''
        
        # Add IS_VARIABLE constant
        result += '\n    IS_VARIABLE = True\n'
        
        # Generate serialized_size method
        result += '\n    def serialized_size(self) -> int:\n'
        result += '        """Calculate the serialized size using variable-length encoding."""\n'
        result += '        size = 0\n'
        
        for key, f in msg.fields.items():
            if f.is_array and f.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if f.fieldType == "string":
                    element_size = f.element_size if f.element_size else 1
                else:
                    element_size = type_sizes.get(f.fieldType, (f.size - 1) // f.max_size)
                result += f'        size += 1 + (min(len(self.{f.name}), {f.max_size}) * {element_size})  # {f.name}\n'
            elif f.fieldType == "string" and f.max_size is not None:
                # Variable string
                result += f'        size += 1 + min(len(self.{f.name}), {f.max_size})  # {f.name}\n'
            else:
                result += f'        size += {f.size}  # {f.name}\n'
        
        result += '        return size\n'
        
        # Generate _serialize_variable method (internal method)
        result += '\n    def _serialize_variable(self) -> bytes:\n'
        result += '        """Serialize message using variable-length encoding (only serializes used bytes)."""\n'
        result += '        data = b""\n'
        
        for key, f in msg.fields.items():
            if f.is_array and f.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if f.fieldType == "string":
                    element_size = f.element_size if f.element_size else 1
                    result += f'        # {f.name}: variable string array\n'
                    result += f'        count = min(len(self.{f.name}), {f.max_size})\n'
                    result += f'        data += struct.pack("<B", count)\n'
                    result += f'        for i in range(count):\n'
                    result += f'            data += struct.pack("<{element_size}s", self.{f.name}[i][:{element_size}])\n'
                elif f.isEnum:
                    result += f'        # {f.name}: variable enum array\n'
                    result += f'        count = min(len(self.{f.name}), {f.max_size})\n'
                    result += f'        data += struct.pack("<B", count)\n'
                    result += f'        for i in range(count):\n'
                    result += f'            data += struct.pack("<B", int(self.{f.name}[i]))\n'
                elif f.fieldType in type_sizes:
                    element_size = type_sizes[f.fieldType]
                    fmt = py_struct_format.get(f.fieldType, 'B')
                    result += f'        # {f.name}: variable {f.fieldType} array\n'
                    result += f'        count = min(len(self.{f.name}), {f.max_size})\n'
                    result += f'        data += struct.pack("<B", count)\n'
                    result += f'        for i in range(count):\n'
                    result += f'            data += struct.pack("<{fmt}", self.{f.name}[i])\n'
                else:
                    # Nested message array
                    result += f'        # {f.name}: variable nested message array\n'
                    result += f'        count = min(len(self.{f.name}), {f.max_size})\n'
                    result += f'        data += struct.pack("<B", count)\n'
                    result += f'        for i in range(count):\n'
                    result += f'            data += self.{f.name}[i].serialize()\n'
            elif f.fieldType == "string" and f.max_size is not None:
                # Variable string
                result += f'        # {f.name}: variable string\n'
                result += f'        str_data = self.{f.name}[:{f.max_size}]\n'
                result += f'        data += struct.pack("<B", len(str_data))\n'
                result += f'        data += str_data\n'
            elif f.fieldType == "string" and f.size_option is not None:
                # Fixed string
                result += f'        # {f.name}: fixed string\n'
                result += f'        data += struct.pack("<{f.size_option}s", self.{f.name}[:{f.size_option}])\n'
            elif f.is_array and f.size_option is not None:
                # Fixed array (pack as usual)
                if f.isEnum:
                    result += f'        # {f.name}: fixed enum array\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            val = self.{f.name}[i] if i < len(self.{f.name}) else 0\n'
                    result += f'            data += struct.pack("<B", int(val))\n'
                elif f.fieldType in py_struct_format:
                    fmt = py_struct_format[f.fieldType]
                    result += f'        # {f.name}: fixed {f.fieldType} array\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            val = self.{f.name}[i] if i < len(self.{f.name}) else 0\n'
                    result += f'            data += struct.pack("<{fmt}", val)\n'
                else:
                    # Nested message fixed array
                    type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                    result += f'        # {f.name}: fixed nested message array\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            if i < len(self.{f.name}):\n'
                    result += f'                data += self.{f.name}[i].serialize()\n'
                    result += f'            else:\n'
                    result += f'                data += {type_name}().serialize()\n'
            elif f.fieldType in py_struct_format:
                fmt = py_struct_format[f.fieldType]
                result += f'        # {f.name}: {f.fieldType}\n'
                result += f'        data += struct.pack("<{fmt}", self.{f.name})\n'
            elif f.isEnum:
                result += f'        # {f.name}: enum\n'
                result += f'        data += struct.pack("<B", int(self.{f.name}))\n'
            else:
                # Nested message
                result += f'        # {f.name}: nested message\n'
                result += f'        data += self.{f.name}.serialize()\n'
        
        result += '        return data\n'
        
        # Generate _deserialize_variable class method (internal method)
        result += '\n    @classmethod\n'
        result += '    def _deserialize_variable(cls, data: bytes):\n'
        result += '        """Deserialize message using variable-length encoding."""\n'
        result += '        offset = 0\n'
        result += '        fields = {}\n'
        
        for key, f in msg.fields.items():
            if f.is_array and f.max_size is not None:
                # Variable array
                type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                if f.fieldType == "string":
                    element_size = f.element_size if f.element_size else 1
                    result += f'        # {f.name}: variable string array\n'
                    result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range(min(count, {f.max_size})):\n'
                    result += f'            s = struct.unpack_from("<{element_size}s", data, offset)[0]\n'
                    result += f'            fields["{f.name}"].append(s)\n'
                    result += f'            offset += {element_size}\n'
                elif f.isEnum:
                    result += f'        # {f.name}: variable enum array\n'
                    result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range(min(count, {f.max_size})):\n'
                    result += f'            val = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'            offset += 1\n'
                    result += f'            fields["{f.name}"].append(val)\n'
                elif f.fieldType in type_sizes:
                    element_size = type_sizes[f.fieldType]
                    fmt = py_struct_format.get(f.fieldType, 'B')
                    result += f'        # {f.name}: variable {f.fieldType} array\n'
                    result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range(min(count, {f.max_size})):\n'
                    result += f'            val = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                    result += f'            offset += {element_size}\n'
                    result += f'            fields["{f.name}"].append(val)\n'
                else:
                    # Nested message array
                    type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                    element_size = (f.size - 1) // f.max_size
                    result += f'        # {f.name}: variable nested message array\n'
                    result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range(min(count, {f.max_size})):\n'
                    result += f'            msg = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.MAX_SIZE])\n'
                    result += f'            fields["{f.name}"].append(msg)\n'
                    result += f'            offset += {type_name}.MAX_SIZE\n'
            elif f.fieldType == "string" and f.max_size is not None:
                # Variable string
                result += f'        # {f.name}: variable string\n'
                result += f'        str_len = struct.unpack_from("<B", data, offset)[0]\n'
                result += f'        offset += 1\n'
                result += f'        str_len = min(str_len, {f.max_size})\n'
                result += f'        fields["{f.name}"] = data[offset:offset+str_len]\n'
                result += f'        offset += str_len\n'
            elif f.fieldType == "string" and f.size_option is not None:
                # Fixed string
                result += f'        # {f.name}: fixed string\n'
                result += f'        fields["{f.name}"] = struct.unpack_from("<{f.size_option}s", data, offset)[0]\n'
                result += f'        offset += {f.size_option}\n'
            elif f.is_array and f.size_option is not None:
                # Fixed array
                if f.isEnum:
                    result += f'        # {f.name}: fixed enum array\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            val = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'            offset += 1\n'
                    result += f'            fields["{f.name}"].append(val)\n'
                elif f.fieldType in py_struct_format:
                    fmt = py_struct_format[f.fieldType]
                    size = struct_format_sizes[fmt]
                    result += f'        # {f.name}: fixed {f.fieldType} array\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            val = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                    result += f'            offset += {size}\n'
                    result += f'            fields["{f.name}"].append(val)\n'
                else:
                    # Nested message fixed array
                    type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                    result += f'        # {f.name}: fixed nested message array\n'
                    result += f'        fields["{f.name}"] = []\n'
                    result += f'        for i in range({f.size_option}):\n'
                    result += f'            msg = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.MAX_SIZE])\n'
                    result += f'            fields["{f.name}"].append(msg)\n'
                    result += f'            offset += {type_name}.MAX_SIZE\n'
            elif f.fieldType in py_struct_format:
                fmt = py_struct_format[f.fieldType]
                size = struct_format_sizes[fmt]
                result += f'        # {f.name}: {f.fieldType}\n'
                result += f'        fields["{f.name}"] = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                result += f'        offset += {size}\n'
            elif f.isEnum:
                result += f'        # {f.name}: enum\n'
                result += f'        fields["{f.name}"] = struct.unpack_from("<B", data, offset)[0]\n'
                result += f'        offset += 1\n'
            else:
                # Nested message
                type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                result += f'        # {f.name}: nested message\n'
                result += f'        fields["{f.name}"] = {type_name}._deserialize_fixed(data[offset:offset+{type_name}.MAX_SIZE])\n'
                result += f'        offset += {type_name}.MAX_SIZE\n'
        
        result += '        return cls(**fields)\n'
        
        return result
    
    @staticmethod
    def generate_envelope_methods(msg, structName):
        """Generate envelope-specific helper methods for wrapping inner messages."""
        result = ''
        
        # Get the single oneof (validation ensures exactly one exists)
        oneof_name = list(msg.oneofs.keys())[0]
        oneof = msg.oneofs[oneof_name]
        
        result += '\n    # ========================================\n'
        result += '    # Envelope message helper methods\n'
        result += '    # ========================================\n'
        
        # Build list of valid payload types and their field mappings (with field order)
        payload_types = []
        payload_field_map = []
        for idx, (field_name, field) in enumerate(oneof.fields.items()):
            type_pkg = field.type_package if field.type_package else field.package
            payload_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
            payload_types.append(f'"{payload_type}"')
            payload_field_map.append((payload_type, field_name, idx + 1))  # 1-based index
        
        # Build union type hint for payload parameter
        union_type = f'Union[{", ".join(payload_types)}]'
        
        # Generate parameter list for envelope fields (non-oneof fields)
        field_params = []
        field_inits = []
        for f_name, f in msg.fields.items():
            type_hint = FieldPyGen.get_type_hint(f)
            if f.is_array or f.fieldType == "string":
                field_params.append(f'{f.name}: {type_hint} = None')
            else:
                field_params.append(f'{f.name}: {type_hint}')
            field_inits.append(f'            {f.name}={f.name}')
        
        # Build parameter list: payload first, then envelope fields
        all_params = [f'payload: {union_type}'] + field_params
        
        # Generate class-level constant for valid payload types
        result += f'\n    # Valid payload types for this envelope\n'
        result += f'    _VALID_PAYLOAD_TYPES = ({", ".join(payload_types)},)\n'
        
        # Build cleaned payload type names for docstring (without quotes)
        payload_type_names = [pt.strip('"') for pt in payload_types]
        
        result += f'\n    @classmethod\n'
        result += f'    def wrap(cls, {", ".join(all_params)}) -> "{structName}":\n'
        result += f'        """Create a {structName} envelope wrapping a payload message.\n'
        result += f'        \n'
        result += f'        Args:\n'
        result += f'            payload: The message to wrap (must be one of: {", ".join(payload_type_names)})\n'
        for f_name, f in msg.fields.items():
            result += f'            {f.name}: Envelope field value\n'
        result += f'        \n'
        result += f'        Returns:\n'
        result += f'            A fully initialized {structName} envelope\n'
        result += f'        \n'
        result += f'        Raises:\n'
        result += f'            TypeError: If payload is not a valid payload type\n'
        result += f'        """\n'
        
        # Runtime type check
        result += f'        payload_type_name = type(payload).__name__\n'
        result += f'        if payload_type_name not in cls._VALID_PAYLOAD_TYPES:\n'
        result += f'            raise TypeError(f"Invalid payload type {{payload_type_name}}. Must be one of: {{cls._VALID_PAYLOAD_TYPES}}")\n'
        result += f'        \n'
        
        # Determine field name and field_order based on payload type
        if oneof.discriminator_type == "msgid":
            result += f'        # Determine which oneof field to use based on MSG_ID\n'
            for payload_type, field_name, field_order in payload_field_map:
                result += f'        if payload.MSG_ID == {payload_type}.MSG_ID:\n'
                result += f'            field_name = "{field_name}"\n'
        else:  # field_order
            enum_name = EnumPyGen.get_discriminator_enum_name(oneof, structName)
            result += f'        # Determine which oneof field to use and its discriminator value\n'
            first = True
            for payload_type, field_name, field_order in payload_field_map:
                enum_value = CamelToSnakeCase(field_name).upper()
                if first:
                    result += f'        if payload_type_name == "{payload_type}":\n'
                    first = False
                else:
                    result += f'        elif payload_type_name == "{payload_type}":\n'
                result += f'            field_name = "{field_name}"\n'
                result += f'            discriminator_value = {enum_name}.{enum_value}\n'
        
        # Create envelope instance
        result += f'        \n'
        result += f'        envelope = cls(\n'
        for init_line in field_inits:
            result += f'{init_line},\n'
        result += f'            {oneof_name}={{field_name: payload}},\n'
        result += f'            {oneof_name}_which=field_name'
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                result += f',\n            {oneof_name}_discriminator=payload.MSG_ID'
            else:  # field_order - use the enum value
                result += f',\n            {oneof_name}_discriminator=discriminator_value'
        result += f'\n        )\n'
        result += f'        return envelope\n'
        
        # Generate single unwrap method that returns the correct message based on discriminator
        if oneof.auto_discriminator:
            # Build union type hint for return type
            payload_types_for_hint = []
            for field_name, field in oneof.fields.items():
                type_pkg = field.type_package if field.type_package else field.package
                payload_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                payload_types_for_hint.append(f'"{payload_type}"')
            union_type = f'Union[{", ".join(payload_types_for_hint)}, None]'
            
            result += f'\n    def unwrap(self) -> {union_type}:\n'
            result += f'        """Unwrap and get the payload message based on the discriminator.\n'
            result += f'        \n'
            result += f'        Returns:\n'
            result += f'            The payload message matching the discriminator, or None if not set\n'
            result += f'        """\n'
            
            # Generate if/elif chain to check discriminator and return correct field
            first = True
            enum_name = EnumPyGen.get_discriminator_enum_name(oneof, structName) if oneof.discriminator_type == "field_order" else None
            for idx, (field_name, field) in enumerate(oneof.fields.items()):
                type_pkg = field.type_package if field.type_package else field.package
                payload_type = '%s%s' % (pascalCase(type_pkg), field.fieldType)
                field_order = idx + 1
                
                if oneof.discriminator_type == "msgid":
                    discriminator_check = f'{payload_type}.MSG_ID'
                else:  # field_order - use enum
                    enum_value = CamelToSnakeCase(field_name).upper()
                    discriminator_check = f'{enum_name}.{enum_value}'
                
                if first:
                    result += f'        if self.{oneof_name}_discriminator == {discriminator_check}:\n'
                    first = False
                else:
                    result += f'        elif self.{oneof_name}_discriminator == {discriminator_check}:\n'
                result += f'            return self.{oneof_name}.get("{field_name}")\n'
            result += f'        return None\n'
        
        # Generate helper to get the discriminator value
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                result += f'\n    def get_payload_message_id(self) -> int:\n'
                result += f'        """Get the message ID of the wrapped payload.\n'
                result += f'        \n'
                result += f'        Returns:\n'
                result += f'            The message ID of the payload in the {oneof_name} union\n'
                result += f'        """\n'
                result += f'        return self.{oneof_name}_discriminator\n'
            else:  # field_order
                enum_name = EnumPyGen.get_discriminator_enum_name(oneof, structName)
                result += f'\n    def get_payload_field(self) -> "{enum_name}":\n'
                result += f'        """Get the discriminator enum value for the wrapped payload.\n'
                result += f'        \n'
                result += f'        Returns:\n'
                result += f'            The {enum_name} enum value for the active payload\n'
                result += f'        """\n'
                result += f'        return self.{oneof_name}_discriminator\n'
        
        return result


class FilePyGen():
    @staticmethod
    def generate(package, equality=False):
        yield '# Automatically generated struct frame header \n'
        yield '# Generated by %s at %s. \n\n' % (version, time.asctime())

        yield 'import struct\n'
        yield 'from enum import Enum\n'
        yield 'from typing import List, Union\n'
        yield '\n'
        yield '# Helper function to truncate float64 to float32 precision\n'
        yield 'def _truncate_float32(val: float) -> float:\n'
        yield '    """Truncate a Python float (float64) to float32 precision"""\n'
        yield '    return struct.unpack("<f", struct.pack("<f", val))[0]\n\n'

        # Add package ID constant if present
        if package.package_id is not None:
            yield f'# Package ID for extended message IDs\n'
            yield f'PACKAGE_ID = {package.package_id}\n\n'

        if package.enums:
            yield '# Enum definitions\n'
            for key, enum in package.enums.items():
                yield EnumPyGen.generate(enum) + '\n\n'

        # Generate discriminator enums for field_order oneofs (must come before message definitions)
        has_discriminator_enums = False
        for key, msg in package.messages.items():
            structName = '%s%s' % (pascalCase(msg.package), msg.name)
            for oneof_name, oneof in msg.oneofs.items():
                enum_code = EnumPyGen.generate_discriminator_enum(oneof, structName)
                if enum_code:
                    if not has_discriminator_enums:
                        yield '# Oneof discriminator enums\n'
                        has_discriminator_enums = True
                    yield enum_code + '\n'

        if package.messages:
            yield '# Message definitions \n'
            # Need to sort messages to make sure dependencies are properly met
            for key, msg in package.sortedMessages().items():
                yield MessagePyGen.generate(msg, equality) + '\n'
            yield '\n'

        if package.messages:
            if package.package_id is not None:
                # When using package ID, use 16-bit message IDs
                yield f'# Message definitions dictionary with package ID support\n'
                yield f'# Format: (package_id << 8) | msg_id => Message class\n'
                yield '%s_definitions = {\n' % package.name
                for key, msg in package.sortedMessages().items():
                    if msg.id != None:
                        structName = '%s%s' % (pascalCase(msg.package), msg.name)
                        # Encode package ID in upper byte
                        encoded_id = (package.package_id << 8) | msg.id
                        yield f'    {encoded_id}: {structName},  # pkg_id={package.package_id}, msg_id={msg.id}\n'
                yield '}\n\n'
                
                # Add helper function to get message class
                yield f'def get_message_class(msg_id: int):\n'
                yield f'    """Get message class from 16-bit message ID (package_id << 8 | msg_id)"""\n'
                yield f'    return {package.name}_definitions.get(msg_id)\n\n'
                
                yield f'def get_message_size(msg_id: int) -> int:\n'
                yield f'    """Get message size from 16-bit message ID"""\n'
                yield f'    msg_class = get_message_class(msg_id)\n'
                yield f'    return msg_class.msg_size if msg_class else 0\n\n'
                
                yield f'# Alias for minimal frame parsing compatibility\n'
                yield f'get_msg_length = get_message_size\n\n'
                
                # Add unified get_message_info function
                yield f'def get_message_info(msg_id: int):\n'
                yield f'    """\n'
                yield f'    Get unified message info (size and magic numbers) for a 16-bit message ID.\n'
                yield f'    \n'
                yield f'    Args:\n'
                yield f'        msg_id: 16-bit message ID (pkg_id << 8 | local_msg_id)\n'
                yield f'    \n'
                yield f'    Returns:\n'
                yield f'        MessageInfo(size, magic1, magic2) or None if message not found\n'
                yield f'    """\n'
                yield f'    from frame_profiles import MessageInfo\n'
                yield f'    msg_class = get_message_class(msg_id)\n'
                yield f'    if not msg_class:\n'
                yield f'        return None\n'
                yield f'    magic1 = getattr(msg_class, "MAGIC1", 0)\n'
                yield f'    magic2 = getattr(msg_class, "MAGIC2", 0)\n'
                yield f'    return MessageInfo(size=msg_class.msg_size, magic1=magic1, magic2=magic2)\n'
            else:
                # Flat namespace mode: 8-bit message ID
                yield '%s_definitions = {\n' % package.name
                for key, msg in package.sortedMessages().items():
                    if msg.id != None:
                        structName = '%s%s' % (pascalCase(msg.package), msg.name)
                        yield '    %s: %s,\n' % (msg.id, structName)
                yield '}\n\n'
                
                # Add helper functions for message lookup and size
                yield f'def get_message_class(msg_id: int):\n'
                yield f'    """Get message class from message ID"""\n'
                yield f'    return {package.name}_definitions.get(msg_id)\n\n'
                
                yield f'def get_msg_length(msg_id: int) -> int:\n'
                yield f'    """Get message size from message ID (for minimal frame parsing)"""\n'
                yield f'    msg_class = get_message_class(msg_id)\n'
                yield f'    return msg_class.msg_size if msg_class else 0\n\n'
                
                # Add unified get_message_info function
                yield f'def get_message_info(msg_id: int):\n'
                yield f'    """\n'
                yield f'    Get unified message info (size and magic numbers) for a message ID.\n'
                yield f'    \n'
                yield f'    Args:\n'
                yield f'        msg_id: Message ID\n'
                yield f'    \n'
                yield f'    Returns:\n'
                yield f'        MessageInfo(size, magic1, magic2) or None if message not found\n'
                yield f'    """\n'
                yield f'    from frame_profiles import MessageInfo\n'
                yield f'    msg_class = get_message_class(msg_id)\n'
                yield f'    if not msg_class:\n'
                yield f'        return None\n'
                yield f'    magic1 = getattr(msg_class, "MAGIC1", 0)\n'
                yield f'    magic2 = getattr(msg_class, "MAGIC2", 0)\n'
                yield f'    return MessageInfo(size=msg_class.msg_size, magic1=magic1, magic2=magic2)\n'


class TestPyGen():
    """Generator for Python test code with dummy values for round-trip verification."""
    
    @staticmethod
    def _get_dummy_value(field, index=0):
        """Generate a dummy value for a field based on its type."""
        type_name = field.fieldType
        
        # Basic type dummy values
        type_values = {
            "uint8": str((42 + index) % 256),
            "int8": str((42 + index) % 128),
            "uint16": str(1000 + index),
            "int16": str(500 + index),
            "uint32": str(123456 + index),
            "int32": str(123456 + index),
            "uint64": str(9876543210 + index),
            "int64": str(9876543210 + index),
            "float": str(3.14159 + index),
            "double": str(2.718281828 + index),
            "bool": "True" if index % 2 == 0 else "False",
        }
        
        if type_name in type_values:
            return type_values[type_name]
        elif type_name == "string":
            return f'b"test_{index}"'
        elif field.isEnum:
            # Return 0 as a safe default for enums
            return "0"
        else:
            # Nested struct
            nested_struct_name = f'{pascalCase(field.package)}{type_name}'
            return f'{nested_struct_name}()'
    
    @staticmethod
    def _generate_field_init(field, prefix="msg", index=0):
        """Generate initialization code for a field."""
        var_name = field.name
        type_name = field.fieldType
        result = ""
        
        # Handle arrays
        if field.is_array:
            if field.size_option is not None:
                # Fixed array
                for i in range(min(field.size_option, 3)):
                    if type_name == "string":
                        result += f'    {prefix}.{var_name}[{i}] = b"test_{i}"\n'
                    else:
                        result += f"    {prefix}.{var_name}[{i}] = {TestPyGen._get_dummy_value(field, i)}\n"
            elif field.max_size is not None:
                # Variable array
                num_elements = min(field.max_size, 3)
                result += f"    {prefix}.{var_name} = []\n"
                for i in range(num_elements):
                    if type_name == "string":
                        result += f'    {prefix}.{var_name}.append(b"test_{i}")\n'
                    else:
                        result += f"    {prefix}.{var_name}.append({TestPyGen._get_dummy_value(field, i)})\n"
        # Handle regular strings
        elif type_name == "string":
            result += f'    {prefix}.{var_name} = b"test_string"\n'
        else:
            # Regular field
            result += f"    {prefix}.{var_name} = {TestPyGen._get_dummy_value(field, index)}\n"
        
        return result
    
    @staticmethod
    def generate(package):
        """Generate test code for all messages in a package."""
        yield '"""\n'
        yield 'Automatically generated test code for struct-frame messages.\n'
        yield 'This file provides round-trip encode/decode verification tests.\n'
        yield f'Generated by {version} at {time.asctime()}.\n'
        yield '"""\n\n'
        
        yield 'import sys\n'
        yield 'from typing import List, Tuple, Optional\n'
        yield f'from {package.name} import *\n'
        yield 'from frame_profiles import (\n'
        yield '    encode_profile_standard, parse_profile_standard,\n'
        yield '    encode_profile_sensor, parse_profile_sensor,\n'
        yield '    encode_profile_ipc, parse_profile_ipc,\n'
        yield '    encode_profile_bulk, parse_profile_bulk,\n'
        yield '    encode_profile_network, parse_profile_network,\n'
        yield ')\n\n'
        
        # Collect testable messages
        testable_messages = [(key, msg) for key, msg in package.sortedMessages().items() 
                            if msg.id is not None]
        
        # Generate message creation functions
        for key, msg in testable_messages:
            struct_name = f'{pascalCase(msg.package)}{msg.name}'
            func_name = f'create_test_{CamelToSnakeCase(msg.name)}'
            
            yield f'def {func_name}() -> {struct_name}:\n'
            yield f'    """Create a test instance of {struct_name}."""\n'
            yield f'    msg = {struct_name}()\n'
            
            # Generate field initializations (skip oneofs)
            field_index = 0
            for field_key, field in msg.fields.items():
                yield TestPyGen._generate_field_init(field, "msg", field_index)
                field_index += 1
            
            yield '    return msg\n\n'
        
        # Generate test function
        yield 'def verify_roundtrip(msg, encode_fn, parse_fn, get_info_fn) -> bool:\n'
        yield '    """Verify round-trip encode/decode for a message."""\n'
        yield '    try:\n'
        yield '        # Encode\n'
        yield '        buffer = encode_fn(msg)\n'
        yield '        if not buffer:\n'
        yield '            return False\n'
        yield '        \n'
        yield '        # Parse\n'
        yield '        result = parse_fn(buffer, get_info_fn)\n'
        yield '        if not result.valid:\n'
        yield '            return False\n'
        yield '        \n'
        yield '        # Deserialize\n'
        yield '        decoded = type(msg)()\n'
        yield '        decoded.deserialize(result.msg_data)\n'
        yield '        \n'
        yield '        # Compare bytes\n'
        yield '        return msg.serialize() == decoded.serialize()\n'
        yield '    except Exception as e:\n'
        yield '        print(f"Round-trip failed: {e}")\n'
        yield '        return False\n\n'
        
        # Generate test result class
        yield 'class TestResult:\n'
        yield '    """Test result container."""\n'
        yield '    def __init__(self, passed: bool, name: str, error: Optional[str] = None):\n'
        yield '        self.passed = passed\n'
        yield '        self.name = name\n'
        yield '        self.error = error\n\n'
        
        # Generate per-message test functions
        for key, msg in testable_messages:
            struct_name = f'{pascalCase(msg.package)}{msg.name}'
            func_name = f'test_{CamelToSnakeCase(msg.name)}'
            create_func = f'create_test_{CamelToSnakeCase(msg.name)}'
            
            yield f'def {func_name}(encode_fn, parse_fn, get_info_fn) -> TestResult:\n'
            yield f'    """Test round-trip for {struct_name}."""\n'
            yield f'    msg = {create_func}()\n'
            yield f'    passed = verify_roundtrip(msg, encode_fn, parse_fn, get_info_fn)\n'
            yield f'    return TestResult(passed, "{struct_name}", None if passed else "Round-trip failed")\n\n'
        
        # Generate run_all_tests function
        yield 'TEST_MESSAGE_COUNT = %d\n\n' % len(testable_messages)
        
        yield 'def run_all_tests(encode_fn, parse_fn, get_info_fn, verbose: bool = False) -> int:\n'
        yield '    """Run all message tests. Returns count of passed tests."""\n'
        yield '    passed = 0\n'
        yield '    results = [\n'
        for key, msg in testable_messages:
            func_name = f'test_{CamelToSnakeCase(msg.name)}'
            yield f'        {func_name}(encode_fn, parse_fn, get_info_fn),\n'
        yield '    ]\n'
        yield '    \n'
        yield '    for result in results:\n'
        yield '        if result.passed:\n'
        yield '            passed += 1\n'
        yield '            if verbose:\n'
        yield '                print(f"[PASS] {result.name}")\n'
        yield '        else:\n'
        yield '            if verbose:\n'
        yield '                print(f"[FAIL] {result.name}: {result.error}")\n'
        yield '    \n'
        yield '    if verbose:\n'
        yield '        print(f"\\nTest Results: {passed}/{TEST_MESSAGE_COUNT} passed")\n'
        yield '    \n'
        yield '    return passed\n\n'
        
        # Generate main function for standalone execution
        yield 'def run_tests_standard(verbose: bool = False) -> int:\n'
        yield '    """Run all tests with ProfileStandard."""\n'
        yield '    return run_all_tests(encode_profile_standard, parse_profile_standard, get_message_info, verbose)\n\n'
        
        yield 'if __name__ == "__main__":\n'
        yield '    verbose = "--verbose" in sys.argv or "-v" in sys.argv\n'
        yield '    passed = run_tests_standard(verbose=verbose)\n'
        yield '    print(f"Tests: {passed}/{TEST_MESSAGE_COUNT} passed")\n'
        yield '    sys.exit(0 if passed == TEST_MESSAGE_COUNT else 1)\n'
