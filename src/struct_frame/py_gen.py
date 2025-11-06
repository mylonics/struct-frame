#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase
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
        leading_comment = field.comments

        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '#%s\n' % c

        enumName = '%s%s' % (pascalCase(field.package), field.name)
        result += 'class %s(Enum):\n' % (enumName)

        enum_length = len(field.data)
        enum_values = []
        for index, (d) in enumerate(field.data):
            leading_comment = field.data[d][1]

            if leading_comment:
                for c in leading_comment:
                    enum_values.append("#" + c)

            enum_value = "    %s_%s = %d" % (CamelToSnakeCase(
                field.name).upper(), StyleC.enum_entry(d), field.data[d][0])

            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        return result


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
    def generate_pack_method(msg):
        """Generate the pack() method"""
        result = '\n    def pack(self) -> bytes:\n'
        result += '        """Pack the message into binary format"""\n'
        result += '        data = b""\n'
        
        for key, f in msg.fields.items():
            if f.fieldType == "string" and not f.is_array:
                # String field
                if f.size_option is not None:
                    # Fixed string
                    result += f'        # Fixed string: {f.name}\n'
                    result += f'        data += struct.pack("<{f.size_option}s", self.{f.name}[:{f.size_option}])\n'
                elif f.max_size is not None:
                    # Variable string with length prefix
                    result += f'        # Variable string: {f.name}\n'
                    result += f'        str_data = self.{f.name}[:{f.max_size}]\n'
                    result += f'        data += struct.pack("<B", len(str_data))\n'
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
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Bounded string array: {f.name}\n'
                        result += f'        data += struct.pack("<B", min(len(self.{f.name}), {f.max_size}))\n'
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
                            result += f'                data += self.{f.name}[i].pack()\n'
                            result += f'            else:\n'
                            result += f'                data += {type_name}().pack()\n'
                    elif f.max_size is not None:
                        # Bounded array
                        if f.isDefaultType or f.isEnum:
                            # Primitives/enums
                            result += f'        # Bounded array: {f.name}\n'
                            result += f'        data += struct.pack("<B", min(len(self.{f.name}), {f.max_size}))\n'
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
                            result += f'        data += struct.pack("<B", min(len(self.{f.name}), {f.max_size}))\n'
                            result += f'        for i in range({f.max_size}):\n'
                            result += f'            if i < len(self.{f.name}):\n'
                            result += f'                data += self.{f.name}[i].pack()\n'
                            result += f'            else:\n'
                            # Need to create empty instance
                            type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                            result += f'                data += {type_name}().pack()\n'
            else:
                # Regular field
                fmt = MessagePyGen.get_struct_format(f)
                if fmt:
                    # Simple type
                    result += f'        data += struct.pack("<{fmt}", self.{f.name})\n'
                else:
                    # Nested message
                    result += f'        data += self.{f.name}.pack()\n'
        
        result += '        return data\n'
        return result
    
    @staticmethod
    def generate_unpack_method(msg):
        """Generate the create_unpack() class method"""
        result = '\n    @classmethod\n'
        result += '    def create_unpack(cls, data: bytes):\n'
        result += '        """Unpack binary data into a message instance"""\n'
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
                    result += f'        # Variable string: {f.name}\n'
                    result += f'        str_len = struct.unpack_from("<B", data, offset)[0]\n'
                    result += f'        offset += 1\n'
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
                        element_size = f.element_size if f.element_size else 16
                        result += f'        # Bounded string array: {f.name}\n'
                        result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                        result += f'        offset += 1\n'
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
                            result += f'            msg = {type_name}.create_unpack(data[offset:offset+{type_name}.msg_size])\n'
                            result += f'            fields["{f.name}"].append(msg)\n'
                            result += f'            offset += {type_name}.msg_size\n'
                    elif f.max_size is not None:
                        # Bounded array
                        if f.isDefaultType or f.isEnum:
                            # Primitives/enums
                            result += f'        # Bounded array: {f.name}\n'
                            result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                            result += f'        offset += 1\n'
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
                            result += f'        count = struct.unpack_from("<B", data, offset)[0]\n'
                            result += f'        offset += 1\n'
                            result += f'        fields["{f.name}"] = []\n'
                            result += f'        for i in range({f.max_size}):\n'
                            result += f'            msg = {type_name}.create_unpack(data[offset:offset+{type_name}.msg_size])\n'
                            result += f'            if i < count:\n'
                            result += f'                fields["{f.name}"].append(msg)\n'
                            result += f'            offset += {type_name}.msg_size\n'
            else:
                # Regular field
                fmt = MessagePyGen.get_struct_format(f)
                if fmt:
                    # Simple type
                    size = struct_format_sizes.get(fmt, 0)
                    if f.fieldType == "string":
                        result += f'        fields["{f.name}"] = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                    else:
                        result += f'        fields["{f.name}"] = struct.unpack_from("<{fmt}", data, offset)[0]\n'
                    result += f'        offset += {size}\n'
                else:
                    # Nested message
                    type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                    result += f'        fields["{f.name}"] = {type_name}.create_unpack(data[offset:offset+{type_name}.msg_size])\n'
                    result += f'        offset += {type_name}.msg_size\n'
        
        result += '        return cls(**fields)\n'
        return result
    
    @staticmethod
    def generate(msg):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '#%s\n' % c

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        result += 'class %s:\n' % structName
        result += '    msg_size = %s\n' % msg.size
        if msg.id != None:
            result += '    msg_id = %s\n' % msg.id
        result += '\n'

        # Generate __init__ method
        result += '    def __init__(self'
        init_params = []
        for key, f in msg.fields.items():
            type_hint = FieldPyGen.get_type_hint(f)
            init_params.append(f'{f.name}: {type_hint} = None')
        
        if init_params:
            result += ', ' + ', '.join(init_params)
        result += '):\n'
        
        for key, f in msg.fields.items():
            # Initialize with defaults
            if f.is_array:
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else []\n'
            elif f.fieldType == "string":
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else b""\n'
            elif f.fieldType in py_type_hints:
                if f.fieldType == "bool":
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else False\n'
                elif "float" in f.fieldType or "double" in f.fieldType:
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0.0\n'
                else:
                    result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0\n'
            elif f.isEnum:
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else 0\n'
            else:
                # Nested message
                type_name = '%s%s' % (pascalCase(f.package), f.fieldType)
                result += f'        self.{f.name} = {f.name} if {f.name} is not None else {type_name}()\n'

        # Generate pack method
        result += MessagePyGen.generate_pack_method(msg)

        # Generate unpack method
        result += MessagePyGen.generate_unpack_method(msg)

        # Generate __str__ method
        result += '\n    def __str__(self):\n'
        result += f'        out = "{msg.name} Msg, ID {msg.id}, Size {msg.size} \\n"\n'
        for key, f in msg.fields.items():
            result += f'        out += f"{key} = '
            result += '{self.' + key + '}\\n"\n'
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
        result += '        if include_name:\n'
        result += f'            out["name"] = "{msg.name}"\n'
        result += '        if include_id:\n'
        result += f'            out["msg_id"] = "{msg.id}"\n'
        result += '        return out\n'

        return result


class FilePyGen():
    @staticmethod
    def generate(package):
        yield '# Automatically generated struct frame header \n'
        yield '# Generated by %s at %s. \n\n' % (version, time.asctime())

        yield 'import struct\n'
        yield 'from enum import Enum\n'
        yield 'from typing import List, Optional\n\n'

        if package.enums:
            yield '# Enum definitions\n'
            for key, enum in package.enums.items():
                yield EnumPyGen.generate(enum) + '\n\n'

        if package.messages:
            yield '# Message definitions \n'
            # Need to sort messages to make sure dependencies are properly met
            for key, msg in package.sortedMessages().items():
                yield MessagePyGen.generate(msg) + '\n'
            yield '\n'

        if package.messages:
            yield '%s_definitions = {\n' % package.name
            for key, msg in package.sortedMessages().items():
                if msg.id != None:
                    structName = '%s%s' % (pascalCase(msg.package), msg.name)
                    yield '    %s: %s,\n' % (msg.id, structName)
            yield '}\n'
