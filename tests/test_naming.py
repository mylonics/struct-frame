#!/usr/bin/env python3
"""
Tests for acronym-aware identifier conversion and per-language name overrides.

Source identifiers such as ``BleMCuHost``, ``BleHost`` and ``GateCurrent`` used
to be flattened by the converters (``Blemcuhost``, ``BLEHOST``, ``Gatecurrent``).
One tokenizer now drives every language; these tests pin the exact C++, C# and
TypeScript names (plus C, Python, Rust and JavaScript) and the explicit
``--name_overrides`` escape hatch for names heuristics cannot resolve.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from test_utils import SRC_DIR, _check, run_generator

NAMES_SCHEMA = """\
package names_test;

enum BleHost {
  BLE_HOST_OK = 0;
  GateCurrent = 1;
  BleMCuHost = 2;
  BLEHost = 3;
}

message BleMCuHost {
  option msgid = 1;
  uint32 gate_current = 1;
  uint32 BLEHost = 2;
  uint32 bleHostId = 3;
  BleHost mode = 4;
}

message BleHostStatus {
  option msgid = 2;
  BleMCuHost host = 1;
}
"""


# ---------------------------------------------------------------------------
# Converter unit tests
#
# The converters are exercised in a subprocess: importing the ``struct_frame``
# source package into the pytest process would shadow the generated
# ``struct_frame.generated`` packages other tests import.
# ---------------------------------------------------------------------------

_PROBE = r"""
import json, sys
from struct_frame import pascal_case
from struct_frame.base import NamingStyleC, NamingStyleCpp
from struct_frame.naming import (NameOverrides, NameOverrideError, split_identifier,
                                 to_camel_case, to_pascal_case, to_screaming_snake_case)
names = json.loads(sys.argv[1])
c, cpp = NamingStyleC(), NamingStyleCpp()
out = {}
for n in names:
    out[n] = {
        "tokens": split_identifier(n),
        "pascal": to_pascal_case(n),
        "pascal_case": pascal_case(n),
        "screaming": to_screaming_snake_case(n),
        "camel": to_camel_case(n),
        "c_enum_entry": c.enum_entry(n),
        "cpp_enum_entry": cpp.enum_entry(n),
        "c_underscore": c.underscore(n),
    }
