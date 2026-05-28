#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
C code generator for struct-frame.

This module generates C code for struct serialization with manual Pack/Unpack
functions for binary compatibility across platforms.
"""

from struct_frame import version, NamingStyleC, camel_to_snake_case, pascal_case, build_enum_leading_comments, build_enum_values
import time

_style_c = NamingStyleC()

c_types = {"uint8": "uint8_t",
           "int8": "int8_t",
           "uint16": "uint16_t",
           "int16": "int16_t",
           "uint32": "uint32_t",
           "int32": "int32_t",
           "bool": "bool",
           "float": "float",
           "double": "double",
           "uint64": 'uint64_t',
           "int64":  'int64_t',
           "string": "char",  # Add string type support
           }


class EnumCGen():
    @staticmethod
    def generate(field):
        result = build_enum_leading_comments(field.comments)

        enum_name = '%s%s' % (pascal_case(field.package), field.name)
        result += 'typedef enum %s {\n' % (enum_name)

        # C uses ENUM_NAME_VALUE format with prefix
        enum_prefix = camel_to_snake_case(field.name).upper()
        
        def c_value_generator(name, entry_name, value, comma):
            return "    %s_%s = %d%s" % (enum_prefix, entry_name, value, comma)

        enum_values = build_enum_values(
            field, _style_c,
            skip_trailing_comma=True,
            value_generator=c_value_generator
        )

        result += '\n'.join(enum_values)
        result += '\n} %s;\n' % (enum_name)

        result += 'typedef uint8_t %s_t;' % (enum_name)

        # Add module-prefixed enum constants for compatibility
        result += '\n\n/* Enum constants with module prefix */\n'
        module_prefix = camel_to_snake_case(field.package).upper()
        for d in field.data:
            # Use the already correct enum constant name
            enum_constant = f"{enum_prefix}_{_style_c.enum_entry(d)}"
            module_constant = f"{module_prefix}_{enum_constant}"
            result += f'#define {module_constant:<35} {enum_constant}\n'

        # Add enum-to-string helper function
        result += f'\n\n/* Convert {enum_name} to string */\n'
        result += f'static inline const char* {enum_name}_to_string({enum_name} value) {{\n'
        result += '    switch (value) {\n'
        for d in field.data:
            enum_constant = f"{enum_prefix}_{_style_c.enum_entry(d)}"
            result += f'        case {enum_constant}: return "{_style_c.enum_entry(d)}";\n'
        result += '        default: return "UNKNOWN";\n'
        result += '    }\n'
        result += '}\n'

        return result

    @staticmethod
    def generate_nested_for_c(enum, msg_name):
        """Generate a flattened C enum for a message-nested enum (C has no nested types).
        
        The enum is named MsgNameEnumName and values are MSGNAME_ENUMNAME_VALUE.
        """
        result = ''
        if enum.comments:
            result += build_enum_leading_comments(enum.comments)
        enum_name = f'{msg_name}{enum.name}'
        enum_prefix = f'{camel_to_snake_case(msg_name).upper()}_{camel_to_snake_case(enum.name).upper()}'
        result += f'/* Nested enum {msg_name}::{enum.name} (flattened for C) */\n'
        result += f'typedef enum {enum_name} {{\n'
        entries = list(enum.data.items())
        for i, (entry_name, (value, comments)) in enumerate(entries):
            for c in comments:
                result += f'    {c}\n'
            comma = ',' if i < len(entries) - 1 else ''
            result += f'    {enum_prefix}_{entry_name.upper()} = {value}{comma}\n'
        result += f'}} {enum_name};\n'
        result += f'typedef uint8_t {enum_name}_t;\n'
        # enum-to-string helper
        result += f'\n/* Convert {enum_name} to string */\n'
        result += f'static inline const char* {enum_name}_to_string({enum_name} value) {{\n'
        result += '    switch (value) {\n'
        for entry_name, (value, _) in enum.data.items():
            result += f'        case {enum_prefix}_{entry_name.upper()}: return "{entry_name.upper()}";\n'
        result += '        default: return "UNKNOWN";\n'
        result += '    }\n'
        result += '}\n'
        return result


class FieldCGen():
    @staticmethod
    def generate(field):
        result = ''
        var_name = field.name
        type_name = field.field_type

        # Handle basic type resolution
        if type_name in c_types:
            base_type = c_types[type_name]
        else:
            if getattr(field, 'type_message', None):
                # Nested enum: flattened as PackageMsgNameEnumName_t
                pkg_prefix = pascal_case(field.type_package if field.type_package else field.package)
                base_type = f'{pkg_prefix}{field.type_message}{type_name}_t'
            else:
                pkg_prefix = field.type_package if field.type_package else field.package
                if field.is_enum:
                    base_type = '%s%s_t' % (pascal_case(pkg_prefix), type_name)
                else:
                    base_type = '%s%s' % (pascal_case(pkg_prefix), type_name)

        # Handle arrays
        if field.is_array:
            if field.field_type == "string":
                # String arrays need both array size and individual string size
                if field.size_option is not None:
                    # Fixed string array: size_option strings, each element_size chars
                    declaration = f"char {var_name}[{field.size_option}][{field.element_size}];"
                    comment = f"  // Fixed string array: {field.size_option} strings, each max {field.element_size} chars"
                elif field.max_size is not None:
                    # Variable string array: count (uint8_t or uint16_t) + max_size strings of element_size chars each
                    count_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                    declaration = f"struct {{ {count_type} count; char data[{field.max_size}][{field.element_size}]; }} {var_name};"
                    comment = f"  // Variable string array: up to {field.max_size} strings, each max {field.element_size} chars"
                else:
                    declaration = f"char {var_name}[1][1];"  # Fallback
                    comment = "  // String array (error in size specification)"
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array: always exact size
                    declaration = f"{base_type} {var_name}[{field.size_option}];"
                    comment = f"  // Fixed array: always {field.size_option} elements"
                elif field.max_size is not None:
                    # Variable array: count (uint8_t or uint16_t) + max elements
                    count_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                    declaration = f"struct {{ {count_type} count; {base_type} data[{field.max_size}]; }} {var_name};"
                    comment = f"  // Variable array: up to {field.max_size} elements"
                else:
                    declaration = f"{base_type} {var_name}[1];"  # Fallback
                    comment = "  // Array (error in size specification)"

            result += f"    {declaration}{comment}"

        # Handle regular strings
        elif field.field_type == "string":
            if field.size_option is not None:
                # Fixed string: exactly size_option characters
                declaration = f"char {var_name}[{field.size_option}];"
                comment = f"  // Fixed string: exactly {field.size_option} chars"
            elif field.max_size is not None:
                # Variable string: length (uint8_t or uint16_t) + max characters
                length_type = "uint16_t" if field.max_size > 255 else "uint8_t"
                declaration = f"struct {{ {length_type} length; char data[{field.max_size}]; }} {var_name};"
                comment = f"  // Variable string: up to {field.max_size} chars"
            else:
                declaration = f"char {var_name}[1];"  # Fallback
                comment = "  // String (error in size specification)"

            result += f"    {declaration}{comment}"

        # Handle regular fields
        else:
            result += f"    {base_type} {var_name};"

        # Add leading comments
        leading_comment = field.comments
        if leading_comment:
            for c in leading_comment:
                result = c + "\n" + result

        return result



class OneOfCGen():
    @staticmethod
    def generate_discriminator_enum(oneof, msg_name, package=None):
        """Generate a discriminator enum for field_order oneofs in C."""
        if not oneof.auto_discriminator or oneof.discriminator_type != "field_order":
            return ''
        
        result = ''
        enum_name = f'{msg_name}{pascal_case(oneof.name)}Field'
        
        result += f'/* Discriminator enum for {msg_name}::{oneof.name} oneof */\n'
        result += f'typedef enum {enum_name} {{\n'
        result += f'    {camel_to_snake_case(msg_name).upper()}_{camel_to_snake_case(oneof.name).upper()}_FIELD_NONE = 0,\n'
        
        for idx, (field_name, field) in enumerate(oneof.fields.items()):
            field_order = idx + 1
            # Use SCREAMING_SNAKE_CASE for enum values with message prefix
            enum_value = f'{camel_to_snake_case(msg_name).upper()}_{camel_to_snake_case(oneof.name).upper()}_FIELD_{camel_to_snake_case(field_name).upper()}'
            result += f'    {enum_value} = {field_order},\n'
        
        result += f'}} {enum_name};\n\n'
        return result
    
    @staticmethod
    def get_discriminator_enum_name(oneof, msg_name):
        """Get the enum type name for a field_order discriminator."""
        return f'{msg_name}{pascal_case(oneof.name)}Field'
    
    @staticmethod
    def generate(oneof, package=None, msg_name=None):
        """Generate C union for a oneof construct."""
        result = ''
        
        # Add comments
        if oneof.comments:
            for c in oneof.comments:
                result += '%s\n' % c
        
        # If discriminator is enabled, add discriminator field first
        if oneof.auto_discriminator:
            if oneof.discriminator_type == "msgid":
                # Use uint16_t since message IDs can be up to 65535
                result += f'    uint16_t {oneof.name}_discriminator;  // Auto-generated message ID discriminator\n'
            else:  # field_order
                # Use the generated enum type for better type safety
                enum_name = OneOfCGen.get_discriminator_enum_name(oneof, msg_name) if msg_name else 'uint8_t'
                result += f'    {enum_name} {oneof.name}_discriminator;  // Auto-generated field order discriminator\n'
        
        # Generate the union
        result += f'    union {{\n'
        
        # Generate each field in the union
        for key, field in oneof.fields.items():
            field_code = FieldCGen.generate(field)
            # Indent the field code properly (remove leading spaces and add union indent)
            field_code = field_code.strip()
            result += f'        {field_code}\n'
        
        result += f'    }} {oneof.name};'
        
        return result


class MessageCGen():
    @staticmethod
    def _generate_field_comparison(field):
        """Generate comparison code for a single field in C."""
        var_name = field.name
        type_name = field.field_type
        
        # Handle arrays
        if field.is_array:
            if field.field_type == "string":
                if field.size_option is not None:
                    # Fixed string array: memcmp
                    return f'(memcmp(a->{var_name}, b->{var_name}, sizeof(a->{var_name})) == 0)'
                elif field.max_size is not None:
                    # Variable string array: compare count and data
                    return f'(a->{var_name}.count == b->{var_name}.count && memcmp(a->{var_name}.data, b->{var_name}.data, sizeof(a->{var_name}.data)) == 0)'
                else:
                    return f'(memcmp(a->{var_name}, b->{var_name}, sizeof(a->{var_name})) == 0)'
            else:
                # Non-string arrays
                if field.size_option is not None:
                    # Fixed array: memcmp
                    return f'(memcmp(a->{var_name}, b->{var_name}, sizeof(a->{var_name})) == 0)'
                elif field.max_size is not None:
                    # Variable array: compare count and data
                    return f'(a->{var_name}.count == b->{var_name}.count && memcmp(a->{var_name}.data, b->{var_name}.data, sizeof(a->{var_name}.data)) == 0)'
                else:
                    return f'(memcmp(a->{var_name}, b->{var_name}, sizeof(a->{var_name})) == 0)'
        
        # Handle regular strings
        elif field.field_type == "string":
            if field.size_option is not None:
                # Fixed string: strncmp
                return f'(strncmp(a->{var_name}, b->{var_name}, {field.size_option}) == 0)'
            elif field.max_size is not None:
                # Variable string: compare length and data
                return f'(a->{var_name}.length == b->{var_name}.length && strncmp(a->{var_name}.data, b->{var_name}.data, {field.max_size}) == 0)'
            else:
                return f'(strcmp(a->{var_name}, b->{var_name}) == 0)'
        
        # Handle nested structs and enums with memcmp
        elif type_name not in c_types:
            return f'(memcmp(&a->{var_name}, &b->{var_name}, sizeof(a->{var_name})) == 0)'
        
        # Handle regular fields (primitives)
        else:
            return f'(a->{var_name} == b->{var_name})'
    
    @staticmethod
    def _generate_oneof_comparison(oneof):
        """Generate comparison code for a oneof (union) in C."""
        comparisons = []
        
        # If auto-discriminator is enabled, compare discriminator first
        if oneof.auto_discriminator:
            comparisons.append(f'(a->{oneof.name}_discriminator == b->{oneof.name}_discriminator)')
        
        # Compare the union as raw bytes (since we don't know which variant is active)
        comparisons.append(f'(memcmp(&a->{oneof.name}, &b->{oneof.name}, sizeof(a->{oneof.name})) == 0)')
        
        return ' && '.join(comparisons)
    
    @staticmethod
    def generate(msg, package=None, equality=False):
        leading_comment = msg.comments

        result = ''
        if leading_comment:
            for c in msg.comments:
                result = '%s\n' % c

        structName = '%s%s' % (pascal_case(msg.package), msg.name)
        result += 'typedef struct %s {' % structName

        result += '\n'

        size = 1
        if not msg.fields and not msg.oneofs:
            # Empty structs are not allowed in C standard.
            # Therefore add a dummy field if an empty message occurs.
            result += '    char dummy_field;'
        else:
            size = msg.size

        # Generate regular fields
        result += '\n'.join([FieldCGen.generate(f)
                            for key, f in msg.fields.items()])
        
        # Generate oneofs
        if msg.oneofs:
            if msg.fields:
                result += '\n'
            result += '\n'.join([OneOfCGen.generate(o, package, structName)
                                for key, o in msg.oneofs.items()])
        
        result += '\n}'
        result += ' %s;\n\n' % structName

        defineName = '%s_%s' % (camel_to_snake_case(
            msg.package).upper(), camel_to_snake_case(msg.name).upper())
        result += '#define %s_MAX_SIZE %d\n' % (defineName, size)
        # Wire-evolution: BASE_SIZE is the size of the non-extension portion.
        # Equal to MAX_SIZE for messages without `option extensions_start = N;`.
        result += '#define %s_BASE_SIZE %d\n' % (defineName, msg.base_size)
        
        # Add MIN_SIZE for variable messages
        if msg.variable:
            result += '#define %s_MIN_SIZE %d\n' % (defineName, msg.min_size)
            result += '#define %s_IS_VARIABLE 1\n' % defineName

        if msg.id:
            # When package has a package ID, generate 16-bit message ID as (pkg_id << 8) | msg_id
            if package and package.package_id is not None:
                # Compute combined 16-bit message ID
                combined_msg_id = (package.package_id << 8) | msg.id
                result += '#define %s_MSG_ID %d\n' % (defineName, combined_msg_id)
            else:
                # No package ID, use plain message ID
                result += '#define %s_MSG_ID %d\n' % (defineName, msg.id)
        
        # Add magic numbers for checksum
        if msg.id is not None and msg.magic_bytes:
            result += f'#define {defineName}_MAGIC1 {msg.magic_bytes[0]} /* Checksum magic (based on field types and positions) */\n'
            result += f'#define {defineName}_MAGIC2 {msg.magic_bytes[1]} /* Checksum magic (based on field types and positions) */\n'

        # Generate variable message functions
        if msg.variable:
            result += MessageCGen._generate_variable_functions(msg, structName, defineName)
        
        # Generate unified unpack() for messages with MSG_ID (both variable and non-variable)
        if msg.id:
            result += MessageCGen._generate_unified_unpack(msg, structName, defineName)

        # Generate equality function if requested
        if equality:
            func_name = f'{structName}_equals'
            result += f'\nstatic inline bool {func_name}(const {structName}* a, const {structName}* b) {{\n'
            
            comparisons = []
            
            # Handle empty structs
            if not msg.fields and not msg.oneofs:
                comparisons.append('(a->dummy_field == b->dummy_field)')
            else:
                # Generate field comparisons
                for key, field in msg.fields.items():
                    comparisons.append(MessageCGen._generate_field_comparison(field))
                
                # Generate oneof comparisons
                for key, oneof in msg.oneofs.items():
                    comparisons.append(MessageCGen._generate_oneof_comparison(oneof))
            
            if comparisons:
                result += '    return ' + ' &&\n           '.join(comparisons) + ';\n'
            else:
                result += '    return true;\n'
            
            result += '}\n'

        return result + '\n'
    
    @staticmethod
    def _generate_variable_functions(msg, structName, defineName):
        """Generate serialized_size and serialize (variable) functions for variable messages."""
        result = ''
        
        # Generate serialized_size function - calculates actual size based on current data
        result += f'\n/**\n'
        result += f' * Calculate the serialized size of a {structName} message.\n'
        result += f' * @param msg Pointer to the message\n'
        result += f' * @return The size in bytes when serialized (variable, between MIN_SIZE and MAX_SIZE)\n'
        result += f' */\n'
        result += f'static inline size_t {structName}_serialized_size(const {structName}* msg) {{\n'
        result += f'    size_t size = 0;\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                # Variable array: count byte + actual data
                if field.field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                    result += f'    size += 1 + (msg->{var_name}.count * {element_size});  // {var_name}: count + data\n'
                else:
                    element_size = field.size // field.max_size if field.max_size else 1
                    # Recalculate element size from the actual type
                    type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                    if field.field_type in type_sizes:
                        element_size = type_sizes[field.field_type]
                    else:
                        # For nested messages, we need the actual size
                        element_size = (field.size - 1) // field.max_size
                    result += f'    size += 1 + (msg->{var_name}.count * {element_size});  // {var_name}: count + data\n'
            elif field.field_type == "string" and field.max_size is not None:
                # Variable string: length byte + actual data
                result += f'    size += 1 + msg->{var_name}.length;  // {var_name}: length + data\n'
            else:
                # Fixed-size field
                result += f'    size += {field.size};  // {var_name}\n'
        
        # Oneofs: discriminator (1 or 2 bytes) + full union payload
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                result += f'    size += {disc_bytes};  // {oneof_name} discriminator\n'
            result += f'    size += {oneof.size};  // {oneof_name} union payload\n'
        
        result += f'    return size;\n'
        result += f'}}\n'
        
        # Generate _serialize_variable function - serializes only used bytes (internal function)
        result += f'\n/**\n'
        result += f' * Serialize a {structName} message into a buffer using variable-length encoding.\n'
        result += f' * Only serializes the actual used bytes, not the full MAX_SIZE.\n'
        result += f' * @param msg Pointer to the message to serialize\n'
        result += f' * @param buffer Output buffer (must be at least {structName}_serialized_size(msg) bytes)\n'
        result += f' * @return The number of bytes written\n'
        result += f' */\n'
        result += f'static inline size_t {structName}_serialize_variable(const {structName}* msg, uint8_t* buffer) {{\n'
        result += f'    size_t offset = 0;\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                # Variable array
                if field.field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                    result += f'    // {var_name}: variable string array\n'
                    result += f'    buffer[offset++] = msg->{var_name}.count;\n'
                    result += f'    memcpy(buffer + offset, msg->{var_name}.data, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
                else:
                    type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                    if field.field_type in type_sizes:
                        element_size = type_sizes[field.field_type]
                    else:
                        element_size = (field.size - 1) // field.max_size
                    result += f'    // {var_name}: variable array\n'
                    result += f'    buffer[offset++] = msg->{var_name}.count;\n'
                    result += f'    memcpy(buffer + offset, msg->{var_name}.data, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
            elif field.field_type == "string" and field.max_size is not None:
                # Variable string
                result += f'    // {var_name}: variable string\n'
                result += f'    buffer[offset++] = msg->{var_name}.length;\n'
                result += f'    memcpy(buffer + offset, msg->{var_name}.data, msg->{var_name}.length);\n'
                result += f'    offset += msg->{var_name}.length;\n'
            else:
                # Fixed-size field - copy directly
                result += f'    // {var_name}: fixed size ({field.size} bytes)\n'
                result += f'    memcpy(buffer + offset, &msg->{var_name}, {field.size});\n'
                result += f'    offset += {field.size};\n'
        
        # Oneofs: write discriminator then full union bytes
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'    // {oneof_name} discriminator (uint16)\n'
                    result += f'    memcpy(buffer + offset, &msg->{oneof_name}_discriminator, 2);\n'
                    result += f'    offset += 2;\n'
                else:  # field_order (uint8)
                    result += f'    // {oneof_name} discriminator (uint8)\n'
                    result += f'    memcpy(buffer + offset, &msg->{oneof_name}_discriminator, 1);\n'
                    result += f'    offset += 1;\n'
            result += f'    // {oneof_name} union payload\n'
            result += f'    memcpy(buffer + offset, &msg->{oneof_name}, {oneof.size});\n'
            result += f'    offset += {oneof.size};\n'
        
        result += f'    return offset;\n'
        result += f'}}\n'
        
        # Generate _deserialize_variable function - deserializes variable-length data (internal function)
        result += f'\n/**\n'
        result += f' * Deserialize a {structName} message from a buffer with variable-length encoding.\n'
        result += f' * @param buffer Input buffer\n'
        result += f' * @param buffer_size Size of the input buffer\n'
        result += f' * @param msg Pointer to the message to deserialize into\n'
        result += f' * @return The number of bytes read, or 0 if buffer is too small\n'
        result += f' */\n'
        result += f'static inline size_t {structName}_deserialize_variable(const uint8_t* buffer, size_t buffer_size, {structName}* msg) {{\n'
        result += f'    size_t offset = 0;\n'
        result += f'    memset(msg, 0, sizeof({structName}));  // Zero-initialize\n'
        
        for key, field in msg.fields.items():
            var_name = field.name
            if field.is_array and field.max_size is not None:
                # Variable array
                if field.field_type == "string":
                    element_size = field.element_size if field.element_size else 1
                    result += f'    // {var_name}: variable string array\n'
                    result += f'    if (offset >= buffer_size) return 0;\n'
                    result += f'    msg->{var_name}.count = buffer[offset++];\n'
                    result += f'    if (msg->{var_name}.count > {field.max_size}) msg->{var_name}.count = {field.max_size};\n'
                    result += f'    if (offset + msg->{var_name}.count * {element_size} > buffer_size) return 0;\n'
                    result += f'    memcpy(msg->{var_name}.data, buffer + offset, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
                else:
                    type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                    if field.field_type in type_sizes:
                        element_size = type_sizes[field.field_type]
                    else:
                        element_size = (field.size - 1) // field.max_size
                    result += f'    // {var_name}: variable array\n'
                    result += f'    if (offset >= buffer_size) return 0;\n'
                    result += f'    msg->{var_name}.count = buffer[offset++];\n'
                    result += f'    if (msg->{var_name}.count > {field.max_size}) msg->{var_name}.count = {field.max_size};\n'
                    result += f'    if (offset + msg->{var_name}.count * {element_size} > buffer_size) return 0;\n'
                    result += f'    memcpy(msg->{var_name}.data, buffer + offset, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
            elif field.field_type == "string" and field.max_size is not None:
                # Variable string
                result += f'    // {var_name}: variable string\n'
                result += f'    if (offset >= buffer_size) return 0;\n'
                result += f'    msg->{var_name}.length = buffer[offset++];\n'
                result += f'    if (msg->{var_name}.length > {field.max_size}) msg->{var_name}.length = {field.max_size};\n'
                result += f'    if (offset + msg->{var_name}.length > buffer_size) return 0;\n'
                result += f'    memcpy(msg->{var_name}.data, buffer + offset, msg->{var_name}.length);\n'
                result += f'    offset += msg->{var_name}.length;\n'
            else:
                # Fixed-size field
                result += f'    // {var_name}: fixed size ({field.size} bytes)\n'
                result += f'    if (offset + {field.size} > buffer_size) return 0;\n'
                result += f'    memcpy(&msg->{var_name}, buffer + offset, {field.size});\n'
                result += f'    offset += {field.size};\n'
        
        # Oneofs: read discriminator then full union bytes
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'    // {oneof_name} discriminator (uint16)\n'
                    result += f'    if (offset + 2 > buffer_size) return 0;\n'
                    result += f'    memcpy(&msg->{oneof_name}_discriminator, buffer + offset, 2);\n'
                    result += f'    offset += 2;\n'
                else:  # field_order (uint8)
                    result += f'    // {oneof_name} discriminator (uint8)\n'
                    result += f'    if (offset + 1 > buffer_size) return 0;\n'
                    result += f'    memcpy(&msg->{oneof_name}_discriminator, buffer + offset, 1);\n'
                    result += f'    offset += 1;\n'
            result += f'    // {oneof_name} union payload\n'
            result += f'    if (offset + {oneof.size} > buffer_size) return 0;\n'
            result += f'    memcpy(&msg->{oneof_name}, buffer + offset, {oneof.size});\n'
            result += f'    offset += {oneof.size};\n'
        
        result += f'    return offset;\n'
        result += f'}}\n'
        
        # Generate unified deserialize() function
        result += f'\n/**\n'
        result += f' * Unified deserialize function for {structName}.\n'
        result += f' * Automatically detects whether the buffer contains variable-length or MAX_SIZE encoding.\n'
        result += f' * For MAX_SIZE buffers: uses memcpy (compatible with minimal profiles)\n'
        result += f' * For variable-length buffers: uses {structName}_deserialize_variable()\n'
        result += f' * @param buffer Input buffer\n'
        result += f' * @param buffer_size Size of the input buffer\n'
        result += f' * @param msg Pointer to the message to deserialize into\n'
        result += f' * @return The number of bytes read, or 0 if buffer is invalid\n'
        result += f' */\n'
        result += f'static inline size_t {structName}_deserialize(const uint8_t* buffer, size_t buffer_size, {structName}* msg) {{\n'
        if msg.oneofs:
            # Structs with oneof discriminators: C enum fields are 4 bytes but wire is 1/2 bytes.
            # Always use _deserialize_variable to avoid struct layout mismatch.
            result += f'    return {structName}_deserialize_variable(buffer, buffer_size, msg);\n'
        else:
            result += f'    if (buffer_size == {defineName}_MAX_SIZE) {{\n'
            result += f'        /* MAX_SIZE encoding (from minimal profiles or non-variable encoding) */\n'
            result += f'        memcpy(msg, buffer, {defineName}_MAX_SIZE);\n'
            result += f'        return {defineName}_MAX_SIZE;\n'
            result += f'    }} else {{\n'
            result += f'        /* Variable-length encoding */\n'
            result += f'        return {structName}_deserialize_variable(buffer, buffer_size, msg);\n'
            result += f'    }}\n'
        result += f'}}\n'
        
        # Also generate serialize() function for variable messages
        result += f'\n/**\n'
        result += f' * Serialize a {structName} message.\n'
        result += f' * Automatically uses variable-length encoding.\n'
        result += f' * @param msg Pointer to the message to serialize\n'
        result += f' * @param buffer Output buffer (must be at least {structName}_serialized_size(msg) bytes)\n'
        result += f' * @return The number of bytes written\n'
        result += f' */\n'
        result += f'static inline size_t {structName}_serialize(const {structName}* msg, uint8_t* buffer) {{\n'
        result += f'    return {structName}_serialize_variable(msg, buffer);\n'
        result += f'}}\n'
        
        return result

    @staticmethod
    def _generate_unified_unpack(msg, structName, defineName):
        """Generate unified deserialize() function for non-variable messages with MSG_ID."""
        result = ''
        
        # For variable messages, deserialize() was already generated inline in _generate_variable_functions
        # This method handles non-variable messages
        if not msg.variable:
            result += f'\n/**\n'
            result += f' * Unified unpack function for {structName}.\n'
            result += f' * For fixed-size messages: uses memcpy with size validation\n'
            result += f' * @param buffer Input buffer\n'
            result += f' * @param buffer_size Size of the input buffer\n'
            result += f' * @param msg Pointer to the message to unpack into\n'
            result += f' * @return The number of bytes read, or 0 if buffer is invalid\n'
            result += f' */\n'
            result += f'static inline size_t {structName}_unpack(const uint8_t* buffer, size_t buffer_size, {structName}* msg) {{\n'
            result += f'    /* Fixed-size message - use direct copy */\n'
            result += f'    if (buffer_size < {defineName}_MAX_SIZE) return 0;\n'
            result += f'    memcpy(msg, buffer, {defineName}_MAX_SIZE);\n'
            result += f'    return {defineName}_MAX_SIZE;\n'
            result += f'}}\n'
        
        return result

    @staticmethod
    def _generate_unified_unpack(msg, structName, defineName):
        """Generate unified deserialize() and serialize() functions for non-variable messages with MSG_ID."""
        result = ''
        
        # For variable messages, deserialize() was already generated inline in _generate_variable_functions
        # This method handles non-variable messages
        if not msg.variable:
            result += f'\n/**\n'
            result += f' * Deserialize function for {structName}.\n'
            result += f' * For fixed-size messages: uses memcpy with size validation\n'
            result += f' * @param buffer Input buffer\n'
            result += f' * @param buffer_size Size of the input buffer\n'
            result += f' * @param msg Pointer to the message to deserialize into\n'
            result += f' * @return The number of bytes read, or 0 if buffer is invalid\n'
            result += f' */\n'
            result += f'static inline size_t {structName}_deserialize(const uint8_t* buffer, size_t buffer_size, {structName}* msg) {{\n'
            result += f'    /* Fixed-size message - use direct copy */\n'
            result += f'    if (buffer_size < {defineName}_MAX_SIZE) return 0;\n'
            result += f'    memcpy(msg, buffer, {defineName}_MAX_SIZE);\n'
            result += f'    return {defineName}_MAX_SIZE;\n'
            result += f'}}\n'
            
            # Also add serialize() for non-variable messages
            result += f'\n/**\n'
            result += f' * Serialize function for {structName}.\n'
            result += f' * For fixed-size messages: uses memcpy\n'
            result += f' * @param msg Pointer to the message to serialize\n'
            result += f' * @param buffer Output buffer (must be at least {defineName}_MAX_SIZE bytes)\n'
            result += f' * @return The number of bytes written\n'
            result += f' */\n'
            result += f'static inline size_t {structName}_serialize(const {structName}* msg, uint8_t* buffer) {{\n'
            result += f'    memcpy(buffer, msg, {defineName}_MAX_SIZE);\n'
            result += f'    return {defineName}_MAX_SIZE;\n'
            result += f'}}\n'
        
        return result

    @staticmethod
    def get_initializer(msg, null_init):
        if not msg.fields:
            return '{0}'

        parts = []
        for field in msg.fields:
            parts.append(field.get_initializer(null_init))
        return '{' + ', '.join(parts) + '}'


class FileCGen():
    @staticmethod
    def generate(package, imported_packages=None, equality=False):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by struct-frame %s. */\n\n' % version

        yield '#pragma once\n'
        yield '#include <stdbool.h>\n'
        yield '#include <stdint.h>\n'
        yield '#include "frame_base.h"  // For message_info_t\n'
        yield '#include <stddef.h>\n'
        
        # Include string.h for equality comparisons
        if equality:
            yield '#include <string.h>\n'
        
        # Include generated headers for imported packages (enables language server navigation)
        if imported_packages:
            for pkg_name in imported_packages:
                yield '#include "%s.structframe.h"\n' % pkg_name
        
        yield '\n'
        yield '#ifdef __cplusplus\n'
        yield 'extern "C" {\n'
        yield '#endif\n\n'

        # Add package ID constant if present
        if package.package_id is not None:
            pkg_name_upper = camel_to_snake_case(package.name).upper()
            yield f'/* Package ID for extended message IDs */\n'
            yield f'#define {pkg_name_upper}_PACKAGE_ID {package.package_id}\n\n'

        # include additional header files if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumCGen.generate(enum) + '\n\n'

        # Generate discriminator enums for field_order oneofs (must come before struct definitions)
        has_discriminator_enums = False
        for key, msg in package.messages.items():
            structName = '%s%s' % (pascal_case(msg.package), msg.name)
            # Nested message enums (flattened for C)
            for enum_name, enum in msg.enums.items():
                yield EnumCGen.generate_nested_for_c(enum, structName) + '\n\n'
            for oneof_name, oneof in msg.oneofs.items():
                enum_code = OneOfCGen.generate_discriminator_enum(oneof, structName, package)
                if enum_code:
                    if not has_discriminator_enums:
                        yield '/* Oneof discriminator enums */\n'
                        has_discriminator_enums = True
                    yield enum_code

        if package.messages:
            yield '/* Struct definitions */\n'
            # When all messages are variable, struct packing is not needed because
            # serialization/deserialization is performed field-by-field.
            all_variable = all(m.variable for m in package.messages.values())
            if not all_variable:
                yield '#pragma pack(push, 1)\n'
            # Need to sort messages to make sure dependencies are properly met

            for key, msg in package.sortedMessages().items():
                yield MessageCGen.generate(msg, package, equality) + '\n'
            if not all_variable:
                yield '#pragma pack(pop)\n'
            yield '\n'

        # Add default initializers if needed
        # if package.messages:
        #    yield '/* Initializer values for message structs */\n'
        #    for key, msg in package.messages.items():
        #        identifier = '%s_%s_init_default' % (package.name, _style_c.struct_name(msg.name))
        #        yield '#define %-40s %s\n' % (identifier, MessageCGen.get_initializer(msg, False))
        #    for key, msg in package.messages.items():
        #        identifier = '%s_%s_init_zero' % (package.name, _style_c.struct_name(msg.name))
        #        yield '#define %-40s %s\n' % (identifier, msg.get_initializer(True))
        #    yield '\n'

        if package.messages:
            pkg_fn_name = f'{camel_to_snake_case(package.name)}_get_message_info'
            if package.package_id is not None:
                # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                yield '/**\n'
                yield ' * Get message info (size and magic numbers) for a given message ID.\n'
                yield ' * @param msg_id The 16-bit message ID (pkg_id << 8 | msg_id)\n'
                yield ' * @param info Pointer to message_info_t struct to fill\n'
                yield ' * @return true if message ID is known, false otherwise\n'
                yield ' */\n'
                yield f'static inline bool {pkg_fn_name}(uint16_t msg_id, message_info_t* info) {{\n'
                yield '    /* Extract package ID and message ID from 16-bit message ID */\n'
                yield '    uint8_t pkg_id = (msg_id >> 8) & 0xFF;\n'
                yield '    uint8_t local_msg_id = msg_id & 0xFF;\n'
                yield '    \n'
                pkg_name_upper = camel_to_snake_case(package.name).upper()
                yield f'    /* Check if this is our package */\n'
                yield f'    if (pkg_id != {pkg_name_upper}_PACKAGE_ID) {{\n'
                yield f'        return false;\n'
                yield f'    }}\n'
                yield '    \n'
                yield '    switch (local_msg_id) {\n'
            else:
                # Flat namespace mode: 8-bit message ID
                yield '/**\n'
                yield ' * Get message info (size and magic numbers) for a given message ID.\n'
                yield ' * @param msg_id The message ID\n'
                yield ' * @param info Pointer to message_info_t struct to fill\n'
                yield ' * @return true if message ID is known, false otherwise\n'
                yield ' */\n'
                yield f'static inline bool {pkg_fn_name}(uint16_t msg_id, message_info_t* info) {{\n'
                yield '    switch (msg_id) {\n'
            
            for key, msg in package.sortedMessages().items():
                name = '%s_%s' % (camel_to_snake_case(
                    msg.package).upper(), camel_to_snake_case(msg.name).upper())
                if msg.id:
                    if package.package_id is not None:
                        # When using package ID, compare against local message ID
                        yield '        case %d:\n' % msg.id
                    else:
                        # No package ID, compare against full message ID constant
                        yield '        case %s_MSG_ID:\n' % name
                    
                    # Get magic bytes values
                    magic1 = '0'
                    magic2 = '0'
                    if msg.magic_bytes:
                        magic1 = f'{name}_MAGIC1'
                        magic2 = f'{name}_MAGIC2'
                    
                    yield f'            info->size = {name}_MAX_SIZE;\n'
                    yield f'            info->base_size = {name}_BASE_SIZE;\n'
                    yield f'            info->magic1 = {magic1};\n'
                    yield f'            info->magic2 = {magic2};\n'
                    yield '            return true;\n'

            yield '        default: break;\n'
            yield '    }\n'
            yield '    return false;\n'
            yield '}\n'

            # Provide an unprefixed alias `get_message_info` resolving to this
            # package's function. When a package header is included after other
            # package headers (which also define this macro), the alias is
            # redefined so the most-recently-included package wins. This
            # preserves backward compatibility with downstream code that uses
            # the unprefixed name while avoiding the duplicate function-symbol
            # error that occurs when multiple package headers are included in
            # one translation unit.
            yield '\n'
            yield '#ifdef get_message_info\n'
            yield '#  undef get_message_info\n'
            yield '#endif\n'
            yield f'#define get_message_info {pkg_fn_name}\n'

        yield '\n#ifdef __cplusplus\n'
        yield '}\n'
        yield '#endif\n'


class TestCGen():
    """Generator for C round-trip test code with deterministic dummy values.

    Emits two files per package:
      * ``<pkg>.tests.h`` – header with ``create_test_*`` factories and
        ``roundtrip_*`` per-message test functions.
      * ``test_roundtrip_<pkg>.c`` – tiny ``main()`` that invokes the runner.
    """

    @staticmethod
    def _dummy_value(field, index=0):
        """Return a C literal for a dummy value of *field*'s type, or None when
        the type cannot be assigned by a single literal (nested struct)."""
        type_name = field.field_type
        type_values = {
            "uint8":  f"(uint8_t){(42 + index) % 256}",
            "int8":   f"(int8_t){(42 + index) % 128}",
            "uint16": f"(uint16_t){1000 + index}",
            "int16":  f"(int16_t){500 + index}",
            "uint32": f"{123456 + index}U",
            "int32":  f"{123456 + index}",
            "uint64": f"{9876543210 + index}ULL",
            "int64":  f"{9876543210 + index}LL",
            "float":  f"{3.14159 + index}f",
            "double": f"{2.718281828 + index}",
            "bool":   "true" if index % 2 == 0 else "false",
        }
        if type_name in type_values:
            return type_values[type_name]
        if field.is_enum:
            if getattr(field, 'type_message', None):
                pkg_prefix = pascal_case(field.type_package if field.type_package else field.package)
                return f'({pkg_prefix}{field.type_message}{type_name}_t)0'
            pkg_prefix = pascal_case(field.type_package if field.type_package else field.package)
            return f'({pkg_prefix}{type_name}_t)0'
        # Nested struct - cannot init with single literal; leave zero-initialised
        return None

    @staticmethod
    def _generate_field_init(field, prefix="msg", index=0):
        var_name = field.name
        type_name = field.field_type
        out = ""

        if field.is_array:
            if type_name == "string":
                if field.size_option is not None:
                    count = min(field.size_option, 3)
                    for i in range(count):
                        out += f'    strncpy({prefix}.{var_name}[{i}], "test_{i}", sizeof({prefix}.{var_name}[{i}]) - 1);\n'
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    out += f'    {prefix}.{var_name}.count = {count};\n'
                    for i in range(count):
                        out += f'    strncpy({prefix}.{var_name}.data[{i}], "test_{i}", sizeof({prefix}.{var_name}.data[{i}]) - 1);\n'
            else:
                dummy = TestCGen._dummy_value(field, 0)
                if field.size_option is not None:
                    count = min(field.size_option, 3)
                    if dummy is not None:
                        for i in range(count):
                            out += f'    {prefix}.{var_name}[{i}] = {TestCGen._dummy_value(field, i)};\n'
                    # else: nested struct array – leave zero-initialised
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    out += f'    {prefix}.{var_name}.count = {count};\n'
                    if dummy is not None:
                        for i in range(count):
                            out += f'    {prefix}.{var_name}.data[{i}] = {TestCGen._dummy_value(field, i)};\n'
                    # else: nested struct array – leave .data zero-initialised
        elif type_name == "string":
            if field.size_option is not None:
                out += f'    strncpy({prefix}.{var_name}, "test_string", sizeof({prefix}.{var_name}) - 1);\n'
            elif field.max_size is not None:
                test_str = "test_string"
                out += f'    {prefix}.{var_name}.length = {len(test_str)};\n'
                out += f'    strncpy({prefix}.{var_name}.data, "{test_str}", sizeof({prefix}.{var_name}.data) - 1);\n'
        else:
            dummy = TestCGen._dummy_value(field, index)
            if dummy is not None:
                out += f'    {prefix}.{var_name} = {dummy};\n'
            # else: nested struct – leave zero-initialised
        return out

    @staticmethod
    def _struct_name(msg):
        return '%s%s' % (pascal_case(msg.package), msg.name)

    @staticmethod
    def _define_name(msg):
        return '%s_%s' % (camel_to_snake_case(msg.package).upper(),
                          camel_to_snake_case(msg.name).upper())

    @staticmethod
    def generate(package):
        """Generate the ``<pkg>.tests.h`` header content."""
        yield '/* Automatically generated round-trip test header for struct-frame messages. */\n'
        yield f'/* Generated by struct-frame {version}. */\n\n'
        yield '#pragma once\n\n'
        yield '#include <stdio.h>\n'
        yield '#include <string.h>\n'
        yield '#include <stdint.h>\n'
        yield '#include <stdbool.h>\n'
        yield '#include <stddef.h>\n\n'
        yield f'#include "{package.name}.structframe.h"\n'
        yield '#include "frame_profiles.h"\n\n'

        # Profile descriptor table - mirrors the Python/C++ profile entries.
        yield '/* Profile descriptor used by the round-trip runner. */\n'
        yield 'typedef struct sf_profile_entry {\n'
        yield '    const char* name;\n'
        yield '    profile_config_t config;\n'
        yield '    bool has_pkg_id;\n'
        yield '    bool has_length;\n'
        yield '    long max_payload;  /* -1 == unlimited */\n'
        yield '} sf_profile_entry_t;\n\n'

        yield 'static const sf_profile_entry_t SF_TEST_PROFILES[] = {\n'
        yield '    {"ProfileStandard", PROFILE_STANDARD_CONFIG, false, true,  255},\n'
        yield '    {"ProfileSensor",   PROFILE_SENSOR_CONFIG,   false, false, -1},\n'
        yield '    {"ProfileIPC",      PROFILE_IPC_CONFIG,      false, false, -1},\n'
        yield '    {"ProfileBulk",     PROFILE_BULK_CONFIG,     true,  true,  65535},\n'
        yield '    {"ProfileNetwork",  PROFILE_NETWORK_CONFIG,  true,  true,  65535},\n'
        yield '};\n'
        yield '#define SF_TEST_PROFILE_COUNT (sizeof(SF_TEST_PROFILES) / sizeof(SF_TEST_PROFILES[0]))\n\n'

        # Skip ``oneof`` messages (variant unions) – the simple round-trip path
        # does not encode discriminators.
        testable_messages = [(key, msg) for key, msg in package.sortedMessages().items()
                             if msg.id is not None and not getattr(msg, 'oneofs', {})]

        # create_test_<msg>() factories
        for key, msg in testable_messages:
            structName = TestCGen._struct_name(msg)
            yield f'/* Create a deterministic test instance of {structName}. */\n'
            yield f'static inline {structName} sf_create_test_{camel_to_snake_case(msg.name)}(void) {{\n'
            yield f'    {structName} msg;\n'
            yield f'    memset(&msg, 0, sizeof(msg));\n'
            field_index = 0
            for fkey, field in msg.fields.items():
                yield TestCGen._generate_field_init(field, "msg", field_index)
                field_index += 1
            yield '    return msg;\n'
            yield '}\n\n'

        # Per-message round-trip tests
        for key, msg in testable_messages:
            structName = TestCGen._struct_name(msg)
            defineName = TestCGen._define_name(msg)
            snake = camel_to_snake_case(msg.name)
            magic1 = f'{defineName}_MAGIC1' if msg.magic_bytes else '0'
            magic2 = f'{defineName}_MAGIC2' if msg.magic_bytes else '0'

            yield f'/* Round-trip {structName} through *p* and verify field equivalence. */\n'
            yield f'static inline bool sf_roundtrip_{snake}(const sf_profile_entry_t* p, bool verbose) {{\n'
            yield f'    if (!p->has_pkg_id && ({defineName}_MSG_ID > 255)) {{\n'
            yield f'        if (verbose) printf("[SKIP] {structName} (%s): msg_id > 255 needs has_pkg_id\\n", p->name);\n'
            yield f'        return true;\n'
            yield f'    }}\n'
            yield f'    if (p->max_payload >= 0 && ({defineName}_MAX_SIZE > p->max_payload)) {{\n'
            yield f'        if (verbose) printf("[SKIP] {structName} (%s): exceeds max_payload\\n", p->name);\n'
            yield f'        return true;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    {structName} orig = sf_create_test_{snake}();\n'
            yield f'\n'
            yield f'    /* Serialise payload according to profile encoding. */\n'
            yield f'    uint8_t payload[{defineName}_MAX_SIZE];\n'
            yield f'    size_t payload_size;\n'
            yield f'    if (p->has_length) {{\n'
            yield f'        payload_size = {structName}_serialize(&orig, payload);\n'
            yield f'    }} else {{\n'
            yield f'        memcpy(payload, &orig, {defineName}_MAX_SIZE);\n'
            yield f'        payload_size = {defineName}_MAX_SIZE;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    /* Encode framed bytes into a fresh buffer. */\n'
            yield f'    uint8_t buffer[{defineName}_MAX_SIZE + 256];\n'
            yield f'    buffer_writer_t writer;\n'
            yield f'    buffer_writer_init(&writer, &p->config, buffer, sizeof(buffer));\n'
            yield f'\n'
            yield f'    uint16_t full_id = (uint16_t){defineName}_MSG_ID;\n'
            yield f'    uint8_t msg_id_byte = (uint8_t)(full_id & 0xFF);\n'
            yield f'    uint8_t pkg_id_byte = (uint8_t)((full_id >> 8) & 0xFF);\n'
            yield f'\n'
            yield f'    /* Some encoder paths emit truncated bytes for variable messages\n'
            yield f'       only when the profile carries a length field. */\n'
            yield f'    has_length_field_for_variable_encoding = p->has_length;\n'
            yield f'\n'
            yield f'    size_t written = buffer_writer_write_ext(&writer, msg_id_byte,\n'
            yield f'                                         payload, payload_size,\n'
            yield f'                                         0, 0, 0, pkg_id_byte,\n'
            yield f'                                         (size_t){defineName}_BASE_SIZE,\n'
            yield f'                                         (uint8_t)({magic1}), (uint8_t)({magic2}));\n'
            yield f'    if (written == 0) {{\n'
            yield f'        printf("[FAIL] {structName} (%s): encode failed\\n", p->name);\n'
            yield f'        return false;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    /* Decode the framed bytes back into a struct. */\n'
            yield f'    buffer_reader_t reader;\n'
            yield f'    buffer_reader_init(&reader, &p->config, buffer, written, {camel_to_snake_case(package.name)}_get_message_info);\n'
            yield f'    frame_msg_info_t info = buffer_reader_next(&reader);\n'
            yield f'    if (!info.valid) {{\n'
            yield f'        printf("[FAIL] {structName} (%s): parse failed\\n", p->name);\n'
            yield f'        return false;\n'
            yield f'    }}\n'
            yield f'    if (info.msg_id != full_id) {{\n'
            yield f'        printf("[FAIL] {structName} (%s): msg_id mismatch (expected %u, got %u)\\n",\n'
            yield f'               p->name, (unsigned)full_id, (unsigned)info.msg_id);\n'
            yield f'        return false;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    {structName} decoded;\n'
            yield f'    memset(&decoded, 0, sizeof(decoded));\n'
            yield f'    if ({structName}_deserialize(info.msg_data, info.msg_len, &decoded) == 0) {{\n'
            yield f'        printf("[FAIL] {structName} (%s): deserialize failed\\n", p->name);\n'
            yield f'        return false;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    /* Compare via re-serialised bytes (handles padding in unused tail). */\n'
            yield f'    uint8_t orig_buf[{defineName}_MAX_SIZE];\n'
            yield f'    uint8_t dec_buf[{defineName}_MAX_SIZE];\n'
            yield f'    size_t a = {structName}_serialize(&orig, orig_buf);\n'
            yield f'    size_t b = {structName}_serialize(&decoded, dec_buf);\n'
            yield f'    if (a != b || memcmp(orig_buf, dec_buf, a) != 0) {{\n'
            yield f'        printf("[FAIL] {structName} (%s): decoded data differs from original\\n", p->name);\n'
            yield f'        return false;\n'
            yield f'    }}\n'
            yield f'\n'
            yield f'    if (verbose) printf("[PASS] {structName} (%s)\\n", p->name);\n'
            yield f'    return true;\n'
            yield f'}}\n\n'

        # Master runner
        yield f'#define SF_TEST_MESSAGE_COUNT {len(testable_messages)}\n\n'
        yield 'static inline size_t sf_run_all_tests_for_profile(const sf_profile_entry_t* p, bool verbose) {\n'
        yield '    size_t passed = 0;\n'
        for key, msg in testable_messages:
            snake = camel_to_snake_case(msg.name)
            yield f'    if (sf_roundtrip_{snake}(p, verbose)) passed++;\n'
        yield '    if (verbose) printf("  -> %zu/%d passed\\n", passed, SF_TEST_MESSAGE_COUNT);\n'
        yield '    return passed;\n'
        yield '}\n\n'

        yield 'static inline bool sf_run_roundtrip_all_profiles(bool verbose) {\n'
        yield '    bool all_ok = true;\n'
        yield '    for (size_t i = 0; i < SF_TEST_PROFILE_COUNT; i++) {\n'
        yield '        const sf_profile_entry_t* p = &SF_TEST_PROFILES[i];\n'
        yield '        if (verbose) printf("\\n--- %s ---\\n", p->name);\n'
        yield '        size_t passed = sf_run_all_tests_for_profile(p, verbose);\n'
        yield '        if (passed != SF_TEST_MESSAGE_COUNT) {\n'
        yield '            all_ok = false;\n'
        yield '            printf("[FAIL] %s: %zu/%d passed\\n", p->name, passed, SF_TEST_MESSAGE_COUNT);\n'
        yield '        } else if (verbose) {\n'
        yield '            printf("[OK] %s: %zu/%d passed\\n", p->name, passed, SF_TEST_MESSAGE_COUNT);\n'
        yield '        }\n'
        yield '    }\n'
        yield '    return all_ok;\n'
        yield '}\n'

    @staticmethod
    def generate_roundtrip_main(package):
        """Generate the standalone ``test_roundtrip_<pkg>.c`` file."""
        yield '/* Automatically generated round-trip test runner for struct-frame messages. */\n'
        yield f'/* Generated by struct-frame {version}. */\n\n'
        yield '#include <stdio.h>\n'
        yield '#include <string.h>\n'
        yield f'#include "{package.name}.tests.h"\n\n'
        yield 'int main(int argc, char** argv) {\n'
        yield '    bool verbose = false;\n'
        yield '    for (int i = 1; i < argc; i++) {\n'
        yield '        if (strcmp(argv[i], "-v") == 0 || strcmp(argv[i], "--verbose") == 0) {\n'
        yield '            verbose = true;\n'
        yield '        }\n'
        yield '    }\n\n'
        yield f'    printf("Running round-trip tests for package \'{package.name}\' across 5 profiles...\\n");\n'
        yield '    bool ok = sf_run_roundtrip_all_profiles(verbose);\n'
        yield '    if (ok) {\n'
        yield f'        printf("[TEST PASSED] All round-trip tests for \'{package.name}\' succeeded.\\n");\n'
        yield '        return 0;\n'
        yield '    } else {\n'
        yield f'        printf("[TEST FAILED] Round-trip tests for \'{package.name}\' had failures.\\n");\n'
        yield '        return 1;\n'
        yield '    }\n'
        yield '}\n'
