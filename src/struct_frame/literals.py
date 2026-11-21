"""Source-code literals for schema values, one renderer per target language.

Every generator that writes a schema value into code (constants, default values) goes
through these functions, so special cases are handled once:

* non-finite floats (``inf``, ``-inf``, ``nan``) use each language's spelling;
* 64-bit integers get the suffixes their language needs, and the minimum ``int64`` /
  ``int32`` values are written so they are valid constant expressions;
* strings are escaped so the generated file is pure ASCII.

``ftype`` is a canonical primitive name (``uint8`` ... ``double``, ``bool``, ``string``).
"""

import math

_C_TYPES = {"uint8": "uint8_t", "int8": "int8_t", "uint16": "uint16_t", "int16": "int16_t",
            "uint32": "uint32_t", "int32": "int32_t", "uint64": "uint64_t", "int64": "int64_t",
            "float": "float", "double": "double", "bool": "bool"}
_CS_TYPES = {"uint8": "byte", "int8": "sbyte", "uint16": "ushort", "int16": "short",
             "uint32": "uint", "int32": "int", "uint64": "ulong", "int64": "long",
             "float": "float", "double": "double", "bool": "bool", "string": "string"}
_RUST_TYPES = {"uint8": "u8", "int8": "i8", "uint16": "u16", "int16": "i16",
               "uint32": "u32", "int32": "i32", "uint64": "u64", "int64": "i64",
               "float": "f32", "double": "f64", "bool": "bool", "string": "&str"}
_INT64_MIN = -(1 << 63)
_SIMPLE_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}
_INT32_MIN = -(1 << 31)


def is_nonfinite(value):
    return isinstance(value, float) and not math.isfinite(value)


def _float_text(value):
    """Shortest round-tripping decimal text, always with a '.' or an exponent."""
    text = repr(float(value))
    if "e" not in text and "." not in text:
        text += ".0"
    return text


# ---------------------------------------------------------------------------
# C / C++
# ---------------------------------------------------------------------------

def c_string(text):
    """A C/C++ string literal; non-ASCII and control bytes as octal escapes."""
    out = ['"']
    for byte in text.encode("utf-8"):
        ch = chr(byte)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= byte < 0x7F and ch != "?":
            out.append(ch)
        else:
            out.append(f"\\{byte:03o}")   # octal is never greedy beyond 3 digits
    out.append('"')
    return "".join(out)


def c_scalar(ftype, value, cpp=False):
    """A C (or C++) literal of primitive type *ftype*.

    Non-finite floats use the ``INFINITY``/``NAN`` macros of ``<math.h>``/``<cmath>``;
    callers include the header when :func:`is_nonfinite` says a value needs it.
    """
    if ftype == "bool":
        return "true" if value else "false"
    if ftype in ("float", "double"):
        value = float(value)
        suffix = "f" if ftype == "float" else ""
        if math.isnan(value):
            return "NAN" if ftype == "float" else "((double)NAN)"
        if math.isinf(value):
            inf = "INFINITY" if ftype == "float" else "((double)INFINITY)"
            return inf if value > 0 else f"(-{inf})"
        text = _float_text(value) + suffix
        return f"({text})" if value < 0 else text
    if ftype == "string":
        return c_string(value)
    value = int(value)
    if ftype == "int64":
        if value == _INT64_MIN:
            return "(-9223372036854775807LL - 1)"
        return f"({value}LL)" if value < 0 else f"{value}LL"
    if ftype == "uint64":
        return f"{value}ULL"
    if ftype == "int32" and value == _INT32_MIN:
        return "(-2147483647 - 1)"
    if ftype == "uint32":
        return f"{value}u"
    return f"({value})" if value < 0 else str(value)


def c_const_define(name, ftype, value):
    """``#define NAME value`` with a typed value (usable as an array size in C)."""
    if ftype == "string":
        return f"#define {name} {c_string(value)}"
    if ftype == "bool":
        return f"#define {name} {'true' if value else 'false'}"
    if ftype in ("float", "double"):
        return f"#define {name} {c_scalar(ftype, value)}"
    return f"#define {name} (({_C_TYPES[ftype]}){c_scalar(ftype, value)})"


def cpp_const(name, ftype, value):
    if ftype == "string":
        return f"constexpr const char* {name} = {c_string(value)};"
    return f"constexpr {_C_TYPES[ftype]} {name} = {c_scalar(ftype, value, cpp=True)};"


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def py_scalar(ftype, value):
    if ftype == "bool":
        return "True" if value else "False"
    if ftype in ("float", "double"):
        value = float(value)
        if math.isnan(value):
            return 'float("nan")'
        if math.isinf(value):
            return 'float("inf")' if value > 0 else 'float("-inf")'
        return _float_text(value)
    if ftype == "string":
        return ascii(value)   # pure ASCII source, whatever the file encoding
    return str(int(value))


