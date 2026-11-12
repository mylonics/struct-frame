#!/usr/bin/env python3
"""Command-line behaviour of the generator: option spellings, --lang/--out, config files,
catalog placement, usage errors and in-process use of ``struct_frame.main``.

Run with ``pytest tests/test_cli.py``.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, SRC_DIR

try:  # structframe.toml needs tomllib (3.11+) or tomli
    import tomllib  # noqa: F401
    HAVE_TOML = True
except ModuleNotFoundError:
    try:
        import tomli  # noqa: F401
        HAVE_TOML = True
    except ModuleNotFoundError:
        HAVE_TOML = False

needs_toml = pytest.mark.skipif(not HAVE_TOML, reason="no TOML parser (Python < 3.11 without tomli)")

SCHEMA ="""package hello;
message Pose {
  option msgid = 1;
  float pitch = 1;
  uint32 sample = 2;
}
"""


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "struct_frame", *args], cwd=cwd,
                          capture_output=True, text=True, env=env)


def schema(tmp: Path, name: str = "hello.sf", text: str = SCHEMA) -> Path:
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    return path


def snapshot(directory: Path) -> dict:
    return {p.relative_to(directory).as_posix(): p.read_bytes()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def test_snake_and_kebab_spellings_generate_identical_output(tmp_path):
    import shutil
    schema(tmp_path)
    old = run(tmp_path, "hello.sf", "--build_c", "--build_py", "--c_path", "o/c",
              "--py_path", "o/py", "--equality", "--catalog_path", "o")
    assert old.returncode == 0, old.stderr
    before = snapshot(tmp_path / "o")
    shutil.rmtree(tmp_path / "o")
    new = run(tmp_path, "hello.sf", "--build-c", "--build-py", "--c-path", "o/c",
              "--py-path", "o/py", "--equality", "--catalog-path", "o")
    assert new.returncode == 0, new.stderr
    assert snapshot(tmp_path / "o") == before


def test_lang_and_out_layout(tmp_path):
    schema(tmp_path)
    r = run(tmp_path, "hello.sf", "--lang", "c,python", "--lang", "ts", "--out", "build")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "build"
    assert (out / "c" / "hello.structframe.h").is_file()
    assert (out / "py" / "structframe" / "hello.py").is_file()
    assert (out / "ts" / "hello.structframe.ts").is_file()
    assert (out / "sf_compile.json").is_file()
    assert not (out / "cpp").exists()
    assert not (tmp_path / "generated").exists(), "wrote into ./generated despite --out"


def test_lang_all_and_explicit_path_wins_over_out(tmp_path):
    schema(tmp_path)
    r = run(tmp_path, "hello.sf", "--lang", "all", "--out", "build", "--c-path", "fw")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "fw" / "hello.structframe.h").is_file()
    assert not (tmp_path / "build" / "c").exists()
    for lang in ("cpp", "py", "ts", "js", "csharp", "gql", "rust"):
        assert (tmp_path / "build" / lang).is_dir(), lang


def test_catalog_follows_explicit_output_paths(tmp_path):
    """sf_compile.json used to land in ./generated/ whatever the output paths were."""
    schema(tmp_path)
    one = run(tmp_path, "hello.sf", "--build-c", "--c-path", "out/c")
    assert one.returncode == 0, one.stderr
    assert (tmp_path / "out" / "c" / "sf_compile.json").is_file()
    two = run(tmp_path, "hello.sf", "--build-c", "--c-path", "out2/c", "--build-py",
              "--py-path", "out2/py")
    assert two.returncode == 0, two.stderr
    assert (tmp_path / "out2" / "sf_compile.json").is_file()
    assert not (tmp_path / "generated").exists()


def test_default_layout_is_unchanged(tmp_path):
    schema(tmp_path)
    r = run(tmp_path, "hello.sf", "--build-c")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "generated" / "c" / "hello.structframe.h").is_file()
    assert (tmp_path / "generated" / "sf_compile.json").is_file()


@needs_toml
def test_config_file_paths_are_relative_to_the_file(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    schema(proj)
    (proj / "structframe.toml").write_text(
        'schema = "hello.sf"\nlang = ["c", "py"]\nout = "gen"\nequality = true\n',
        encoding="utf-8")
    r = run(tmp_path, "--config", "proj/structframe.toml")
    assert r.returncode == 0, r.stderr
    assert (proj / "gen" / "c" / "hello.structframe.h").is_file()
    assert "_equals" in (proj / "gen" / "c" / "hello.structframe.h").read_text(encoding="utf-8")
    assert (proj / "gen" / "py").is_dir()


@needs_toml
def test_config_is_found_in_working_directory_and_cli_overrides_it(tmp_path):
    schema(tmp_path)
    (tmp_path / "structframe.toml").write_text(
        'schema = "hello.sf"\nlang = "c"\nout = "gen"\n', encoding="utf-8")
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "gen" / "c").is_dir()

    # Command-line options win; --lang adds to the configured languages.
    r = run(tmp_path, "--out", "other", "--lang", "rust")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "other" / "c").is_dir() and (tmp_path / "other" / "rust").is_dir()


@needs_toml
def test_config_rejects_unknown_and_mistyped_keys(tmp_path):
    schema(tmp_path)
    (tmp_path / "a.toml").write_text('schema = "hello.sf"\nlangs = "c"\n', encoding="utf-8")
    r = run(tmp_path, "--config", "a.toml")
    assert r.returncode == 2
    assert "unknown key 'langs'" in r.stderr and "did you mean 'lang'" in r.stderr

    (tmp_path / "b.toml").write_text('schema = "hello.sf"\nlang = "c"\nequality = "yes"\n',
                                     encoding="utf-8")
    r = run(tmp_path, "--config", "b.toml")
    assert r.returncode == 2 and "'equality' must be true or false" in r.stderr


def test_usage_errors_exit_2_on_stderr(tmp_path):
    schema(tmp_path)
    for args, needle in ((["hello.sf"], "no language selected"),
                         ([], "no schema given"),
                         (["hello.sf", "--lang", "cobol"], "unknown language 'cobol'")):
        r = run(tmp_path, *args)
        assert r.returncode == 2, (args, r.returncode, r.stdout, r.stderr)
        assert needle in r.stderr, (args, r.stderr)
        assert r.stdout == "", (args, r.stdout)


def test_version_matches_pyproject(tmp_path):
    r = run(tmp_path, "--version")
    assert r.returncode == 0
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    import re
    version = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)
    assert r.stdout.strip() == f"struct-frame {version}"


def test_quiet_prints_nothing_on_success(tmp_path):
    schema(tmp_path)
    r = run(tmp_path, "hello.sf", "--lang", "c", "--out", "o", "-q")
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""


def test_main_can_run_twice_in_one_process(tmp_path):
    """Parse state used to persist between calls, leaking the first schema into the second."""
    schema(tmp_path, "a.sf", "package alpha;\nmessage A { option msgid = 1; uint8 x = 1; }\n")
    schema(tmp_path, "b.sf", "package beta;\nmessage B { option msgid = 1; uint8 y = 1; }\n")
    code = (
        "from struct_frame import main\n"
        "assert main(['a.sf', '--lang', 'c', '--out', 'oa', '-q']) == 0\n"
        "assert main(['b.sf', '--lang', 'c', '--out', 'ob', '-q']) == 0\n"
        "assert main(['b.sf', '--lang', 'c', '--out', 'ob', '-q']) == 0  # cache skip\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True,
                       text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (tmp_path / "ob" / "c" / "alpha.structframe.h").exists()
    assert (tmp_path / "ob" / "c" / "beta.structframe.h").is_file()


def test_python_output_is_one_package_that_can_be_nested(tmp_path):
    """Python output is PY_PATH/<py-package>/ (runtime + modules, relative imports), so it can
    live inside the user's own package; it used to be struct_frame/generated, which collided
    with the generator's own package."""
    schema(tmp_path)
    app = tmp_path / "app"
    app.mkdir()
    (app / "__init__.py").write_text("", encoding="utf-8")
    r = run(tmp_path, "hello.sf", "--lang", "py", "--py-path", "app", "--py-package", "msgs", "--sdk")
    assert r.returncode == 0, r.stderr
    assert (app / "msgs" / "frame_profiles.py").is_file()
    assert (app / "msgs" / "struct_frame_sdk" / "__init__.py").is_file()
    code = ("from app.msgs import frame_profiles as fp, hello\n"
            "from app.msgs.struct_frame_sdk import StructFrameSdk\n"
            "import app.msgs as m\n"
            "w = fp.BufferWriter(fp.PROFILE_STANDARD_CONFIG, 64)\n"
            "w.write(hello.Pose(pitch=1.0, sample=7))\n"
            "r = m.AccumulatingReader(fp.PROFILE_STANDARD_CONFIG, get_message_info=hello.get_message_info)\n"
            "r.add_data(w.data())\n"
            "print(hello.decode_message(r.try_next()).sample)\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)  # not the generator's src
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True,
                         text=True, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "7"


def test_python_package_names_that_cannot_work_are_rejected(tmp_path):
    schema(tmp_path)
    r = run(tmp_path, "hello.sf", "--lang", "py", "--py-package", "struct_frame")
    assert r.returncode == 1 and "shadow the struct-frame generator" in r.stderr
    r = run(tmp_path, "hello.sf", "--lang", "py", "--py-package", "not-valid")
    assert r.returncode == 1 and "not a valid Python identifier" in r.stderr
    schema(tmp_path, "frame_profiles.sf",
           "package frame_profiles;\nmessage M { option msgid = 1; uint8 x = 1; }\n")
    r = run(tmp_path, "frame_profiles.sf", "--lang", "py")
    assert r.returncode == 1 and "same name as a module of the Python runtime" in r.stderr
    # Other languages are unaffected by the Python-only restriction.
    assert run(tmp_path, "frame_profiles.sf", "--lang", "c").returncode == 0


STRINGS_SF = """package strs;
message S {
  option msgid = 1;
  option variable = true;
  string fixed = 1 [size=8];
  string var = 2 [max_size=12];
  repeated string fixed_arr = 3 [size=2, element_size=6];
  repeated string var_arr = 4 [max_size=3, element_size=6];
}
message F {
  option msgid = 2;
  string fixed = 1 [size=8];
  string var = 2 [max_size=12];
  repeated string arr = 3 [max_size=2, element_size=4];
}
"""

STRINGS_PY = r"""
from structframe import frame_profiles as fp
from structframe.strs import S, F
for cls in (S, F):
    kw_str = dict(fixed="héllo", var="naïve ✓")
    kw_bytes = dict(fixed="héllo".encode(), var="naïve ✓".encode())
    if cls is S:
        kw_str.update(fixed_arr=["a", "é"], var_arr=["x", "ÿy"])
        kw_bytes.update(fixed_arr=[b"a", "é".encode()], var_arr=[b"x", "ÿy".encode()])
    else:
        kw_str.update(arr=["ab", "ç"])
        kw_bytes.update(arr=[b"ab", "ç".encode()])
    a, b = cls(**kw_str), cls(**kw_bytes)
    assert a.serialize() == b.serialize(), cls.__name__
    assert isinstance(a.var, bytes) and a.var == "naïve ✓".encode()
    # str assigned after construction is encoded too, and sized by its UTF-8 bytes.
    c = cls(**kw_bytes)
    c.var = "naïve ✓"
    assert c.serialize() == b.serialize(), cls.__name__ + " (assigned)"
    for cfg in (fp.PROFILE_STANDARD_CONFIG, fp.PROFILE_SENSOR_CONFIG):
        assert fp.encode_message(cfg, a) == fp.encode_message(cfg, b)
    back = cls.deserialize(a.serialize())
    assert back.var.rstrip(b"\x00").decode() == "naïve ✓"
print("ok")
"""


def test_python_string_fields_accept_str(tmp_path):
    """Python string fields used to require bytes (a str raised struct.error)."""
    schema(tmp_path, "strs.sf", STRINGS_SF)
    r = run(tmp_path, "strs.sf", "--lang", "py", "--out", "o")
    assert r.returncode == 0, r.stderr
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "o" / "py")
    out = subprocess.run([sys.executable, "-c", STRINGS_PY], capture_output=True, text=True,
                         env=env, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"
