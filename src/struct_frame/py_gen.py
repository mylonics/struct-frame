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
                # For enums, use the full enum class name for better type safety
                base_type = '%s%s' % (pascalCase(field.package), type_name)
            else:
                base_type = '%s%s' % (pascalCase(field.package), type_name)

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                # String arrays require both array size and individual element size
                if field.size_option is not None:
                    type_annotation = f"list[{base_type}]  # Fixed string array size={field.size_option}, each max {field.element_size} chars"
                elif field.max_size is not None:
                    type_annotation = f"list[{base_type}]  # Bounded string array max_size={field.max_size}, each max {field.element_size} chars"
                else:
                    type_annotation = f"list[{base_type}]  # String array"
            else:
                # Non-string arrays
                if field.size_option is not None:
                    type_annotation = f"list[{base_type}]  # Fixed array size={field.size_option}"
                elif field.max_size is not None:
                    type_annotation = f"list[{base_type}]  # Bounded array max_size={field.max_size}"
                else:
                    type_annotation = f"list[{base_type}]  # Array"
        # Handle strings with size info
        elif field.fieldType == "string":
            if field.size_option is not None:
                # Fixed string - exact length
                type_annotation = f"str  # Fixed string size={field.size_option}"
            elif field.max_size is not None:
                # Variable string - up to max length
                type_annotation = f"str  # Variable string max_size={field.max_size}"
            else:
                # Fallback (shouldn't happen with validation)
                type_annotation = "str  # String"
        else:
            # Regular field
            type_annotation = base_type

        result += '    %s: %s' % (var_name, type_annotation)

        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = "#" + c + "\n" + result

        return result


class MessagePyGen():
    @staticmethod
    def generate(msg):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '#%s\n' % c

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
        result += 'class %s(Structured, byte_order=ByteOrder.LE, byte_order_mode=ByteOrderMode.OVERRIDE):\n' % structName
        result += '    msg_size = %s\n' % msg.size
        if msg.id != None:
            result += '    msg_id = %s\n' % msg.id

        result += '\n'.join([FieldPyGen.generate(f)
                            for key, f in msg.fields.items()])

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
        yield 'from enum import Enum\n\n'

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
