#!/usr/bin/env python3
"""
Tests for the ``--equality`` CLI flag.

The flag should cause generated code for all supported languages to include
equality-comparison functions/operators for every message type.  This test
verifies:

1. **Python** – generated ``__eq__`` / ``__ne__`` methods return the correct
   result when comparing equal and unequal message instances.
2. **C** – generated ``*_equals()`` inline functions compile and return the
   correct result.
3. **C++** – generated ``operator==`` methods compile and return the correct
   result.
4. **TypeScript** – generated ``equals()`` method works correctly at runtime.
5. **JavaScript** – generated ``equals()`` method works correctly at runtime.
6. **C#** – generated ``Equals()`` / ``==`` operator works correctly.
7. **Rust** – ``PartialEq`` derive (added when ``--equality`` is used) works correctly.

Usage:
    python tests/test_equality.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from test_utils import _check
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
PROTO_FILE = REPO_ROOT / "tests" / "proto" / "test_messages.sf"


def _run_generator(out_dir: Path, *extra_args: str) -> None:
    cmd = [
        sys.executable,
        str(SRC_DIR / "main.py"),
        str(PROTO_FILE),
        "--build_c",
        "--c_path", str(out_dir / "c") + os.sep,
        "--build_cpp",
        "--cpp_path", str(out_dir / "cpp") + os.sep,
        "--build_py",
        "--py_path", str(out_dir / "py") + os.sep,
        "--build_ts",
        "--ts_path", str(out_dir / "ts") + os.sep,
        "--build_js",
        "--js_path", str(out_dir / "js") + os.sep,
        "--build_csharp",
        "--csharp_path", str(out_dir / "csharp") + os.sep,
        "--build_rust",
        "--rust_path", str(out_dir / "rust") + os.sep,
        "--equality",
        "--force",
    ] + list(extra_args)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(cmd, env=env)




# ---------------------------------------------------------------------------
# Python equality tests
# ---------------------------------------------------------------------------

def test_python_equality(gen_dir: Path) -> None:
    """Generated Python __eq__ / __ne__ work correctly."""
    py_root = gen_dir / "py"
    sys.path.insert(0, str(py_root))
    try:
        from struct_frame.generated.serialization_test import BasicTypesMessage  # type: ignore
    except ImportError as exc:
        _check(False, f"failed to import generated Python module: {exc}")
        return
    finally:
        sys.path.pop(0)

    a = BasicTypesMessage()
    a.small_int = 42
    a.medium_int = 1000
    a.regular_int = 9876
    a.large_int = -123456789
    a.small_uint = 200
    a.medium_uint = 50000
    a.regular_uint = 300000
    a.large_uint = 999999999
    a.single_precision = 3.14
    a.double_precision = 2.71828
    a.flag = True

    b = BasicTypesMessage()
    b.small_int = 42
    b.medium_int = 1000
    b.regular_int = 9876
    b.large_int = -123456789
    b.small_uint = 200
    b.medium_uint = 50000
    b.regular_uint = 300000
    b.large_uint = 999999999
    b.single_precision = 3.14
    b.double_precision = 2.71828
    b.flag = True

    c = BasicTypesMessage()
    c.small_int = 99  # differs from a
    c.medium_int = 1000
    c.regular_int = 9876
    c.large_int = -123456789
    c.small_uint = 200
    c.medium_uint = 50000
    c.regular_uint = 300000
    c.large_uint = 999999999
    c.single_precision = 3.14
    c.double_precision = 2.71828
    c.flag = True

    _check(a == b, "equal messages should compare as equal")
    _check(not (a == c), "messages with differing fields should not be equal")
    _check(a != c, "__ne__ should return True for unequal messages")
    _check(not (a != b), "__ne__ should return False for equal messages")


# ---------------------------------------------------------------------------
# C equality tests
# ---------------------------------------------------------------------------

def test_c_equality(gen_dir: Path) -> None:
    """Generated C *_equals() functions compile and work correctly."""
    if not shutil.which("gcc"):
        print("SKIP: gcc not available")
        return

    c_dir = gen_dir / "c"
    src = c_dir / "_equality_test.c"
    src.write_text(
        '#include <stdio.h>\n'
        '#include "serialization_test.structframe.h"\n'
        "int main(void) {\n"
        "    SerializationTestBasicTypesMessage a = {0}, b = {0}, c = {0};\n"
        "    a.small_int = 42; a.medium_int = 1000;\n"
        "    b.small_int = 42; b.medium_int = 1000;\n"
        "    c.small_int = 99; c.medium_int = 1000;\n"
        "    if (!SerializationTestBasicTypesMessage_equals(&a, &b)) return 1;\n"
        "    if (SerializationTestBasicTypesMessage_equals(&a, &c)) return 2;\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    out = c_dir / "_equality_test.out"
    try:
        subprocess.check_call(
            ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
        )
        subprocess.check_call([str(out)])
    except subprocess.CalledProcessError as exc:
        _check(False, f"C equality test failed: {exc}")


# ---------------------------------------------------------------------------
# C++ equality tests
# ---------------------------------------------------------------------------

def test_cpp_equality(gen_dir: Path) -> None:
    """Generated C++ operator== compiles and works correctly."""
    if not shutil.which("g++"):
        print("SKIP: g++ not available")
        return

    cpp_dir = gen_dir / "cpp"
    src = cpp_dir / "_equality_test.cpp"
    src.write_text(
        '#include "serialization_test.structframe.hpp"\n'
        "using structframe::serialization_test::BasicTypesMessage;\n"
        "int main() {\n"
        "    BasicTypesMessage a{}, b{}, c{};\n"
        "    a.small_int = 42; a.medium_int = 1000;\n"
        "    b.small_int = 42; b.medium_int = 1000;\n"
        "    c.small_int = 99; c.medium_int = 1000;\n"
        "    if (!(a == b)) return 1;\n"
        "    if (a == c) return 2;\n"
        "    if (a != b) return 3;\n"
        "    if (!(a != c)) return 4;\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    out = cpp_dir / "_equality_test.out"
    try:
        subprocess.check_call(
            ["g++", "-std=c++20", "-I", str(cpp_dir), str(src), "-o", str(out)],
        )
        subprocess.check_call([str(out)])
    except subprocess.CalledProcessError as exc:
        _check(False, f"C++ equality test failed: {exc}")


# ---------------------------------------------------------------------------
# TypeScript equality tests
# ---------------------------------------------------------------------------

def test_ts_equality(gen_dir: Path) -> None:
    """Generated TypeScript equals() method works correctly."""
    tsc = shutil.which("tsc")
    if not tsc or not shutil.which("node"):
        print("SKIP: tsc or node not available")
        return

    ts_dir = gen_dir / "ts"
    # Find the existing node_modules with @types/node (installed in tests/ts)
    repo_ts_dir = Path(__file__).parent / "ts"
    node_modules = repo_ts_dir / "node_modules"
    # Write a minimal tsconfig so tsc can compile standalone
    tsconfig = ts_dir / "tsconfig.json"
    type_roots = f'"typeRoots":["{(node_modules / "@types").as_posix()}"],' if node_modules.exists() else ''
    types = '"types":["node"],' if node_modules.exists() else ''
    tsconfig.write_text(
        '{"compilerOptions":{"target":"ES2020","module":"commonjs",'
        '"outDir":"./build","strict":false,"skipLibCheck":true,'
        f'{type_roots}{types}'
        '"lib":["ES2020"]},"include":["*.ts"]}',
        encoding="utf-8",
    )
    # Determine field names: TS generator uses camelCase
    test_src = ts_dir / "_equality_test.ts"
    test_src.write_text(
        "import { BasicTypesMessage } from './serialization-test.structframe';\n"
        "const a = new BasicTypesMessage();\n"
        "a.smallInt = 42; a.mediumInt = 1000;\n"
        "const b = new BasicTypesMessage();\n"
        "b.smallInt = 42; b.mediumInt = 1000;\n"
        "const c = new BasicTypesMessage();\n"
        "c.smallInt = 99; c.mediumInt = 1000;\n"
        "if (!a.equals(b)) { throw new Error('FAIL: equal messages should compare as equal'); }\n"
        "if (a.equals(c)) { throw new Error('FAIL: unequal messages should not compare as equal'); }\n",
        encoding="utf-8",
    )
    try:
        compile_result = subprocess.run(
            [tsc, "--project", str(tsconfig)],
            capture_output=True, text=True, cwd=str(ts_dir),
        )
        if compile_result.returncode != 0:
            # Treat deprecation warnings as non-fatal
            lines = (compile_result.stdout + compile_result.stderr).splitlines()
            errors = [l for l in lines if "error TS" in l and "deprecated" not in l.lower()]
            if errors:
                _check(False, f"TypeScript compile errors:\n" + "\n".join(errors))
        run_result = subprocess.run(
            ["node", str(ts_dir / "build" / "_equality_test.js")],
            capture_output=True, text=True,
        )
        _check(run_result.returncode == 0,
               f"TypeScript equality test failed (exit {run_result.returncode}):\n"
               f"{run_result.stdout}{run_result.stderr}")
    finally:
        test_src.unlink(missing_ok=True)
        tsconfig.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# JavaScript equality tests
# ---------------------------------------------------------------------------

def test_js_equality(gen_dir: Path) -> None:
    """Generated JavaScript equals() method works correctly."""
    if not shutil.which("node"):
        print("SKIP: node not available")
        return

    js_dir = gen_dir / "js"
    test_js = js_dir / "_equality_test.js"
    test_js.write_text(
        '"use strict";\n'
        'const { BasicTypesMessage } = require("./serialization-test.structframe.js");\n'
        "const a = new BasicTypesMessage();\n"
        "a.smallInt = 42; a.mediumInt = 1000;\n"
        "const b = new BasicTypesMessage();\n"
        "b.smallInt = 42; b.mediumInt = 1000;\n"
        "const c = new BasicTypesMessage();\n"
        "c.smallInt = 99; c.mediumInt = 1000;\n"
        "if (!a.equals(b)) { console.error('FAIL: equal messages should compare as equal'); process.exit(1); }\n"
        "if (a.equals(c)) { console.error('FAIL: unequal messages should not compare as equal'); process.exit(2); }\n"
        "process.exit(0);\n",
        encoding="utf-8",
    )
    try:
        subprocess.check_call(["node", str(test_js)], cwd=str(js_dir))
    except subprocess.CalledProcessError as exc:
        _check(False, f"JavaScript equality test failed: {exc}")


# ---------------------------------------------------------------------------
# C# equality tests
# ---------------------------------------------------------------------------

def test_csharp_equality(gen_dir: Path) -> None:
    """Generated C# Equals() / == operator compiles and works correctly."""
    if not shutil.which("dotnet"):
        print("SKIP: dotnet not available")
        return

    cs_dir = gen_dir / "csharp"
    test_dir = gen_dir / "_cs_eq_test"
    test_dir.mkdir(exist_ok=True)
    (test_dir / "Program.cs").write_text(
        "using System;\n"
        "using StructFrame.SerializationTest;\n"
        "var a = new BasicTypesMessage { SmallInt = 42, MediumInt = 1000 };\n"
        "var b = new BasicTypesMessage { SmallInt = 42, MediumInt = 1000 };\n"
        "var c = new BasicTypesMessage { SmallInt = 99, MediumInt = 1000 };\n"
        "if (!a.Equals(b)) { Console.Error.WriteLine(\"FAIL: equal messages should be equal\"); return 1; }\n"
        "if (a.Equals(c)) { Console.Error.WriteLine(\"FAIL: unequal messages should not be equal\"); return 2; }\n"
        "if (!(a == b)) { Console.Error.WriteLine(\"FAIL: == should return true for equal messages\"); return 3; }\n"
        "if (a == c) { Console.Error.WriteLine(\"FAIL: == should return false for unequal messages\"); return 4; }\n"
        "return 0;\n",
        encoding="utf-8",
    )
    (test_dir / "EqualityTest.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        "  <PropertyGroup>\n"
        "    <OutputType>Exe</OutputType>\n"
        "    <TargetFramework>net8.0</TargetFramework>\n"
        "    <Nullable>disable</Nullable>\n"
        "    <ImplicitUsings>disable</ImplicitUsings>\n"
        "  </PropertyGroup>\n"
        "  <ItemGroup>\n"
        f'    <ProjectReference Include="{cs_dir / "StructFrame.csproj"}" />\n'
        "  </ItemGroup>\n"
        "</Project>\n",
        encoding="utf-8",
    )
    try:
        build_result = subprocess.run(
            ["dotnet", "build", str(test_dir / "EqualityTest.csproj"),
             "-c", "Release", "--verbosity", "quiet"],
            capture_output=True, text=True,
        )
        _check(build_result.returncode == 0,
               f"C# equality test build failed:\n{build_result.stdout}\n{build_result.stderr}")
        run_result = subprocess.run(
            ["dotnet", "run", "--project", str(test_dir / "EqualityTest.csproj"),
             "--no-build", "-c", "Release"],
            capture_output=True, text=True,
        )
        _check(run_result.returncode == 0,
               f"C# equality test failed (exit {run_result.returncode}):\n"
               f"{run_result.stdout}{run_result.stderr}")
    except subprocess.CalledProcessError as exc:
        _check(False, f"C# equality test error: {exc}")


