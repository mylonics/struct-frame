"""Tokenizer for the struct-frame schema language.

Produces a flat token list. Comments are kept as ``COMMENT`` tokens (the parser decides
what they document); whitespace is dropped. Positions are 1-based lines and columns.

Comment kinds:

* ``///`` line comments and ``/** ... */`` block comments are *doc comments*: they reach
  the generated code.
* ``//`` and ``/* ... */`` comments are private to the schema.
"""

from dataclasses import dataclass
from typing import Optional

from .diagnostics import Position

IDENT = "ident"
INT = "int"
FLOAT = "float"
STRING = "string"
PUNCT = "punct"
COMMENT = "comment"
EOF = "eof"

_PUNCT2 = ("->",)
_PUNCT1 = "{}[]()<>,;=@:.-+"

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\", '"': '"', "'": "'"}


@dataclass
class Token:
    kind: str
    text: str           # source text of the token
    pos: Position
    value: object = None
    # COMMENT only
    doc: bool = False
    inline: bool = False      # shares its first line with an earlier token
    end_line: int = 0
    ir_text: Optional[str] = None   # documentation text handed to the generators

    @property
    def end_col(self):
        return self.pos.col + len(self.text)

    def __repr__(self):
        return f"Token({self.kind}, {self.text!r}, {self.pos.line}:{self.pos.col})"


def _doc_ir_text(raw):
    """Documentation text for a doc comment.

    The generators expect each comment as it would be written in C-family source, so a
    ``/// text`` doc comment becomes ``// text`` and ``/** text */`` becomes ``/* text */``.
    """
    if raw.startswith("///"):
        return "//" + raw[3:].rstrip()
    if raw.startswith("/**"):
        return ("/*" + raw[3:]).rstrip()
    return raw.rstrip()


def tokenize(text, sink):
    """Tokenize *text*; lexical errors go to *sink*. Always ends with an EOF token."""
    tokens = []
    i = 0
    n = len(text)
    line = 1
    line_start = 0
    last_code_line = 0   # line of the most recent non-comment token

    if text.startswith("﻿"):
        i = 1
        line_start = 1

    def pos_at(index):
        return Position(line, index - line_start + 1)

    while i < n:
        ch = text[i]

        if ch == "\n":
            line += 1
            i += 1
            line_start = i
            continue
        if ch in " \t\r\f\v":
            i += 1
            continue

        start = i
        pos = pos_at(i)

        # Comments
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            raw = text[i:j].rstrip("\r")
            doc = raw.startswith("///")
            tokens.append(Token(COMMENT, raw, pos, doc=doc, inline=(last_code_line == line),
                                end_line=line, ir_text=_doc_ir_text(raw) if doc else None))
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                sink.error("SF0103", "unterminated block comment", pos, 2,
                           hint="close it with */")
                j = n
                raw = text[i:]
            else:
                j += 2
                raw = text[i:j]
            doc = raw.startswith("/**") and not raw.startswith("/**/")
            first_line = line
            newlines = raw.count("\n")
            tok = Token(COMMENT, raw, pos, doc=doc, inline=(last_code_line == first_line),
                        end_line=first_line + newlines,
                        ir_text=_doc_ir_text(raw) if doc else None)
            tokens.append(tok)
            if newlines:
                line += newlines
                line_start = start + raw.rfind("\n") + 1
            i = j
            continue

        # Identifiers / keywords
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            tokens.append(Token(IDENT, word, pos, word))
            last_code_line = line
            i = j
            continue

        # Numbers
        if ch.isdigit():
            j, tok = _number(text, i, pos, sink)
            tokens.append(tok)
            last_code_line = line
            i = j
            continue

        # Strings
        if ch == '"':
            j, tok = _string(text, i, pos, sink)
            tokens.append(tok)
            last_code_line = line
            i = j
            continue

        two = text[i:i + 2]
        if two in _PUNCT2:
            tokens.append(Token(PUNCT, two, pos, two))
            last_code_line = line
            i += 2
            continue
        if ch in _PUNCT1:
            tokens.append(Token(PUNCT, ch, pos, ch))
            last_code_line = line
            i += 1
            continue

        if ch == "'":
            sink.error("SF0105", "strings use double quotes", pos, 1,
                       hint="write \"...\" instead of '...'")
        else:
            sink.error("SF0101", f"unexpected character {ch!r}", pos, 1)
        i += 1

    tokens.append(Token(EOF, "", Position(line, i - line_start + 1)))
    return tokens


