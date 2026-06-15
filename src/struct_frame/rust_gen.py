#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;
"""
Rust code generator for struct-frame.

This module generates Rust code for struct serialization with explicit
pack/unpack methods for binary compatibility across platforms.
"""

from struct_frame import version, NamingStyleC, camel_to_snake_case, pascal_case, build_enum_leading_comments, build_enum_values, normalize_bytes_type
import os
import time

_style_c = NamingStyleC()

# Mapping from proto types to Rust types
rust_types = {
    "uint8": "u8",
    "int8": "i8",
    "uint16": "u16",
    "int16": "i16",
    "uint32": "u32",
    "int32": "i32",
    "bool": "bool",
    "float": "f32",
    "double": "f64",
    "uint64": "u64",
    "int64": "i64",
    "string": "u8",  # strings are byte arrays in Rust
    "bytes": "u8",   # bytes fields are byte arrays in Rust (same wire format as string)
}

# Rust reserved keywords that need escaping with r# prefix
RUST_KEYWORDS = {
    "as", "async", "await", "break", "const", "continue", "crate", "dyn",
    "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in",
    "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return",
    "self", "Self", "static", "struct", "super", "trait", "true", "type",
    "union", "unsafe", "use", "where", "while", "abstract", "become",
    "box", "do", "final", "macro", "override", "priv", "typeof", "unsized",
    "virtual", "yield", "try",
}

def _escape_rust_field_name(name):
    """Escape field names that conflict with Rust keywords."""
    if name in RUST_KEYWORDS:
        return f'r#{name}'
    return name

def _normalize_bytes_type(type_name):
    """Normalize 'bytes' to 'string' since they share the same wire format
    and Rust representation ([u8; N] byte arrays)."""
    return normalize_bytes_type(type_name)

