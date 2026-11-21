"""Syntax tree of the struct-frame schema language.

The tree keeps every comment (doc and private) so the formatter can reprint a file
without losing any of them. ``Comments.before`` holds the own-line comments written
directly before a declaration, ``Comments.after`` the comments on the same line after it
(for a block declaration, on the line of its ``{`` or ``}``).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

from .diagnostics import Position
from .lexer import Token


@dataclass
class Comments:
    before: List[Token] = field(default_factory=list)
    after: List[Token] = field(default_factory=list)

    def leading_docs(self):
        return [c.ir_text for c in self.before if c.doc]

    def trailing_docs(self):
        return [c.ir_text for c in self.after if c.doc]


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

@dataclass
class IntLit:
    value: int
    pos: Position
    text: str = ""


@dataclass
class FloatLit:
    value: float
    pos: Position
    text: str = ""


@dataclass
class StrLit:
    value: str
    pos: Position
    text: str = ""


@dataclass
class BoolLit:
    value: bool
    pos: Position


@dataclass
class NameRef:
    """An identifier in value position: a const, an enum member, ``inf`` or ``nan``."""
    name: str
    pos: Position


@dataclass
class Neg:
    operand: "Literal"
    pos: Position


@dataclass
class ArrayLit:
    items: List["Literal"]
    pos: Position


@dataclass
class StructLitField:
    name: str
    value: "Literal"
    pos: Position


@dataclass
class StructLit:
    fields: List[StructLitField]
    pos: Position


Literal = Union[IntLit, FloatLit, StrLit, BoolLit, NameRef, Neg, ArrayLit, StructLit]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class TypeRef:
    """A field type.

    ``container`` is the canonical container name (``array``, ``vector``, ``string``,
    ``bytes``, ``fixed_string``, ``fixed_bytes``) or None for a plain named type.
    ``spelled`` is the word as written (``vec``, ``u8``, ...).
    """
    name: str
    pos: Position
    spelled: str = ""
    container: Optional[str] = None
    element: Optional["TypeRef"] = None
    size: Optional[Literal] = None


@dataclass
class Attribute:
    name: str
    value: Optional[Literal]
    pos: Position


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

@dataclass
class FieldDecl:
    type: TypeRef
    name: str
    pos: Position
    name_pos: Position
    attrs: List[Attribute] = field(default_factory=list)
    default: Optional[Literal] = None
    comments: Comments = field(default_factory=Comments)


@dataclass
class EnumEntry:
    name: str
    value: Optional[Literal]
    pos: Position
    comments: Comments = field(default_factory=Comments)


@dataclass
class EnumDecl:
    name: str
    pos: Position
    entries: List[EnumEntry] = field(default_factory=list)
    ext_entries: Optional[List[EnumEntry]] = None
    attrs: List[Attribute] = field(default_factory=list)
    comments: Comments = field(default_factory=Comments)
    dangling: List[Token] = field(default_factory=list)
    ext_pos: Optional[Position] = None
    ext_comments: Comments = field(default_factory=Comments)
    ext_dangling: List[Token] = field(default_factory=list)


@dataclass
class OneofDecl:
    name: str
    pos: Position
    attrs: List[Attribute] = field(default_factory=list)
    variants: List[FieldDecl] = field(default_factory=list)
    ext_variants: Optional[List[FieldDecl]] = None
    comments: Comments = field(default_factory=Comments)
    dangling: List[Token] = field(default_factory=list)
    ext_pos: Optional[Position] = None
    ext_comments: Comments = field(default_factory=Comments)
    ext_dangling: List[Token] = field(default_factory=list)


@dataclass
class ExtensionsBlock:
    pos: Position
    fields: List[FieldDecl] = field(default_factory=list)
    comments: Comments = field(default_factory=Comments)
    dangling: List[Token] = field(default_factory=list)


Member = Union[FieldDecl, OneofDecl, EnumDecl, ExtensionsBlock]


@dataclass
class MessageDecl:
    """``message Name @id [...] { ... }`` or, with ``kind == "struct"``, an id-less struct."""
    kind: str
    name: str
    pos: Position
    id: Optional[Literal] = None
    attrs: List[Attribute] = field(default_factory=list)
    members: List[Member] = field(default_factory=list)
    comments: Comments = field(default_factory=Comments)
    dangling: List[Token] = field(default_factory=list)


@dataclass
class ConstDecl:
    type: TypeRef
    name: str
    value: Literal
    pos: Position
    name_pos: Position
    comments: Comments = field(default_factory=Comments)


@dataclass
class RpcDecl:
    name: str
    request: TypeRef
    response: Optional[TypeRef]
    pos: Position
    attrs: List[Attribute] = field(default_factory=list)
    comments: Comments = field(default_factory=Comments)


@dataclass
class ServiceDecl:
    name: str
    pos: Position
    rpcs: List[RpcDecl] = field(default_factory=list)
    comments: Comments = field(default_factory=Comments)
    dangling: List[Token] = field(default_factory=list)


@dataclass
class ImportDecl:
    path: str
    pos: Position
    comments: Comments = field(default_factory=Comments)


@dataclass
class PackageDecl:
    name: str
    pos: Position
    id: Optional[Literal] = None
    comments: Comments = field(default_factory=Comments)


Decl = Union[MessageDecl, EnumDecl, ConstDecl, ServiceDecl]


@dataclass
class File:
    path: Optional[str]
    package: Optional[PackageDecl] = None
    imports: List[ImportDecl] = field(default_factory=list)
    decls: List[Decl] = field(default_factory=list)
    header: List[Token] = field(default_factory=list)   # comments before `package`
    dangling: List[Token] = field(default_factory=list)  # comments at the end of the file

    def file_docs(self):
        return [c.ir_text for c in self.header if c.doc]
