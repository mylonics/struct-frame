#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

from struct_frame import version, NamingStyleC, CamelToSnakeCase, pascalCase
import time

StyleC = NamingStyleC()

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
        leading_comment = field.comments

        result = ''
        if leading_comment:
            for c in leading_comment:
                result = '%s\n' % c

        enumName = '%s%s' % (pascalCase(field.package), field.name)
        result += 'typedef enum %s' % (enumName)

        result += ' {\n'

        enum_length = len(field.data)
        enum_values = []
        for index, (d) in enumerate(field.data):
            leading_comment = field.data[d][1]

            if leading_comment:
                for c in leading_comment:
                    enum_values.append(c)

            comma = ","
            if index == enum_length - 1:
                # last enum member should not end with a comma
                comma = ""

            enum_value = "    %s_%s = %d%s" % (CamelToSnakeCase(
                field.name).upper(), StyleC.enum_entry(d), field.data[d][0], comma)

            enum_values.append(enum_value)

        result += '\n'.join(enum_values)
        result += '\n}'

        result += ' %s;\n' % (enumName)

        result += 'typedef uint8_t %s_t;' % (enumName)

        # Add module-prefixed enum constants for compatibility
        result += '\n\n/* Enum constants with module prefix */\n'
        module_prefix = CamelToSnakeCase(field.package).upper()
        for d in field.data:
            # Use the already correct enum constant name
            enum_constant = f"{CamelToSnakeCase(field.name).upper()}_{StyleC.enum_entry(d)}"
            module_constant = f"{module_prefix}_{enum_constant}"
            result += f'#define {module_constant:<35} {enum_constant}\n'

        # Add enum-to-string helper function
        result += f'\n\n/* Convert {enumName} to string */\n'
        result += f'static inline const char* {enumName}_to_string({enumName} value) {{\n'
        result += '    switch (value) {\n'
        for d in field.data:
            enum_constant = f"{CamelToSnakeCase(field.name).upper()}_{StyleC.enum_entry(d)}"
            result += f'        case {enum_constant}: return "{StyleC.enum_entry(d)}";\n'
        result += '        default: return "UNKNOWN";\n'
        result += '    }\n'
        result += '}\n'

        return result