def _number(text, i, pos, sink):
    n = len(text)
    j = i
    base = 10
    if text.startswith(("0x", "0X"), i):
        base, j = 16, i + 2
        digits = "0123456789abcdefABCDEF_"
    elif text.startswith(("0b", "0B"), i):
        base, j = 2, i + 2
        digits = "01_"
    elif text.startswith(("0o", "0O"), i):
        base, j = 8, i + 2
        digits = "01234567_"
    else:
        digits = "0123456789_"
    k = j
    while k < n and (text[k] in digits):
        k += 1
    is_float = False
    if base == 10:
        if k < n and text[k] == "." and k + 1 < n and text[k + 1].isdigit():
            is_float = True
            k += 1
            while k < n and (text[k].isdigit() or text[k] == "_"):
                k += 1
        if k < n and text[k] in "eE":
            m = k + 1
            if m < n and text[m] in "+-":
                m += 1
            if m < n and text[m].isdigit():
                is_float = True
                k = m
                while k < n and text[k].isdigit():
                    k += 1
    # Identifier characters glued to a number (e.g. 12abc, 0x1G) are an error.
    end = k
    while end < n and (text[end].isalnum() or text[end] == "_"):
        end += 1
    raw = text[i:end]
    if end != k or (base != 10 and k == j):
        sink.error("SF0102", f"invalid number literal '{raw}'", pos, len(raw))
        return end, Token(INT, raw, pos, 0)
    body = raw.replace("_", "")
    if "__" in raw or raw.endswith("_"):
        sink.error("SF0102", f"invalid number literal '{raw}' (misplaced '_')", pos, len(raw))
    if is_float:
        return end, Token(FLOAT, raw, pos, float(body))
    if base == 10 and len(body) > 1 and body.startswith("0"):
        sink.error("SF0102", f"invalid number literal '{raw}' (leading zero)", pos, len(raw),
                   hint="write 0o17 for octal, or drop the leading zero")
        return end, Token(INT, raw, pos, int(body, 10))
    value = int(body[2:] if base != 10 else body, base)
    return end, Token(INT, raw, pos, value)


def _string(text, i, pos, sink):
    n = len(text)
    j = i + 1
    out = []
    while j < n:
        ch = text[j]
        if ch == '"':
            return j + 1, Token(STRING, text[i:j + 1], pos, "".join(out))
        if ch == "\n":
            break
        if ch == "\\":
            if j + 1 >= n:
                break
            esc = text[j + 1]
            if esc in _ESCAPES:
                out.append(_ESCAPES[esc])
                j += 2
                continue
            if esc == "x":
                hexd = text[j + 2:j + 4]
                if len(hexd) == 2 and all(c in "0123456789abcdefABCDEF" for c in hexd):
                    code = int(hexd, 16)
                    if code > 0x7F:
                        col = pos.col + (j - i)
                        sink.error("SF0104", f"'\\x{hexd}' is not ASCII; strings are UTF-8 text",
                                   Position(pos.line, col), 4,
                                   hint=f"write \\u00{hexd.upper()} for the code point, or a byte "
                                        f"array such as [0x{hexd.upper()}] for raw bytes")
                    out.append(chr(code))
                    j += 4
                    continue
            if esc == "u":
                hexd = text[j + 2:j + 6]
                if len(hexd) == 4 and all(c in "0123456789abcdefABCDEF" for c in hexd):
                    out.append(chr(int(hexd, 16)))
                    j += 6
                    continue
            col = pos.col + (j - i)
            sink.error("SF0104", f"invalid escape sequence '\\{esc}'",
                       Position(pos.line, col), 2,
                       hint="valid escapes: \\n \\r \\t \\0 \\\\ \\\" \\' \\xNN \\uNNNN")
            j += 2
            continue
        out.append(ch)
        j += 1
    sink.error("SF0103", "unterminated string literal", pos, 1, hint='close it with "')
    return j, Token(STRING, text[i:j], pos, "".join(out))
