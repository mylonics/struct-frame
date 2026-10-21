"""
Base utilities for struct-frame code generation.

This module provides naming conventions and utilities shared across all
language-specific code generators.
"""

import re

from struct_frame.naming import to_pascal_case, to_screaming_snake_case

try:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    version = _pkg_version("struct-frame")
except (ImportError, ModuleNotFoundError, PackageNotFoundError):
    version = "0.0.1"


def normalize_bytes_type(type_name):
    """Normalize 'bytes' to 'string' since they share the same wire format
    (variable-length byte arrays). All generators treat them identically."""
    return "string" if type_name == "bytes" else type_name


class NamingStyle:
    """
    Base class for naming conventions across different languages.
    
    Override methods in subclasses to customize naming for specific
    language conventions (e.g., snake_case for C, PascalCase for C#).
    
    The base class returns names unchanged - subclasses add language-specific 
    prefixes, suffixes, or case transformations as needed.
    """
    def enum_name(self, name):
        return name

    def struct_name(self, name):
        return name

    def union_name(self, name):
        return name

    def type_name(self, name):
        return "%s" % (name)

    def define_name(self, name):
        return "%s" % (name)

    def var_name(self, name):
        return "%s" % (name)

    def enum_entry(self, name):
        return "%s" % (name)

    def func_name(self, name):
        return "%s" % (name)

    def bytes_type(self, struct_name, name):
        return "%s_%s_t" % (struct_name, name)


class NamingStyleC(NamingStyle):
    """
    C-style naming conventions.
    
    Uses snake_case for variables and functions, UPPER_CASE for enums
    and defines, and adds _t suffix for type names.
    """
    def enum_name(self, name):
        return self.underscore(name)

    def struct_name(self, name):
        return self.underscore(name)

    def union_name(self, name):
        return self.underscore(name)

    def type_name(self, name):
        return "%s_t" % self.underscore(name)

    def define_name(self, name):
        return self.underscore(name).upper()

    def var_name(self, name):
        return self.underscore(name)

    def enum_entry(self, name):
        return to_screaming_snake_case(name)

    def func_name(self, name):
        return self.underscore(name)

    def bytes_type(self, struct_name, name):
        return "%s_%s_t" % (self.underscore(struct_name), self.underscore(name))

    def underscore(self, word):
        word = str(word)
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
        word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
        word = word.replace("-", "_")
        return word.lower()


class NamingStyleCpp(NamingStyleC):
    """
    C++ style naming conventions (Google C++ Style Guide).

    Inherits from NamingStyleC but uses PascalCase for enum values,
    as recommended by the Google C++ Style Guide.
    """
    def enum_entry(self, name):
        return pascal_case(name)


def pascal_case(st):
    """Convert string to PascalCase (first letter uppercase).

    Acronyms that are visible in the source are preserved:
    ``BleMCuHost`` stays ``BleMCuHost`` and ``gate_current`` becomes
    ``GateCurrent``.  See :mod:`struct_frame.naming` for the tokenizer rules.
    """
    return to_pascal_case(st)


pattern = re.compile(r'(?<!^)(?=[A-Z])')


def camel_to_snake_case(data):
    """Convert CamelCase or PascalCase to snake_case."""
    return pattern.sub('_', data).lower()


# =============================================================================
# File-level documentation
# =============================================================================

def comment_text_lines(text):
    """Strip comment delimiters (``//``, ``///``, ``/* ... */``) from a schema comment.

    Returns the plain text lines.  Used for file-level docs, which are
    re-rendered with each target language's own line-comment syntax so that a
    block comment can never terminate the generated comment early.
    """
    text = str(text).strip()
    if text.startswith('/*'):
        body = text[2:]
        if body.endswith('*/'):
            body = body[:-2]
        lines = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith('*'):
                line = line[1:].strip()
            lines.append(line)
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return lines
    return [re.sub(r'^/+\s?', '', text).rstrip()]


