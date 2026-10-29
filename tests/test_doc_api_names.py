#!/usr/bin/env python3
"""Every SDK identifier a documentation page mentions must exist in that SDK's source.

The doc-sample compiler skips most snippets (they depend on generated code or on the reader's own
variables), which is how pages kept calling ``new TcpTransport("host", 8080)`` after the constructor
took a config object. This test is a cheaper net: it pulls the type, function and method names out
of each SDK page's code blocks and requires every one to appear somewhere in the runtime source for
that language, the generated test output, or the page's own definitions.

Names the page's reader is expected to define (their messages, handlers, variables) are listed in
``USER_DEFINED``. A genuinely stale name fails with the page and the name.

A second test catches the commonest naming mistake: only the C generator prefixes types with the
package name (``SensorSystemSensorType``); every other language uses a namespace or module, so a
package-prefixed name in a non-C code block is always wrong.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs" / "src" / "content" / "docs"
BOILER = REPO / "src" / "struct_frame" / "boilerplate"
GENERATED = REPO / "tests" / "generated"

# fence language tag(s) -> (source dirs/files to search, file suffixes)
LANGS = {
    "c": (("c",), [BOILER / "c", GENERATED / "c"], {".h"}),
    "cpp": (("cpp",), [BOILER / "cpp" / "frame_profiles.hpp", BOILER / "cpp" / "frame_base.hpp",
                       BOILER / "cpp" / "struct_frame_sdk", GENERATED / "cpp"], {".hpp", ".h"}),
    "python": (("python", "py"), [BOILER / "py", GENERATED / "py"], {".py"}),
    "ts": (("ts", "typescript", "js", "javascript"), [BOILER / "ts", GENERATED / "ts"], {".ts"}),
    "rust": (("rust",), [BOILER / "rust", GENERATED / "rust"], {".rs"}),
    "csharp": (("csharp", "cs"), [BOILER / "csharp", GENERATED / "csharp"], {".cs"}),
}

# Names a reader defines themselves, standard-library names, and message types from the
# documentation's example schemas. Extend this list rather than weakening the check.
USER_DEFINED = {
    # example messages / user code
    "Status", "StatusMessage", "SensorDataMessage", "Ping", "Pong", "Heartbeat", "Command", "Telemetry",
    "BasicTypesMessage", "MyMessage", "SensorData", "Vehicle", "Position",
    "source_sdk", "target_sdk", "sensor_sdk", "bulk_sdk", "ipc_sdk", "handle_command",
    "handle_status", "HandleStatus", "handleStatus", "on_status", "my_serial_port", "send_bytes",
    "received_bytes", "get_info", "getInfo", "main", "Main", "run", "RunAsync", "Program",
    # language / standard library
    "Console", "WriteLine", "Task", "Func", "Action", "Math", "Array", "Promise", "Error", "Date", "JSON",
    "console", "log", "print", "len", "range", "str", "int", "bytes", "bytearray", "list", "dict", "set",
    "format", "println", "vec", "Vec", "Some", "None", "Ok", "Err", "Option", "Result", "String", "Box",
    "std", "chrono", "thread", "this_thread", "sleep_for", "array", "span", "vector", "memcpy", "printf",
    "uint8_t", "uint16_t", "uint32_t", "size_t", "unique_ptr", "make_unique", "move",
    "from_secs", "from_millis", "now", "elapsed", "unwrap", "expect", "clone", "iter", "collect", "push",
    "async", "await", "then", "catch", "resolve", "reject", "setTimeout", "require", "import",
    "handle_message", "send_data", "setup",
    # placeholders from the documentation's example schemas
    # (C names, which carry the package prefix)
    "ExampleSensorData", "ExampleStatus_deserialize", "SensorSystemSensorType_to_string",
    "SensorType_to_string",
    "asyncio", "sleep", "create_task", "gather", "time", "threading", "Thread", "Event", "Lock",
}

IDENT = re.compile(r"(?<![\w.])(?:new\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^>\n]*>)?\s*\(")
QUALIFIED = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Transport|Config|Reader|Writer|Sdk|Subscription)[A-Za-z0-9_]*)\b")
FENCE = re.compile(r"```([^\n`]*)\n(.*?)\n```", re.S)
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "foreach", "using", "lock", "sizeof", "nameof",
            "typeof", "fn", "def", "match", "when", "with", "assert", "else", "elif", "function", "async"}


def _corpus(dirs, suffixes) -> str:
    chunks = []
    for d in dirs:
        files = [d] if d.is_file() else [f for f in d.rglob("*") if f.suffix in suffixes]
        for f in files:
            if "asio-repo" in f.parts or "node_modules" in f.parts or "target" in f.parts:
                continue
            try:
                chunks.append(f.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    return "\n".join(chunks)


def _names(page: Path, langs):
    text = page.read_text(encoding="utf-8")
    found = set()
    for m in FENCE.finditer(text):
        info = m.group(1).split()
        if not info or info[0].lower() not in langs:
            continue
        body = m.group(2)
        # Names declared inside the snippet itself are the reader's own.
        declared = set(re.findall(r"\b(?:class|struct|def|fn|function|interface|enum|let|var|const|auto|record)\s+([A-Za-z_]\w*)", body))
        declared |= set(re.findall(r"\b(?:int|string|bool|float|double|uint\d*_t|byte|void)\s+([A-Za-z_]\w*)", body))
        # Comments mention names that are not code.
        code = re.sub(r"(//[^\n]*|#[^\n]*|/\*.*?\*/)", "", body, flags=re.S)
        for name in IDENT.findall(code):
            if name not in KEYWORDS and name not in declared:
                found.add(name)
        for name in QUALIFIED.findall(code):
            if name not in declared:
                found.add(name)
    return found


def _pages():
    return sorted(p for p in DOCS.rglob("*") if p.suffix in (".md", ".mdx"))


@pytest.fixture(scope="module")
def corpora():
    if not (GENERATED / "py").exists():
        pytest.skip("generated tests not present (run python test_all.py first)")
    return {key: re.sub(r"_", "", _corpus(dirs, suffixes)).lower() for key, (_, dirs, suffixes) in LANGS.items()}


@pytest.mark.parametrize("lang", sorted(LANGS))
def test_documented_names_exist_in_sdk_source(lang, corpora):
    tags, _, _ = LANGS[lang]
    problems = {}
    for page in _pages():
        # Case/underscore-insensitive match covers snake_case / camelCase / PascalCase spellings.
        missing = sorted(n for n in _names(page, tags)
                         if n not in USER_DEFINED and re.sub(r"_", "", n).lower() not in corpora[lang])
        if missing:
            problems[str(page.relative_to(DOCS)).replace(chr(92), "/")] = missing
    assert not problems, (
        f"documentation mentions {lang} names that appear nowhere in the {lang} runtime or generated code:"
        + chr(10) + chr(10).join(f"  {page}: {names}" for page, names in problems.items())
        + chr(10) + "Fix the page, or add genuinely user-defined names to USER_DEFINED in this test.")


def _pascal(name: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in re.split(r"[_\W]+", name) if w)


def _package_prefixes() -> set:
    """PascalCase package names used anywhere in the docs or the test schemas."""
    names = set()
    sources = list(_pages()) + sorted((REPO / "tests" / "proto").glob("*.sf"))
    for path in sources:
        text = path.read_text(encoding="utf-8")
        names.update(_pascal(m) for m in re.findall(r"^\s*package\s+([A-Za-z_][\w.]*)\s*;", text, re.M))
        names.update(re.findall(r"StructFrame\.([A-Z][A-Za-z0-9]*)", text))
        names.update(_pascal(m) for m in re.findall(r"structframe::([a-z_][a-z0-9_]*)", text))
        names.update(_pascal(m) for m in re.findall(r"struct_frame\.generated\.([a-z_][a-z0-9_]*)", text))
    return names - {"Sdk", "Framing", "Profiles", "Generated", "Types"}


NON_C_TAGS = {tag for key, (tags, _, _) in LANGS.items() if key != "c" for tag in tags}


def test_no_c_style_package_prefixed_names_outside_c():
    prefixes = sorted(_package_prefixes(), key=len, reverse=True)
    rx = re.compile(r"(?:" + "|".join(prefixes) + r")[A-Z][A-Za-z0-9]*")
    problems = {}
    for page in _pages():
        for m in FENCE.finditer(page.read_text(encoding="utf-8")):
            info = m.group(1).split()
            if not info or info[0].lower() not in NON_C_TAGS:
                continue
            hits = sorted(set(rx.findall(m.group(2))))
            if hits:
                problems.setdefault(str(page.relative_to(DOCS)).replace(chr(92), "/"), set()).update(hits)
    assert not problems, (
        "only C prefixes generated type names with the package; these non-C code blocks use C-style names:"
        + chr(10) + chr(10).join(f"  {page}: {sorted(names)}" for page, names in problems.items()))
