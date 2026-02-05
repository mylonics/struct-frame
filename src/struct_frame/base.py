"""
Base utilities for struct-frame code generation.

This module provides naming conventions and utilities shared across all
language-specific code generators.
"""

import re

version = "0.0.1"


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
        return name.upper()

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


def camelCase(st):
    """Convert string to camelCase (first letter lowercase)."""
    output = ''.join(x for x in st.title() if x.isalnum())
    return output[0].lower() + output[1:]


def pascalCase(st):
    """Convert string to PascalCase (first letter uppercase)."""
    return ''.join(x for x in st.title() if x.isalnum())


pattern = re.compile(r'(?<!^)(?=[A-Z])')


def CamelToSnakeCase(data):
    """Convert CamelCase or PascalCase to snake_case."""
    return pattern.sub('_', data).lower()


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