class FieldCGen():
    @staticmethod
    def generate(field):
        result = ''
        var_name = field.name
        type_name = field.fieldType

        # Handle basic type resolution
        if type_name in c_types:
            base_type = c_types[type_name]
        else:
            if field.isEnum:
                base_type = '%s%s_t' % (pascalCase(field.package), type_name)
            else:
                base_type = '%s%s' % (pascalCase(field.package), type_name)

        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
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
        elif field.fieldType == "string":
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
    def generate(oneof, package=None):
        """Generate C union for a oneof construct."""
        result = ''
        
        # Add comments
        if oneof.comments:
            for c in oneof.comments:
                result += '%s\n' % c
        
        # If auto-discriminator is enabled, add discriminator field first
        if oneof.auto_discriminator:
            # Always use uint16_t since message IDs can be up to 65535
            result += f'    uint16_t {oneof.name}_discriminator;  // Auto-generated message ID discriminator\n'
        
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
        type_name = field.fieldType
        
        # Handle arrays
        if field.is_array:
            if field.fieldType == "string":
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
        elif field.fieldType == "string":
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

        structName = '%s%s' % (pascalCase(msg.package), msg.name)
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
            result += '\n'.join([OneOfCGen.generate(o, package)
                                for key, o in msg.oneofs.items()])
        
        result += '\n}'
        result += ' %s;\n\n' % structName

        defineName = '%s_%s' % (CamelToSnakeCase(
            msg.package).upper(), CamelToSnakeCase(msg.name).upper())
        result += '#define %s_MAX_SIZE %d\n' % (defineName, size)
        
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
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                    result += f'    size += 1 + (msg->{var_name}.count * {element_size});  // {var_name}: count + data\n'
                else:
                    element_size = field.size // field.max_size if field.max_size else 1
                    # Recalculate element size from the actual type
                    type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                    if field.fieldType in type_sizes:
                        element_size = type_sizes[field.fieldType]
                    else:
                        # For nested messages, we need the actual size
                        element_size = (field.size - 1) // field.max_size
                    result += f'    size += 1 + (msg->{var_name}.count * {element_size});  // {var_name}: count + data\n'
            elif field.fieldType == "string" and field.max_size is not None:
                # Variable string: length byte + actual data
                result += f'    size += 1 + msg->{var_name}.length;  // {var_name}: length + data\n'
            else:
                # Fixed-size field
                result += f'    size += {field.size};  // {var_name}\n'
        
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
                if field.fieldType == "string":
                    element_size = field.element_size if field.element_size else 1
                    result += f'    // {var_name}: variable string array\n'
                    result += f'    buffer[offset++] = msg->{var_name}.count;\n'
                    result += f'    memcpy(buffer + offset, msg->{var_name}.data, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
                else:
                    type_sizes = {"uint8": 1, "int8": 1, "uint16": 2, "int16": 2, "uint32": 4, "int32": 4, "uint64": 8, "int64": 8, "float": 4, "double": 8, "bool": 1}
                    if field.fieldType in type_sizes:
                        element_size = type_sizes[field.fieldType]
                    else:
                        element_size = (field.size - 1) // field.max_size
                    result += f'    // {var_name}: variable array\n'
                    result += f'    buffer[offset++] = msg->{var_name}.count;\n'
                    result += f'    memcpy(buffer + offset, msg->{var_name}.data, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
            elif field.fieldType == "string" and field.max_size is not None:
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
                if field.fieldType == "string":
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
                    if field.fieldType in type_sizes:
                        element_size = type_sizes[field.fieldType]
                    else:
                        element_size = (field.size - 1) // field.max_size
                    result += f'    // {var_name}: variable array\n'
                    result += f'    if (offset >= buffer_size) return 0;\n'
                    result += f'    msg->{var_name}.count = buffer[offset++];\n'
                    result += f'    if (msg->{var_name}.count > {field.max_size}) msg->{var_name}.count = {field.max_size};\n'
                    result += f'    if (offset + msg->{var_name}.count * {element_size} > buffer_size) return 0;\n'
                    result += f'    memcpy(msg->{var_name}.data, buffer + offset, msg->{var_name}.count * {element_size});\n'
                    result += f'    offset += msg->{var_name}.count * {element_size};\n'
            elif field.fieldType == "string" and field.max_size is not None:
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
    def generate(package, equality=False):
        yield '/* Automatically generated struct frame header */\n'
        yield '/* Generated by %s at %s. */\n\n' % (version, time.asctime())

        yield '#pragma once\n'
        yield '#pragma pack(1)\n'
        yield '#include <stdbool.h>\n'
        yield '#include <stdint.h>\n'
        yield '#include "frame_base.h"  // For message_info_t\n'
        yield '#include <stddef.h>\n'
        
        # Include string.h for equality comparisons
        if equality:
            yield '#include <string.h>\n'
        
        yield '\n'

        # Add package ID constant if present
        if package.package_id is not None:
            pkg_name_upper = CamelToSnakeCase(package.name).upper()
            yield f'/* Package ID for extended message IDs */\n'
            yield f'#define {pkg_name_upper}_PACKAGE_ID {package.package_id}\n\n'

        # include additional header files if available in the future

        if package.enums:
            yield '/* Enum definitions */\n'
            for key, enum in package.enums.items():
                yield EnumCGen.generate(enum) + '\n\n'

        if package.messages:
            yield '/* Struct definitions */\n'
            # Need to sort messages to make sure dependecies are properly met

            for key, msg in package.sortedMessages().items():
                yield MessageCGen.generate(msg, package, equality) + '\n'
            yield '\n'

        # Add default initializers if needed
        # if package.messages:
        #    yield '/* Initializer values for message structs */\n'
        #    for key, msg in package.messages.items():
        #        identifier = '%s_%s_init_default' % (package.name, StyleC.struct_name(msg.name))
        #        yield '#define %-40s %s\n' % (identifier, MessageCGen.get_initializer(msg, False))
        #    for key, msg in package.messages.items():
        #        identifier = '%s_%s_init_zero' % (package.name, StyleC.struct_name(msg.name))
        #        yield '#define %-40s %s\n' % (identifier, msg.get_initializer(True))
        #    yield '\n'

        if package.messages:
            if package.package_id is not None:
                # When using package ID, message ID is 16-bit (package_id << 8 | msg_id)
                yield '/**\n'
                yield ' * Get message info (size and magic numbers) for a given message ID.\n'
                yield ' * @param msg_id The 16-bit message ID (pkg_id << 8 | msg_id)\n'
                yield ' * @param info Pointer to message_info_t struct to fill\n'
                yield ' * @return true if message ID is known, false otherwise\n'
                yield ' */\n'
                yield 'static inline bool get_message_info(uint16_t msg_id, message_info_t* info) {\n'
                yield '    /* Extract package ID and message ID from 16-bit message ID */\n'
                yield '    uint8_t pkg_id = (msg_id >> 8) & 0xFF;\n'
                yield '    uint8_t local_msg_id = msg_id & 0xFF;\n'
                yield '    \n'
                pkg_name_upper = CamelToSnakeCase(package.name).upper()
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
                yield 'static inline bool get_message_info(uint16_t msg_id, message_info_t* info) {\n'
                yield '    switch (msg_id) {\n'
            
            for key, msg in package.sortedMessages().items():
                name = '%s_%s' % (CamelToSnakeCase(
                    msg.package).upper(), CamelToSnakeCase(msg.name).upper())
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
                    yield f'            info->magic1 = {magic1};\n'
                    yield f'            info->magic2 = {magic2};\n'
                    yield '            return true;\n'

            yield '        default: break;\n'
            yield '    }\n'
            yield '    return false;\n'
            yield '}\n'