# Byte sizes for each proto type
rust_type_sizes = {
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

# Pack/unpack method names (Rust read/write functions)
rust_pack_fns = {
    "uint8": ("buf[_pos] = self.{f};", 1),
    "int8": ("buf[_pos] = self.{f} as u8;", 1),
    "uint16": ("buf[_pos.._pos+2].copy_from_slice(&self.{f}.to_le_bytes());", 2),
    "int16": ("buf[_pos.._pos+2].copy_from_slice(&self.{f}.to_le_bytes());", 2),
    "uint32": ("buf[_pos.._pos+4].copy_from_slice(&self.{f}.to_le_bytes());", 4),
    "int32": ("buf[_pos.._pos+4].copy_from_slice(&self.{f}.to_le_bytes());", 4),
    "bool": ("buf[_pos] = if self.{f} { 1 } else { 0 };", 1),
    "float": ("buf[_pos.._pos+4].copy_from_slice(&self.{f}.to_le_bytes());", 4),
    "double": ("buf[_pos.._pos+8].copy_from_slice(&self.{f}.to_le_bytes());", 8),
    "uint64": ("buf[_pos.._pos+8].copy_from_slice(&self.{f}.to_le_bytes());", 8),
    "int64": ("buf[_pos.._pos+8].copy_from_slice(&self.{f}.to_le_bytes());", 8),
}

rust_unpack_fns = {
    "uint8": ("buf[_pos]", 1),
    "int8": ("buf[_pos] as i8", 1),
    "uint16": ("u16::from_le_bytes(buf[_pos.._pos+2].try_into().ok()?)", 2),
    "int16": ("i16::from_le_bytes(buf[_pos.._pos+2].try_into().ok()?)", 2),
    "uint32": ("u32::from_le_bytes(buf[_pos.._pos+4].try_into().ok()?)", 4),
    "int32": ("i32::from_le_bytes(buf[_pos.._pos+4].try_into().ok()?)", 4),
    "bool": ("buf[_pos] != 0", 1),
    "float": ("f32::from_le_bytes(buf[_pos.._pos+4].try_into().ok()?)", 4),
    "double": ("f64::from_le_bytes(buf[_pos.._pos+8].try_into().ok()?)", 8),
    "uint64": ("u64::from_le_bytes(buf[_pos.._pos+8].try_into().ok()?)", 8),
    "int64": ("i64::from_le_bytes(buf[_pos.._pos+8].try_into().ok()?)", 8),
}


def _rust_struct_name(package, name):
    """Get Rust struct name: just the name (no package prefix; use module for namespacing)"""
    return name


def _rust_const_prefix(package, name):
    """Get constant prefix: UPPER_SNAKE_CASE(package) + '_' + UPPER_SNAKE_CASE(name)"""
    return '%s_%s' % (camel_to_snake_case(package).upper(), camel_to_snake_case(name).upper())


class EnumRustGen():
    @staticmethod
    def generate(field):
        result = build_enum_leading_comments(field.comments, comment_prefix='//')

        enum_name = _rust_struct_name(field.package, field.name)
        result += '#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]\n'
        result += '#[repr(u8)]\n'
        result += 'pub enum %s {\n' % enum_name

        enum_entries = list(field.data.items())

        for idx, (entry_key, (value, comments)) in enumerate(enum_entries):
            if comments:
                for c in comments:
                    result += '    //%s\n' % c
            display_name = _style_c.enum_entry(entry_key)
            # First variant gets #[default]
            if idx == 0:
                result += '    #[default]\n'
            result += '    %s = %d,\n' % (display_name, value)

        result += '}\n\n'

        # Add from_u8 impl for deserialization
        result += 'impl %s {\n' % enum_name
        result += '    pub fn from_u8(v: u8) -> Option<Self> {\n'
        result += '        match v {\n'
        for entry_key, (value, _) in field.data.items():
            display_name = _style_c.enum_entry(entry_key)
            result += '            %d => Some(Self::%s),\n' % (value, display_name)
        result += '            _ => None,\n'
        result += '        }\n'
        result += '    }\n'
        result += '}\n'

        return result

    @staticmethod
    def generate_for_message(field, msg_name):
        """Generate a flattened Rust enum for a message-nested enum.

        Rust doesn't support enum nesting inside structs, so the enum is
        emitted at module scope with a prefixed name: MsgNameEnumName.
        """
        result = ''
        if field.comments:
            for c in field.comments:
                result += '//%s\n' % c
        enum_name = f'{msg_name}{field.name}'
        result += '/// Nested enum %s::%s (module-scoped for Rust)\n' % (msg_name, field.name)
        result += '#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]\n'
        result += '#[repr(u8)]\n'
        result += 'pub enum %s {\n' % enum_name

        entries = list(field.data.items())
        for idx, (entry_key, (value, comments)) in enumerate(entries):
            for c in comments:
                result += '    //%s\n' % c
            display_name = _style_c.enum_entry(entry_key)
            if idx == 0:
                result += '    #[default]\n'
            result += '    %s = %d,\n' % (display_name, value)

        result += '}\n\n'
        # from_u8 impl
        result += 'impl %s {\n' % enum_name
        result += '    pub fn from_u8(v: u8) -> Option<Self> {\n'
        result += '        match v {\n'
        for entry_key, (value, _) in field.data.items():
            display_name = _style_c.enum_entry(entry_key)
            result += '            %d => Some(Self::%s),\n' % (value, display_name)
        result += '            _ => None,\n'
        result += '        }\n'
        result += '    }\n'
        result += '}\n'
        return result


def _get_field_type(field):
    """Get Rust type for a field (non-array, non-string)."""
    type_name = field.field_type
    if type_name in rust_types:
        return rust_types[type_name]
    # Nested enum: flattened as MsgNameEnumName
    type_msg = getattr(field, 'type_message', None)
    if type_msg and field.is_enum:
        return type_msg + type_name
    # Use type_package if available (for cross-package type references)
    type_pkg = getattr(field, 'type_package', None) or field.package
    if field.is_enum:
        return _rust_struct_name(type_pkg, type_name)
    return _rust_struct_name(type_pkg, type_name)


def _generate_field_decl(field):
    """Generate a Rust struct field declaration."""
    var_name = _escape_rust_field_name(field.name)
    type_name = _normalize_bytes_type(field.field_type)

    if field.is_array:
        if type_name == "string":
            elem_size = field.element_size if field.element_size else 16
            if field.size_option is not None:
                # Fixed string array: [[u8; elem_size]; size]
                return f'    pub {var_name}: [[u8; {elem_size}]; {field.size_option}],  // Fixed string array'
            elif field.max_size is not None:
                count_type = "u16" if field.max_size > 255 else "u8"
                return f'    pub {var_name}_count: {count_type},  // Bounded string array count\n    pub {var_name}: [[u8; {elem_size}]; {field.max_size}],  // Bounded string array: up to {field.max_size} strings'
        else:
            base_type = _get_field_type(field)
            if field.size_option is not None:
                return f'    pub {var_name}: [{base_type}; {field.size_option}],  // Fixed array'
            elif field.max_size is not None:
                count_type = "u16" if field.max_size > 255 else "u8"
                return f'    pub {var_name}_count: {count_type},  // Bounded array count\n    pub {var_name}: [{base_type}; {field.max_size}],  // Bounded array: up to {field.max_size} elements'
    elif type_name == "string":
        if field.size_option is not None:
            return f'    pub {var_name}: [u8; {field.size_option}],  // Fixed string: {field.size_option} bytes'
        elif field.max_size is not None:
            count_type = "u16" if field.max_size > 255 else "u8"
            return f'    pub {var_name}_length: {count_type},  // Variable string length\n    pub {var_name}: [u8; {field.max_size}],  // Variable string: up to {field.max_size} bytes'
    else:
        base_type = _get_field_type(field)
        return f'    pub {var_name}: {base_type},'

    return f'    pub {var_name}: u8,  // Unknown type'


def _generate_pack_field(field, indent='        ', variable=False):
    """Generate pack code for a single field.

    When variable=True, bounded arrays and variable strings are packed with
    only actual elements (variable-length encoding). When variable=False,
    always packs max_size elements (fixed-size encoding).

    C3: u8 fixed/bounded arrays use copy_from_slice bulk copy.
    A5: nested messages always use pack_max_size (fixed-size on wire).
    """
    var_name = _escape_rust_field_name(field.name)
    type_name = _normalize_bytes_type(field.field_type)
    lines = []

    if field.is_array:
        if type_name == "string":
            elem_size = field.element_size if field.element_size else 16
            if field.size_option is not None:
                # Fixed string array - same in both modes
                lines.append(f'{indent}// Fixed string array: {var_name}')
                lines.append(f'{indent}for i in 0..{field.size_option} {{')
                lines.append(f'{indent}    buf[_pos.._pos+{elem_size}].copy_from_slice(&self.{var_name}[i]);')
                lines.append(f'{indent}    _pos += {elem_size};')
                lines.append(f'{indent}}}')
            elif field.max_size is not None:
                count_size = 2 if field.max_size > 255 else 1
                count_fmt = "u16" if field.max_size > 255 else "u8"
                loop_limit = f'self.{var_name}_count as usize' if variable else str(field.max_size)
                lines.append(f'{indent}// Bounded string array: {var_name}')
                lines.append(f'{indent}buf[_pos.._pos+{count_size}].copy_from_slice(&self.{var_name}_count.to_le_bytes());')
                lines.append(f'{indent}_pos += {count_size};')
                lines.append(f'{indent}for i in 0..{loop_limit} {{')
                lines.append(f'{indent}    buf[_pos.._pos+{elem_size}].copy_from_slice(&self.{var_name}[i]);')
                lines.append(f'{indent}    _pos += {elem_size};')
                lines.append(f'{indent}}}')
        else:
            if type_name in rust_type_sizes:
                type_size = rust_type_sizes[type_name]
                if field.size_option is not None:
                    # C3: u8 fixed arrays — bulk copy
                    if type_name == "uint8":
                        lines.append(f'{indent}// Fixed array: {var_name}')
                        lines.append(f'{indent}buf[_pos.._pos+{field.size_option}].copy_from_slice(&self.{var_name});')
                        lines.append(f'{indent}_pos += {field.size_option};')
                    else:
                        lines.append(f'{indent}// Fixed array: {var_name}')
                        lines.append(f'{indent}for i in 0..{field.size_option} {{')
                        if type_name == "bool":
                            lines.append(f'{indent}    buf[_pos] = if self.{var_name}[i] {{ 1 }} else {{ 0 }};')
                            lines.append(f'{indent}    _pos += 1;')
                        elif type_size == 1:
                            lines.append(f'{indent}    buf[_pos] = self.{var_name}[i] as u8;')
                            lines.append(f'{indent}    _pos += 1;')
                        else:
                            lines.append(f'{indent}    buf[_pos.._pos+{type_size}].copy_from_slice(&self.{var_name}[i].to_le_bytes());')
                            lines.append(f'{indent}    _pos += {type_size};')
                        lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    loop_limit = f'self.{var_name}_count as usize' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded array: {var_name}')
                    lines.append(f'{indent}buf[_pos.._pos+{count_size}].copy_from_slice(&self.{var_name}_count.to_le_bytes());')
                    lines.append(f'{indent}_pos += {count_size};')
                    # C3: u8 bounded arrays — bulk copy
                    if type_name == "uint8":
                        lines.append(f'{indent}let _n = {loop_limit};')
                        lines.append(f'{indent}buf[_pos.._pos+_n].copy_from_slice(&self.{var_name}[.._n]);')
                        lines.append(f'{indent}_pos += _n;')
                    else:
                        lines.append(f'{indent}for i in 0..{loop_limit} {{')
                        if type_name == "bool":
                            lines.append(f'{indent}    buf[_pos] = if self.{var_name}[i] {{ 1 }} else {{ 0 }};')
                            lines.append(f'{indent}    _pos += 1;')
                        elif type_size == 1:
                            lines.append(f'{indent}    buf[_pos] = self.{var_name}[i] as u8;')
                            lines.append(f'{indent}    _pos += 1;')
                        else:
                            lines.append(f'{indent}    buf[_pos.._pos+{type_size}].copy_from_slice(&self.{var_name}[i].to_le_bytes());')
                            lines.append(f'{indent}    _pos += {type_size};')
                        lines.append(f'{indent}}}')
            elif field.is_enum:
                # Enum array (u8)
                if field.size_option is not None:
                    lines.append(f'{indent}// Fixed enum array: {var_name}')
                    lines.append(f'{indent}for i in 0..{field.size_option} {{')
                    lines.append(f'{indent}    buf[_pos] = self.{var_name}[i] as u8;')
                    lines.append(f'{indent}    _pos += 1;')
                    lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    loop_limit = f'self.{var_name}_count as usize' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded enum array: {var_name}')
                    lines.append(f'{indent}buf[_pos.._pos+{count_size}].copy_from_slice(&self.{var_name}_count.to_le_bytes());')
                    lines.append(f'{indent}_pos += {count_size};')
                    lines.append(f'{indent}for i in 0..{loop_limit} {{')
                    lines.append(f'{indent}    buf[_pos] = self.{var_name}[i] as u8;')
                    lines.append(f'{indent}    _pos += 1;')
                    lines.append(f'{indent}}}')
            else:
                # A5: nested message arrays — always pack_max_size (fixed-size on wire)
                if field.size_option is not None:
                    lines.append(f'{indent}// Fixed nested message array: {var_name}')
                    lines.append(f'{indent}for i in 0..{field.size_option} {{')
                    lines.append(f'{indent}    _pos += self.{var_name}[i].pack_max_size(&mut buf[_pos..]);')
                    lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    loop_limit = f'self.{var_name}_count as usize' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded nested message array: {var_name}')
                    lines.append(f'{indent}buf[_pos.._pos+{count_size}].copy_from_slice(&self.{var_name}_count.to_le_bytes());')
                    lines.append(f'{indent}_pos += {count_size};')
                    lines.append(f'{indent}for i in 0..{loop_limit} {{')
                    lines.append(f'{indent}    _pos += self.{var_name}[i].pack_max_size(&mut buf[_pos..]);')
                    lines.append(f'{indent}}}')
    elif type_name == "string":
        if field.size_option is not None:
            # Fixed string - same in both modes
            lines.append(f'{indent}// Fixed string: {var_name}')
            lines.append(f'{indent}buf[_pos.._pos+{field.size_option}].copy_from_slice(&self.{var_name});')
            lines.append(f'{indent}_pos += {field.size_option};')
        elif field.max_size is not None:
            count_size = 2 if field.max_size > 255 else 1
            lines.append(f'{indent}// Variable string: {var_name}')
            lines.append(f'{indent}buf[_pos.._pos+{count_size}].copy_from_slice(&self.{var_name}_length.to_le_bytes());')
            lines.append(f'{indent}_pos += {count_size};')
            if variable:
                lines.append(f'{indent}let _str_len = self.{var_name}_length as usize;')
                lines.append(f'{indent}buf[_pos.._pos+_str_len].copy_from_slice(&self.{var_name}[.._str_len]);')
                lines.append(f'{indent}_pos += _str_len;')
            else:
                lines.append(f'{indent}buf[_pos.._pos+{field.max_size}].copy_from_slice(&self.{var_name});')
                lines.append(f'{indent}_pos += {field.max_size};')
    else:
        if type_name in rust_pack_fns:
            pack_stmt, type_size = rust_pack_fns[type_name]
            pack_stmt = pack_stmt.replace('{f}', var_name)
            lines.append(f'{indent}{pack_stmt}')
            lines.append(f'{indent}_pos += {type_size};')
        elif field.is_enum:
            lines.append(f'{indent}buf[_pos] = self.{var_name} as u8;')
            lines.append(f'{indent}_pos += 1;')
        else:
            # A5: nested message — always pack_max_size (fixed-size on wire)
            lines.append(f'{indent}_pos += self.{var_name}.pack_max_size(&mut buf[_pos..]);')

    return '\n'.join(lines)


def _generate_unpack_field(field, indent='        ', variable=False):
    """Generate unpack code for a single field.

    When variable=True, bounded arrays and variable strings are unpacked with
    only actual elements (variable-length). When variable=False (fixed),
    always reads max_size elements.

    A1: all reads use buf.get(...)? / *buf.get(_pos)? to avoid panics on truncated input.
    A5: nested messages are always read from a bounded SIZE-byte slice (fixed-size on wire).
    """
    var_name = _escape_rust_field_name(field.name)
    type_name = _normalize_bytes_type(field.field_type)
    lines = []

    if field.is_array:
        if type_name == "string":
            elem_size = field.element_size if field.element_size else 16
            if field.size_option is not None:
                lines.append(f'{indent}// Fixed string array: {var_name}')
                lines.append(f'{indent}let mut {var_name}: [[u8; {elem_size}]; {field.size_option}] = [[0u8; {elem_size}]; {field.size_option}];')
                lines.append(f'{indent}for i in 0..{field.size_option} {{')
                # A1: safe slice
                lines.append(f'{indent}    {var_name}[i].copy_from_slice(buf.get(_pos.._pos+{elem_size})?);')
                lines.append(f'{indent}    _pos += {elem_size};')
                lines.append(f'{indent}}}')
            elif field.max_size is not None:
                count_size = 2 if field.max_size > 255 else 1
                count_type = "u16" if field.max_size > 255 else "u8"
                loop_limit = f'({var_name}_count as usize).min({field.max_size})' if variable else str(field.max_size)
                lines.append(f'{indent}// Bounded string array: {var_name}')
                lines.append(f'{indent}let {var_name}_count = {count_type}::from_le_bytes(buf.get(_pos.._pos+{count_size})?.try_into().ok()?);')
                lines.append(f'{indent}_pos += {count_size};')
                lines.append(f'{indent}let mut {var_name}: [[u8; {elem_size}]; {field.max_size}] = [[0u8; {elem_size}]; {field.max_size}];')
                lines.append(f'{indent}for i in 0..{loop_limit} {{')
                # A1: safe slice
                lines.append(f'{indent}    {var_name}[i].copy_from_slice(buf.get(_pos.._pos+{elem_size})?);')
                lines.append(f'{indent}    _pos += {elem_size};')
                lines.append(f'{indent}}}')
        else:
            if type_name in rust_type_sizes:
                type_size = rust_type_sizes[type_name]
                rust_t = rust_types[type_name]
                if field.size_option is not None:
                    lines.append(f'{indent}// Fixed array: {var_name}')
                    lines.append(f'{indent}let mut {var_name}: [{rust_t}; {field.size_option}] = [{rust_t}::default(); {field.size_option}];')
                    lines.append(f'{indent}for i in 0..{field.size_option} {{')
                    if type_name == "bool":
                        lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)? != 0;')
                        lines.append(f'{indent}    _pos += 1;')
                    elif type_size == 1:
                        if type_name == "int8":
                            lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)? as i8;')
                        else:
                            lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)?;')
                        lines.append(f'{indent}    _pos += 1;')
                    else:
                        lines.append(f'{indent}    {var_name}[i] = {rust_t}::from_le_bytes(buf.get(_pos.._pos+{type_size})?.try_into().ok()?);')
                        lines.append(f'{indent}    _pos += {type_size};')
                    lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    count_type = "u16" if field.max_size > 255 else "u8"
                    loop_limit = f'({var_name}_count as usize).min({field.max_size})' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded array: {var_name}')
                    lines.append(f'{indent}let {var_name}_count = {count_type}::from_le_bytes(buf.get(_pos.._pos+{count_size})?.try_into().ok()?);')
                    lines.append(f'{indent}_pos += {count_size};')
                    lines.append(f'{indent}let mut {var_name}: [{rust_t}; {field.max_size}] = [{rust_t}::default(); {field.max_size}];')
                    lines.append(f'{indent}for i in 0..{loop_limit} {{')
                    if type_name == "bool":
                        lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)? != 0;')
                        lines.append(f'{indent}    _pos += 1;')
                    elif type_size == 1:
                        if type_name == "int8":
                            lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)? as i8;')
                        else:
                            lines.append(f'{indent}    {var_name}[i] = *buf.get(_pos)?;')
                        lines.append(f'{indent}    _pos += 1;')
                    else:
                        lines.append(f'{indent}    {var_name}[i] = {rust_t}::from_le_bytes(buf.get(_pos.._pos+{type_size})?.try_into().ok()?);')
                        lines.append(f'{indent}    _pos += {type_size};')
                    lines.append(f'{indent}}}')
            elif field.is_enum:
                type_msg = getattr(field, 'type_message', None)
                if type_msg:
                    enum_type = type_msg + field.field_type
                else:
                    enum_type = _rust_struct_name(getattr(field, "type_package", None) or field.package, field.field_type)
                if field.size_option is not None:
                    lines.append(f'{indent}// Fixed enum array: {var_name}')
                    lines.append(f'{indent}let mut {var_name}: [{enum_type}; {field.size_option}] = [{enum_type}::default(); {field.size_option}];')
                    lines.append(f'{indent}for i in 0..{field.size_option} {{')
                    lines.append(f'{indent}    {var_name}[i] = {enum_type}::from_u8(*buf.get(_pos)?).unwrap_or_default();')
                    lines.append(f'{indent}    _pos += 1;')
                    lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    count_type = "u16" if field.max_size > 255 else "u8"
                    loop_limit = f'({var_name}_count as usize).min({field.max_size})' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded enum array: {var_name}')
                    lines.append(f'{indent}let {var_name}_count = {count_type}::from_le_bytes(buf.get(_pos.._pos+{count_size})?.try_into().ok()?);')
                    lines.append(f'{indent}_pos += {count_size};')
                    lines.append(f'{indent}let mut {var_name}: [{enum_type}; {field.max_size}] = [{enum_type}::default(); {field.max_size}];')
                    lines.append(f'{indent}for i in 0..{loop_limit} {{')
                    lines.append(f'{indent}    {var_name}[i] = {enum_type}::from_u8(*buf.get(_pos)?).unwrap_or_default();')
                    lines.append(f'{indent}    _pos += 1;')
                    lines.append(f'{indent}}}')
            else:
                # A5: nested message array — bounded slice, always fixed-size decode
                nested_type = _rust_struct_name(getattr(field, "type_package", None) or field.package, field.field_type)
                if field.size_option is not None:
                    lines.append(f'{indent}// Fixed nested message array: {var_name}')
                    lines.append(f'{indent}let mut {var_name}: [{nested_type}; {field.size_option}] = [{nested_type}::default(); {field.size_option}];')
                    lines.append(f'{indent}for i in 0..{field.size_option} {{')
                    lines.append(f'{indent}    let msg = {nested_type}::unpack(buf.get(_pos.._pos+{nested_type}::SIZE)?)?;')
                    lines.append(f'{indent}    _pos += {nested_type}::SIZE;')
                    lines.append(f'{indent}    {var_name}[i] = msg;')
                    lines.append(f'{indent}}}')
                elif field.max_size is not None:
                    count_size = 2 if field.max_size > 255 else 1
                    count_type = "u16" if field.max_size > 255 else "u8"
                    loop_limit = f'({var_name}_count as usize).min({field.max_size})' if variable else str(field.max_size)
                    lines.append(f'{indent}// Bounded nested message array: {var_name}')
                    lines.append(f'{indent}let {var_name}_count = {count_type}::from_le_bytes(buf.get(_pos.._pos+{count_size})?.try_into().ok()?);')
                    lines.append(f'{indent}_pos += {count_size};')
                    lines.append(f'{indent}let mut {var_name}: [{nested_type}; {field.max_size}] = [{nested_type}::default(); {field.max_size}];')
                    lines.append(f'{indent}for i in 0..{loop_limit} {{')
                    lines.append(f'{indent}    let msg = {nested_type}::unpack(buf.get(_pos.._pos+{nested_type}::SIZE)?)?;')
                    lines.append(f'{indent}    _pos += {nested_type}::SIZE;')
                    lines.append(f'{indent}    {var_name}[i] = msg;')
                    lines.append(f'{indent}}}')
    elif type_name == "string":
        if field.size_option is not None:
            lines.append(f'{indent}// Fixed string: {var_name}')
            lines.append(f'{indent}let mut {var_name} = [0u8; {field.size_option}];')
            lines.append(f'{indent}let _str_slice = buf.get(_pos.._pos+{field.size_option})?;')
            lines.append(f'{indent}{var_name}.copy_from_slice(_str_slice);')
            lines.append(f'{indent}_pos += {field.size_option};')
        elif field.max_size is not None:
            count_size = 2 if field.max_size > 255 else 1
            count_type = "u16" if field.max_size > 255 else "u8"
            lines.append(f'{indent}// Variable string: {var_name}')
            lines.append(f'{indent}let {var_name}_length = {count_type}::from_le_bytes(buf.get(_pos.._pos+{count_size})?.try_into().ok()?);')
            lines.append(f'{indent}_pos += {count_size};')
            lines.append(f'{indent}let mut {var_name} = [0u8; {field.max_size}];')
            if variable:
                lines.append(f'{indent}let _str_len = ({var_name}_length as usize).min({field.max_size});')
                lines.append(f'{indent}let _str_slice = buf.get(_pos.._pos+_str_len)?;')
                lines.append(f'{indent}{var_name}[.._str_len].copy_from_slice(_str_slice);')
                lines.append(f'{indent}_pos += _str_len;')
            else:
                lines.append(f'{indent}let _str_slice = buf.get(_pos.._pos+{field.max_size})?;')
                lines.append(f'{indent}{var_name}.copy_from_slice(_str_slice);')
                lines.append(f'{indent}_pos += {field.max_size};')
    else:
        if type_name in rust_unpack_fns:
            unpack_expr, type_size = rust_unpack_fns[type_name]
            # A1: replace bare buf[_pos] with safe *buf.get(_pos)?
            safe_expr = unpack_expr.replace('buf[_pos]', '*buf.get(_pos)?')
            # A1: replace multi-byte buf[_pos.._pos+N] with safe buf.get(...)?
            import re as _re
            safe_expr = _re.sub(
                r'buf\[_pos\.\._pos\+(\d+)\]',
                r'buf.get(_pos.._pos+\1)?',
                safe_expr
            )
            lines.append(f'{indent}let {var_name} = {safe_expr};')
            lines.append(f'{indent}_pos += {type_size};')
        elif field.is_enum:
            type_msg = getattr(field, 'type_message', None)
            if type_msg:
                enum_type = type_msg + field.field_type
            else:
                enum_type = _rust_struct_name(getattr(field, "type_package", None) or field.package, field.field_type)
            # A1: safe single-byte read
            lines.append(f'{indent}let {var_name} = {enum_type}::from_u8(*buf.get(_pos)?).unwrap_or_default();')
            lines.append(f'{indent}_pos += 1;')
        else:
            # A5: nested message — bounded slice for fixed-size decode
            nested_type = _rust_struct_name(getattr(field, "type_package", None) or field.package, field.field_type)
            lines.append(f'{indent}let {var_name} = {nested_type}::unpack(buf.get(_pos.._pos+{nested_type}::SIZE)?)?;')
            lines.append(f'{indent}_pos += {nested_type}::SIZE;')

    return '\n'.join(lines)


