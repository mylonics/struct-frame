# struct-frame Test Suite

Comprehensive test suite for struct-frame that validates code generation and serialization/deserialization across all supported languages (C, C++, Python, TypeScript, JavaScript, C#, and GraphQL).

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

The test runner provides clean, organized output showing code generation, compilation, and test execution results for each language and frame profile.

## Cross-Platform Compatibility Matrix

The test suite includes cross-platform serialization tests. Each language can encode messages, and then any language can decode and validate them, producing a compatibility matrix.

## Test Architecture

The test suite follows a consistent **three-component pattern** across all languages:

### 1. Entry Point (`test_<suite>.*`)
Minimal main function that configures and runs the test:
```
test_standard.c     →  Runs standard message tests
test_extended.c     →  Runs extended message ID tests  
test_variable_flag.c →  Runs variable-length truncation tests
```

### 2. Test Data (`include/*_test_data.*`)
Contains three logical sections:
- **Message Definitions**: Hardcoded test messages with known values
- **Encoder**: Functions to serialize messages into a byte stream
- **Validator**: Functions to deserialize and compare with expected values

### 3. Test Codec (`include/test_codec.*`)
Shared infrastructure for all test suites:
- Frame profile configuration
- File I/O utilities
- Command-line parsing
- Encode/decode orchestration

## Test Suites

### 1. Standard Messages Test (`test_standard.*`)
**Purpose**: Validates serialization of common message types across all frame profiles.

**What it tests**:
- `SerializationTestMessage`: Magic numbers, strings, floats, bools, arrays
- `BasicTypesMessage`: All integer sizes (8/16/32/64-bit signed/unsigned), floats, doubles
- `UnionTestMessage`: Discriminated unions with nested message payloads
- `VariableSingleArray`: Variable-length arrays with different fill levels
- `Message`: Simple message with severity enum

**Frame Profiles**: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network

### 2. Extended Messages Test (`test_extended.*`)
**Purpose**: Validates message IDs greater than 255 (requiring 2-byte encoding).

**What it tests**:
- Extended message IDs (256-4095)
- Large payload messages (up to 280 bytes)
- Package ID support

**Frame Profiles**: profile_bulk, profile_network (profiles that support pkg_id)

### 3. Variable Flag Test (`test_variable_flag.*`)
**Purpose**: Validates the `variable=true` option truncates unused array space.

**What it tests**:
- Non-variable messages: Full struct size transmitted
- Variable messages: Only used array elements transmitted

**Frame Profiles**: profile_bulk

## Test Organization

```
tests/
├── run_tests.py              # Main test runner
├── README.md                 # This file
├── proto/                    # Proto definitions for tests
│   ├── test_messages.proto       # Standard test messages
│   ├── pkg_test_messages.proto   # Package ID test messages
│   └── extended_messages.proto   # Extended message ID tests
├── c/                        # C language tests
│   ├── test_standard.c           # Entry point
│   ├── test_extended.c           # Entry point
│   ├── test_variable_flag.c      # Entry point
│   └── include/
│       ├── standard_test_data.h      # Message definitions + encode/validate
│       ├── extended_test_data.h      # Extended test data
│       ├── variable_flag_test_data.h # Variable flag test data
│       └── test_codec.h              # Shared codec infrastructure
├── cpp/                      # C++ language tests (same structure)
├── py/                       # Python tests (same structure)
├── ts/                       # TypeScript tests (same structure)
├── js/                       # JavaScript tests (same structure)
├── csharp/                   # C# tests (same structure)
└── generated/                # Generated code output
    ├── c/
    ├── cpp/
    ├── py/
    ├── ts/
    ├── js/
    ├── csharp/
    └── gql/
```

## How Tests Work

### Encode Phase
1. Create hardcoded test messages with known values
2. Serialize messages in order using a BufferWriter
3. Write encoded byte stream to a file

### Decode Phase
1. Read encoded byte stream from file
2. Parse frames using an AccumulatingReader
3. Deserialize each message and compare with expected values
4. Report PASS if all messages match, FAIL otherwise

### Cross-Platform Validation
The test runner orchestrates encode/decode across languages:
1. Language A encodes messages to a file
2. Language B decodes that file and validates
3. Matrix shows which combinations work

## Command Line Options

```bash
python tests/run_tests.py [options]

Options:
  --verbose, -v       Enable verbose output for debugging
  --skip-lang LANG    Skip specific language (can be used multiple times)
  --only-generate     Only run code generation, skip compilation and tests
  --only-compile      Only run code generation and compilation, skip tests
  --check-tools       Only check tool availability
  --no-clean          Skip cleaning generated files (faster iteration)
  --profile NAME      Only test specific profile (e.g., ProfileStandard)
  --no-parallel       Disable parallel compilation
  --no-color          Disable colored output

Examples:
  python tests/run_tests.py                      # Run all tests
  python tests/run_tests.py --no-clean           # Skip cleaning for faster iteration
  python tests/run_tests.py --profile ProfileStandard  # Test only one profile
  python tests/run_tests.py --only-compile       # Stop after compilation
  python tests/run_tests.py --skip-lang ts       # Skip TypeScript tests
  python tests/run_tests.py --verbose            # Show detailed output
```

## Prerequisites

**Python 3.8+** with packages:
```bash
pip install proto-schema-parser
```

**For C tests**:
- GCC compiler

**For C++ tests**:
- G++ compiler with C++20 support

**For TypeScript tests**:
- Node.js
- Install dependencies: `cd tests/ts && npm install`

**For C# tests**:
- .NET SDK

## Adding a New Test Suite

1. Create proto definitions in `tests/proto/`
2. For each language, create:
   - Entry point: `test_<name>.<ext>`
   - Test data: `include/<name>_test_data.<ext>` with:
     - Message creation functions
     - Message arrays
     - Encoder functions
     - Validator functions
     - Test configuration
3. Use the shared `test_codec` infrastructure for encode/decode orchestration
4. Use the standard test output format:
   - Print `[TEST START] <Language> <Profile> <Mode>`
   - Print `[TEST END] <Language> <Profile> <Mode>: PASS` or `FAIL`
5. Return exit code 0 on success, 1 on failure

## Debugging Failed Tests

When a test fails, it prints detailed failure information including hex dump of the encoded data. Use `--verbose` flag to see all command output including successful operations.
