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
  --skip-lang LANG    Skip a language (c, cpp, py, ts, js, csharp, gql)
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

## Test Prerequisites

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
```

**C++ tests**: G++ with C++14 support
```bash
# Ubuntu/Debian
sudo apt install g++

# macOS
xcode-select --install
```

**TypeScript/JavaScript tests**: Node.js + npm
```bash
# Ubuntu/Debian
sudo apt install nodejs npm

# macOS
brew install node

# Then install dependencies
cd tests/ts && npm install
```

**C# tests**: .NET SDK 8.0+
```bash
# Ubuntu/Debian
sudo apt install dotnet-sdk-8.0

# macOS
brew install dotnet-sdk
```

## Test Types

### Basic Types Test
Validates serialization of primitive types (integers, floats, booleans, strings).

### Array Operations Test
Validates array serialization (fixed arrays, bounded arrays, nested arrays).

### Cross-Platform Compatibility
Tests interoperability between languages. Produces a compatibility matrix showing which language pairs can exchange data.

## Adding a New Test

1. Add test to `tests/test_suites.json`
2. Create test files in `tests/<lang>/`
3. Follow test output format:
   - Print `[TEST START] <Language> <Test Name>`
   - Print `[TEST END] <Language> <Test Name>: PASS` or `FAIL`
   - Exit with code 0 on success, 1 on failure

## CI Integration

GitHub Actions runs tests on every push to main and every pull request. Artifacts are available for download for 5 days after each run.