def _get_field_var_names(field):
    """Get variable names introduced by _generate_unpack_field for a field.
    Order must match the declaration order in _generate_unpack_field."""
    var_name = _escape_rust_field_name(field.name)
    type_name = field.field_type
    names = []

    if field.is_array:
        if field.max_size is not None:
            # Bounded arrays declare count first, then the array
            names.append(f'{var_name}_count')
        names.append(var_name)
    elif type_name == "string":
        if field.max_size is not None:
            names.append(f'{var_name}_length')
        names.append(var_name)
    else:
        names.append(var_name)

    return names


def _msg_is_variable(msg):
    """Returns True if the message uses variable-length encoding (has option variable = true in proto)."""
    return getattr(msg, 'variable', False)


def _large_array_size(field):
    """Returns array size if field is a large array needing manual Default, else 0."""
    if field.is_array:
        if field.size_option is not None and field.size_option > 32:
            return field.size_option
        if field.max_size is not None and field.max_size > 32:
            return field.max_size
    if field.field_type in ("string", "bytes"):
        if field.size_option is not None and field.size_option > 32:
            return field.size_option
        if field.max_size is not None and field.max_size > 32:
            return field.max_size
    return 0


def _needs_manual_default(msg):
    """Returns True if the message struct has arrays larger than 32 elements."""
    for field in msg.fields.values():
        if _large_array_size(field) > 0:
            return True
        # Non-array string/bytes fields with large max_size or size_option
        if field.field_type in ("string", "bytes") and not field.is_array:
            if field.size_option is not None and field.size_option > 32:
                return True
            if field.max_size is not None and field.max_size > 32:
                return True
    for oneof in msg.oneofs.values():
        if oneof.size > 32:
            return True
    return False


