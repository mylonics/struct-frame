# Testing

## Running Tests

From the project root:

```bash
# Run all tests
python test_all.py

# Or use the test runner directly
python tests/run_tests.py
```

## Test Runner Options

```bash
python tests/run_tests.py [options]

Options:
  --verbose, -v       Show detailed output
  --skip-lang LANG    Skip a language (c, cpp, py, ts, gql)
  --only-generate     Generate code only, skip tests
  --check-tools       Check tool availability only
  --clean             Clean generated and compiled files
```

Examples:

```bash
# Skip TypeScript tests
python tests/run_tests.py --skip-lang ts

# Only check if compilers are installed
python tests/run_tests.py --check-tools

# Generate code without running tests
python tests/run_tests.py --only-generate
```

## Test Output

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

============================================================
CODE GENERATION
============================================================

           C: PASS
         C++: PASS
      Python: PASS
  TypeScript: PASS
     GraphQL: PASS

============================================================
TEST EXECUTION
============================================================

[TEST] Basic types test
           C: PASS
         C++: PASS
      Python: PASS
  TypeScript: PASS
```

## Test Types

### Basic Types Test

Validates serialization of primitive types:
- Integer types (int8, int16, int32, int64, uint8, uint16, uint32, uint64)
- Floating point (float, double)
- Boolean
- Fixed strings

Files:
- `tests/c/test_basic_types.c`
- `tests/cpp/test_basic_types.cpp`
- `tests/py/test_basic_types.py`
- `tests/ts/test_basic_types.ts`

### Array Operations Test

Validates array serialization:
- Fixed arrays (always exact size)
- Bounded arrays (variable count)
- String arrays
- Enum arrays
- Nested message arrays

Files:
- `tests/c/test_arrays.c`
- `tests/cpp/test_arrays.cpp`
- `tests/py/test_arrays.py`
- `tests/ts/test_arrays.ts`

### Cross-Platform Serialization

Validates that data serialized in one language can be read in another.

Files:
- `tests/c/test_cross_platform_serialization.c`
- `tests/cpp/test_cross_platform_serialization.cpp`
- `tests/py/test_cross_platform_serialization.py`
- `tests/ts/test_cross_platform_serialization.ts`

### Cross-Platform Deserialization

Tests interoperability between languages. Produces a compatibility matrix:

```
Compatibility Matrix:
Encoder\Decoder     C          C++        Python    TypeScript
---------------------------------------------------------------
C                  OK          OK          OK         OK
C++                OK          OK          OK         OK
Python             OK          OK          OK         OK
TypeScript         OK          OK          OK         OK
```

## Adding a New Test

1. Add test to `test_config.json`:

```json
{
  "test_suites": [
    {
      "name": "new_test",
      "description": "Tests new feature",
      "plugin": "standard"
    }
  ]
}
```

2. Create test files:
   - `tests/c/test_new_test.c`
   - `tests/cpp/test_new_test.cpp`
   - `tests/py/test_new_test.py`
   - `tests/ts/test_new_test.ts`

3. Follow test output format:
   - Print `[TEST START] <Language> <Test Name>`
   - Print `[TEST END] <Language> <Test Name>: PASS` or `FAIL`
   - Exit with code 0 on success, 1 on failure

Example Python test:

```python
import sys
sys.path.insert(0, 'tests/generated/py')
from messages_sf import MyMessage

def test():
    msg = MyMessage()
    msg.value = 42
    
    # Serialize
    data = msg.to_bytes()
    
    # Deserialize
    parsed = MyMessage.from_bytes(data)
    
    if parsed.value != 42:
        return False
    return True

if __name__ == '__main__':
    print('[TEST START] Python NewTest')
    if test():
        print('[TEST END] Python NewTest: PASS')
        sys.exit(0)
    else:
        print('[TEST END] Python NewTest: FAIL')
        sys.exit(1)
```

## Test Organization

```
tests/
  run_tests.py              # Entry point
  test_config.json          # Configuration
  expected_values.json      # Expected values for cross-platform tests
  runner/                   # Test runner modules
    base.py                 # Base utilities
    tool_checker.py         # Tool availability
    code_generator.py       # Code generation
    compiler.py             # Compilation
    test_executor.py        # Test execution
    output_formatter.py     # Output formatting
    plugins.py              # Test plugins
    runner.py               # Main runner
  proto/                    # Test proto files
    basic_types.proto
    comprehensive_arrays.proto
    nested_messages.proto
    serialization_test.proto
  c/                        # C tests
    test_runner.c           # Test entry point
    test_codec.c            # Encode/decode logic
    test_codec.h
    build/                  # Compiled executables
  cpp/                      # C++ tests
    test_runner.cpp
    test_codec.cpp
    test_codec.hpp
    build/
  csharp/                   # C# tests
    TestRunner.cs
    TestCodec.cs
    StructFrameTests.csproj
  py/                       # Python tests
    test_runner.py
    test_codec.py
  ts/                       # TypeScript tests
    test_runner.ts
    test_codec.ts
    package.json
    tsconfig.json
    build/
  js/                       # JavaScript tests
    test_runner.js
    test_codec.js
  generated/                # Generated code for tests
    c/
    cpp/
    csharp/
    py/
    ts/
    js/
    gql/
```

## Prerequisites

**Python 3.8+** with:
```bash
pip install proto-schema-parser
```

**C tests**: GCC
```bash
# Ubuntu/Debian
sudo apt install gcc

# macOS
xcode-select --install

# Windows (MinGW)
# Download from https://www.mingw-w64.org/
```

**C++ tests**: G++ with C++14 support
```bash
# Ubuntu/Debian
sudo apt install g++

# macOS
xcode-select --install

# Windows (MinGW)
# Included with MinGW-w64
```

**TypeScript/JavaScript tests**: Node.js + npm
```bash
# Ubuntu/Debian
sudo apt install nodejs npm

# macOS
brew install node

# Windows
# Download from https://nodejs.org/

# Then install dependencies
cd tests/ts && npm install
```

**C# tests**: .NET SDK 8.0+
```bash
# Ubuntu/Debian
sudo apt install dotnet-sdk-8.0

# macOS
brew install dotnet-sdk

# Windows
# Download from https://dotnet.microsoft.com/download
# Or via winget:
winget install Microsoft.DotNet.SDK.8
```

## Debugging Failures

Failed tests print detailed information:

```
============================================================
FAILURE DETAILS: Basic types test
============================================================

Expected Values:
  int32_val: 12345
  float_val: 3.14

Actual Values:
  int32_val: 0
  float_val: 0.0

Raw Data (8 bytes):
  Hex: 0000000000000000
============================================================
```

Use `--verbose` to see command output for all operations.

## CI Integration

GitHub Actions runs tests on every push to main and every pull request.

The pipeline:
1. Sets up Python 3.11 and Node.js 20
2. Installs GCC and G++
3. Installs Python dependencies
4. Installs Node.js dependencies
5. Runs `python test_all.py`
6. Uploads test artifacts (generated code, binaries)

Artifacts are available for download for 5 days after each run.
