# struct-frame Test Suite

This directory contains a comprehensive test suite for the struct-frame project that validates code generation and serialization/deserialization functionality across all supported languages (C, TypeScript, and Python).

## Quick Start

Run all tests from the project root:

```bash
python test_all.py
```

Or run the test suite directly:

```bash
python tests/run_tests.py
```

## Test Structure

### Test Organization

```
tests/
├── run_tests.py              # Main test runner script
├── proto/                    # Test protocol buffer definitions
│   ├── basic_types.proto     # Tests all basic data types
│   ├── nested_messages.proto # Tests nested message structures
│   ├── comprehensive_arrays.proto # Tests all array types
│   └── serialization_test.proto   # Cross-language compatibility
├── c/                        # C language test programs
│   ├── test_basic_types.c    # Basic types serialization tests
│   ├── test_arrays.c         # Array operations tests
│   └── test_serialization.c  # Cross-language compatibility
├── ts/                       # TypeScript test programs
│   ├── test_basic_types.ts   # Basic types serialization tests
│   ├── test_arrays.ts        # Array operations tests
│   └── test_serialization.ts # Cross-language compatibility
├── py/                       # Python test programs
│   ├── test_basic_types.py   # Basic types serialization tests
│   ├── test_arrays.py        # Array operations tests
│   └── test_serialization.py # Cross-language compatibility
└── generated/                # Generated code output directory
    ├── c/                    # Generated C headers
    ├── ts/                   # Generated TypeScript modules
    └── py/                   # Generated Python classes
```

### Test Categories

1. **Code Generation Tests**
   - Verifies that proto files generate valid code for all languages
   - Tests all basic data types, arrays, nested messages, and enums
   - Ensures generated code compiles without errors

2. **Basic Types Tests**
   - Tests serialization/deserialization of all primitive types
   - Covers int8, int16, int32, int64, uint8, uint16, uint32, uint64
   - Tests float32, float64, bool, and string types
   - Validates fixed-size vs variable-size strings

3. **Array Tests**
   - Tests fixed arrays (always exact size)
   - Tests bounded arrays (variable count up to maximum)
   - Covers primitive arrays, string arrays, enum arrays
   - Tests nested message arrays

4. **Cross-Language Compatibility Tests**
   - Verifies data serialized in one language can be deserialized in another
   - Creates binary test files that are shared between language tests
   - Ensures protocol compatibility across all implementations

## Command Line Options

```bash
python tests/run_tests.py [options]

Options:
  --generate-only    Only run code generation tests
  --skip-c          Skip C language tests
  --skip-ts         Skip TypeScript language tests  
  --skip-py         Skip Python language tests
  --verbose, -v     Enable verbose output

Examples:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py --generate-only   # Just generate code
  python tests/run_tests.py --skip-ts         # Skip TypeScript tests
  python tests/run_tests.py --verbose         # Detailed output
```

## Prerequisites

### Required Dependencies

- **Python 3.8+** with packages:
  - `proto-schema-parser`
  - `structured-classes`

- **For C tests:**
  - GCC compiler or equivalent
  - Standard C library

- **For TypeScript tests:**
  - Node.js runtime
  - TypeScript compiler (`npm install -g typescript`)
  - typed-struct package (`npm install`)

### Installation

1. Install Python dependencies:
   ```bash
   pip install proto-schema-parser structured-classes
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Ensure GCC is available (Windows users may need MinGW)

## Test Workflow

The test runner executes the following sequence:

1. **Setup**: Creates test directories and cleans previous output
2. **Code Generation**: Generates C, TypeScript, and Python code from proto files
3. **Compilation**: Compiles generated code to verify syntax correctness
4. **Basic Tests**: Runs fundamental serialization/deserialization tests
5. **Array Tests**: Runs comprehensive array operation tests  
6. **Cross-Language Tests**: Verifies inter-language compatibility
7. **Summary**: Reports pass/fail status for all test categories

## Understanding Results

The test runner provides detailed output showing:

- ✅ **PASS**: Test completed successfully
- ❌ **FAIL**: Test failed - check error messages
- ⚠️  **WARNING**: Test skipped or had non-critical issues

### Expected Behavior

- **Code Generation**: Should always pass for all languages
- **C Tests**: Should compile and run successfully
- **Python Tests**: Should always pass (most reliable implementation)
- **TypeScript Tests**: May have warnings due to runtime complexity
- **Cross-Language**: Should create compatible binary data

## Debugging Failed Tests

### Code Generation Failures
- Check that proto files are valid
- Verify Python dependencies are installed
- Ensure `PYTHONPATH` includes the `src` directory

### C Compilation Failures
- Verify GCC is installed and available in PATH
- Check that generated headers exist in `tests/generated/c/`
- Look for missing boilerplate files

### Python Test Failures
- Verify `structured-classes` package is installed
- Check that generated Python files exist
- Ensure imports can resolve generated modules

### TypeScript Test Failures
- Verify Node.js and TypeScript are installed
- Check that `npm install` completed successfully
- Review TypeScript compiler errors in verbose mode

## Adding New Tests

### Adding a New Proto File

1. Create `tests/proto/your_test.proto`
2. Add appropriate message definitions with msgid
3. The test runner will automatically generate code for it

### Adding Language-Specific Tests

1. Create test program in appropriate language directory
2. Follow the naming convention: `test_<category>.ext`
3. Import generated modules and test serialization/deserialization
4. Update test runner if needed for new test categories

### Test Program Structure

Each test program should:
- Import generated code modules
- Create message instances with test data  
- Serialize messages to binary format
- Deserialize and verify data integrity
- Handle missing modules gracefully (before code generation)
- Return appropriate exit codes (0 = success, 1 = failure)

## Known Issues and Limitations

- **TypeScript**: Generated code may have runtime issues with method calls
- **C**: Some generated macro conflicts may occur
- **Cross-Language**: Binary compatibility depends on consistent framing
- **Windows**: Path handling may require PowerShell or cmd adjustments

## Contributing

When adding new features to struct-frame:

1. Add appropriate test proto definitions
2. Create test programs for each supported language
3. Verify cross-language compatibility
4. Update this documentation

The comprehensive test suite helps ensure that changes don't break existing functionality across all supported languages and use cases.