# struct-frame Repository

struct-frame is a multi-language code generation framework that converts Protocol Buffer (.proto) files into serialization/deserialization code for C, C++, TypeScript, Python, JavaScript, GraphQL, and C#. It provides framing and parsing utilities for structured message communication.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Prerequisites and Dependencies

- Install Python dependencies:
  - `pip install proto-schema-parser`
- Install Node.js dependencies (for TypeScript):
  - `npm install`
- For C tests: GCC compiler
- For C++ tests: G++ compiler with C++14 support
- For TypeScript tests: Node.js + `cd tests/ts && npm install`

### Core Build Commands

- **NEVER CANCEL**: All commands below complete quickly
- Generate code for all languages:
  - `PYTHONPATH=src python3 src/main.py [proto_file] --build_c --build_cpp --build_ts --build_py --build_gql`
- Run the full test suite:
  - `python test_all.py` or `python tests/run_tests.py`
- Python module works via:
  - `PYTHONPATH=src python3 -c "import struct_frame; struct_frame.main()"`

### Known Working Components

- **Code Generator**: FULLY FUNCTIONAL for C, C++, Python, TypeScript, JavaScript, GraphQL, C#
  - Reads .proto files and generates code for all target languages
  - CLI interface works correctly
  - Code generation completes successfully
- **Test Suite**: COMPREHENSIVE
  - Located in `tests/` directory with modular runner architecture
  - Validates code generation, compilation, and serialization across all languages
  - Includes cross-platform compatibility matrix tests

### Running Tests and Validation

- **Use the test suite** for validation:
  ```bash
  python test_all.py                           # Run all tests
  python tests/run_tests.py --verbose          # Verbose output
  python tests/run_tests.py --skip-lang ts     # Skip TypeScript tests
  python tests/run_tests.py --only-generate    # Only generate code
  python tests/run_tests.py --check-tools      # Check tool availability
  python tests/run_tests.py --clean            # Clean generated files
  ```
- Test proto files are in `tests/proto/` (test_messages.proto)
- Generated test code goes to `tests/generated/`

### Build Times and Timeouts

- Code generation: ~0.1 seconds - NEVER CANCEL
- npm install: ~1 second - NEVER CANCEL
- TypeScript compilation: ~2 seconds - NEVER CANCEL
- Full test suite: Varies by available compilers
- All operations are very fast, no long builds

## Validation Scenarios

- **Run the test suite** after making changes to generators
- **Use test proto files** in `tests/proto/` for validation
- **Check test output** for cross-platform compatibility matrix
- Example proto files in `examples/` are for demonstration (array_test.proto, frame_formats.proto, generic_robot.proto)

## Repository Structure

```
/
├── src/                      # Source code directory
│   ├── main.py              # CLI entry point
│   └── struct_frame/        # Code generators
│       ├── generate.py      # Main generation logic
│       ├── c_gen.py         # C code generator
│       ├── cpp_gen.py       # C++ code generator
│       ├── ts_gen.py        # TypeScript code generator
│       ├── js_gen.py        # JavaScript code generator
│       ├── py_gen.py        # Python code generator
│       ├── gql_gen.py       # GraphQL code generator
│       ├── csharp_gen.py    # C# code generator
│       ├── frame_parser_*   # Frame parser generators per language
│       └── boilerplate/     # Template files for each language
├── tests/                   # Comprehensive test suite
│   ├── run_tests.py         # Main test runner entry point
│   ├── test_config.json     # Test configuration
│   ├── expected_values.json # Expected values for cross-platform tests
│   ├── runner/              # Modular test runner components
│   │   ├── base.py          # Base utilities
│   │   ├── tool_checker.py  # Tool availability checking
│   │   ├── code_generator.py# Code generation from proto files
│   │   ├── compiler.py      # Compilation for C, C++, TypeScript
│   │   ├── test_executor.py # Test execution
│   │   ├── output_formatter.py # Result formatting
│   │   ├── runner.py        # Main ConfigDrivenTestRunner
│   │   └── plugins.py       # Test plugins (Standard, CrossPlatformMatrix)
│   ├── proto/               # Test proto definitions
│   │   └── test_messages.proto
│   ├── c/                   # C test files + build/
│   ├── cpp/                 # C++ test files + build/
│   ├── py/                  # Python test files
│   ├── ts/                  # TypeScript test files + package.json
│   ├── csharp/              # C# test files + project
│   ├── js/                  # JavaScript test files
│   └── generated/           # Generated code output (c/, cpp/, py/, ts/, gql/)
├── examples/                # Example proto files
│   ├── array_test.proto
│   ├── frame_formats.proto
│   ├── generic_robot.proto
│   ├── index.ts             # TypeScript example
│   └── main.c               # C example
├── docs/                    # Documentation
│   ├── installation.md
│   ├── development.md
│   ├── testing.md
│   ├── framing.md
│   └── message-definitions.md
├── gen/                     # Generated code output directory
├── test_all.py              # Test suite wrapper script
├── pyproject.toml           # Python package configuration
└── package.json             # Node.js dependencies
```

## Quick Start for New Developers

1. Install dependencies: `pip install proto-schema-parser && npm install`
2. Run the test suite: `python test_all.py`
3. Generate code: `PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_py --py_path gen/py`
4. For development: Run tests after changes to validate generators

## Test Suite Architecture

The test runner uses a modular, plugin-based architecture:

- **ToolChecker**: Verifies compilers/interpreters are available
- **CodeGenerator**: Generates code from proto files
- **Compiler**: Compiles C, C++, TypeScript
- **TestExecutor**: Runs test suites with plugins
- **Plugins**: StandardTestPlugin, CrossPlatformMatrixPlugin

## Common Tasks Reference

### Generate Code for a Specific Language

```bash
# Python only
PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_py --py_path gen/py

# All languages
PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_c --build_cpp --build_ts --build_py --build_gql
```

### Run Specific Test Types

```bash
python tests/run_tests.py --only-generate  # Just generate code
python tests/run_tests.py --check-tools    # Check available tools
python tests/run_tests.py --skip-lang c    # Skip C tests
```

### Adding New Tests

1. Add entry to `tests/test_config.json` under `test_suites`
2. Create test files: `tests/<lang>/test_<name>.<ext>`
3. Use standard output format: `[TEST START]`, `[TEST END]`
4. Return exit code 0 on success, 1 on failure