# ---------------------------------------------------------------------------
# Rust equality tests
# ---------------------------------------------------------------------------

def test_rust_equality(gen_dir: Path) -> None:
    """Rust PartialEq derive (added when --equality is used) works correctly."""
    if not shutil.which("cargo"):
        print("SKIP: cargo not available")
        return

    rust_lib_dir = gen_dir / "rust"
    # Create a small Cargo binary project that depends on the generated library
    test_proj = gen_dir / "_rust_eq_test"
    test_proj.mkdir(exist_ok=True)
    (test_proj / "Cargo.toml").write_text(
        "[package]\n"
        'name = "eq_test"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n'
        "\n[dependencies]\n"
        f'struct_frame_sdk = {{ path = "{rust_lib_dir.as_posix()}" }}\n',
        encoding="utf-8",
    )
    src_dir = test_proj / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.rs").write_text(
        "use struct_frame_sdk::serialization_test::BasicTypesMessage;\n"
        "fn main() {\n"
        "    let mut a = BasicTypesMessage::default();\n"
        "    a.small_int = 42; a.medium_int = 1000;\n"
        "    let mut b = BasicTypesMessage::default();\n"
        "    b.small_int = 42; b.medium_int = 1000;\n"
        "    let mut c = BasicTypesMessage::default();\n"
        "    c.small_int = 99; c.medium_int = 1000;\n"
        '    assert!(a == b, "equal messages should compare as equal");\n'
        '    assert!(a != c, "unequal messages should not be equal");\n'
        "}\n",
        encoding="utf-8",
    )
    run_result = subprocess.run(
        ["cargo", "run", "--quiet"],
        capture_output=True, text=True, cwd=str(test_proj),
    )
    _check(run_result.returncode == 0,
           f"Rust equality test failed:\n{run_result.stdout}\n{run_result.stderr}")


