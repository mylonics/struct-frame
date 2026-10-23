#!/usr/bin/env python3
"""
GraphQL schema generator for struct-frame.

This module generates GraphQL type definitions from Protocol Buffer messages,
converting proto types to GraphQL scalars and generating type/input definitions.
"""

from struct_frame import version, pascal_case, camel_to_snake_case
from struct_frame.base import format_file_docs
from struct_frame.naming import ExplicitName

# Mapping from proto primitive types to GraphQL scalar types
gql_types = {
    "uint8": "Int",
    "int8": "Int",
    "uint16": "Int",
    "int16": "Int",
    "uint32": "UInt32",  # exceeds GraphQL's signed 32-bit Int
    "int32": "Int",
    "uint64": "UInt64",  # custom scalars: GraphQL Int cannot hold 64-bit values
    "int64": "Int64",
    "bool": "Boolean",
    "float": "Float",
    "double": "Float",
    "string": "String",
    "bytes": "String",    # bytes treated identically to string (same wire format)
}


# Custom scalar declarations emitted once per schema document, next to the
# @package directive definition, for the integer types GraphQL's Int cannot hold.
_SCALAR_DEFS = 'scalar UInt32\nscalar Int64\nscalar UInt64'


def _enum_type_name(enum) -> str:
    """GraphQL type name of an enum.

    Message-scoped enums include the message name so two messages can declare a
    nested enum with the same name without colliding.
    """
    message = getattr(enum, 'message', None)
    if message:
        return f"{pascal_case(enum.package)}{message}{enum.name}"
    return f"{pascal_case(enum.package)}{enum.name}"


def _gql_enum_value_name(name: str) -> str:
    if isinstance(name, ExplicitName):
        return str(name)
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
        enum_name = _enum_type_name(enum)
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
        if t in gql_types:
            base_type = gql_types[t]
        else:
            # Name the type after the package that *defines* it, which differs
            # from the package of the field for imported types.
            owner = getattr(field, 'type_package', None) or field.package
            nested_in = getattr(field, 'type_message', None)
            if nested_in and getattr(field, 'is_enum', False):
                base_type = f"{pascal_case(owner)}{nested_in}{t}"
            else:
                base_type = f"{pascal_case(owner)}{t}"

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
        child_msg = getattr(field, 'type_ref', None)
        if child_msg is None or not hasattr(child_msg, 'fields'):
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
                    # Oneof members are nullable since only one is populated
                    gql_type = FieldGqlGen.type_name(oneof_field)
                    lines.append(f"  {field_name}: {gql_type}")
        lines.append("}\n")
        return '\n'.join(lines)


class FileGqlGen:
    @staticmethod
    def definitions(package):
        """Yield the enum and object-type definitions of *package*, one block each.

        Shared by the per-package files and the stitched schema so both contain
        exactly the same declarations (including message-scoped enums).
        """
        for _, enum in package.enums.items():
            yield EnumGqlGen.generate(enum).rstrip() + '\n'
        for _, msg in package.sortedMessages().items():
            for _, enum_obj in getattr(msg, 'enums', {}).items():
                yield EnumGqlGen.generate(enum_obj).rstrip() + '\n'
        for _, msg in package.sortedMessages().items():
            yield MessageGqlGen.generate(package, msg).rstrip() + '\n'

    @staticmethod
    def stitched(packages, generator_version):
        """Return one self-contained schema document covering every package.

        Uses the same definitions as the per-package files (so message-scoped
        enums are included) and declares the shared directive and scalars once.
        Query fields keep the bare message name unless two packages declare the
        same message name, in which case those fields are prefixed with their
        package to stay unique.
        """
        parts = [
            f'# Stitched schema - generated by struct-frame {generator_version}\n',
            f'# Contains all packages: {", ".join(sorted(packages.keys()))}\n\n',
            _PACKAGE_DIRECTIVE_DEF + '\n\n',
            _SCALAR_DEFS + '\n\n',
        ]
        counts = {}
        for pkg in packages.values():
            for _, msg in pkg.sortedMessages().items():
                counts[msg.name] = counts.get(msg.name, 0) + 1

        query_fields = []
        for pkg in packages.values():
            parts.append(f'# --- Package: {pkg.name} ---\n')
            for block in FileGqlGen.definitions(pkg):
                parts.append(block + '\n')
            for _, msg in pkg.sortedMessages().items():
                field_name = msg.name if counts[msg.name] == 1 else f"{pkg.name}_{msg.name}"
                query_fields.append(f"  {field_name}: {pascal_case(msg.package)}{msg.name}")
        if query_fields:
            parts.append('type Query {\n' + '\n'.join(query_fields) + '\n}\n')
        return ''.join(parts)

    @staticmethod
    def generate(package):
        # Multiline triple-quoted header block
        yield f"# Automatically generated GraphQL schema\n# Generated by struct-frame {version}\n"
        yield format_file_docs(package, '# ')

        # Add package ID as a comment if present
        if package.package_id is not None:
            yield f"# Package: {package.name} (ID: {package.package_id})\n"
        yield "\n"

        # Emit the @package directive definition so consumers can introspect it
        yield _PACKAGE_DIRECTIVE_DEF + '\n\n'
        yield _SCALAR_DEFS + '\n\n'

        first_block = True
        # Enums (package-level and message-scoped) followed by object types
        for block in FileGqlGen.definitions(package):
            if not first_block:
                yield '\n'
            first_block = False
            yield block

        # Root Query type
        if package.messages:
            if not first_block:
                yield '\n'
            yield 'type Query {\n'
            for _, msg in package.sortedMessages().items():
                type_name = f"{pascal_case(msg.package)}{msg.name}"
                yield f"  {msg.name}: {type_name}\n"
            yield '}\n'
