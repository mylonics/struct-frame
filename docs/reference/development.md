# Development

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
      generate.py           # Proto parsing and validation
      c_gen.py              # C code generator
      cpp_gen.py            # C++ code generator
      ts_gen.py             # TypeScript code generator
      py_gen.py             # Python code generator
      js_gen.py             # JavaScript code generator
      gql_gen.py            # GraphQL code generator
      csharp_gen.py         # C# code generator
      boilerplate/          # Runtime library templates
        c/
        cpp/
        ts/
        py/
        js/
        csharp/
  tests/
    run_tests.py            # Test runner entry point
    proto/                  # Test proto definitions
    c/, cpp/, py/, ts/      # Language-specific tests
  examples/                 # Example proto files
  docs/                     # Documentation
```

## Code Generation Pipeline

1. **Parsing**: Read proto file using proto-schema-parser
2. **Validation**: Check schema (unique IDs, field numbers, required options)
3. **Generation**: Language-specific generators produce output files
4. **Boilerplate**: Runtime libraries are copied to output directories

## Making Changes

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
6. Update `tests/test_config.json`

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
- C: See `.clang-format`
- Generated code should be readable and debuggable