def test_equality_flag():
    with tempfile.TemporaryDirectory() as tmp:
        gen_dir = Path(tmp)
        _run_generator(gen_dir)

        # 1. Verify equality functions / operators are present in generated code
        c_header = (gen_dir / "c" / "serialization_test.structframe.h").read_text(encoding="utf-8")
        _check("_equals(" in c_header,
               "C header should contain *_equals() functions")

        cpp_header = (gen_dir / "cpp" / "serialization_test.structframe.hpp").read_text(encoding="utf-8")
        _check("operator==" in cpp_header,
               "C++ header should contain operator== methods")

        py_files = list((gen_dir / "py").rglob("*.py"))
        _check(any("def __eq__" in f.read_text(encoding="utf-8") for f in py_files),
               "Generated Python files should contain __eq__ methods")

        ts_src = (gen_dir / "ts" / "serialization-test.structframe.ts").read_text(encoding="utf-8")
        _check("equals(" in ts_src,
               "Generated TypeScript file should contain equals() method")

        js_src = (gen_dir / "js" / "serialization-test.structframe.js").read_text(encoding="utf-8")
        _check("equals(" in js_src,
               "Generated JavaScript file should contain equals() method")

        cs_files = list((gen_dir / "csharp").rglob("*.cs"))
        _check(any("Equals(" in f.read_text(encoding="utf-8", errors="replace") for f in cs_files),
               "Generated C# files should contain Equals() method")

        rust_src = (gen_dir / "rust" / "serialization_test.structframe.rs").read_text(encoding="utf-8")
        _check("PartialEq" in rust_src,
               "Generated Rust file should derive PartialEq")

        # 2. Functional tests
        test_python_equality(gen_dir)
        test_c_equality(gen_dir)
        test_cpp_equality(gen_dir)
        test_ts_equality(gen_dir)
        test_js_equality(gen_dir)
        test_csharp_equality(gen_dir)
        test_rust_equality(gen_dir)

    print("PASS: --equality flag tests")


if __name__ == "__main__":
    test_equality_flag()
