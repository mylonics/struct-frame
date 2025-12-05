# struct-frame Test Suite

Comprehensive test suite for struct-frame that validates code generation and serialization/deserialization across all supported languages (C, C++, Python, TypeScript, and GraphQL).

## Quick Start

Run all tests from the project root:

```bash
python tests/run_tests.py
```

Or use the wrapper script:

```bash
python test_all.py
```

## Test Output Format

The test runner provides clean, organized output:

```
============================================================
TOOL AVAILABILITY CHECK
============================================================

  [OK] C
      Compiler:    [OK] gcc (gcc 6.3.0)

  [OK] C++
      Compiler:    [OK] g++ (g++ 6.3.0)

  [OK] Python
      Interpreter: [OK] python (Python 3.11.8)

  [OK] TypeScript
      Compiler:    [OK] npx tsc (Version 5.7.3)
      Interpreter: [OK] node (v24.4.1)

  [OK] GraphQL
      (generation only)

============================================================
CODE GENERATION
============================================================

           C: PASS
         C++: PASS
      Python: PASS
  TypeScript: PASS
     GraphQL: PASS

============================================================
COMPILATION (all test files)
============================================================

           C: PASS
         C++: PASS
  TypeScript: PASS

============================================================
TEST EXECUTION
============================================================

[TEST] Tests basic integer, float, and boolean types

           C: PASS
         C++: PASS
      Python: PASS
  TypeScript: PASS
```

## Cross-Platform Compatibility Matrix

The test suite includes cross-platform serialization tests that produce a compatibility matrix:

```
Compatibility Matrix:
Encoder\Decoder     C          C++        Python    TypeScript
---------------------------------------------------------------
C                  OK          OK          OK         FAIL
C++               FAIL         OK         FAIL        FAIL
Python             OK          OK          OK         FAIL
TypeScript        FAIL         OK         FAIL        FAIL

Success rate: 8/16 (50%)
```

## Test Types

### 1. Basic Types Test
**Purpose**: Validates serialization and deserialization of primitive data types

**What it tests**:
- Integer types: int8, int16, int32, int64, uint8, uint16, uint32, uint64
- Floating point types: float32, float64
- Boolean type: bool
- String types: fixed-size strings

**Files**:
- C: `tests/c/test_basic_types.c`
- C++: `tests/cpp/test_basic_types.cpp`
- Python: `tests/py/test_basic_types.py`
- TypeScript: `tests/ts/test_basic_types.ts`

### 2. Array Operations Test
**Purpose**: Validates array serialization for both fixed and bounded arrays

**What it tests**:
- Fixed arrays: Arrays with a predetermined, unchanging size
- Bounded arrays: Arrays with variable count up to a maximum size
- Array element types: primitives, strings, enums, and nested messages

**Files**:
- C: `tests/c/test_arrays.c`
- C++: `tests/cpp/test_arrays.cpp`
- Python: `tests/py/test_arrays.py`
- TypeScript: `tests/ts/test_arrays.ts`

### 3. Cross-Platform Serialization Test
**Purpose**: Validates data serialization format consistency

**What it tests**:
- Binary format compatibility
- Correct encoding/decoding of message framing
- Data integrity

**Files**:
- C: `tests/c/test_cross_platform_serialization.c`
- C++: `tests/cpp/test_cross_platform_serialization.cpp`
- Python: `tests/py/test_cross_platform_serialization.py`
- TypeScript: `tests/ts/test_cross_platform_serialization.ts`

### 4. Cross-Platform Deserialization Test
**Purpose**: Ensures data serialized in one language can be deserialized in another

**What it tests**:
- Binary format compatibility across language implementations
- Correct decoding across language boundaries
- Produces compatibility matrix

**Files**:
- C: `tests/c/test_cross_platform_deserialization.c`
- C++: `tests/cpp/test_cross_platform_deserialization.cpp`
- Python: `tests/py/test_cross_platform_deserialization.py`
- TypeScript: `tests/ts/test_cross_platform_deserialization.ts`

## Test Organization

