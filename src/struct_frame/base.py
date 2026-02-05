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
    """
    def enum_name(self, name):
        return "_%s" % (name)

    def struct_name(self, name):
        return "_%s" % (name)

    def union_name(self, name):
        return "_%s" % (name)

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