def _rust_zero_literal(type_name):
    """Get the zero literal for a Rust type."""
    if type_name in ('float',):
        return '0.0f32'
    if type_name in ('double',):
        return '0.0f64'
    if type_name == 'bool':
        return 'false'
    return '0'


def _generate_default_impl(msg, struct_name):
    """Generate manual Default implementation for structs with large arrays."""
    result = f'impl Default for {struct_name} {{\n'
    result += '    fn default() -> Self {\n'
    result += '        Self {\n'
    for field in msg.fields.values():
        var_name = _escape_rust_field_name(field.name)
        type_name = _normalize_bytes_type(field.field_type)
        if field.is_array:
            if field.size_option is not None:
                if type_name == "string":
                    elem_size = field.element_size if field.element_size else 16
                    result += f'            {var_name}: [[0u8; {elem_size}]; {field.size_option}],\n'
                elif type_name in rust_types:
                    zero = _rust_zero_literal(type_name)
                    result += f'            {var_name}: [{zero}; {field.size_option}],\n'
                else:
                    nested_type = _get_field_type(field)
                    result += f'            {var_name}: core::array::from_fn(|_| {nested_type}::default()),\n'
            elif field.max_size is not None:
                result += f'            {var_name}_count: 0,\n'
                if type_name == "string":
                    elem_size = field.element_size if field.element_size else 16
                    result += f'            {var_name}: [[0u8; {elem_size}]; {field.max_size}],\n'
                elif type_name in rust_types:
                    zero = _rust_zero_literal(type_name)
                    result += f'            {var_name}: [{zero}; {field.max_size}],\n'
                else:
                    nested_type = _get_field_type(field)
                    result += f'            {var_name}: core::array::from_fn(|_| {nested_type}::default()),\n'
        elif type_name == "string":
            if field.size_option is not None:
                result += f'            {var_name}: [0u8; {field.size_option}],\n'
            elif field.max_size is not None:
                result += f'            {var_name}_length: 0,\n'
                result += f'            {var_name}: [0u8; {field.max_size}],\n'
            else:
                result += f'            {var_name}: Default::default(),\n'
        else:
            result += f'            {var_name}: Default::default(),\n'
    for oneof_name, oneof in msg.oneofs.items():
        if oneof.auto_discriminator:
            result += f'            {oneof_name}_discriminator: 0,\n'
        result += f'            {oneof_name}_bytes: [0u8; {oneof.size}],\n'
    result += '        }\n'
    result += '    }\n'
    result += '}\n\n'
    return result


