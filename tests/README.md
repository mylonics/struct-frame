# struct-frame Test Suite

Comprehensive test suite for struct-frame that validates code generation and serialization/deserialization across all supported languages (C, C++, TypeScript, and Python).

## Quick Start

Run all tests from the project root:

```bash
python test_all.py
```

Or run the test suite directly:

```bash
python tests/run_tests.py
```

## Test Output Format

Tests follow a consistent format across all languages:

```
[TEST START] <Language> <Test Type>
[TEST END] <Language> <Test Type>: PASS/FAIL
```

- **Success**: Only start and end messages are printed
- **Failure**: Detailed failure information including expected values, actual values, and raw data hex dump

## Test Types

### 1. Basic Types Test
**Purpose**: Validates serialization and deserialization of primitive data types

**What it tests**:
- Integer types: int8, int16, int32, int64, uint8, uint16, uint32, uint64
- Floating point types: float32, float64
- Boolean type: bool
- String types: fixed-size strings and variable-length strings

**Test flow**:
1. Create a message with sample values for all basic types
2. Serialize the message to binary format
3. Deserialize the binary data back to a message
4. Verify all values match the original

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

**Test flow**:
1. Create a message containing various array types
2. Populate arrays with test data
3. Serialize the message to binary format
4. Deserialize and verify array counts and values

**Files**:
- C: `tests/c/test_arrays.c`
- C++: `tests/cpp/test_arrays.cpp`
- Python: `tests/py/test_arrays.py`
- TypeScript: `tests/ts/test_arrays.ts`

### 3. Cross-Language Serialization Test
**Purpose**: Ensures data serialized in one language can be deserialized in another

**What it tests**:
- Binary format compatibility across language implementations
- Correct encoding/decoding of message framing
- Data integrity across language boundaries

**Test flow**:
1. Each language creates a test message and serializes it to a binary file
2. Each language attempts to read and deserialize binary files from other languages
3. Verify decoded values match expected values

**Files**:
- C: `tests/c/test_serialization.c` → creates `c_test_data.bin`
- C++: `tests/cpp/test_serialization.cpp` → creates `cpp_test_data.bin`
- Python: `tests/py/test_serialization.py` → creates `python_test_data.bin`
- TypeScript: `tests/ts/test_serialization.ts` → creates `typescript_test_data.bin`

## Test Organization

```
tests/
├── run_tests.py              # Main test runner
├── proto/                    # Proto definitions for tests
│   ├── basic_types.proto     # Defines all basic data types
│   ├── nested_messages.proto # Defines nested message structures
│   ├── comprehensive_arrays.proto # Defines all array types
│   └── serialization_test.proto   # Defines cross-language test message
├── c/                        # C language tests
├── cpp/                      # C++ language tests
├── ts/                       # TypeScript tests
├── py/                       # Python tests
└── generated/                # Generated code output
```

## Command Line Options

```bash
python tests/run_tests.py [options]

Options:
  --generate-only    Only run code generation tests
  --skip-c          Skip C language tests
  --skip-cpp        Skip C++ language tests
  --skip-ts         Skip TypeScript language tests  
  --skip-py         Skip Python language tests
  --verbose, -v     Enable verbose output for debugging

Examples:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py --generate-only   # Just generate code
  python tests/run_tests.py --skip-ts         # Skip TypeScript tests
  python tests/run_tests.py --verbose         # Show detailed output
```

## Prerequisites

**Python 3.8+** with packages:
```bash
pip install proto-schema-parser structured-classes
```

**For C tests**:
- GCC compiler

**For C++ tests**:
- G++ compiler with C++14 support

**For TypeScript tests**:
- Node.js
- TypeScript compiler: `npm install -g typescript`
- Dependencies: `npm install` in project root

## Understanding Test Results

The test runner provides a summary showing:

```
🔧 Code Generation: PASS/FAIL for each language
🔨 Compilation: PASS/FAIL for compiled languages
🧪 Basic Types Tests: PASS/FAIL for each language
🧪 Arrays Tests: PASS/FAIL for each language
�� Serialization Tests: PASS/FAIL for each language
🌐 Cross-Language Compatibility: Cross-language decode matrix
```

Expected behavior:
- **Code Generation**: Should always pass if dependencies are installed
- **C/C++ Tests**: Should pass if compilers are available
- **Python Tests**: Should pass (most reliable implementation)
- **TypeScript Tests**: May have issues due to runtime complexity
- **Cross-Language Tests**: Should show high compatibility rate

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

This information helps diagnose:
- Which specific values don't match
- The exact binary data that was encoded/decoded
- Whether the issue is in encoding or decoding

## Adding New Tests

To add a new test type:

1. Create a new proto file in `tests/proto/`
2. Add test programs for each language following the naming convention: `test_<name>.<ext>`
3. Use the standard test output format with `[TEST START]` and `[TEST END]`
4. Print failure details only when tests fail
5. Test programs should return exit code 0 on success, 1 on failure
