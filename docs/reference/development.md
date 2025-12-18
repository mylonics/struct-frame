# Development Guide

## Setting Up Development Environment

To contribute to struct-frame or modify the code generator itself, you'll need to clone the repository and set up a development environment.

### Clone the Repository

```bash
git clone https://github.com/mylonics/struct-frame.git
cd struct-frame
```

### Install Dependencies

```bash
# Install Python dependencies
pip install proto-schema-parser

# Install Node.js dependencies (for TypeScript tests)
npm install
```

### Running from Source

When developing, you can run the code generator directly from source:

```bash
# Using PYTHONPATH
PYTHONPATH=src python src/main.py examples/test.proto --build_py

# Or install in editable mode
pip install -e .
python -m struct_frame examples/test.proto --build_py
```

## Project Structure

```
struct-frame/
  src/
    main.py                 # CLI entry point
    struct_frame/
      __init__.py
      __main__.py           # Module entry point
      base.py               # Base classes
      generate.py           # Proto parsing and validation
      c_gen.py              # C code generator
      cpp_gen.py            # C++ code generator
      ts_gen.py             # TypeScript code generator
      py_gen.py             # Python code generator
      gql_gen.py            # GraphQL code generator
      js_gen.py             # JavaScript code generator
      boilerplate/          # Runtime library templates
        c/
        cpp/
        ts/
        py/
  examples/
    generic_robot.proto     # Example proto file
    array_test.proto        # Array feature tests
    main.c                  # C usage example
    index.ts                # TypeScript usage example
  tests/
    run_tests.py            # Test runner entry point
    test_config.json        # Test configuration
    expected_values.json    # Expected test values
    runner/                 # Test runner modules
    proto/                  # Test proto definitions
    c/                      # C tests
    cpp/                    # C++ tests
    py/                     # Python tests
    ts/                     # TypeScript tests
  generated/                # Output directory (gitignored)
```

## Code Generation Pipeline

1. **Parsing**: `generate.py` reads the proto file using proto-schema-parser
2. **Validation**: Schema is validated (unique IDs, field numbers, required options)
3. **Generation**: Language-specific generators produce output files
4. **Boilerplate**: Runtime libraries are copied to output directories

## Adding a New Target Language

1. Create `<lang>_gen.py` in `src/struct_frame/`
2. Implement the generator class extending base classes
3. Add boilerplate files to `src/struct_frame/boilerplate/<lang>/`
4. Add CLI flag in `src/main.py`
5. Add tests in `tests/<lang>/`
6. Update test_config.json with language settings

Generator must implement:
- Type mapping from proto types to target language types
- Message struct/class generation
- Enum generation
- Array handling (fixed and bounded)
- String handling
- Serialization/deserialization code

## Making Changes

### Modifying Frame Format

Frame encoding/decoding is in boilerplate files:
- `boilerplate/c/struct_frame_parser.h`
- `boilerplate/cpp/struct_frame.hpp`
- `boilerplate/ts/struct_frame_parser.ts`
- `boilerplate/py/struct_frame_parser.py`

To add a new frame format:
1. Add encoding/decoding functions to boilerplate
2. Update parser state machine if needed
3. Add tests for the new format

### Modifying Proto Parser

The `generate.py` file handles proto parsing and validation. Key functions:
- `parse_proto()`: Reads and parses proto file
- `validate_schema()`: Checks for errors
- `process_messages()`: Prepares data for generators

## Building for Release

### Python Package

```bash
# Update version in pyproject.toml
pip install --upgrade build twine
python -m build
python -m twine upload dist/*
```

### Running Locally

```bash
pip install proto-schema-parser
PYTHONPATH=src python src/main.py examples/generic_robot.proto --build_c --build_py
```

## Common Development Tasks

### Regenerate All Examples

```bash
PYTHONPATH=src python src/main.py examples/generic_robot.proto \
    --build_c --build_cpp --build_ts --build_py --build_gql
```

### Run Quick Validation

```bash
# Generate and check for errors
PYTHONPATH=src python src/main.py examples/array_test.proto --build_py
# Import generated code
python -c "import sys; sys.path.insert(0, 'generated/py'); import array_test_sf"
```

## Code Style

- Python: Follow existing style in codebase
- C: See .clang-format
- Generated code should be readable and debuggable

## Error Handling

Generators should:
- Validate input before generating
- Provide clear error messages with file/line info
- Fail early on invalid input rather than generating broken code