def format_file_docs(package, prefix='// '):
    """Render a package's file-level docs as line comments.

    File docs are the own-line comments written *before* the ``package``
    statement of a schema file.  Each file contributes one block; blocks are
    emitted in a layout-independent order (see ``Package.file_doc_blocks``).
    Returns an empty string when the package has no file docs, otherwise the
    comment lines followed by one blank line.
    """
    blocks = getattr(package, 'file_doc_blocks', None)
    if blocks is None:
        return ''
    rendered = []
    for block in blocks():
        lines = []
        for comment in block:
            lines.extend(comment_text_lines(comment))
        if any(lines):
            rendered.append(lines)
    if not rendered:
        return ''
    out = []
    for index, lines in enumerate(rendered):
        if index:
            out.append(prefix.rstrip() + '\n')
        for line in lines:
            out.append((prefix + line).rstrip() + '\n')
    out.append('\n')
    return ''.join(out)


# =============================================================================
# Shared Enum Generation Utilities
# =============================================================================

def build_enum_leading_comments(comments, comment_prefix='', comment_suffix=''):
    """
    Build leading comments for an enum definition.
    
    Args:
        comments: List of comment strings or None
        comment_prefix: Prefix for each comment line (e.g., '#' for Python, '//' for C)
        comment_suffix: Suffix for each comment line (e.g., '\n')
    
    Returns:
        String with formatted comments
    """
    if not comments:
        return ''
    result = ''
    for c in comments:
        result += '%s%s%s\n' % (comment_prefix, c, comment_suffix)
    return result


def build_enum_values(field, naming_style, value_format=None, comment_formatter=None, 
                      skip_trailing_comma=True, value_generator=None):
    """
    Build the list of enum value strings.
    
    Args:
        field: Enum field object with 'data' dict of {name: (value, comments)}
        naming_style: NamingStyle instance for formatting entry names
        value_format: Format string with placeholders: {indent}, {name}, {value}, {comma}
                      Not used if value_generator is provided.
        comment_formatter: Optional function(comments) -> list of comment lines
        skip_trailing_comma: If True, last value has no trailing comma
        value_generator: Optional function(name, entry_name, value, comma) -> str
                         for custom value formatting. If provided, value_format is ignored.
    
    Returns:
        List of formatted enum value lines
    """
    enum_values = []
    enum_length = len(field.data)
    
    for index, d in enumerate(field.data):
        value_tuple = field.data[d]
        numeric_value = value_tuple[0]
        leading_comment = value_tuple[1] if len(value_tuple) > 1 else None
        
        # Add comments for this value
        if leading_comment and comment_formatter:
            enum_values.extend(comment_formatter(leading_comment))
        elif leading_comment:
            for c in leading_comment:
                enum_values.append(c)
        
        # Determine comma
        comma = ','
        if skip_trailing_comma and index == enum_length - 1:
            comma = ''
        
        # Format the enum value
        entry_name = naming_style.enum_entry(d)
        
        if value_generator:
            enum_value = value_generator(d, entry_name, numeric_value, comma)
        else:
            enum_value = value_format.format(
                indent='    ',
                name=entry_name,
                value=numeric_value,
                comma=comma
            )
        enum_values.append(enum_value)
    
    return enum_values


def get_discriminator_enum_name(oneof, msg_name):
    """Return the standard discriminator enum type name used by most generators.

    Produces ``{msg_name}{PascalCase(oneof.name)}Field``, which is the shared
    convention for C, C#, JavaScript, Python, and TypeScript generators.
    (C++ uses a scoped name without the message prefix and calls its own helper.)
    """
    return f'{msg_name}{pascal_case(oneof.name)}Field'


def build_discriminator_enum_values(oneof, none_entry_fn, field_entry_fn):
    """Build the ``None`` + per-field entries for a field_order discriminator enum.

    Args:
        oneof: The oneof model object with ``.fields`` (ordered dict of field_name→field).
        none_entry_fn: Callable() → str — returns the formatted ``None = 0`` line.
        field_entry_fn: Callable(field_name, field_order, is_last) → str — returns one
            formatted enum-value line for the given field.

    Returns:
        List of formatted enum-value lines (strings, without trailing newlines).
    """
    lines = [none_entry_fn()]
    items = list(oneof.fields.items())
    for idx, (field_name, _field) in enumerate(items):
        field_order = idx + 1
        is_last = idx == len(items) - 1
        lines.append(field_entry_fn(field_name, field_order, is_last))
    return lines
