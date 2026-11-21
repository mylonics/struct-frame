"""Diagnostics for the struct-frame schema language.

Every problem found while reading a schema is a :class:`Diagnostic` with a stable code, a
severity, a source position and an optional hint.  Rendered, it reads::

    robot.sf:12:5: error[SF0201]: unknown type 'Positon' (did you mean 'Position'?)
       12 |     Positon pos;
          |     ^^^^^^^

Codes are grouped by stage:

* ``SF01xx`` lexical (bad characters, unterminated strings, bad numbers)
* ``SF02xx`` syntax (unexpected token, missing ``;``)
* ``SF03xx`` declarations (duplicates, bad attributes, bad sizes, legacy syntax)
* ``SF04xx`` literals and constants (wrong type, out of range)
"""

import difflib
from dataclasses import dataclass, field
from typing import List, Optional

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Position:
    line: int
    col: int


@dataclass
class Diagnostic:
    code: str
    severity: str
    message: str
    path: Optional[str] = None
    line: Optional[int] = None
    col: Optional[int] = None
    length: int = 1
    hint: Optional[str] = None
    source_line: Optional[str] = None

    def location(self):
        if self.path and self.line:
            return f"{self.path}:{self.line}:{self.col or 1}"
        return self.path or ""

    def render(self, snippet=True):
        loc = self.location()
        head = f"{loc}: " if loc else ""
        text = f"{head}{self.severity}[{self.code}]: {self.message}"
        if snippet and self.source_line is not None and self.line:
            gutter = f"{self.line:>5} | "
            pad = " " * (len(gutter) - 2) + "| "
            line_text = self.source_line.rstrip("\r\n").expandtabs(1)
            col = max(1, self.col or 1)
            width = max(1, min(self.length, max(1, len(line_text) - col + 1)))
            text += f"\n{gutter}{line_text}\n{pad}{' ' * (col - 1)}{'^' * width}"
        if self.hint:
            text += f"\n  = hint: {self.hint}"
        return text

    def __str__(self):
        return self.render()


class SchemaError(Exception):
    """Raised when a schema has at least one error. Carries every diagnostic found."""

    def __init__(self, diagnostics):
        self.diagnostics = list(diagnostics)
        super().__init__("\n".join(d.render() for d in self.diagnostics))


@dataclass
class DiagnosticSink:
    """Collects diagnostics for one file and attaches source lines for snippets."""

    path: Optional[str] = None
    text: str = ""
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def __post_init__(self):
        self._lines = self.text.splitlines()

    def _source(self, line):
        if line and 0 < line <= len(self._lines):
            return self._lines[line - 1]
        return None

    def add(self, severity, code, message, pos=None, length=1, hint=None):
        line = pos.line if pos else None
        col = pos.col if pos else None
        diag = Diagnostic(code, severity, message, self.path, line, col, length, hint,
                          self._source(line))
        self.diagnostics.append(diag)
        return diag

    def error(self, code, message, pos=None, length=1, hint=None):
        return self.add(ERROR, code, message, pos, length, hint)

    def warning(self, code, message, pos=None, length=1, hint=None):
        return self.add(WARNING, code, message, pos, length, hint)

    @property
    def errors(self):
        return [d for d in self.diagnostics if d.severity == ERROR]

    @property
    def warnings(self):
        return [d for d in self.diagnostics if d.severity == WARNING]

    def raise_if_errors(self):
        if self.errors:
            raise SchemaError(self.diagnostics)


def did_you_mean(name, candidates):
    """`` (did you mean 'x'?)`` when a candidate is close to *name*, else ``''``."""
    close = difflib.get_close_matches(str(name), list(candidates), n=1, cutoff=0.6)
    return f" (did you mean '{close[0]}'?)" if close else ""