class MessageRustGen():
    @staticmethod
    def generate(msg, package=None, equality=False):
        """Generate a Rust struct and impl for a message."""
        struct_name = _rust_struct_name(msg.package, msg.name)
        const_prefix = _rust_const_prefix(msg.package, msg.name)

        result = ''

        # Comments
        if msg.comments:
            for c in msg.comments:
                result += '//%s\n' % c

        # Emit nested enum definitions before the struct (Rust has no nested types in structs)
        for enum_name, enum in msg.enums.items():
            result += EnumRustGen.generate_for_message(enum, struct_name)
            result += '\n'

        # Derive attributes (Default is manually implemented if large arrays are present)
        needs_manual_default = _needs_manual_default(msg)
        eq_derive = ', PartialEq' if equality else ''
        if needs_manual_default:
            result += f'#[derive(Debug, Clone{eq_derive})]\n'
        else:
            result += f'#[derive(Debug, Clone, Default{eq_derive})]\n'
        result += 'pub struct %s {\n' % struct_name

        # Regular fields
        for key, field in msg.fields.items():
            if field.comments:
                for c in field.comments:
                    result += '    //%s\n' % c
            decl = _generate_field_decl(field)
            result += decl + '\n'

        # Oneof fields: discriminator + raw bytes storage (union semantics)
        for oneof_name, oneof in msg.oneofs.items():
            if oneof.comments:
                for c in oneof.comments:
                    result += '    //%s\n' % c
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    result += f'    pub {oneof_name}_discriminator: u16,  // Auto-generated message ID discriminator\n'
                else:
                    result += f'    pub {oneof_name}_discriminator: u8,  // Field order discriminator\n'
            result += f'    pub {oneof_name}_bytes: [u8; {oneof.size}],  // Union storage: max of all variant sizes\n'

        result += '}\n\n'

        # Manual Default implementation if needed
        if needs_manual_default:
            result += _generate_default_impl(msg, struct_name)

        # Constants
        has_msg_id = msg.id is not None
        is_variable = _msg_is_variable(msg)
        if has_msg_id:
            msg_id_value = msg.id
            if package and package.package_id is not None:
                msg_id_value = (package.package_id << 8) | msg.id
            magic1 = msg.magic_bytes[0] if msg.magic_bytes else 0
            magic2 = msg.magic_bytes[1] if msg.magic_bytes else 0
            result += f'pub const {const_prefix}_MSG_ID: u16 = {msg_id_value};\n'
            result += f'pub const {const_prefix}_MAX_SIZE: usize = {msg.size};\n'
            result += f'pub const {const_prefix}_BASE_SIZE: usize = {msg.base_size};\n'
            result += f'pub const {const_prefix}_MAGIC1: u8 = {magic1};\n'
            result += f'pub const {const_prefix}_MAGIC2: u8 = {magic2};\n'
        else:
            result += f'pub const {const_prefix}_MAX_SIZE: usize = {msg.size};\n'

        result += '\n'

        # impl block
        result += 'impl %s {\n' % struct_name

        if has_msg_id:
            result += f'    pub const MSG_ID: u16 = {const_prefix}_MSG_ID;\n'
            result += f'    pub const MAX_SIZE: usize = {const_prefix}_MAX_SIZE;\n'
            result += f'    pub const SIZE: usize = {const_prefix}_MAX_SIZE;\n'
            result += f'    pub const BASE_SIZE: usize = {const_prefix}_BASE_SIZE;\n'
            result += f'    pub const MAGIC1: u8 = {const_prefix}_MAGIC1;\n'
            result += f'    pub const MAGIC2: u8 = {const_prefix}_MAGIC2;\n'
            result += f'    pub const IS_VARIABLE: bool = {str(is_variable).lower()};\n'
        else:
            result += f'    pub const MAX_SIZE: usize = {const_prefix}_MAX_SIZE;\n'
            result += f'    pub const SIZE: usize = {const_prefix}_MAX_SIZE;\n'

        # Oneof accessor methods
        for oneof_name, oneof in msg.oneofs.items():
            for field_name, field in oneof.fields.items():
                nested_type = _rust_struct_name(getattr(field, "type_package", None) or field.package, field.field_type)
                result += f'\n    /// Get {field_name} from the {oneof_name} oneof.\n'
                result += f'    pub fn get_{field_name}(&self) -> Option<{nested_type}> {{\n'
                # A4: slice to exactly MAX_SIZE so unpack dispatches to the fixed path
                result += f'        {nested_type}::unpack(&self.{oneof_name}_bytes[..{nested_type}::MAX_SIZE])\n'
                result += f'    }}\n'
                result += f'\n    /// Set {field_name} in the {oneof_name} oneof.\n'
                result += f'    pub fn set_{field_name}(&mut self, msg: &{nested_type}) {{\n'
                if oneof.auto_discriminator:
                    if oneof.discriminator_type == "msgid":
                        result += f'        self.{oneof_name}_discriminator = {nested_type}::MSG_ID;\n'
                    else:
                        # field_order: find the 1-based index of this field
                        idx = list(oneof.fields.keys()).index(field_name) + 1
                        result += f'        self.{oneof_name}_discriminator = {idx};\n'
                result += f'        let mut tmp = [0u8; {oneof.size}];\n'
                result += f'        msg.pack_max_size(&mut tmp);\n'
                result += f'        self.{oneof_name}_bytes.copy_from_slice(&tmp[..{oneof.size}]);\n'
                result += f'    }}\n'

        # Helper to generate oneof pack code
        def _pack_oneofs(result, variable_pack=False):
            for oneof_name, oneof in msg.oneofs.items():
                if oneof.auto_discriminator:
                    if oneof.discriminator_type == "msgid":
                        result += f'        // Oneof {oneof_name} discriminator (msgid)\n'
                        result += f'        buf[_pos.._pos+2].copy_from_slice(&self.{oneof_name}_discriminator.to_le_bytes());\n'
                        result += f'        _pos += 2;\n'
                    else:
                        result += f'        // Oneof {oneof_name} discriminator (field_order)\n'
                        result += f'        buf[_pos] = self.{oneof_name}_discriminator;\n'
                        result += f'        _pos += 1;\n'
                if oneof.variable and variable_pack:
                    result += f'        // Oneof {oneof_name} variable-length union bytes\n'
                    result += f'        let _{oneof_name}_raw_len: u16 = match self.{oneof_name}_discriminator as u16 {{\n'
                    for disc_val, field_name, field_size in oneof.variant_info:
                        result += f'            {disc_val} => {field_size},  // {field_name}\n'
                    result += f'            _ => 0,\n'
                    result += f'        }};\n'
                    if oneof.min_size_override:
                        result += f'        let _{oneof_name}_len: u16 = if _{oneof_name}_raw_len < {oneof.min_size_override} {{ {oneof.min_size_override} }} else {{ _{oneof_name}_raw_len }};\n'
                    else:
                        result += f'        let _{oneof_name}_len: u16 = _{oneof_name}_raw_len;\n'
                    result += f'        buf[_pos.._pos+2].copy_from_slice(&_{oneof_name}_len.to_le_bytes());\n'
                    result += f'        _pos += 2;\n'
                    result += f'        buf[_pos.._pos+_{oneof_name}_raw_len as usize].copy_from_slice(&self.{oneof_name}_bytes[.._{oneof_name}_raw_len as usize]);\n'
                    if oneof.min_size_override:
                        result += f'        if _{oneof_name}_len > _{oneof_name}_raw_len {{\n'
                        result += f'            buf[_pos+_{oneof_name}_raw_len as usize.._pos+_{oneof_name}_len as usize].fill(0);\n'
                        result += f'        }}\n'
                    result += f'        _pos += _{oneof_name}_len as usize;\n'
                elif oneof.variable and not variable_pack:
                    # A3: pack_max_size must write full fixed-size oneof bytes (no length prefix)
                    result += f'        // Oneof {oneof_name} union bytes (fixed-size pad to {oneof.size})\n'
                    result += f'        buf[_pos.._pos+{oneof.size}].copy_from_slice(&self.{oneof_name}_bytes);\n'
                    result += f'        _pos += {oneof.size};\n'
                elif variable_pack and oneof.auto_discriminator:
                    _min_sz = oneof.min_size_override or 0
                    _trim_label = f'trimmed union bytes (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union bytes'
                    result += f'        // Oneof {oneof_name} {_trim_label}\n'
                    result += f'        let _{oneof_name}_tlen: usize = match self.{oneof_name}_discriminator as u16 {{\n'
                    for disc_val, field_name, field_size in oneof.variant_info:
                        result += f'            {disc_val} => {max(field_size, _min_sz)},  // {field_name}\n'
                    result += f'            _ => {_min_sz},\n'
                    result += f'        }};\n'
                    result += f'        buf[_pos.._pos+_{oneof_name}_tlen].copy_from_slice(&self.{oneof_name}_bytes[.._{oneof_name}_tlen]);\n'
                    result += f'        _pos += _{oneof_name}_tlen;\n'
                else:
                    result += f'        // Oneof {oneof_name} union bytes\n'
                    result += f'        buf[_pos.._pos+{oneof.size}].copy_from_slice(&self.{oneof_name}_bytes);\n'
                    result += f'        _pos += {oneof.size};\n'
            return result

        # pack method (variable-length for IS_VARIABLE, same as pack_max_size for fixed)
        result += '\n    /// Serialize the message into a byte buffer. Returns bytes written.\n'
        if is_variable:
            result += '    /// For variable messages, only actual data is written (not padded to MAX_SIZE).\n'
        result += '    pub fn pack(&self, buf: &mut [u8]) -> usize {\n'
        result += '        let mut _pos = 0usize;\n'
        for key, field in msg.fields.items():
            pack_code = _generate_pack_field(field, variable=is_variable)
            if pack_code:
                result += pack_code + '\n'
        result = _pack_oneofs(result, variable_pack=is_variable)
        result += '        _pos\n'
        result += '    }\n'

        # pack_max_size method (always fixed-size, writes MAX_SIZE bytes)
        result += '\n    /// Serialize the message to exactly MAX_SIZE bytes (fixed-size encoding).\n'
        result += '    /// Use this for profiles without a length field (sensor, ipc).\n'
        result += '    pub fn pack_max_size(&self, buf: &mut [u8]) -> usize {\n'
        result += '        let mut _pos = 0usize;\n'
        for key, field in msg.fields.items():
            pack_code = _generate_pack_field(field, variable=False)
            if pack_code:
                result += pack_code + '\n'
        result = _pack_oneofs(result)
        result += '        _pos\n'
        result += '    }\n'

        # unpack method - smart dispatch for variable messages
        result += '\n    /// Deserialize a message from a byte buffer. Returns None if buffer is too small.\n'
        if is_variable:
            result += '    /// For variable messages: if buf.len() == MAX_SIZE, uses fixed-size reading;\n'
            result += '    /// otherwise uses variable-length reading.\n'
        result += '    pub fn unpack(buf: &[u8]) -> Option<Self> {\n'

        if is_variable:
            has_variable_oneof = any(o.variable for o in msg.oneofs.values())
            if has_variable_oneof:
                # Variable oneof: memcpy shortcut invalid (wire has length prefix, struct doesn't)
                result += '        // Variable oneof message - always use variable-length unpack\n'
                result += '        Self::_unpack_variable(buf)\n'
                result += '    }\n'
            else:
                result += '        if buf.len() == Self::MAX_SIZE {\n'
                result += '            Self::_unpack_fixed(buf)\n'
                result += '        } else {\n'
                result += '            Self::_unpack_variable(buf)\n'
                result += '        }\n'
                result += '    }\n'

            # Helper to build unpack body
            def _build_unpack_body(result, variable_mode, indent='        '):
                field_names = []
                result += f'{indent}if buf.len() < Self::{"SIZE" if not variable_mode else "MIN_SIZE"} {{ return None; }}\n'
                result += f'{indent}let mut _pos = 0usize;\n'
                result += f'{indent}#[allow(unused_variables)]\n'
                result += f'{indent}let _ = _pos;\n'
                for key, field in msg.fields.items():
                    unpack_code = _generate_unpack_field(field, variable=variable_mode)
                    if unpack_code:
                        result += unpack_code + '\n'
                    field_names.extend(_get_field_var_names(field))
                oneof_var_names = []
                for oneof_name, oneof in msg.oneofs.items():
                    if oneof.auto_discriminator:
                        if oneof.discriminator_type == "msgid":
                            # A1: safe read
                            result += f'{indent}let {oneof_name}_discriminator = u16::from_le_bytes(buf.get(_pos.._pos+2)?.try_into().ok()?);\n'
                            result += f'{indent}_pos += 2;\n'
                            oneof_var_names.append(f'{oneof_name}_discriminator')
                        else:
                            # A1: safe read
                            result += f'{indent}let {oneof_name}_discriminator = *buf.get(_pos)?;\n'
                            result += f'{indent}_pos += 1;\n'
                            oneof_var_names.append(f'{oneof_name}_discriminator')
                    result += f'{indent}let mut {oneof_name}_bytes = [0u8; {oneof.size}];\n'
                    if oneof.variable:
                        # A1: safe read
                        result += f'{indent}let _{oneof_name}_len = u16::from_le_bytes(buf.get(_pos.._pos+2)?.try_into().ok()?) as usize;\n'
                        result += f'{indent}_pos += 2;\n'
                        result += f'{indent}if _pos + _{oneof_name}_len > buf.len() {{ return None; }}\n'
                        result += f'{indent}let _copy = _{oneof_name}_len.min({oneof.size});\n'
                        # A1: safe slice
                        result += f'{indent}{oneof_name}_bytes[.._copy].copy_from_slice(buf.get(_pos.._pos+_copy)?);\n'
                        result += f'{indent}_pos += _{oneof_name}_len;\n'
                    elif variable_mode and oneof.auto_discriminator:
                        _min_sz = oneof.min_size_override or 0
                        _trim_label = f'trimmed union read (min_size={oneof.min_size_override})' if oneof.min_size_override else 'trimmed union read'
                        result += f'{indent}// Oneof {oneof_name} {_trim_label}\n'
                        result += f'{indent}let _{oneof_name}_rlen: usize = match {oneof_name}_discriminator as u16 {{\n'
                        for disc_val, field_name, field_size in oneof.variant_info:
                            result += f'{indent}    {disc_val} => {max(field_size, _min_sz)},  // {field_name}\n'
                        result += f'{indent}    _ => {_min_sz},\n'
                        result += f'{indent}}};\n'
                        result += f'{indent}if _pos + _{oneof_name}_rlen > buf.len() {{ return None; }}\n'
                        result += f'{indent}let _copy = _{oneof_name}_rlen.min({oneof.size});\n'
                        # A1: safe slice
                        result += f'{indent}{oneof_name}_bytes[.._copy].copy_from_slice(buf.get(_pos.._pos+_copy)?);\n'
                        result += f'{indent}_pos += _{oneof_name}_rlen;\n'
                    else:
                        # A1: safe slice
                        result += f'{indent}{oneof_name}_bytes.copy_from_slice(buf.get(_pos.._pos+{oneof.size})?);\n'
                        result += f'{indent}_pos += {oneof.size};\n'
                    oneof_var_names.append(f'{oneof_name}_bytes')
                result += f'{indent}Some(Self {{\n'
                for var in field_names:
                    result += f'{indent}    {var},\n'
                for var in oneof_var_names:
                    result += f'{indent}    {var},\n'
                result += f'{indent}}})\n'
                return result

            # MIN_SIZE constant for variable messages
            result += '\n    /// Calculate minimum serialized size (all variable fields empty).\n'
            min_size = 0
            for field in msg.fields.values():
                if field.is_array:
                    if field.max_size is not None:
                        min_size += 2 if field.max_size > 255 else 1  # just the count
                    elif field.size_option is not None:
                        ts = rust_type_sizes.get(field.field_type, 1)
                        elem_size = field.element_size if (field.field_type in ("string", "bytes") and field.element_size) else ts
                        if field.field_type in ("string", "bytes"):
                            elem_size = field.element_size if field.element_size else 16
                        min_size += field.size_option * elem_size
                    else:
                        min_size += field.size if field.size else 0
                elif field.field_type in ("string", "bytes"):
                    if field.max_size is not None and field.size_option is None:
                        min_size += 2 if field.max_size > 255 else 1  # just the length
                    elif field.size_option is not None:
                        min_size += field.size_option
                    else:
                        min_size += field.size if field.size else 0
                else:
                    min_size += field.size if field.size else 0
            for oneof in msg.oneofs.values():
                if oneof.variable:
                    min_size += 2  # length prefix only; minimum payload is 0 bytes
                    if oneof.min_size_override:
                        min_size += oneof.min_size_override  # min_size guarantee
                elif oneof.auto_discriminator:
                    min_size += oneof.min_size_override or 0  # trimmed min is min_size (or 0 if unset)
                else:
                    min_size += oneof.size
                if oneof.auto_discriminator:
                    min_size += 2 if oneof.discriminator_type == "msgid" else 1
            result += f'    pub const MIN_SIZE: usize = {min_size};\n'

            # Fixed unpack (for sensor/ipc profiles where payload is MAX_SIZE)
            result += '\n    fn _unpack_fixed(buf: &[u8]) -> Option<Self> {\n'
            result = _build_unpack_body(result, variable_mode=False, indent='        ')
            result += '    }\n'

            # Variable unpack (for standard/bulk/network profiles where payload is variable)
            result += '\n    fn _unpack_variable(buf: &[u8]) -> Option<Self> {\n'
            result = _build_unpack_body(result, variable_mode=True, indent='        ')
            result += '    }\n'
        else:
            # Fixed message: simple unpack
            result += f'        if buf.len() < Self::SIZE {{ return None; }}\n'
            result += '        let mut _pos = 0usize;\n'
            result += '        #[allow(unused_variables)]\n'
            result += '        let _ = _pos;\n'
            field_names = []
            for key, field in msg.fields.items():
                unpack_code = _generate_unpack_field(field, variable=False)
                if unpack_code:
                    result += unpack_code + '\n'
                field_names.extend(_get_field_var_names(field))
            oneof_var_names = []
            for oneof_name, oneof in msg.oneofs.items():
                if oneof.auto_discriminator:
                    if oneof.discriminator_type == "msgid":
                        # A1: safe read
                        result += f'        let {oneof_name}_discriminator = u16::from_le_bytes(buf.get(_pos.._pos+2)?.try_into().ok()?);\n'
                        result += f'        _pos += 2;\n'
                        oneof_var_names.append(f'{oneof_name}_discriminator')
                    else:
                        # A1: safe read
                        result += f'        let {oneof_name}_discriminator = *buf.get(_pos)?;\n'
                        result += f'        _pos += 1;\n'
                        oneof_var_names.append(f'{oneof_name}_discriminator')
                result += f'        let mut {oneof_name}_bytes = [0u8; {oneof.size}];\n'
                if oneof.variable:
                    # A1: safe read
                    result += f'        let _{oneof_name}_len = u16::from_le_bytes(buf.get(_pos.._pos+2)?.try_into().ok()?) as usize;\n'
                    result += f'        _pos += 2;\n'
                    result += f'        if _pos + _{oneof_name}_len > buf.len() {{ return None; }}\n'
                    result += f'        let _copy = _{oneof_name}_len.min({oneof.size});\n'
                    # A1: safe slice
                    result += f'        {oneof_name}_bytes[.._copy].copy_from_slice(buf.get(_pos.._pos+_copy)?);\n'
                    result += f'        _pos += _{oneof_name}_len;\n'
                else:
                    # A1: safe slice
                    result += f'        {oneof_name}_bytes.copy_from_slice(buf.get(_pos.._pos+{oneof.size})?);\n'
                    result += f'        _pos += {oneof.size};\n'
                oneof_var_names.append(f'{oneof_name}_bytes')
            result += '        Some(Self {\n'
            for var in field_names:
                result += f'            {var},\n'
            for var in oneof_var_names:
                result += f'            {var},\n'
            result += '        })\n'
            result += '    }\n'

        # message_info method for messages with ID
        if has_msg_id:
            result += '\n    /// Get message info (size + magic numbers) for frame parsing.\n'
            result += '    pub fn message_info() -> crate::frame_base::MessageInfo {\n'
            if is_variable:
                # Variable messages: emit min_size so the reader can detect length errors
                result += f'        crate::frame_base::MessageInfo::new_variable(Self::MAX_SIZE, Self::MAGIC1, Self::MAGIC2, Self::BASE_SIZE, Self::MIN_SIZE)\n'
            else:
                result += f'        crate::frame_base::MessageInfo::new_with_base_size(Self::MAX_SIZE, Self::MAGIC1, Self::MAGIC2, Self::BASE_SIZE)\n'
            result += '    }\n'

        result += '}\n\n'

        # Implement StructFrameMessage for messages with IDs
        if has_msg_id:
            result += f'impl crate::frame_base::StructFrameMessage for {struct_name} {{\n'
            result += f'    const MSG_ID: u16 = {const_prefix}_MSG_ID;\n'
            result += f'    const MAX_SIZE: usize = {const_prefix}_MAX_SIZE;\n'
            result += f'    const MAGIC1: u8 = {const_prefix}_MAGIC1;\n'
            result += f'    const MAGIC2: u8 = {const_prefix}_MAGIC2;\n'
            # Only emit BASE_SIZE override when it differs from MAX_SIZE (extension messages).
            if msg.base_size < msg.size:
                result += f'    const BASE_SIZE: usize = {const_prefix}_BASE_SIZE;\n'
            result += f'    const IS_VARIABLE: bool = {str(is_variable).lower()};\n'
            result += f'    fn pack(&self, buf: &mut [u8]) -> usize {{ Self::pack(self, buf) }}\n'
            result += f'    fn pack_max_size(&self, buf: &mut [u8]) -> usize {{ Self::pack_max_size(self, buf) }}\n'
            result += f'    fn unpack(buf: &[u8]) -> Option<Self> {{ Self::unpack(buf) }}\n'
            result += f'}}\n\n'

        return result