print(json.dumps(out))
"""


def _convert(names):
    env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
    result = subprocess.run([sys.executable, "-c", _PROBE, json.dumps(list(names))],
                            capture_output=True, text=True, env=env)
    _check(result.returncode == 0, f"converter probe failed:\n{result.stderr}")
    return json.loads(result.stdout)


def test_split_identifier_tokenizer():
    cases = {
        "BleMCuHost": ["Ble", "M", "Cu", "Host"],
        "BleHost": ["Ble", "Host"],
        "BLEHost": ["BLE", "Host"],
        "GateCurrent": ["Gate", "Current"],
        "gate_current": ["gate", "current"],
        "bleHostId": ["ble", "Host", "Id"],
        "BLE_HOST_OK": ["BLE", "HOST", "OK"],
        "ADCCommand": ["ADC", "Command"],
        "Float32Value": ["Float32", "Value"],
        "_leading__and-trailing_": ["leading", "and", "trailing"],
    }
    results = _convert(cases)
    for name, expected in cases.items():
        _check(results[name]["tokens"] == expected,
               f"split_identifier({name!r}) = {results[name]['tokens']}, expected {expected}")


def test_pascal_case_is_acronym_aware():
    cases = {
        "BleMCuHost": "BleMCuHost",
        "BleHost": "BleHost",
        "BLEHost": "BLEHost",
        "GateCurrent": "GateCurrent",
        "gate_current": "GateCurrent",
        "bleHostId": "BleHostId",
        "ble_host": "BleHost",
        # single-case names carry no acronym information: title-cased as before
        "BLE_HOST_OK": "BleHostOk",
        "LOW": "Low",
        "value2x": "Value2X",
        "order_test": "OrderTest",
    }
    results = _convert(cases)
    for name, expected in cases.items():
        for key in ("pascal", "pascal_case", "cpp_enum_entry"):
            _check(results[name][key] == expected, f"{key}({name!r}) = {results[name][key]!r}, expected {expected!r}")


def test_enum_entry_is_acronym_aware():
    cases = {
        "BLE_HOST_OK": "BLE_HOST_OK",
        "ADC1": "ADC1",
        "LOW": "LOW",
        "GateCurrent": "GATE_CURRENT",
        "BleHost": "BLE_HOST",
        "BleMCuHost": "BLE_M_CU_HOST",
        "BLEHost": "BLE_HOST",
        "idle": "IDLE",
        "error_state": "ERROR_STATE",
    }
    results = _convert(cases)
    for name, expected in cases.items():
        for key in ("screaming", "c_enum_entry"):
            _check(results[name][key] == expected, f"{key}({name!r}) = {results[name][key]!r}, expected {expected!r}")


def test_camel_case_is_acronym_aware():
    cases = {
        "gate_current": "gateCurrent",
        "GateCurrent": "GateCurrent",
        "bleHostId": "bleHostId",
        "BLEHost": "BLEHost",
        "ble_HOST_id": "bleHOSTId",
        "single": "single",
        "MAX_VALUE": "MAXValue",
    }
    results = _convert(cases)
    for name, expected in cases.items():
        _check(results[name]["camel"] == expected, f"to_camel_case({name!r}) = {results[name]['camel']!r}, expected {expected!r}")


def test_tokenizer_agrees_with_c_underscore():
    """C-style snake_case (NamingStyleC.underscore) and the shared tokenizer
    must agree on word boundaries."""
    names = ("BleMCuHost", "BleHost", "BLEHost", "GateCurrent", "bleHostId", "ADCCommand",
             "Float32Value", "gate_current", "BLE_HOST_OK")
    results = _convert(names)
    for name in names:
        tokens = "_".join(t.lower() for t in results[name]["tokens"])
        _check(results[name]["c_underscore"] == tokens,
               f"underscore({name!r}) = {results[name]['c_underscore']!r} but tokens give {tokens!r}")


# ---------------------------------------------------------------------------
# Generated names
# ---------------------------------------------------------------------------

LANG_SUFFIXES = {
    "c": ("--build_c", "--c_path"),
    "cpp": ("--build_cpp", "--cpp_path"),
    "ts": ("--build_ts", "--ts_path"),
    "js": ("--build_js", "--js_path"),
    "py": ("--build_py", "--py_path"),
    "csharp": ("--build_csharp", "--csharp_path"),
    "rust": ("--build_rust", "--rust_path"),
}


def _generate(tmp: Path, extra=(), schema: str = NAMES_SCHEMA) -> dict[str, Path]:
    proto = tmp / "names.sf"
    proto.write_text(schema, encoding="utf-8")
    flags = ["--force", "--catalog_path", str(tmp / "catalog") + os.sep]
    dirs = {}
    for lang, (build, path) in LANG_SUFFIXES.items():
        dirs[lang] = tmp / lang
        flags += [build, path, str(dirs[lang]) + os.sep]
    flags += list(extra)
    result = run_generator(proto, *flags)
    _check(result.returncode == 0, f"Generation failed:\n{result.stdout}\n{result.stderr}")
    return dirs


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_generated_names_cpp_csharp_typescript():
    """Exact names produced for the cases that used to be flattened."""
    with tempfile.TemporaryDirectory() as tmp:
        dirs = _generate(Path(tmp))

        cpp = _read(dirs["cpp"] / "names_test.structframe.hpp")
        for expected in ("enum class BleHost : uint8_t {",
                         "    BleHostOk = 0,",
                         "    GateCurrent = 1,",
                         "    BleMCuHost = 2,",
                         "    BLEHost = 3",
                         "struct BleMCuHost : ",
                         "struct BleHostStatus : "):
            _check(expected in cpp, f"C++ output should contain {expected!r}")
        for flattened in ("Blemcuhost", "Blehost", "Gatecurrent", "BLEMCUHOST", "GATECURRENT"):
            _check(flattened not in cpp, f"C++ output must not contain flattened {flattened!r}")

        cs_enum = _read(dirs["csharp"] / "NamesTest" / "Enums" / "BleHost.cs")
        for expected in ("BLE_HOST_OK = 0,", "GATE_CURRENT = 1,", "BLE_M_CU_HOST = 2,", "BLE_HOST = 3"):
            _check(expected in cs_enum, f"C# enum should contain {expected!r}")
        cs_msg = _read(dirs["csharp"] / "NamesTest" / "Messages" / "BleMCuHost.cs")
        for expected in ("public class BleMCuHost : ",
                         "public uint GateCurrent { get; set; }",
                         "public uint BLEHost { get; set; }",
                         "public uint BleHostId { get; set; }",
                         "public BleHost Mode { get; set; }"):
            _check(expected in cs_msg, f"C# message should contain {expected!r}")
        for flattened in ("Gatecurrent", "Blehost"):
            _check(flattened not in cs_msg + cs_enum, f"C# output must not contain flattened {flattened!r}")

        ts = _read(dirs["ts"] / "names-test.structframe.ts")
        for expected in ("export enum BleHost {",
                         "    BleHostOk = 0,",
                         "    GateCurrent = 1,",
                         "    BleMCuHost = 2,",
                         "    BLEHost = 3",
                         "export class BleMCuHost extends MessageBase",
                         "get gateCurrent(): number",
                         "get BLEHost(): number",
                         "get bleHostId(): number"):
            _check(expected in ts, f"TypeScript output should contain {expected!r}")
        _check("Blemcuhost" not in ts and "Gatecurrent" not in ts, "TypeScript output must not contain flattened names")

        js = _read(dirs["js"] / "names-test.structframe.js")
        for expected in ("BleHostOk: 0,", "GateCurrent: 1,", "BleMCuHost: 2,", "BLEHost: 3"):
            _check(expected in js, f"JavaScript output should contain {expected!r}")


def test_generated_names_c_python_rust():
    with tempfile.TemporaryDirectory() as tmp:
        dirs = _generate(Path(tmp))

        c = _read(dirs["c"] / "names_test.structframe.h")
        for expected in ("BLE_HOST_BLE_HOST_OK = 0,", "BLE_HOST_GATE_CURRENT = 1,",
                         "BLE_HOST_BLE_M_CU_HOST = 2,", "BLE_HOST_BLE_HOST = 3"):
            _check(expected in c, f"C output should contain {expected!r}")
        _check("GATECURRENT" not in c and "BLEMCUHOST" not in c, "C output must not contain flattened names")

        py = _read(dirs["py"] / "struct_frame" / "generated" / "names_test.py")
        for expected in ("BLE_HOST_OK = 0", "GATE_CURRENT = 1", "BLE_M_CU_HOST = 2", "BLE_HOST = 3"):
            _check(expected in py, f"Python output should contain {expected!r}")

        rs = _read(dirs["rust"] / "names_test.structframe.rs")
        for expected in ("BLE_HOST_OK = 0,", "GATE_CURRENT = 1,", "BLE_M_CU_HOST = 2,", "BLE_HOST = 3,"):
            _check(expected in rs, f"Rust output should contain {expected!r}")


# ---------------------------------------------------------------------------
# Explicit overrides
# ---------------------------------------------------------------------------

OVERRIDES = {
    "all": {"BleMCuHost": "BleMcuHost"},
    "csharp": {"BleMCuHost.gate_current": "GateCurrentRaw", "BleHost.BleMCuHost": "McuHostEntry"},
    "cpp": {"BleHost.GateCurrent": "GateCurrentAmps"},
}


def _write_overrides(tmp: Path, table) -> Path:
    path = tmp / "overrides.json"
    path.write_text(json.dumps(table), encoding="utf-8")
    return path


def test_name_overrides_per_language():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        dirs = _generate(tmp, ["--name_overrides", str(_write_overrides(tmp, OVERRIDES))])

        cpp = _read(dirs["cpp"] / "names_test.structframe.hpp")
        _check("struct BleMcuHost : " in cpp, "C++ message should use the 'all' override")
        _check("    GateCurrentAmps = 1," in cpp, "C++ enum entry should use the cpp override")
        _check("    BleMCuHost = 2," in cpp, "C++ enum entry 'BleMCuHost' is not covered by the 'all' message override")
        _check("BleMcuHost host;" in cpp, "References to a renamed message must follow the rename")

        cs_msg = _read(dirs["csharp"] / "NamesTest" / "Messages" / "BleMcuHost.cs")
        _check("public class BleMcuHost : " in cs_msg, "C# message class should be renamed")
        _check("public uint GateCurrentRaw { get; set; }" in cs_msg, "C# field property should use the csharp override")
        _check("public BleMcuHost Host { get; set; }" in _read(
            dirs["csharp"] / "NamesTest" / "Messages" / "BleHostStatus.cs"),
            "C# field typed with a renamed message should reference the new name")
        _check("McuHostEntry = 2," in _read(dirs["csharp"] / "NamesTest" / "Enums" / "BleHost.cs"),
               "C# enum entry should use the csharp override")

        ts = _read(dirs["ts"] / "names-test.structframe.ts")
        _check("export class BleMcuHost extends MessageBase" in ts, "TypeScript gets the 'all' override")
        _check("GateCurrentAmps" not in ts and "GateCurrentRaw" not in ts,
               "Language-specific overrides must not leak into other languages")

        catalog = json.loads(_read(tmp / "catalog" / "sf_compile.json"))
        host = next(m for m in catalog["messages"] if m["name"] == "BleMCuHost")
        _check(host["generated_files"]["cpp"]["element"] == "BleMcuHost", "Catalog C++ element follows overrides")
        _check(host["generated_files"]["csharp"]["qualified_element"] == "StructFrame.NamesTest.BleMcuHost",
               "Catalog C# element follows overrides")
        _check(host["generated_files"]["csharp"]["path"].endswith("Messages/BleMcuHost.cs"),
               "Catalog C# path follows overrides")


def test_name_overrides_do_not_change_wire_format():
    """Overrides rename declarations only: IDs, sizes and magic bytes are identical."""
    with tempfile.TemporaryDirectory() as plain_dir, tempfile.TemporaryDirectory() as renamed_dir:
        _generate(Path(plain_dir))
        renamed = Path(renamed_dir)
        _generate(renamed, ["--name_overrides", str(_write_overrides(renamed, OVERRIDES))])
        plain_catalog = json.loads(_read(Path(plain_dir) / "catalog" / "sf_compile.json"))
        renamed_catalog = json.loads(_read(renamed / "catalog" / "sf_compile.json"))
    keys = ("name", "msgid", "max_size", "base_size", "min_size", "magic_bytes", "is_variable")
    plain = [{k: m[k] for k in keys} for m in plain_catalog["messages"]]
    over = [{k: m[k] for k in keys} for m in renamed_catalog["messages"]]
    _check(plain == over, f"Wire-relevant catalog data changed under overrides:\n{plain}\n{over}")


def test_name_overrides_change_invalidates_cache():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        proto = tmp / "names.sf"
        proto.write_text(NAMES_SCHEMA, encoding="utf-8")
        out = tmp / "cpp"
        overrides = tmp / "overrides.json"
        flags = ["--build_cpp", "--cpp_path", str(out) + os.sep, "--catalog_path", str(tmp / "catalog") + os.sep]

        overrides.write_text(json.dumps({"cpp": {"BleMCuHost": "BleMcuHost"}}), encoding="utf-8")
        first = run_generator(proto, *flags, "--name_overrides", str(overrides), "--force")
        _check(first.returncode == 0, first.stdout + first.stderr)
        again = run_generator(proto, *flags, "--name_overrides", str(overrides))
        _check("no changes detected" in (again.stdout + again.stderr).lower(), "Unchanged overrides should hit the cache")

        overrides.write_text(json.dumps({"cpp": {"BleMCuHost": "BleMCUHost"}}), encoding="utf-8")
        changed = run_generator(proto, *flags, "--name_overrides", str(overrides))
        _check(changed.returncode == 0, changed.stdout + changed.stderr)
        _check("no changes detected" not in (changed.stdout + changed.stderr).lower(),
               "Changing the overrides must invalidate the cache")
        _check("struct BleMCUHost : " in _read(out / "names_test.structframe.hpp"),
               "Regenerated output should use the new override")


def test_name_overrides_errors():
    """Typos, unknown languages, invalid identifiers and collisions are rejected."""
    bad_tables = [
        ("do not match any declaration", {"cpp": {"NoSuchMessage": "Foo"}}),
        ("unknown language", {"cobol": {"BleMCuHost": "Foo"}}),
        ("not a valid identifier", {"cpp": {"BleMCuHost": "not valid"}}),
        ("resolve to the name", {"cpp": {"BleMCuHost": "BleHostStatus"}}),
        ("built-in schema type", {"cpp": {"BleMCuHost": "uint32"}}),
        ("reserved keyword", {"py": {"BleMCuHost": "class"}}),
        ("generated name collision", {"csharp": {"BleMCuHost.BLEHost": "GateCurrent"}}),
        ("generated name collision", {"csharp": {"BleMCuHost": "BleHost"}}),
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        proto = tmp / "names.sf"
        proto.write_text(NAMES_SCHEMA, encoding="utf-8")
        for expected, table in bad_tables:
            overrides = _write_overrides(tmp, table)
            language = next(iter(table))
            language = language if language in LANG_SUFFIXES else "cpp"
            build, path_flag = LANG_SUFFIXES[language]
            result = run_generator(proto, build, path_flag, str(tmp / language) + os.sep,
                                   "--catalog_path", str(tmp / "catalog") + os.sep,
                                   "--force", "--name_overrides", str(overrides))
            output = result.stdout + result.stderr
            _check(result.returncode == 1, f"Expected failure for {table}, got exit {result.returncode}:\n{output}")
            _check(expected in output, f"Expected {expected!r} in error output for {table}:\n{output}")


def test_name_override_preserves_exact_emitted_enum_spelling():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        table = {"cpp": {"BleHost.GateCurrent": "RUN"}}
        schema = NAMES_SCHEMA.replace(
            "BleHost mode = 4;", "BleHost mode = 4 [default = GateCurrent];")
        dirs = _generate(tmp, ["--name_overrides", str(_write_overrides(tmp, table))], schema)
        cpp = _read(dirs["cpp"] / "names_test.structframe.hpp")
        _check("    RUN = 1," in cpp, "C++ enum-entry overrides must bypass PascalCase conversion")
        _check("case BleHost::RUN:" in cpp, "generated enum references must use the exact override")
        _check("BleHost mode = BleHost::RUN;" in cpp, "enum defaults must use the exact override")


def test_generated_enum_name_collisions_are_rejected_without_overrides():
    schema = """\