# ---------------------------------------------------------------------------
# TypeScript / JavaScript
# ---------------------------------------------------------------------------

def js_string(text):
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[ch])
        elif 0x20 <= code < 0x7F:
            out.append(ch)
        elif code <= 0xFFFF:
            out.append(f"\\u{code:04x}")
        else:
            code -= 0x10000
            out.append(f"\\u{0xD800 + (code >> 10):04x}\\u{0xDC00 + (code & 0x3FF):04x}")
    out.append('"')
    return "".join(out)


def js_scalar(ftype, value):
    if ftype == "bool":
        return "true" if value else "false"
    if ftype in ("float", "double"):
        value = float(value)
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return _float_text(value)
    if ftype == "string":
        return js_string(value)
    if ftype in ("int64", "uint64"):
        return f"{int(value)}n"
    return str(int(value))


def ts_type(ftype):
    if ftype == "bool":
        return "boolean"
    if ftype == "string":
        return "string"
    if ftype in ("int64", "uint64"):
        return "bigint"
    return "number"


# ---------------------------------------------------------------------------
# C#
# ---------------------------------------------------------------------------

def cs_string(text):
    return js_string(text)


def cs_scalar(ftype, value, const=False):
    """A C# literal. ``const`` selects a constant expression (``double.NaN``); otherwise
    a NaN is written with the canonical bit pattern every other language uses (C#'s
    ``double.NaN`` has the sign bit set, which would serialize differently)."""
    if ftype == "bool":
        return "true" if value else "false"
    if ftype in ("float", "double"):
        value = float(value)
        kind = "float" if ftype == "float" else "double"
        if math.isnan(value):
            if const:
                return f"{kind}.NaN"
            if ftype == "float":
                return "BitConverter.Int32BitsToSingle(0x7FC00000)"
            return "BitConverter.Int64BitsToDouble(0x7FF8000000000000L)"
        if math.isinf(value):
            return f"{kind}.PositiveInfinity" if value > 0 else f"{kind}.NegativeInfinity"
        return _float_text(value) + ("f" if ftype == "float" else "d")
    if ftype == "string":
        return cs_string(value)
    value = int(value)
    if ftype == "int64":
        return "long.MinValue" if value == _INT64_MIN else f"{value}L"
    if ftype == "uint64":
        return f"{value}UL"
    if ftype == "int32" and value == _INT32_MIN:
        return "int.MinValue"
    if ftype == "uint32":
        return f"{value}U"
    return str(value)


def cs_type(ftype):
    return _CS_TYPES[ftype]


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------

def rust_string(text):
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= code < 0x7F:
            out.append(ch)
        else:
            out.append(f"\\u{{{code:x}}}")
    out.append('"')
    return "".join(out)


def rust_scalar(ftype, value):
    if ftype == "bool":
        return "true" if value else "false"
    if ftype in ("float", "double"):
        value = float(value)
        kind = "f32" if ftype == "float" else "f64"
        if math.isnan(value):
            return f"{kind}::NAN"
        if math.isinf(value):
            return f"{kind}::INFINITY" if value > 0 else f"{kind}::NEG_INFINITY"
        return _float_text(value) + kind
    if ftype == "string":
        return rust_string(value)
    value = int(value)
    if ftype == "int64" and value == _INT64_MIN:
        return "i64::MIN"
    return str(value)


def rust_type(ftype):
    return _RUST_TYPES[ftype]


# ---------------------------------------------------------------------------
# Package constants
# ---------------------------------------------------------------------------

def const_name(const):
    """Generated name of a schema constant (SCREAMING_SNAKE_CASE in every language)."""
    from struct_frame.naming import to_screaming_snake_case
    return to_screaming_snake_case(const.name)


def doc_lines(comments):
    """Plain text lines of a declaration's doc comments (delimiters stripped)."""
    from struct_frame.base import comment_text_lines
    lines = []
    for comment in comments or []:
        lines.extend(comment_text_lines(comment))
    return lines


def package_consts(package):
    return list(getattr(package, "consts", {}).values())


def consts_need_math(package):
    return any(is_nonfinite(c.value) for c in package_consts(package))


def value_nonfinite(value):
    """True when a (possibly composite) value contains an inf or nan float."""
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return any(value_nonfinite(v) for v in value)
    if isinstance(value, dict):
        return any(value_nonfinite(v) for v in value.values())
    return False


def package_needs_math(package):
    """True when the package's constants or defaults need INFINITY/NAN (<math.h>)."""
    if consts_need_math(package):
        return True
    for msg in package.messages.values():
        for field in msg.fields.values():
            if field.default is not None and value_nonfinite(field.default):
                return True
    return False