class FileRustGen():
    """Generator for Rust files from proto definitions."""

    @staticmethod
    def generate(package, equality=False):
        """Generate Rust source code for a package."""
        result = []

        # File header
        result.append('// Automatically generated struct-frame Rust code\n')
        result.append(f'// Generated by struct-frame {version}\n')
        result.append('// DO NOT EDIT - regenerate using struct-frame\n\n')

        # Collect cross-package imports
        referenced_packages = set()
        for msg in package.messages.values():
            for field in msg.fields.values():
                type_pkg = getattr(field, 'type_package', None)
                if type_pkg and type_pkg != package.name and not field.is_default_type:
                    pkg_mod = type_pkg.replace('-', '_').replace(' ', '_')
                    referenced_packages.add(pkg_mod)
            for oneof in msg.oneofs.values():
                for field in oneof.fields.values():
                    type_pkg = getattr(field, 'type_package', None)
                    if type_pkg and type_pkg != package.name and not field.is_default_type:
                        pkg_mod = type_pkg.replace('-', '_').replace(' ', '_')
                        referenced_packages.add(pkg_mod)

        # Standard imports
        result.append('use crate::frame_base::MessageInfo;\n')
        for pkg_mod in sorted(referenced_packages):
            result.append(f'use crate::{pkg_mod}::*;\n')
        result.append('\n')

        # Package comments
        if hasattr(package, 'comments') and package.comments:
            for c in package.comments:
                result.append('//%s\n' % c)
            result.append('\n')

        # Generate enums
        if package.enums:
            result.append('// ============================================================================\n')
            result.append('// Enums\n')
            result.append('// ============================================================================\n\n')
            for key, enum in package.enums.items():
                result.append(EnumRustGen.generate(enum))
                result.append('\n')

        # Generate structs (messages without IDs first, then with IDs)
        if package.messages:
            result.append('// ============================================================================\n')
            result.append('// Message Structs\n')
            result.append('// ============================================================================\n\n')
            for key, msg in package.messages.items():
                result.append(MessageRustGen.generate(msg, package=package, equality=equality))

        # Generate get_message_info function
        msgs_with_id = [(k, v) for k, v in package.messages.items() if v.id is not None]
        if msgs_with_id:
            result.append('// ============================================================================\n')
            result.append('// Message info lookup\n')
            result.append('// ============================================================================\n\n')
            result.append('/// Look up message info (size + magic bytes) by message ID.\n')
            result.append('pub fn get_message_info(msg_id: u16) -> Option<MessageInfo> {\n')
            result.append('    match msg_id {\n')
            for key, msg in msgs_with_id:
                struct_name = _rust_struct_name(msg.package, msg.name)
                msg_id_value = msg.id
                if package.package_id is not None:
                    msg_id_value = (package.package_id << 8) | msg.id
                result.append(f'        {msg_id_value} => Some({struct_name}::message_info()),\n')
            result.append('        _ => None,\n')
            result.append('    }\n')
            result.append('}\n')
        else:
            result.append('/// Look up message info (size + magic bytes) by message ID.\n')
            result.append('pub fn get_message_info(_msg_id: u16) -> Option<MessageInfo> {\n')
            result.append('    None\n')
            result.append('}\n')

        return result

    @staticmethod
    def generate_cargo_toml(crate_name='struct_frame_sdk', output_path=None):
        """Generate a Cargo.toml for the generated crate.

        If *output_path* is provided, scan it for ``test_roundtrip_*.rs`` files
        and append a ``[[bin]]`` section for each one so they can be built via
        ``cargo build --bin test_roundtrip_<pkg>``.
        """
        toml = f'''[package]
name = "{crate_name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "{crate_name.replace("-", "_")}"
path = "lib.rs"
'''
        if output_path and os.path.isdir(output_path):
            for fname in sorted(os.listdir(output_path)):
                if fname.startswith('test_roundtrip_') and fname.endswith('.rs'):
                    bin_name = fname[:-3]
                    toml += f'\n[[bin]]\nname = "{bin_name}"\npath = "{fname}"\n'
        return toml

    @staticmethod
    def generate_lib_rs(package_names):
        """Generate a lib.rs that mods the boilerplate and all generated packages."""
        result = '// Auto-generated lib.rs for struct-frame SDK\n'
        result += '// DO NOT EDIT - regenerate using struct-frame\n\n'
        result += '#![allow(unused_imports, dead_code, non_camel_case_types)]\n\n'
        result += '// Boilerplate SDK modules\n'
        result += 'pub mod frame_base;\n'
        result += 'pub mod frame_headers;\n'
        result += 'pub mod payload_types;\n'
        result += 'pub mod frame_profiles;\n'
        result += 'pub mod struct_frame_sdk;\n\n'
        result += '// Re-export main SDK items at the crate root for backward compatibility.\n'
        result += '// Prefer `use your_crate::prelude::*;` in new code.\n'
        result += 'pub use frame_base::{\n'
        result += '    fletcher_checksum, fletcher_checksum_ext, FrameChecksum, FrameMsgInfo,\n'
        result += '    FrameMsgStatus, MessageInfo, ParserDiagnostics, StructFrameMessage,\n'
        result += '};\n'
        result += 'pub use frame_profiles::{\n'
        result += '    AccumulatingReader, BufferReader, BufferWriter, ProfileConfig,\n'
        result += '    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,\n'
        result += '    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,\n'
        result += '    encode_message_crc, encode_message_minimal, encode_minimal, encode_with_crc,\n'
        result += '    encode_with_crc_ext, parse_minimal, parse_with_crc,\n'
        result += '    new_bulk_reader, new_bulk_writer, new_ipc_reader, new_ipc_writer,\n'
        result += '    new_network_reader, new_network_writer, new_sensor_reader, new_sensor_writer,\n'
        result += '    new_standard_reader, new_standard_writer,\n'
        result += '};\n'
        result += 'pub use struct_frame_sdk::{MessageHandler, SendResult, Subscription, StructFrameSdk};\n\n'
        result += '/// Convenience prelude — preferred import for new code.\n'
        result += '/// ```rust\n'
        result += '/// use your_crate::prelude::*;\n'
        result += '/// ```\n'
        result += 'pub mod prelude {\n'
        result += '    pub use crate::frame_base::{\n'
        result += '        fletcher_checksum, fletcher_checksum_ext, FrameChecksum, FrameMsgInfo,\n'
        result += '        FrameMsgStatus, MessageInfo, ParserDiagnostics, StructFrameMessage,\n'
        result += '    };\n'
        result += '    pub use crate::frame_profiles::{\n'
        result += '        AccumulatingReader, BufferReader, BufferWriter, ProfileConfig,\n'
        result += '        PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,\n'
        result += '        PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,\n'
        result += '        encode_message_crc, encode_message_minimal, encode_minimal, encode_with_crc,\n'
        result += '        encode_with_crc_ext, parse_minimal, parse_with_crc,\n'
        result += '        new_bulk_reader, new_bulk_writer, new_ipc_reader, new_ipc_writer,\n'
        result += '        new_network_reader, new_network_writer, new_sensor_reader, new_sensor_writer,\n'
        result += '        new_standard_reader, new_standard_writer,\n'
        result += '    };\n'
        result += '    pub use crate::struct_frame_sdk::{MessageHandler, SendResult, Subscription, StructFrameSdk};\n'
        result += '}\n\n'
        result += '// Generated message modules\n'
        for pkg_name in package_names:
            mod_name = pkg_name.replace('-', '_').replace(' ', '_')
            file_name = f'{pkg_name}.structframe.rs'
            result += f'#[path = "{file_name}"]\n'
            result += f'pub mod {mod_name};\n'
        result += '\n'
        result += '// Merged get_message_info that queries all packages\n'
        result += 'pub fn get_message_info(msg_id: u16) -> Option<MessageInfo> {\n'
        for pkg_name in package_names:
            mod_name = pkg_name.replace('-', '_').replace(' ', '_')
            result += f'    if let Some(info) = {mod_name}::get_message_info(msg_id) {{\n'
            result += f'        return Some(info);\n'
            result += f'    }}\n'
        result += '    None\n'
        result += '}\n'
        return result


