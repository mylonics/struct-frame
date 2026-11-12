"""Language facts shared by the compiler and the VS Code extension.

``src/struct_frame/language_facts.py`` is the single source of primitive types, option
names, accepted values and limits. The compiler imports it, and the extension in
``editors/vscode`` reads a generated JSON copy. These tests keep the two in sync:

* the committed JSON must equal what the module renders (CI: ``--check``);
* the compiler's own tables must agree with the facts;
* every schema the extension's corpus test opens must be accepted by the compiler
  (the extension asserts it reports zero errors on the same files).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, SRC_DIR, run_generator

sys.path.insert(0, str(SRC_DIR))

from struct_frame import language_facts as facts  # noqa: E402
import struct_frame.generate as gen  # noqa: E402
import struct_frame.schema_diff as schema_diff  # noqa: E402

FACTS_SCRIPT = SRC_DIR / "struct_frame" / "language_facts.py"

# Keep in sync with CORPUS in editors/vscode/server/src/__tests__/corpus.test.ts.
VALID_SCHEMA_DIRS = [
    REPO_ROOT / "tests" / "proto",
    REPO_ROOT / "tests" / "benchmarks" / "schema",
    REPO_ROOT / "tests" / "docs" / "schemas",
]
EXTENSION_EXAMPLES = [REPO_ROOT / "editors" / "vscode" / "examples" / name
                      for name in ("example.sf", "fixture-imports.sf")]
# examples/**/*.sf is covered by test_generator_regressions.test_example_schemas_validate.
CORPUS = sorted(p for d in VALID_SCHEMA_DIRS for p in d.glob("*.sf")) + EXTENSION_EXAMPLES


def _out(r: subprocess.CompletedProcess) -> str:
    return (r.stdout or "") + "\n" + (r.stderr or "")


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "schema.sf"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The generated JSON
# ---------------------------------------------------------------------------

def test_committed_json_is_up_to_date():
    r = subprocess.run([sys.executable, str(FACTS_SCRIPT), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, _out(r)


def test_json_has_no_release_specific_data():
    data = json.loads(facts.render())
    assert data["schema_version"] == facts.SCHEMA_VERSION
    text = facts.render()
    # A compiler version would change the file every release and force an extension publish.
    assert "version\"" not in text.replace("schema_version\"", "")
    assert str(REPO_ROOT) not in text


def test_64_bit_bounds_are_exact_strings():
    data = json.loads(facts.render())
    assert data["integer_ranges"]["uint64"] == {"min": "0", "max": "18446744073709551615"}
    assert data["integer_ranges"]["int64"]["min"] == "-9223372036854775808"


def test_check_fails_on_a_stale_file(tmp_path):
    stale = tmp_path / "language-facts.json"
    stale.write_text("{}\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(FACTS_SCRIPT), "--check", str(stale)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "--write" in r.stderr


# ---------------------------------------------------------------------------
# The compiler's tables agree with the facts
# ---------------------------------------------------------------------------

def test_compiler_tables_derive_from_the_facts():
    assert list(gen.default_types) == list(facts.PRIMITIVES)
    for name, (_kind, size) in facts.PRIMITIVES.items():
        if size is not None:
            assert gen.default_types[name]["size"] == size
    assert set(gen.type_codes) - {"enum"} == set(facts.PRIMITIVES)
    fixed = {n for n, (_k, s) in facts.PRIMITIVES.items() if s is not None}
    assert set(gen.wire_struct_format) == fixed
    assert schema_diff._SCALAR_SIZES == {n: s for n, (_k, s) in facts.PRIMITIVES.items() if s is not None}
    assert gen.INTEGER_RANGES is facts.INTEGER_RANGES
    assert set(gen._FIELD_OPTIONS) == set(facts.FIELD_OPTIONS)
    assert set(gen._MESSAGE_OPTIONS) == set(facts.MESSAGE_OPTIONS) | set(facts.MESSAGE_OPTION_ALIASES)
    assert set(gen._ONEOF_OPTIONS) == set(facts.ONEOF_OPTIONS)


class _Identifier:
    """Stands in for proto_schema_parser's Identifier (unquoted option values)."""

    def __init__(self, name):
        self.name = name


@pytest.mark.parametrize("value, expected", [
    (True, True), (False, False), ("true", True), ('"TRUE"', True), ("1", True), (1, True),
    ("yes", True), ("on", True), (_Identifier("yes"), True), (_Identifier("On"), True),
    ("false", False), ("0", False), ("maybe", False), (_Identifier("off"), False),
])
def test_is_true(value, expected):
    assert facts.is_true(value) is expected


@pytest.mark.parametrize("value, expected", [
    ("auto", "auto"), ('"msgid"', "msgid"), (_Identifier("field_order"), "field_order"),
    ("none", "none"), ("false", "none"), ("OFF", "none"), (_Identifier("disabled"), "none"),
    ("bogus", None),
])
def test_normalize_discriminator(value, expected):
    assert facts.normalize_discriminator(value) == expected


def test_option_base_name():
    assert facts.option_base_name("(sf.size)") == "size"
    assert facts.option_base_name("(struct_frame.max_size)") == "max_size"
    assert facts.option_base_name("sf.size") == "sf.size"
    assert facts.option_base_name(" default ") == "default"


# ---------------------------------------------------------------------------
# Behaviour that now goes through the shared helpers
# ---------------------------------------------------------------------------

def _oneof_schema(variable_value: str) -> str:
    return f"""
package facts_test;
message Holder {{
  option msgid = 1;
  option variable = true;
  oneof payload {{
    option variable = {variable_value};
    uint8 a = 1;
    uint16 b = 2;
  }}
}}
"""


def test_oneof_variable_on_is_true():
    # `on` was missing from the oneof's true set; the oneof was silently not variable.
    import proto_schema_parser.parser as psp
    file = psp.Parser().parse(_oneof_schema("on"))
    msg = next(e for e in file.file_elements if type(e).__name__ == "Message")
    oneof_ast = next(e for e in msg.elements if type(e).__name__ == "OneOf")
    oneof = gen.OneOf("facts_test", [])
    assert oneof.parse(oneof_ast)
    assert oneof.variable is True


def test_unquoted_yes_enables_message_variable():
    import proto_schema_parser.parser as psp
    file = psp.Parser().parse("package p; message M { option msgid = 1; option variable = yes; uint8 a = 1; }")
    msg_ast = next(e for e in file.file_elements if type(e).__name__ == "Message")
    msg = gen.Message("p", [])
    assert msg.parse(msg_ast)
    assert msg.variable is True


def test_unknown_oneof_option_warns(tmp_path):
    sf = _write(tmp_path, """
package facts_test;
message Holder {
  option msgid = 1;
  oneof payload {
    option discriminater = field_order;
    uint8 a = 1;
  }
}
""")
    r = run_generator(sf, "--validate")
    assert r.returncode == 0, _out(r)
    assert "unknown option 'discriminater' in oneof payload" in r.stderr
    assert "did you mean 'discriminator'" in r.stderr


# ---------------------------------------------------------------------------
# Corpus shared with the extension's corpus.test.ts
# ---------------------------------------------------------------------------

def test_corpus_is_populated():
    assert len(CORPUS) >= 15
    for path in EXTENSION_EXAMPLES:
        assert path.is_file(), path


@pytest.mark.parametrize("sf", CORPUS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_corpus_schema_is_compiler_valid(sf):
    r = run_generator(sf, "--validate")
    assert r.returncode == 0, _out(r)
