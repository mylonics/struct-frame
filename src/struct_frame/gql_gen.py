#!/usr/bin/env python3
# Simple GraphQL schema generator for struct-frame

from struct_frame import version, pascalCase, CamelToSnakeCase
import time

# Mapping from proto primitive types to GraphQL scalar types
gql_types = {
    "uint8": "Int",
    "int8": "Int",
    "uint16": "Int",
    "int16": "Int",
    "uint32": "Int",
    "int32": "Int",
    "uint64": "Int",  # Could be custom scalar if needed
    "int64": "Int",   # Could be custom scalar if needed
    "bool": "Boolean",
    "float": "Float",
    "double": "Float",
    "string": "String",
}


def _gql_enum_value_name(name: str) -> str:
    # If already in ALL_CAPS (possibly with underscores) keep as is
    if name.replace('_', '').isupper():
        return name
    return CamelToSnakeCase(name).upper()


def _clean_comment_line(c: str) -> str:
    c = c.strip()
    if c.startswith('#'):
        c = c[1:].strip()
    # Remove leading // once or twice
    if c.startswith('//'):
        c = c[2:].strip()
    # If parser already kept leading markers inside line, remove repeated
    if c.startswith('//'):
        c = c[2:].strip()
    return c


def _triple_quote_block(lines):
    cleaned = [_clean_comment_line(l) for l in lines if _clean_comment_line(l)]
    if not cleaned:
        return None
    return '"""\n' + '\n'.join(cleaned) + '\n"""'


def _single_quote_line(lines):
    cleaned = [_clean_comment_line(l) for l in lines if _clean_comment_line(l)]
    if not cleaned:
        return None
    # Join multi-line into one sentence for single-line description
    return '"' + ' '.join(cleaned) + '"'


class EnumGqlGen:
    @staticmethod
    def generate(enum):
        lines = []
        if enum.comments:
            desc = _triple_quote_block(enum.comments)
            if desc:
                lines.append(desc)
        enum_name = f"{pascalCase(enum.package)}{enum.name}"
        lines.append(f"enum {enum_name} {{")
        for key, value in enum.data.items():
            if value[1]:
                desc = _single_quote_line(value[1])
                if desc:
                    lines.append(f"  {desc}")
            lines.append(f"  {_gql_enum_value_name(key)}")
        lines.append("}\n")
        return '\n'.join(lines)


class FieldGqlGen:
    @staticmethod
    def type_name(field):
        t = field.fieldType
        base_type = gql_types.get(t, f"{pascalCase(field.package)}{t}")

        # Handle arrays
        if getattr(field, 'is_array', False):
            # Arrays in GraphQL are represented as [Type!]! for non-null arrays of non-null elements
            # or [Type] for nullable arrays, etc. We'll use [Type!]! as the standard
            return f"[{base_type}!]!"

        return base_type

    @staticmethod
    def generate(field, name_override=None):
        lines = []

        # Generate clean comments with size information, preferring our generated descriptions over proto comments
        if getattr(field, 'is_array', False):
            # Array field - use our size descriptions
            if getattr(field, 'size_option', None) is not None:
                # Fixed array
                if field.fieldType == "string":
                    comment_lines = [
                        f"Fixed string array: {field.size_option} strings, each {getattr(field, 'element_size', 'N/A')} chars"]
                else:
                    comment_lines = [
                        f"Fixed array: always {field.size_option} elements"]
            else:
                # Variable array
                if field.fieldType == "string":
                    comment_lines = [
                        f"Variable string array: up to {getattr(field, 'max_size', 'N/A')} strings, each max {getattr(field, 'element_size', 'N/A')} chars"]
                else:
                    comment_lines = [
                        f"Variable array: up to {getattr(field, 'max_size', 'N/A')} elements"]
        elif field.fieldType == "string":
            # Non-array string field
            if getattr(field, 'size_option', None) is not None:
                comment_lines = [
                    f"Fixed string: exactly {field.size_option} characters"]
            elif getattr(field, 'max_size', None) is not None:
                comment_lines = [
                    f"Variable string: up to {field.max_size} characters"]
            else:
                comment_lines = field.comments[:] if field.comments else []
        else:
            # Regular field - use original comments
            comment_lines = field.comments[:] if field.comments else []

        if comment_lines:
            desc = _single_quote_line(comment_lines)
            if desc:
                lines.append(f"  {desc}")

        fname = name_override if name_override else field.name
        lines.append(f"  {fname}: {FieldGqlGen.type_name(field)}")
        return '\n'.join(lines)

    @staticmethod
    def generate_flattened_children(field, package, parent_msg):
        # Expand a message-typed field into its child fields.
        # If a child field name collides, raise an error and fail generation.
        t = field.fieldType
        child_msg = package.messages.get(t)
        if not child_msg:
            # Fallback to normal generation if unknown
            return [FieldGqlGen.generate(field)]

        out_lines = []
        for ck, cf in child_msg.fields.items():
            out_lines.append(FieldGqlGen.generate(cf, name_override=ck))
        return out_lines


class MessageGqlGen:
    @staticmethod
    def generate(package, msg):
        lines = []
        if msg.comments:
            desc = _triple_quote_block(msg.comments)
            if desc:
                lines.append(desc)
        type_name = f"{pascalCase(msg.package)}{msg.name}"
        lines.append(f"type {type_name} {{")
        if not msg.fields:
            lines.append("  _empty: Boolean")
        else:
            for key, f in msg.fields.items():
                if getattr(f, 'flatten', False) and f.fieldType not in gql_types:
                    lines.extend(
                        FieldGqlGen.generate_flattened_children(f, package, msg))
                else:
                    lines.append(FieldGqlGen.generate(f))
        lines.append("}\n")
        return '\n'.join(lines)


class FileGqlGen:
    @staticmethod
    def generate(package):
        # Multiline triple-quoted header block
        yield f"# Automatically generated GraphQL schema\n# Generated by struct-frame {version} at {time.asctime()}\n"
        
        # Add package ID as a comment if present
        if package.package_id is not None:
            yield f"# Package: {package.name} (ID: {package.package_id})\n"
        yield "\n"

        first_block = True
        # Enums
        for _, enum in package.enums.items():
            if not first_block:
                yield '\n'
            first_block = False
            yield EnumGqlGen.generate(enum).rstrip() + '\n'

        # Messages (object types)
        for _, msg in package.sortedMessages().items():
            if not first_block:
                yield '\n'
            first_block = False
            yield MessageGqlGen.generate(package, msg).rstrip() + '\n'

        # Root Query type
        if package.messages:
            if not first_block:
                yield '\n'
            yield 'type Query {\n'
            for _, msg in package.sortedMessages().items():
                type_name = f"{pascalCase(msg.package)}{msg.name}"
                yield f"  {msg.name}: {type_name}\n"
            yield '}\n'