class TestRustGen():
    """Generator for Rust round-trip test code with deterministic dummy values."""

    @staticmethod
    def _get_dummy_value(field, index=0):
        """Generate a Rust literal dummy value for a field's element type."""
        type_name = field.field_type
        type_values = {
            "uint8":  f'{(42 + index) % 256}u8',
            "int8":   f'{(42 + index) % 128}i8',
            "uint16": f'{1000 + index}u16',
            "int16":  f'{500 + index}i16',
            "uint32": f'{123456 + index}u32',
            "int32":  f'{123456 + index}i32',
            "uint64": f'{9876543210 + index}u64',
            "int64":  f'{9876543210 + index}i64',
            "float":  f'{3.14159 + index}f32',
            "double": f'{2.718281828 + index}f64',
            "bool":   "true" if index % 2 == 0 else "false",
        }
        if type_name in type_values:
            return type_values[type_name]
        if field.is_enum:
            # Default-construct the enum (always defined as Default).
            type_pkg = getattr(field, 'type_package', None) or field.package
            type_msg = getattr(field, 'type_message', None)
            if type_msg:
                return f'{type_msg}{type_name}::default()'
            return f'{_rust_struct_name(type_pkg, type_name)}::default()'
        # Nested struct: rely on Default so we don't recurse into possibly
        # large array fields.
        type_pkg = getattr(field, 'type_package', None) or field.package
        return f'{_rust_struct_name(type_pkg, type_name)}::default()'

    @staticmethod
    def _generate_field_init(field, prefix="msg", index=0):
        """Generate Rust code that assigns a dummy value to ``<prefix>.<field>``.

        Strings (fixed and bounded) are filled by copying ``b"test_<i>"`` into
        the underlying byte slice. Bounded arrays/strings also set the
        accompanying ``_count``/``_length`` field.
        """
        var_name = _escape_rust_field_name(field.name)
        type_name = _normalize_bytes_type(field.field_type)
        result = ""

        if field.is_array:
            if type_name == "string":
                if field.size_option is not None:
                    count = min(field.size_option, 3)
                    for i in range(count):
                        s = f'test_{i}'
                        result += f'    {{ let s = b"{s}"; let n = s.len().min({prefix}.{var_name}[{i}].len()); {prefix}.{var_name}[{i}][..n].copy_from_slice(&s[..n]); }}\n'
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    result += f'    {prefix}.{var_name}_count = {count} as _;\n'
                    for i in range(count):
                        s = f'test_{i}'
                        result += f'    {{ let s = b"{s}"; let n = s.len().min({prefix}.{var_name}[{i}].len()); {prefix}.{var_name}[{i}][..n].copy_from_slice(&s[..n]); }}\n'
            else:
                if field.size_option is not None:
                    count = min(field.size_option, 3)
                    for i in range(count):
                        result += f'    {prefix}.{var_name}[{i}] = {TestRustGen._get_dummy_value(field, i)};\n'
                elif field.max_size is not None:
                    count = min(field.max_size, 3)
                    result += f'    {prefix}.{var_name}_count = {count} as _;\n'
                    for i in range(count):
                        result += f'    {prefix}.{var_name}[{i}] = {TestRustGen._get_dummy_value(field, i)};\n'
        elif type_name == "string":
            if field.size_option is not None:
                s = 'test_string'
                result += f'    {{ let s = b"{s}"; let n = s.len().min({prefix}.{var_name}.len()); {prefix}.{var_name}[..n].copy_from_slice(&s[..n]); }}\n'
            elif field.max_size is not None:
                s = 'test_string'
                result += f'    {{ let s = b"{s}"; let n = s.len().min({prefix}.{var_name}.len()); {prefix}.{var_name}_length = n as _; {prefix}.{var_name}[..n].copy_from_slice(&s[..n]); }}\n'
        else:
            result += f'    {prefix}.{var_name} = {TestRustGen._get_dummy_value(field, index)};\n'

        return result

    @staticmethod
    def generate(package):
        """Generate a self-contained Rust round-trip test binary for *package*.

        For every message in the package the generated ``main()`` populates a
        deterministic test instance, encodes it via the profile's BufferWriter,
        decodes it via AccumulatingReader, and compares the original and
        decoded payloads byte-for-byte (using ``pack_max_size``). Each message
        is exercised against all five frame profiles; combinations that are
        intentionally incompatible (msg_id > 255 on a profile without pkg_id,
        or payload exceeding the profile maximum) are reported as skipped.
        """
        crate_name = 'struct_frame_sdk'
        mod_name = package.name.replace('-', '_').replace(' ', '_')
        testable_messages = [(k, m) for k, m in package.sortedMessages().items()
                             if m.id is not None and not getattr(m, 'oneofs', {})]

        # Collect cross-package modules referenced by any field type so we can
        # bring nested struct/enum types into scope for create_test_* helpers.
        referenced_packages = set()
        for _, m in testable_messages:
            for _, field in m.fields.items():
                type_pkg = getattr(field, 'type_package', None)
                if type_pkg and type_pkg != package.name and not field.is_default_type:
                    referenced_packages.add(type_pkg.replace('-', '_').replace(' ', '_'))

        yield '// Automatically generated round-trip test for struct-frame messages.\n'
        yield f'// Generated by struct-frame {version}.\n'
        yield '// DO NOT EDIT - regenerate using struct-frame.\n\n'
        yield '#![allow(unused_imports, dead_code, unused_mut, unused_variables, clippy::all)]\n\n'
        yield f'use {crate_name}::{{\n'
        yield '    AccumulatingReader, BufferWriter, ProfileConfig,\n'
        yield '    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,\n'
        yield '    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,\n'
        yield '    new_bulk_reader, new_bulk_writer, new_ipc_reader, new_ipc_writer,\n'
        yield '    new_network_reader, new_network_writer, new_sensor_reader, new_sensor_writer,\n'
        yield '    new_standard_reader, new_standard_writer,\n'
        yield '};\n'
        yield f'use {crate_name}::frame_base::{{MessageInfo, StructFrameMessage}};\n'
        yield f'use {crate_name}::{mod_name}::*;\n'
        yield f'use {crate_name}::{mod_name}::get_message_info;\n'
        for ref_mod in sorted(referenced_packages):
            yield f'use {crate_name}::{ref_mod}::*;\n'
        yield '\n'

        # create_test_<msg> functions
        for _, msg in testable_messages:
            struct_name = msg.name
            fn = camel_to_snake_case(msg.name)
            yield f'/// Build a deterministic test instance of `{struct_name}`.\n'
            yield f'fn create_test_{fn}() -> {struct_name} {{\n'
            yield f'    let mut msg = {struct_name}::default();\n'
            field_index = 0
            for _, field in msg.fields.items():
                code = TestRustGen._generate_field_init(field, "msg", field_index)
                if code:
                    yield code
                field_index += 1
            yield '    msg\n'
            yield '}\n\n'

        # Profile descriptor table.
        yield 'struct ProfileEntry {\n'
        yield '    name: &\'static str,\n'
        yield '    has_pkg_id: bool,\n'
        yield '    max_payload: Option<u16>,\n'
        yield '    new_writer: fn(usize) -> BufferWriter,\n'
        yield '    new_reader: fn(usize) -> AccumulatingReader,\n'
        yield '    has_crc: bool,\n'
        yield '}\n\n'
        yield 'const PROFILES: &[ProfileEntry] = &[\n'
        yield '    ProfileEntry { name: "ProfileStandard", has_pkg_id: false, max_payload: Some(255),   new_writer: new_standard_writer, new_reader: new_standard_reader, has_crc: true  },\n'
        yield '    ProfileEntry { name: "ProfileSensor",   has_pkg_id: false, max_payload: None,        new_writer: new_sensor_writer,   new_reader: new_sensor_reader,   has_crc: false },\n'
        yield '    ProfileEntry { name: "ProfileIPC",      has_pkg_id: false, max_payload: None,        new_writer: new_ipc_writer,      new_reader: new_ipc_reader,      has_crc: false },\n'
        yield '    ProfileEntry { name: "ProfileBulk",     has_pkg_id: true,  max_payload: Some(65535), new_writer: new_bulk_writer,     new_reader: new_bulk_reader,     has_crc: true  },\n'
        yield '    ProfileEntry { name: "ProfileNetwork",  has_pkg_id: true,  max_payload: Some(65535), new_writer: new_network_writer,  new_reader: new_network_reader,  has_crc: true  },\n'
        yield '];\n\n'

        # Skip-reason logic: returns Some(reason) when this (message, profile) pair
        # cannot legitimately round-trip; counts as "passed" for the suite total.
        yield 'fn skip_reason<M: StructFrameMessage>(profile: &ProfileEntry) -> Option<&\'static str> {\n'
        yield '    if !profile.has_pkg_id && M::MSG_ID > 255 {\n'
        yield '        return Some("msg_id > 255 requires has_pkg_id profile");\n'
        yield '    }\n'
        yield '    if let Some(max) = profile.max_payload {\n'
        yield '        if M::MAX_SIZE > max as usize {\n'
        yield '            return Some("message exceeds profile max_payload");\n'
        yield '        }\n'
        yield '    }\n'
        yield '    if get_message_info(M::MSG_ID).is_none() {\n'
        yield '        return Some("msg_id not registered (cross-package mismatch)");\n'
        yield '    }\n'
        yield '    None\n'
        yield '}\n\n'

        yield 'fn verify_roundtrip<M: StructFrameMessage>(msg: &M, profile: &ProfileEntry) -> Result<(), String> {\n'
        yield '    let buf_size = std::cmp::max(2048, M::MAX_SIZE + 256);\n'
        yield '    let mut writer = (profile.new_writer)(buf_size);\n'
        yield '    let written = if profile.has_crc {\n'
        yield '        writer.write_crc(msg, 0)\n'
        yield '    } else {\n'
        yield '        writer.write_minimal(msg)\n'
        yield '    };\n'
        yield '    if written == 0 {\n'
        yield '        return Err("encode failed (writer returned 0)".to_string());\n'
        yield '    }\n'
        yield '    let encoded: Vec<u8> = writer.data().to_vec();\n'
        yield '    let mut reader = (profile.new_reader)(std::cmp::max(4096, buf_size * 2));\n'
        yield '    reader.add_data(&encoded);\n'
        yield '    let frame = match reader.next(&get_message_info) {\n'
        yield '        Some(f) if f.valid => f,\n'
        yield '        _ => return Err("parse failed".to_string()),\n'
        yield '    };\n'
        yield '    if frame.msg_id != M::MSG_ID {\n'
        yield '        return Err(format!("msg_id mismatch: expected {}, got {}", M::MSG_ID, frame.msg_id));\n'
        yield '    }\n'
        yield '    let decoded = match M::unpack(&frame.msg_data) {\n'
        yield '        Some(d) => d,\n'
        yield '        None => return Err("unpack returned None".to_string()),\n'
        yield '    };\n'
        yield '    let mut a = vec![0u8; M::MAX_SIZE];\n'
        yield '    let mut b = vec![0u8; M::MAX_SIZE];\n'
        yield '    let na = msg.pack_max_size(&mut a);\n'
        yield '    let nb = decoded.pack_max_size(&mut b);\n'
        yield '    if na != nb || a[..na] != b[..nb] {\n'
        yield '        return Err("decoded payload differs from original".to_string());\n'
        yield '    }\n'
        yield '    Ok(())\n'
        yield '}\n\n'

        yield f'const TEST_MESSAGE_COUNT: usize = {len(testable_messages)};\n\n'

        yield '// Runs all message tests for one profile. Skipped (profile-incompatible)\n'
        yield '// messages are tracked separately from passes (NOT counted as passes);\n'
        yield '// tested[i] is set true when message i round-trips under this profile.\n'
        yield '// Returns (passed, skipped).\n'
        yield 'fn run_profile(profile: &ProfileEntry, tested: &mut [bool], verbose: bool) -> (usize, usize) {\n'
        yield '    let mut passed: usize = 0;\n'
        yield '    let mut skipped: usize = 0;\n'
        for idx, (_, msg) in enumerate(testable_messages):
            struct_name = msg.name
            fn = camel_to_snake_case(msg.name)
            yield f'    {{\n'
            yield f'        let m = create_test_{fn}();\n'
            yield f'        if let Some(reason) = skip_reason::<{struct_name}>(profile) {{\n'
            yield f'            skipped += 1;\n'
            yield f'            if verbose {{ println!("[SKIP] {struct_name}: {{}}", reason); }}\n'
            yield f'        }} else {{\n'
            yield f'            match verify_roundtrip(&m, profile) {{\n'
            yield f'                Ok(()) => {{ passed += 1; tested[{idx}] = true; if verbose {{ println!("[PASS] {struct_name}"); }} }}\n'
            yield f'                Err(e)  => {{ if verbose {{ println!("[FAIL] {struct_name}: {{}}", e); }} }}\n'
            yield f'            }}\n'
            yield f'        }}\n'
            yield f'    }}\n'
        yield '    if verbose { println!("  -> {}/{} passed ({} skipped)", passed, TEST_MESSAGE_COUNT - skipped, skipped); }\n'
        yield '    (passed, skipped)\n'
        yield '}\n\n'

        yield 'fn main() {\n'
        yield '    let verbose = std::env::args().any(|a| a == "-v" || a == "--verbose");\n'
        yield f'    println!("Running round-trip tests for package \'{package.name}\' across 5 profiles...");\n'
        yield '    let mut all_ok = true;\n'
        yield '    let mut tested = vec![false; TEST_MESSAGE_COUNT];\n'
        yield '    for p in PROFILES {\n'
        yield '        if verbose { println!("\\n--- {} ---", p.name); }\n'
        yield '        let (passed, skipped) = run_profile(p, &mut tested, verbose);\n'
        yield '        let expected = TEST_MESSAGE_COUNT - skipped;\n'
        yield '        if passed != expected {\n'
        yield '            all_ok = false;\n'
        yield '            println!("[FAIL] {}: {}/{} passed ({} skipped)", p.name, passed, expected, skipped);\n'
        yield '        } else if verbose {\n'
        yield '            println!("[OK] {}: {}/{} passed ({} skipped)", p.name, passed, expected, skipped);\n'
        yield '        }\n'
        yield '    }\n'
        yield '    // Messages skipped under every profile are not exercised by this\n'
        yield '    // generated suite (e.g. cross-package messages the per-package registry\n'
        yield '    // cannot resolve). Reported loudly but non-fatally -- a profile that\n'
        yield '    // *attempts* a message and fails is already caught above.\n'
        yield '    let never: Vec<usize> = (0..TEST_MESSAGE_COUNT).filter(|&i| !tested[i]).collect();\n'
        yield '    if !never.is_empty() {\n'
        yield '        println!("[WARN] {} message(s) skipped under every profile, not exercised by this suite (indices {:?})", never.len(), never);\n'
        yield '    }\n'
        yield '    if all_ok {\n'
        yield f'        println!("[TEST PASSED] All round-trip tests for \'{package.name}\' succeeded.");\n'
        yield '        std::process::exit(0);\n'
        yield '    } else {\n'
        yield f'        println!("[TEST FAILED] Round-trip tests for \'{package.name}\' had failures.");\n'
        yield '        std::process::exit(1);\n'
        yield '    }\n'
        yield '}\n'