```
tests/
├── run_tests.py              # Main test runner entry point
├── test_config.json          # Test configuration (languages, tests, paths)
├── expected_values.json      # Expected values for cross-platform tests
├── README.md                 # This file
├── runner/                   # Modular test runner components
│   ├── __init__.py
│   ├── base.py               # Base utilities (logging, config, commands)
│   ├── tool_checker.py       # Tool availability checking
│   ├── code_generator.py     # Code generation from proto files
│   ├── compiler.py           # Compilation for C, C++, TypeScript
│   ├── test_executor.py      # Test execution
│   ├── output_formatter.py   # Result formatting
│   ├── plugins.py            # Test plugins (StandardTestPlugin, CrossPlatformMatrixPlugin)
│   └── runner.py             # Main ConfigDrivenTestRunner
├── proto/                    # Proto definitions for tests
│   ├── basic_types.proto
│   ├── comprehensive_arrays.proto
│   ├── nested_messages.proto
│   └── serialization_test.proto
├── c/                        # C language tests
│   └── build/                # Compiled C executables
├── cpp/                      # C++ language tests
│   └── build/                # Compiled C++ executables
├── py/                       # Python tests
├── ts/                       # TypeScript tests
│   ├── package.json          # Node.js dependencies
│   ├── tsconfig.json         # TypeScript configuration
│   ├── node_modules/         # Node.js modules
│   └── build/                # Compiled JS files
└── generated/                # Generated code output
    ├── c/                    # Generated C headers
    ├── cpp/                  # Generated C++ headers
    ├── py/                   # Generated Python modules
    ├── ts/                   # Generated TypeScript modules
    └── gql/                  # Generated GraphQL schemas
```

## Command Line Options

```bash
python tests/run_tests.py [options]

Options:
  --config CONFIG     Path to test configuration file (default: tests/test_config.json)
  --verbose, -v       Enable verbose output for debugging
  --skip-lang LANG    Skip specific language (can be used multiple times)
  --only-generate     Only run code generation, skip tests
  --check-tools       Only check tool availability, don't run tests
  --clean             Clean all generated and compiled test files

Examples:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py --clean            # Clean generated files
  python tests/run_tests.py --only-generate    # Just generate code
  python tests/run_tests.py --skip-lang ts     # Skip TypeScript tests
  python tests/run_tests.py --verbose          # Show detailed output
  python tests/run_tests.py --check-tools      # Check available tools
```

## Prerequisites

**Python 3.8+** with packages:
```bash
pip install proto-schema-parser
```

**For C tests**:
- GCC compiler

**For C++ tests**:
- G++ compiler with C++14 support

**For TypeScript tests**:
- Node.js
- Install dependencies: `cd tests/ts && npm install`

## Configuration

Tests are configured via `test_config.json`. Key sections:

- **languages**: Defines each language's compiler, interpreter, flags, and paths
- **test_suites**: Defines test cases with names, descriptions, and plugins
- **proto_files**: Proto files to generate code from

### Adding a New Language

1. Add language configuration to `test_config.json` under `languages`
2. Define code generation flags, compilation settings, and execution interpreter
3. Create test files following the naming convention

### Adding a New Test

1. Add a new entry to `test_suites` in `test_config.json`
2. Create test files for each language: `test_<name>.<ext>`
3. Use the standard test output format:
   - Print `[TEST START] <Language> <Test Name>`
   - Print `[TEST END] <Language> <Test Name>: PASS` or `FAIL`
4. Return exit code 0 on success, 1 on failure

## Debugging Failed Tests

When a test fails, it prints detailed failure information:

```
============================================================
FAILURE DETAILS: <Description>
============================================================

Expected Values:
  field1: value1
  field2: value2

Actual Values:
  field1: wrong_value1
  field2: wrong_value2

Raw Data (N bytes):
  Hex: deadbeef...
============================================================
```

Use `--verbose` flag to see all command output including successful operations.

## Test Runner Architecture

The test runner uses a modular, plugin-based architecture:

```
ConfigDrivenTestRunner
├── ToolChecker        # Verifies compilers/interpreters are available
├── CodeGenerator      # Generates code from proto files
├── Compiler           # Compiles C, C++, TypeScript
├── TestExecutor       # Runs test suites with plugins
│   ├── StandardTestPlugin           # Standard test execution
│   └── CrossPlatformMatrixPlugin    # Cross-platform compatibility matrix
└── OutputFormatter    # Formats and prints results
```

This architecture allows:
- Easy addition of new languages via configuration
- Custom test behavior via plugins
- Clean separation of concerns
