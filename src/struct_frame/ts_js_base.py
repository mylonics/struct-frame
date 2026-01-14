#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
Shared base module for TypeScript and JavaScript code generators.

This module provides common functionality used by both ts_gen.py and js_gen.py
to reduce code duplication and ensure consistent behavior.
"""

from struct_frame import NamingStyleC, pascalCase

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
                    count_method = "UInt16LE" if field.max_size > 255 else "UInt8"
                    result += "    // Variable string array: up to %d strings, each max %d chars\n" % (
                        field.max_size, field.element_size)
                    result += "    .%s('%s_count')\n" % (count_method, var_name)
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
                    # Use field.type_package to get the package where the field's type is defined
                    type_package = getattr(field, 'type_package', None) or packageName
                    base_type = '%s_%s' % (type_package, type_name)
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
                    count_method = "UInt16LE" if field.max_size > 255 else "UInt8"
                    result += '    // Variable array: up to %d elements\n' % max_count
                    result += "    .%s('%s_count')\n" % (count_method, var_name)
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
                    length_method = "UInt16LE" if field.max_size > 255 else "UInt8"
                    result += '    // Variable string: up to %d chars\n' % field.max_size
                    result += "    .%s('%s_length')\n" % (length_method, var_name)
                    result += "    .String('%s_data', %d)" % (var_name, field.max_size)
                else:
                    result += "    .String('%s')" % var_name
            else:
                # Regular types
                if type_name in types_dict:
                    # Built-in primitive type - use method directly
                    type_name = types_dict[type_name]
                    if isEnum:
                        result += "    .UInt8('%s')" % var_name
                    else:
                        result += "    .%s('%s')" % (type_name, var_name)
                else:
                    # Custom message type - use StructArray with length 1
                    type_package = getattr(field, 'type_package', None) or packageName
                    # Use type name directly without case conversion to match how exports are generated
                    struct_name = '%s_%s' % (type_package, type_name)
                    if isEnum:
                        result += "    .UInt8('%s')" % var_name
                    else:
                        # Single nested struct uses StructArray with count=1
                        result += "    .StructArray('%s', 1, %s)" % (var_name, struct_name)

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


# ==============================================================================
# New class-based generation utilities
# These utilities help generate classes that extend MessageBase for better
# performance by avoiding runtime type resolution.
# ==============================================================================

# Type sizes for offset calculation
TYPE_SIZES = {
    "int8": 1,
    "uint8": 1,
    "int16": 2,
    "uint16": 2,
    "int32": 4,
    "uint32": 4,
    "int64": 8,
    "uint64": 8,
    "float": 4,
    "double": 8,
    "bool": 1,
}

# TypeScript type annotations for fields
TS_TYPE_ANNOTATIONS = {
    "int8": "number",
    "uint8": "number",
    "int16": "number",
    "uint16": "number",
    "int32": "number",
    "uint32": "number",
    "int64": "bigint",
    "uint64": "bigint",
    "float": "number",
    "double": "number",
    "bool": "boolean",
    "string": "string",
}

# TypeScript type annotations for array elements
# Boolean arrays are stored as UInt8Array internally, so they return number[]
TS_ARRAY_TYPE_ANNOTATIONS = {
    "int8": "number",
    "uint8": "number",
    "int16": "number",
    "uint16": "number",
    "int32": "number",
    "uint32": "number",
    "int64": "bigint",
    "uint64": "bigint",
    "float": "number",
    "double": "number",
    "bool": "number",  # Boolean arrays stored as UInt8Array return number[]
    "string": "string",
}

# Read method names for MessageBase helper methods
READ_METHODS = {
    "int8": "_readInt8",
    "uint8": "_readUInt8",
    "int16": "_readInt16LE",
    "uint16": "_readUInt16LE",
    "int32": "_readInt32LE",
    "uint32": "_readUInt32LE",
    "int64": "_readBigInt64LE",
    "uint64": "_readBigUInt64LE",
    "float": "_readFloat32LE",
    "double": "_readFloat64LE",
    "bool": "_readBoolean8",
}

# Write method names for MessageBase helper methods
WRITE_METHODS = {
    "int8": "_writeInt8",
    "uint8": "_writeUInt8",
    "int16": "_writeInt16LE",
    "uint16": "_writeUInt16LE",
    "int32": "_writeInt32LE",
    "uint32": "_writeUInt32LE",
    "int64": "_writeBigInt64LE",
    "uint64": "_writeBigUInt64LE",
    "float": "_writeFloat32LE",
    "double": "_writeFloat64LE",
    "bool": "_writeBoolean8",
}

# Array read method names
READ_ARRAY_METHODS = {
    "int8": "_readInt8Array",
    "uint8": "_readUInt8Array",
    "int16": "_readInt16Array",
    "uint16": "_readUInt16Array",
    "int32": "_readInt32Array",
    "uint32": "_readUInt32Array",
    "int64": "_readBigInt64Array",
    "uint64": "_readBigUInt64Array",
    "float": "_readFloat32Array",
    "double": "_readFloat64Array",
    "bool": "_readUInt8Array",  # Boolean arrays stored as UInt8Array
}

# Array write method names
WRITE_ARRAY_METHODS = {
    "int8": "_writeInt8Array",
    "uint8": "_writeUInt8Array",
    "int16": "_writeInt16Array",
    "uint16": "_writeUInt16Array",
    "int32": "_writeInt32Array",
    "uint32": "_writeUInt32Array",
    "int64": "_writeBigInt64Array",
    "uint64": "_writeBigUInt64Array",
    "float": "_writeFloat32Array",
    "double": "_writeFloat64Array",
    "bool": "_writeUInt8Array",  # Boolean arrays stored as UInt8Array
}


class FieldInfo:
    """Information about a field for class-based code generation."""
    
    def __init__(self, name, offset, size, field_type, is_array=False, 
                 array_length=None, element_size=None, is_enum=False,
                 is_nested=False, nested_type=None, is_variable=False,
                 count_field=None, data_field=None, comments=None):
        self.name = name
        self.offset = offset
        self.size = size
        self.field_type = field_type
        self.is_array = is_array
        self.array_length = array_length
        self.element_size = element_size
        self.is_enum = is_enum
        self.is_nested = is_nested
        self.nested_type = nested_type
        self.is_variable = is_variable  # Variable length array/string
        self.count_field = count_field  # For variable arrays
        self.data_field = data_field    # For variable strings/arrays
        self.comments = comments or []


def calculate_field_layout(msg, package, packages):
    """
    Calculate the byte offset for each field in a message.
    
    Args:
        msg: Message object
        package: Current package
        packages: All packages for resolving nested types
        
    Returns:
        List of FieldInfo objects with calculated offsets
    """
    fields = []
    offset = 0
    
    # Process regular fields
    for key, field in msg.fields.items():
        var_name = StyleC.var_name(field.name)
        field_type = field.fieldType
        is_enum = field.isEnum
        comments = field.comments
        
        if field.is_array:
            # Array field
            if field_type == "string":
                # String array
                if field.size_option is not None:
                    # Fixed string array
                    elem_size = field.element_size
                    array_len = field.size_option
                    total_size = elem_size * array_len
                    fields.append(FieldInfo(
                        name=var_name,
                        offset=offset,
                        size=total_size,
                        field_type="string",
                        is_array=True,
                        array_length=array_len,
                        element_size=elem_size,
                        comments=comments
                    ))
                    offset += total_size
                else:
                    # Variable string array - has count + data
                    elem_size = field.element_size
                    max_count = field.max_size
                    # Count field
                    count_name = f"{var_name}_count"
                    data_name = f"{var_name}_data"
                    count_type = "uint16" if max_count > 255 else "uint8"
                    count_size = 2 if max_count > 255 else 1
                    fields.append(FieldInfo(
                        name=count_name,
                        offset=offset,
                        size=count_size,
                        field_type=count_type,
                        comments=comments
                    ))
                    offset += count_size
                    # Data field
                    total_data_size = elem_size * max_count
                    fields.append(FieldInfo(
                        name=data_name,
                        offset=offset,
                        size=total_data_size,
                        field_type="string",
                        is_array=True,
                        array_length=max_count,
                        element_size=elem_size,
                        is_variable=True
                    ))
                    offset += total_data_size
            else:
                # Non-string array
                if is_enum:
                    elem_size = 1
                elif field_type in TYPE_SIZES:
                    elem_size = TYPE_SIZES[field_type]
                else:
                    # Nested message type
                    nested_msg = _find_message_type(field_type, package, packages)
                    if nested_msg is None:
                        raise ValueError(f"Unknown nested message type '{field_type}' for array field '{field.name}'")
                    elem_size = nested_msg.size
                
                if field.size_option is not None:
                    # Fixed array
                    array_len = field.size_option
                    total_size = elem_size * array_len
                    fields.append(FieldInfo(
                        name=var_name,
                        offset=offset,
                        size=total_size,
                        field_type=field_type,
                        is_array=True,
                        array_length=array_len,
                        element_size=elem_size,
                        is_enum=is_enum,
                        is_nested=field_type not in TYPE_SIZES and not is_enum,
                        nested_type=_get_nested_type_name(field, package),
                        comments=comments
                    ))
                    offset += total_size
                else:
                    # Variable array
                    max_count = field.max_size
                    count_name = f"{var_name}_count"
                    data_name = f"{var_name}_data"
                    count_type = "uint16" if max_count > 255 else "uint8"
                    count_size = 2 if max_count > 255 else 1
                    # Count field
                    fields.append(FieldInfo(
                        name=count_name,
                        offset=offset,
                        size=count_size,
                        field_type=count_type,
                        comments=comments
                    ))
                    offset += count_size
                    # Data field
                    total_data_size = elem_size * max_count
                    fields.append(FieldInfo(
                        name=data_name,
                        offset=offset,
                        size=total_data_size,
                        field_type=field_type,
                        is_array=True,
                        array_length=max_count,
                        element_size=elem_size,
                        is_enum=is_enum,
                        is_nested=field_type not in TYPE_SIZES and not is_enum,
                        nested_type=_get_nested_type_name(field, package),
                        is_variable=True
                    ))
                    offset += total_data_size
        elif field_type == "string":
            # Non-array string
            if field.size_option is not None:
                # Fixed string
                str_size = field.size_option
                fields.append(FieldInfo(
                    name=var_name,
                    offset=offset,
                    size=str_size,
                    field_type="string",
                    element_size=str_size,
                    comments=comments
                ))
                offset += str_size
            elif field.max_size is not None:
                # Variable string - has length + data
                max_len = field.max_size
                length_name = f"{var_name}_length"
                data_name = f"{var_name}_data"
                length_type = "uint16" if max_len > 255 else "uint8"
                length_size = 2 if max_len > 255 else 1
                # Length field
                fields.append(FieldInfo(
                    name=length_name,
                    offset=offset,
                    size=length_size,
                    field_type=length_type,
                    comments=comments
                ))
                offset += length_size
                # Data field
                fields.append(FieldInfo(
                    name=data_name,
                    offset=offset,
                    size=max_len,
                    field_type="string",
                    element_size=max_len,
                    is_variable=True
                ))
                offset += max_len
        else:
            # Primitive or nested message type
            if is_enum:
                fields.append(FieldInfo(
                    name=var_name,
                    offset=offset,
                    size=1,
                    field_type="uint8",
                    is_enum=True,
                    comments=comments
                ))
                offset += 1
            elif field_type in TYPE_SIZES:
                # Primitive type
                type_size = TYPE_SIZES[field_type]
                fields.append(FieldInfo(
                    name=var_name,
                    offset=offset,
                    size=type_size,
                    field_type=field_type,
                    comments=comments
                ))
                offset += type_size
            else:
                # Nested message type - treated as single element struct array
                nested_msg = _find_message_type(field_type, package, packages)
                if nested_msg is None:
                    raise ValueError(f"Unknown nested message type '{field_type}' for field '{field.name}'")
                nested_size = nested_msg.size
                fields.append(FieldInfo(
                    name=var_name,
                    offset=offset,
                    size=nested_size,
                    field_type=field_type,
                    is_array=True,
                    array_length=1,
                    element_size=nested_size,
                    is_nested=True,
                    nested_type=_get_nested_type_name(field, package),
                    comments=comments
                ))
                offset += nested_size
    
    # Process oneofs
    for key, oneof in msg.oneofs.items():
        oneof_name = oneof.name
        if oneof.auto_discriminator:
            # Discriminator field (UInt16LE)
            discrim_name = f"{oneof_name}_discriminator"
            fields.append(FieldInfo(
                name=discrim_name,
                offset=offset,
                size=2,
                field_type="uint16"
            ))
            offset += 2
        # Union data (byte array)
        data_name = f"{oneof_name}_data"
        fields.append(FieldInfo(
            name=data_name,
            offset=offset,
            size=oneof.size,
            field_type="uint8",
            is_array=True,
            array_length=oneof.size,
            element_size=1
        ))
        offset += oneof.size
    
    return fields


def _find_message_type(type_name, package, packages):
    """Find a message type by name in packages."""
    # First check current package
    msg = package.findFieldType(type_name)
    if msg:
        return msg
    # Then check all packages
    for pkg_name, pkg in packages.items():
        msg = pkg.findFieldType(type_name)
        if msg:
            return msg
    return None


def _get_nested_type_name(field, package):
    """Get the fully qualified nested type name with PascalCase package name."""
    type_package = getattr(field, 'type_package', None) or package.name
    # Convert package name to PascalCase for TypeScript/JavaScript conventions
    type_package_pascal = pascalCase(type_package)
    return f"{type_package_pascal}{field.fieldType}"
