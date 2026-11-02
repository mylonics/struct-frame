---
title: Development
description: Development setup, contributing guidelines, and project structure.
---

## Setting Up Development Environment

Clone the repository and install dependencies:

```bash
git clone https://github.com/mylonics/struct-frame.git
cd struct-frame

# Install Python dependencies
pip install proto-schema-parser

# Install Node.js dependencies (for TypeScript tests)
npm install
```

## Running from Source

```bash
# Using PYTHONPATH
PYTHONPATH=src python src/main.py examples/basic/hello.sf --build_py

# Or install in editable mode
pip install -e .
python -m struct_frame examples/basic/hello.sf --build_py
```

:::caution
If `struct-frame` is also installed from PyPI, `python -m struct_frame` runs *that* copy, not your checkout, unless it is installed in editable mode (`pip install -e .`) or `PYTHONPATH=src` is set. Check with `python -c "import struct_frame; print(struct_frame.__file__)"`. The dependency `proto-schema-parser` must be 2.0.0 or newer (older versions mis-attribute trailing comments).
:::

## Project Structure

```
struct-frame/
  src/
    main.py                 # CLI entry point
    struct_frame/
      generate.py           # Proto parsing and validation
      c_gen.py              # C code generator
      cpp_gen.py            # C++ code generator
      ts_gen.py             # TypeScript code generator
      py_gen.py             # Python code generator
      js_gen.py             # JavaScript code generator
      gql_gen.py            # GraphQL code generator
      csharp_gen.py         # C# code generator
      rust_gen.py           # Rust code generator
      naming.py             # Generated-name rules, reserved words, --name_overrides
      schema_diff.py        # `struct_frame diff` wire-compatibility check
      boilerplate/          # Runtime library templates
        c/
        cpp/
        ts/
        py/
        js/                 # compiled from ts/ (do not hand-edit; see below)
        csharp/
        rust/
  tests/
    run_tests.py            # Cross-language test runner (see `python test_all.py`)
    proto/                  # Test schemas (.sf)
    c/, cpp/, py/, ts/, js/, csharp/, rust/   # Language-specific tests
    test_*.py               # pytest suites for the generator itself
  examples/                 # Example schemas and tested programs
  wireshark/                # Lua dissector (see wireshark/README.md)
  docs/                     # Documentation site sources
```

## Code Generation Pipeline

1. **Parsing**: Read proto file using proto-schema-parser
2. **Validation**: Check schema (unique IDs, field numbers, required options)
3. **Generation**: Language-specific generators produce output files
4. **Boilerplate**: Runtime libraries are copied to output directories

## Making Changes

### Editing the JavaScript runtime

`boilerplate/js/` is compiled from `boilerplate/ts/`. Edit the TypeScript and rebuild; never edit the JavaScript by hand:

```bash
npm ci
./node_modules/.bin/tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json
```

(A type error about the optional `serialport` module is benign; the output is still emitted.) `tests/test_generator_regressions.py` fails if the compiled SDK lacks members the TypeScript SDK has.

### Modifying Generators

Each language has a generator in `src/struct_frame/<lang>_gen.py`. Generators must implement:

- Type mapping from proto types to target language types
- Message struct/class generation
- Enum generation
- Array handling (fixed and bounded)
- String handling
- Serialization/deserialization code

### Adding a New Target Language

1. Create `<lang>_gen.py` in `src/struct_frame/`
2. Implement the generator class
3. Add boilerplate files to `src/struct_frame/boilerplate/<lang>/`
4. Add CLI flag in `src/main.py`
5. Add tests in `tests/<lang>/`
6. Register the language in `tests/run_tests.py` (`_init_languages`) and add it to the CI lanes in `.github/workflows/test.yml`

## Building for Release

```bash
# Update version in pyproject.toml
pip install --upgrade build twine
python -m build
python -m twine upload dist/*
```

## Common Development Tasks

### Regenerate All Examples

```bash
PYTHONPATH=src python src/main.py examples/generic_robot.sf \
    --build_c --build_cpp --build_ts --build_py --build_gql
```

### Run Quick Validation

```bash
# Generate and check for errors
PYTHONPATH=src python src/main.py examples/array_test.sf --build_py --py_path generated/py

# Import generated code
python -c "import sys; sys.path.insert(0, 'generated/py'); from struct_frame.generated.array_test import get_message_info"
```

## Running the Tests

```bash
python test_all.py                       # every language available on this machine
python test_all.py --require-langs c,cpp,py,ts,js,csharp,rust   # fail instead of skipping a missing toolchain
python -m pytest tests                   # generator-level pytest suites only
```

New schema-validation behaviour should get a test in `tests/test_generator_regressions.py` (or `tests/test_generator_validation.py`); documentation samples that compile belong in `examples/` so `tests/test_examples.py` builds and runs them.

## Code Style

- Python: Follow existing style in codebase
- C: See `.clang-format`
- Generated code should be readable and debuggable

