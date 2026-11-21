"""Every ``sf`` code block in the documentation is valid schema-language text.

Each block must parse without errors. Blocks that are complete schemas (they declare a
``package`` and import nothing) are also compiled with ``--validate``. Blocks without a
``package`` line are fragments: they are wrapped in a package and checked together with
the other fragments of the same page, so a fragment may use types an earlier block of the
page declared.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from struct_frame.schema.parser import parse_text  # noqa: E402

DOCS = sorted((ROOT / "docs" / "src" / "content" / "docs").rglob("*.md*")) + [ROOT / "README.md"]
FENCE = re.compile(r"^(?P<indent>[ \t]*)```sf[^\n]*\n(?P<body>.*?)^(?P=indent)```", re.S | re.M)


def _blocks(path):
    text = path.read_text(encoding="utf-8")
    out = []
    for m in FENCE.finditer(text):
        indent = m.group("indent")
        body = "\n".join(line[len(indent):] if line.startswith(indent) else line
                         for line in m.group("body").split("\n"))
        line = text.count("\n", 0, m.start()) + 1
        out.append((line, body))
    return out


CASES = [(p, line, body) for p in DOCS for line, body in _blocks(p)]


def test_docs_contain_schema_blocks():
    assert len(CASES) >= 40
    assert not any("```proto" in p.read_text(encoding="utf-8") for p in DOCS), \
        "schema examples must use ```sf fences"


@pytest.mark.parametrize("path,line,body", CASES,
                         ids=[f"{p.relative_to(ROOT).as_posix()}:{l}" for p, l, _ in CASES])
def test_schema_block_parses(path, line, body):
    text = body if re.search(r"^\s*package\s", body, re.M) else "package doc_sample;\n" + body
    _tree, sink = parse_text(text, f"{path.name}:{line}")
    assert not sink.errors, "\n".join(d.render() for d in sink.errors)


def _validate(tmp_path, text):
    sf = tmp_path / "doc.sf"
    sf.write_text(text, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "struct_frame", str(sf), "--validate"],
                          capture_output=True, text=True, env=env)


COMPLETE = [(p, l, b) for p, l, b in CASES
            if re.search(r"^\s*package\s", b, re.M) and not re.search(r"^\s*import\s", b, re.M)
            and "service " not in b]


@pytest.mark.parametrize("path,line,body", COMPLETE,
                         ids=[f"{p.relative_to(ROOT).as_posix()}:{l}" for p, l, _ in COMPLETE])
def test_complete_schema_block_compiles(tmp_path, path, line, body):
    r = _validate(tmp_path, body)
    assert r.returncode == 0, r.stdout + r.stderr


def _used_types(node):
    """Type and constant names a declaration refers to."""
    from struct_frame.schema import ast
    names = set()

    def typ(t):
        if t is None:
            return
        if t.container is None:
            names.add(t.name.split(".")[-1])
        if t.element is not None:
            typ(t.element)
        if isinstance(t.size, ast.NameRef):
            names.add(t.size.name)

    def walk(n):
        if isinstance(n, ast.FieldDecl):
            typ(n.type)
            if isinstance(n.default, ast.NameRef):
                names.add(n.default.name)
        elif isinstance(n, ast.MessageDecl):
            for m in n.members:
                walk(m)
        elif isinstance(n, ast.OneofDecl):
            for v in n.variants + (n.ext_variants or []):
                walk(v)
        elif isinstance(n, ast.ExtensionsBlock):
            for f in n.fields:
                walk(f)
        elif isinstance(n, ast.ConstDecl):
            typ(n.type)
    walk(node)
    return names


def _fragment_cases():
    """(path, line, text) of each fragment block, preceded by the earlier declarations of
    the same page that it uses (transitively)."""
    from struct_frame.schema.printer import Printer
    cases = []
    for path in DOCS:
        known = {}   # name -> (decl, source text)
        for line, body in _blocks(path):
            if re.search(r"^\s*(package|import)\s", body, re.M) or "service " in body:
                continue
            tree, sink = parse_text("package doc_sample;\n" + body)
            if sink.errors:
                continue
            own = {d.name for d in tree.decls}
            needed, queue = {}, set()
            for d in tree.decls:
                queue |= _used_types(d)
            while queue:
                name = queue.pop()
                if name in own or name in needed or name not in known:
                    continue
                needed[name] = known[name]
                queue |= _used_types(known[name])
            context = []
            for decl in needed.values():
                printer = Printer()
                printer.decl(0, decl)
                context.append("\n".join(printer.out))
            text = "package doc_sample;\n" + "\n".join(context) + "\n" + body
            cases.append((path, line, text))
            for d in tree.decls:
                known.setdefault(d.name, d)
    return cases


FRAGMENTS = _fragment_cases()


@pytest.mark.parametrize("path,line,text", FRAGMENTS,
                         ids=[f"{p.relative_to(ROOT).as_posix()}:{l}" for p, l, _ in FRAGMENTS])
def test_fragment_block_compiles(tmp_path, path, line, text):
    r = _validate(tmp_path, text)
    assert r.returncode == 0, r.stdout + r.stderr + "\n" + text