package collisions;

enum State {
  FooBar = 0;
  FOO_BAR = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        proto = tmp / "collisions.sf"
        proto.write_text(schema, encoding="utf-8")
        result = run_generator(proto, "--build_py", "--py_path", str(tmp / "py") + os.sep)
    output = result.stdout + result.stderr
    _check(result.returncode == 1, f"target-language enum collision must fail:\n{output}")
    _check("collisions.State.FOO_BAR" in output and "collisions.State.FooBar" in output,
           f"collision should identify both source paths:\n{output}")


_LOOKUP_PROBE = r"""
import json
from struct_frame.naming import NameOverrideError, NameOverrides
o = NameOverrides.from_dict({"cpp": {"pkg_a.Thing": "ThingA", "Other": "OtherX"}})
result = {
    "qualified": o.lookup("cpp", "pkg_a", ("Thing",)),
    "other_pkg": o.lookup("cpp", "pkg_b", ("Thing",)),
    "plain": o.lookup("cpp", "pkg_b", ("Other",)),
    "other_lang": o.lookup("ts", "pkg_a", ("Thing",)),
}
try:
    NameOverrides.from_dict({"all": {"X": "1bad"}})
    result["invalid"] = "accepted"
except NameOverrideError:
    result["invalid"] = "rejected"
print(json.dumps(result))
"""


def test_name_overrides_package_qualified_keys():
    """A package-qualified key addresses one declaration; plain keys match every package."""
    env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
    run = subprocess.run([sys.executable, "-c", _LOOKUP_PROBE], capture_output=True, text=True, env=env)
    _check(run.returncode == 0, run.stderr)
    result = json.loads(run.stdout)
    _check(result["qualified"] == "ThingA", "qualified key should match its package")
    _check(result["other_pkg"] is None, "qualified key must not match other packages")
    _check(result["plain"] == "OtherX", "plain key matches any package")
    _check(result["other_lang"] is None, "cpp override must not apply to ts")
    _check(result["invalid"] == "rejected", "invalid identifier must be rejected")


def test_field_and_oneof_variant_may_share_a_name_except_in_csharp():
    """Variants live in the oneof's own scope in C/C++/..., but C# flattens them into the class."""
    schema = (
        "package shared_name;\n"
        "message Reading {\n"
        "  option msgid = 1;\n"
        "  uint32 value = 1;\n"
        "  oneof payload {\n"
        "    uint32 value = 1;\n"
        "    float ratio = 2;\n"
        "  }\n"
        "}\n")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proto = tmp / "shared_name.sf"
        proto.write_text(schema)
        for lang in ("c", "cpp", "py", "ts", "rust"):
            result = run_generator(proto, f"--build_{lang}", f"--{lang}_path", str(tmp / lang) + os.sep, "--force")
            _check(result.returncode == 0, f"{lang} must accept a field and variant sharing a name:\n{result.stdout}{result.stderr}")
        result = run_generator(proto, "--build_csharp", "--csharp_path", str(tmp / "cs") + os.sep, "--force")
        _check(result.returncode != 0 and "collision" in (result.stdout + result.stderr),
               f"csharp must still reject the colliding member names:\n{result.stdout}{result.stderr}")
