#!/usr/bin/env python3
"""
GraphQL schema generator for struct-frame.

This module generates GraphQL type definitions from Protocol Buffer messages,
converting proto types to GraphQL scalars and generating type/input definitions.
"""

from struct_frame import version, pascal_case, camel_to_snake_case
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
    "bytes": "String",    # bytes treated identically to string (same wire format)
}


def _gql_enum_value_name(name: str) -> str:
    # If already in ALL_CAPS (possibly with underscores) keep as is
    if name.replace('_', '').isupper():
        return name
    return camel_to_snake_case(name).upper()


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
        enum_name = f"{pascal_case(enum.package)}{enum.name}"
        lines.append(f'enum {enum_name} @package(name: "{enum.package}") {{')
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
        t = field.field_type
        base_type = gql_types.get(t, f"{pascal_case(field.package)}{t}")

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
                if field.field_type in ("string", "bytes"):
                    comment_lines = [
                        f"Fixed string array: {field.size_option} strings, each {getattr(field, 'element_size', 'N/A')} chars"]
                else:
                    comment_lines = [
                        f"Fixed array: always {field.size_option} elements"]
            else:
                # Variable array
                if field.field_type in ("string", "bytes"):
                    comment_lines = [
                        f"Variable string array: up to {getattr(field, 'max_size', 'N/A')} strings, each max {getattr(field, 'element_size', 'N/A')} chars"]
                else:
                    comment_lines = [
                        f"Variable array: up to {getattr(field, 'max_size', 'N/A')} elements"]
        elif field.field_type in ("string", "bytes"):
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
        t = field.field_type
        child_msg = package.messages.get(t)
        if not child_msg:
            # Fallback to normal generation if unknown
            return [FieldGqlGen.generate(field)]

        out_lines = []
        for ck, cf in child_msg.fields.items():
            out_lines.append(FieldGqlGen.generate(cf, name_override=ck))
        return out_lines


# SDL directive definition emitted once per generated schema file
_PACKAGE_DIRECTIVE_DEF = 'directive @package(name: String!) on OBJECT | INPUT_OBJECT | ENUM'


class MessageGqlGen:
    @staticmethod
    def generate(package, msg):
        lines = []
        if msg.comments:
            desc = _triple_quote_block(msg.comments)
            if desc:
                lines.append(desc)
        type_name = f"{pascal_case(msg.package)}{msg.name}"
        lines.append(f'type {type_name} @package(name: "{package.name}") {{')
        if not msg.fields and not getattr(msg, 'oneofs', {}):
            lines.append("  _empty: Boolean")
        else:
            for key, f in msg.fields.items():
                if getattr(f, 'flatten', False) and f.field_type not in gql_types:
                    lines.extend(
                        FieldGqlGen.generate_flattened_children(f, package, msg))
                else:
                    lines.append(FieldGqlGen.generate(f))
            # Generate oneof fields as nullable union-type fields
            for oneof_name, oneof in getattr(msg, 'oneofs', {}).items():
                lines.append(f"  # oneof {oneof_name}")
                for field_name, oneof_field in oneof.fields.items():
                    gql_type = gql_types.get(oneof_field.field_type,
                                              f"{pascal_case(oneof_field.package)}{oneof_field.field_type}")
                    if getattr(oneof_field, 'is_array', False):
                        gql_type = f"[{gql_type}!]!"
                    # Oneof members are nullable since only one is populated
                    lines.append(f"  {field_name}: {gql_type}")
        lines.append("}\n")
        return '\n'.join(lines)


class FileGqlGen:
    @staticmethod
    def generate(package):
        # Multiline triple-quoted header block
        yield f"# Automatically generated GraphQL schema\n# Generated by struct-frame {version}\n"

        # Add package ID as a comment if present
        if package.package_id is not None:
            yield f"# Package: {package.name} (ID: {package.package_id})\n"
        yield "\n"

        # Emit the @package directive definition so consumers can introspect it
        yield _PACKAGE_DIRECTIVE_DEF + '\n\n'

        first_block = True
        # Enums (package-level)
        for _, enum in package.enums.items():
            if not first_block:
                yield '\n'
            first_block = False
            yield EnumGqlGen.generate(enum).rstrip() + '\n'

        # Nested enums (message-scoped)
        emitted_nested = set()
        for _, msg in package.sortedMessages().items():
            for enum_name, enum_obj in getattr(msg, 'enums', {}).items():
                if enum_name not in emitted_nested:
                    emitted_nested.add(enum_name)
                    if not first_block:
                        yield '\n'
                    first_block = False
                    yield EnumGqlGen.generate(enum_obj).rstrip() + '\n'

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
                type_name = f"{pascal_case(msg.package)}{msg.name}"
                yield f"  {msg.name}: {type_name}\n"
            yield '}\n'
