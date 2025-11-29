#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
Shared base module for TypeScript and JavaScript code generators.

This module provides common functionality used by both ts_gen.py and js_gen.py
to reduce code duplication and ensure consistent behavior.
"""

from struct_frame import NamingStyleC

StyleC = NamingStyleC()

# Common type mappings shared by TypeScript and JavaScript generators
# Maps proto types to struct method names
common_types = {
    "int8":     'Int8',
    "uint8":    'UInt8',
    "int16":    'Int16LE',
    "uint16":   'UInt16LE',
    "bool":     'Boolean8',
    "double":   'Float64LE',
    "float":    'Float32LE',
    "int32":    'Int32LE',
    "uint32":   'UInt32LE',
    "int64":    'BigInt64LE',
    "uint64":   'BigUInt64LE',
    "string":   'String',
}

# TypeScript type mappings for array declarations (TypeScript only)
ts_array_types = {
    "int8":     'number',
    "uint8":    'number',
    "int16":    'number',
    "uint16":   'number',
    "bool":     'boolean',
    "double":   'number',
    "float":    'number',
    "int32":    'number',
    "uint32":   'number',
    "uint64":   'bigint',
    "int64":    'bigint',
    "string":   'string',
}

# Common typed array methods for array fields
# Maps proto types to typed array method names
common_typed_array_methods = {
    "int8":     'Int8Array',
    "uint8":    'UInt8Array',
    "int16":    'Int16Array',
    "uint16":   'UInt16Array',
    "bool":     'UInt8Array',  # Boolean arrays stored as UInt8Array
    "double":   'Float64Array',
    "float":    'Float32Array',
    "int32":    'Int32Array',
    "uint32":   'UInt32Array',
    "int64":    'BigInt64Array',
    "uint64":   'BigUInt64Array',
    "string":   'StructArray',  # String arrays use StructArray
}


class BaseFieldGen:
    """Base field generator with shared logic for TypeScript and JavaScript."""

    @staticmethod
    def generate(field, packageName, types_dict, typed_array_methods_dict):
        """
        Generate field definition code.

        Args:
            field: Field object containing field metadata
            packageName: Package name prefix
            types_dict: Dictionary mapping proto types to struct method names
            typed_array_methods_dict: Dictionary mapping proto types to typed array method names

        Returns:
            String containing the field definition code
        """
        result = ''
        isEnum = field.isEnum if hasattr(field, 'isEnum') else False
        var_name = StyleC.var_name(field.name)
        type_name = field.fieldType

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
                if field.size_option is not None:  # Fixed size array [size=X]
                    result += "    // Fixed string array: %d strings, each exactly %d chars\n" % (
                        field.size_option, field.element_size)
                    result += "    .StructArray('%s', %d, new Struct().String('value', %d).compile())" % (
                        var_name, field.size_option, field.element_size)
                else:  # Variable size array [max_size=X]
                    result += "    // Variable string array: up to %d strings, each max %d chars\n" % (
                        field.max_size, field.element_size)
                    result += "    .UInt8('%s_count')\n" % var_name
                    result += "    .StructArray('%s_data', %d, new Struct().String('value', %d).compile())" % (
                        var_name, field.max_size, field.element_size)
            else:
                # Regular type arrays
                if type_name in types_dict:
                    base_type = types_dict[type_name]
                    array_method = typed_array_methods_dict.get(
                        type_name, 'StructArray')
                elif isEnum:
                    base_type = 'UInt8'
                    array_method = 'UInt8Array'
                else:
                    base_type = '%s_%s' % (packageName, type_name)
                    array_method = 'StructArray'

                if field.size_option is not None:  # Fixed size array [size=X]
                    array_size = field.size_option
                    result += '    // Fixed array: always %d elements\n' % array_size
                    if array_method == 'StructArray':
                        result += "    .%s('%s', %d, %s)" % (
                            array_method, var_name, array_size, base_type)
                    else:
                        result += "    .%s('%s', %d)" % (
                            array_method, var_name, array_size)
                else:  # Variable size array [max_size=X]
                    max_count = field.max_size
                    result += '    // Variable array: up to %d elements\n' % max_count
                    result += "    .UInt8('%s_count')\n" % var_name
                    if array_method == 'StructArray':
                        result += "    .%s('%s_data', %d, %s)" % (
                            array_method, var_name, max_count, base_type)
                    else:
                        result += "    .%s('%s_data', %d)" % (
                            array_method, var_name, max_count)
        else:
            # Non-array fields
            if field.fieldType == "string":
                if hasattr(field, 'size_option') and field.size_option is not None:
                    result += '    // Fixed string: exactly %d chars\n' % field.size_option
                    result += "    .String('%s', %d)" % (var_name, field.size_option)
                elif hasattr(field, 'max_size') and field.max_size is not None:
                    result += '    // Variable string: up to %d chars\n' % field.max_size
                    result += "    .UInt8('%s_length')\n" % var_name
                    result += "    .String('%s_data', %d)" % (var_name, field.max_size)
                else:
                    result += "    .String('%s')" % var_name
            else:
                # Regular types
                if type_name in types_dict:
                    type_name = types_dict[type_name]
                else:
                    type_name = '%s_%s' % (packageName,
                                           StyleC.struct_name(type_name))

                if isEnum:
                    result += "    .UInt8('%s')" % var_name
                else:
                    result += "    .%s('%s')" % (type_name, var_name)

        # Prepend leading comments
        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = c + "\n" + result

        return result


class BaseEnumGen:
    """Base enum generator with shared logic for TypeScript and JavaScript."""

    @staticmethod
    def get_enum_values(field):
        """
        Get enum values with proper formatting.

        Args:
            field: Enum field object

        Returns:
            Tuple of (enum_length, enum_values_data)
            where enum_values_data is a list of (name, value, comments) tuples
        """
        enum_length = len(field.data)
        enum_values_data = []
        for index, d in enumerate(field.data):
            leading_comment = field.data[d][1]
            value = field.data[d][0]
            is_last = (index == enum_length - 1)
            enum_values_data.append({
                'name': StyleC.enum_entry(d),
                'value': value,
                'comments': leading_comment,
                'is_last': is_last
            })
        return enum_length, enum_values_data
