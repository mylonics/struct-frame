#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase
import time

StyleC = NamingStyleC()

py_types = {"uint8": "uint8",
            "int8": "int8",
            "uint16": "uint16",
            "int16": "int16",
            "uint32": "uint32",
            "int32": "int32",
            "bool": "bool8",
            "float": "float32",
            "double": "float64",
            "uint64": 'uint64',
            "int64":  'int64',
            "string": "str",  # Add string type support
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
    def generate(field):
        result = ''

        var_name = field.name
        type_name = field.fieldType

        # Handle basic type resolution
        if type_name in py_types:
            base_type = py_types[type_name]
        else:
            if field.isEnum:
                # For enums, use uint8 as the serialization type (enums are stored as uint8)
                # but keep the enum class name for documentation
                base_type = 'uint8'
                enum_class_name = '%s%s' % (pascalCase(field.package), type_name)
            else:
                base_type = '%s%s' % (pascalCase(field.package), type_name)

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                # String arrays use char arrays
                if field.size_option is not None:
                    # Fixed string array: char[array_size][string_size]
                    element_size = field.element_size if field.element_size else 16
                    # Use Annotated with StaticStructArraySerializer for array of char arrays
                    type_annotation = f"Annotated[list[bytes], StaticStructArraySerializer({field.size_option}, typing.get_args(char[{element_size}])[1])]  # Fixed string array: {field.size_option} strings, each {element_size} chars"
                elif field.max_size is not None:
                    # Bounded string array - use nested struct
                    type_annotation = f"_BoundedStringArray_{var_name}"
                else:
                    type_annotation = f"list[{base_type}]  # String array (unbounded)"
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array: Use StaticStructArraySerializer
                    if field.isEnum or field.isDefaultType:
                        # For enums and primitives, use Annotated with StaticStructArraySerializer
                        # For enums, they're stored as uint8
                        serializer_type = 'uint8' if field.isEnum else base_type
                        if field.isEnum:
                            type_annotation = f"Annotated[list, StaticStructArraySerializer({field.size_option}, typing.get_args(uint8)[1])]  # Fixed array of {enum_class_name}: {field.size_option} elements"
                        else:
                            type_annotation = f"Annotated[list, StaticStructArraySerializer({field.size_option}, typing.get_args({base_type})[1])]  # Fixed array: {field.size_option} elements"
                    else:
                        # For nested structs, we need to inline them (arrays of structs not directly supported)
                        # Mark this for special handling in MessagePyGen
                        type_annotation = f"_INLINE_STRUCT_ARRAY_{base_type}_{field.size_option}"
                elif field.max_size is not None:
                    # Bounded array - use nested struct
                    type_annotation = f"_BoundedArray_{var_name}"
                else:
                    type_annotation = f"list[{base_type}]  # Array (unbounded)"
        # Handle strings with size info
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string - use char array (this works natively in structured library)
                type_annotation = f"char[{field.size_option}]  # Fixed string: {field.size_option} chars"
            elif field.max_size is not None:
                # Variable string - needs a nested struct with length prefix (like C)
                type_annotation = f"_VariableString_{var_name}"
            else:
                # Fallback (shouldn't happen with validation)
                type_annotation = "str  # String (unbounded)"
        else:
            # Regular field
            if field.isEnum:
                # For enum fields, add comment about the enum type
                type_annotation = f"{base_type}  # Enum: {enum_class_name}"
            else:
                type_annotation = base_type

        result += '    %s: %s' % (var_name, type_annotation)

        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = "#" + c + "\n" + result

        return result


class MessagePyGen():
    @staticmethod
    def generate_variable_string_struct(field, msg_name):
        """Generate a nested struct for variable-size strings"""
        var_name = field.name
        struct_name = f"_VariableString_{var_name}"
        max_size = field.max_size
        
        result = f'class {struct_name}(Structured, byte_order=ByteOrder.LE, byte_order_mode=ByteOrderMode.OVERRIDE):\n'
        result += f'    length: uint8  # Actual length of the string\n'
        result += f'    data: char[{max_size}]  # String data (null-padded)\n'
        
        return result + '\n'
    
    @staticmethod
    def generate_bounded_array_struct(field, msg_name):
        """Generate a nested struct for bounded/variable arrays"""
        var_name = field.name
        type_name = field.fieldType
        
        # Determine the base type
        if type_name in py_types:
            base_type = py_types[type_name]
        else:
            if field.isEnum:
                base_type = '%s%s' % (pascalCase(field.package), type_name)
            else:
                base_type = '%s%s' % (pascalCase(field.package), type_name)
        
        if field.fieldType == "string":
            # Bounded string array
            struct_name = f"_BoundedStringArray_{var_name}"
            element_size = field.element_size if field.element_size else 16
            result = f'class {struct_name}(Structured, byte_order=ByteOrder.LE, byte_order_mode=ByteOrderMode.OVERRIDE):\n'
            result += f'    count: uint8\n'
            result += f'    data: Annotated[list[bytes], StaticStructArraySerializer({field.max_size}, typing.get_args(char[{element_size}])[1])]\n'
        else:
            # Bounded numeric/enum/struct array
            struct_name = f"_BoundedArray_{var_name}"
            result = f'class {struct_name}(Structured, byte_order=ByteOrder.LE, byte_order_mode=ByteOrderMode.OVERRIDE):\n'
            result += f'    count: uint8\n'
            
            if field.isEnum or field.isDefaultType:
                # For enums and primitives
                serializer_type = 'uint8' if field.isEnum else base_type
                result += f'    data: Annotated[list, StaticStructArraySerializer({field.max_size}, typing.get_args({serializer_type})[1])]\n'
            else:
                # For nested structs, inline them
                # Since we can't easily create arrays of Structured objects, we inline the fields
                for i in range(field.max_size):
                    result += f'    item{i}: {base_type}\n'
        
        return result + '\n'
    
    @staticmethod
    def generate(msg):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '#%s\n' % c

        # First, generate nested structs for variable strings and bounded arrays
        for key, f in msg.fields.items():
            if f.fieldType == "string" and f.max_size is not None and not f.is_array:
                # Variable-size string field
                result += MessagePyGen.generate_variable_string_struct(f, msg.name)
            elif f.is_array and f.max_size is not None:
                # Bounded array
                result += MessagePyGen.generate_bounded_array_struct(f, msg.name)
        
        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        result += 'class %s(Structured, byte_order=ByteOrder.LE, byte_order_mode=ByteOrderMode.OVERRIDE):\n' % structName
        result += '    msg_size = %s\n' % msg.size
        if msg.id != None:
            result += '    msg_id = %s\n' % msg.id

        # Generate fields, handling special cases
        field_lines = []
        for key, f in msg.fields.items():
            field_code = FieldPyGen.generate(f)
            
            # Handle inline struct arrays (fixed-size arrays of nested structs)
            if "_INLINE_STRUCT_ARRAY_" in field_code:
                # Extract struct name and count
                import re
                match = re.search(r'_INLINE_STRUCT_ARRAY_(\w+)_(\d+)', field_code)
                if match:
                    struct_name = match.group(1)
                    count = int(match.group(2))
                    # Generate inlined fields
                    for i in range(count):
                        field_lines.append(f'    {f.name}{i}: {struct_name}  # Inlined struct array element {i}')
                    continue
            
            field_lines.append(field_code)
        
        result += '\n'.join(field_lines)

        result += '\n\n    def __str__(self):\n'
        result += f'        out = "{msg.name} Msg, ID {msg.id}, Size {msg.size} \\n"\n'
        for key, f in msg.fields.items():
            result += f'        out += f"{key} = '
            result += '{self.' + key + '}\\n"\n'
        result += f'        out += "\\n"\n'
        result += f'        return out'

        result += '\n\n    def to_dict(self, include_name = True, include_id = True):\n'
        result += '        out = {}\n'
        # Handle all field types including arrays
        for key, f in msg.fields.items():
            if f.is_array:
                if f.isDefaultType or f.isEnum or f.fieldType == "string":
                    # Array of primitives, enums, or strings
                    result += f'        out["{key}"] = self.{key}\n'
                else:
                    # Array of nested messages - convert each element
                    result += f'        out["{key}"] = [item.to_dict(False, False) for item in self.{key}]\n'
            elif f.isDefaultType or f.isEnum or f.fieldType == "string":
                # Regular primitive, enum, or string field
                result += f'        out["{key}"] = self.{key}\n'
            else:
                # Nested message field
                if getattr(f, 'flatten', False):
                    # Merge nested dict into parent
                    result += f'        out.update(self.{key}.to_dict(False, False))\n'
                else:
                    result += f'        out["{key}"] = self.{key}.to_dict(False, False)\n'
        result += '        if include_name:\n'
        result += f'            out["name"] = "{msg.name}"\n'
        result += '        if include_id:\n'
        result += f'            out["msg_id"] = "{msg.id}"\n'
        result += '        return out\n'

        return result

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class FilePyGen():
    @staticmethod
    def generate(package):
        yield '# Automatically generated struct frame header \n'
        yield '# Generated by %s at %s. \n\n' % (version, time.asctime())

        yield 'from structured import *\n'
        yield 'from enum import Enum\n'
        yield 'import typing\n'
        yield 'from typing import Annotated\n'
        yield 'from structured.hint_types.arrays import StaticStructArraySerializer\n\n'

        if package.enums:
            yield '# Enum definitions\n'
            for key, enum in package.enums.items():
                yield EnumPyGen.generate(enum) + '\n\n'

        if package.messages:
            yield '# Struct definitions \n'
            # Need to sort messages to make sure dependecies are properly met

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
