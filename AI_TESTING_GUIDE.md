# AI Agent Guide for struct-frame Testing

This document provides guidance for AI agents working with the struct-frame project's test suite. It explains how to efficiently update, debug, and extend the testing framework.

## Test Architecture Overview

The struct-frame project uses a comprehensive multi-language test suite located in the `tests/` directory:

```
tests/
├── run_tests.py              # Main test orchestrator
├── proto/                    # Protocol buffer test definitions  
├── c/                        # C language test programs
├── ts/                       # TypeScript test programs
├── py/                       # Python test programs
└── generated/                # Generated code output (git-ignored)
```

### Entry Points

- **Primary**: `python test_all.py` (project root)
- **Direct**: `python tests/run_tests.py` (detailed options)

## Key Components

### 1. Test Runner (`tests/run_tests.py`)

The TestRunner class orchestrates all testing activities:
- **Code Generation**: Runs struct-frame generator on proto files
- **Compilation**: Compiles generated C/TypeScript code  
- **Execution**: Runs test programs for each language
- **Cross-Language**: Verifies binary compatibility between languages

**Key Methods:**
- `test_code_generation()`: Generates code for all proto files
- `test_c_compilation()`: Compiles C tests using GCC
- `run_c_tests()`: Executes compiled C test programs  
- `run_python_tests()`: Executes Python test scripts
- `print_summary()`: Reports comprehensive results

### 2. Protocol Definitions (`tests/proto/`)

Test proto files covering different aspects:
- **`basic_types.proto`**: All primitive data types (int8-int64, float, double, bool, string)
- **`comprehensive_arrays.proto`**: Fixed arrays, bounded arrays, string arrays, enum arrays, nested message arrays
- **`nested_messages.proto`**: Message composition, enums, flatten attribute
- **`serialization_test.proto`**: Cross-language compatibility testing

### 3. Language-Specific Tests

Each language directory contains parallel test implementations:
- **`test_basic_types.*`**: Serialization/deserialization of primitive types
- **`test_arrays.*`**: Array operations and memory layout verification
- **`test_serialization.*`**: Cross-language binary compatibility

## Common AI Agent Tasks

### Adding New Test Cases

1. **Create Proto Definition**:
   ```proto
   // tests/proto/new_feature.proto
   package new_feature;
   
   message TestMessage {
     option msgid = 205;  // Use next available ID
     // Add your test fields
   }
   ```

2. **Implement Language Tests**:
   - Copy existing test structure from `test_basic_types.*`
   - Modify to test your specific feature
   - Ensure all languages have parallel implementations

3. **Update Test Runner**:
   - Add proto file to `proto_files` list in `test_code_generation()`
   - Add test category if needed in `TestRunner.results` dictionary

### Debugging Test Failures

#### C Compilation Issues
- **Missing GCC**: Test runner gracefully skips if GCC unavailable
- **Header Issues**: Check generated files in `tests/generated/c/`
- **Boilerplate Problems**: Verify boilerplate files are automatically copied by the main generation script
- **C++ Syntax**: Look for aggregate initialization (`{}`) instead of C-compatible `{0}`

#### Python Test Issues  
- **Import Errors**: Check `PYTHONPATH` includes generated directory
- **Module Missing**: Verify code generation completed successfully
- **Constructor Issues**: Structured classes require positional arguments, not keyword arguments

#### TypeScript Issues
- **Compilation**: Check if `tsc` is available and `npm install` completed
- **Runtime Errors**: Generated TypeScript may have method call issues (known limitation)

#### Cross-Language Compatibility
- **Binary Files**: Tests create `*_test_data.bin` files for compatibility checking
- **Serialization Format**: All languages must produce identical binary output
- **Checksum Validation**: Fletcher checksum algorithm must match across implementations

### Performance Optimization

The test suite is designed for speed:
- **Code Generation**: ~0.1 seconds per proto file
- **C Compilation**: ~1-2 seconds per test file
- **Python Tests**: ~0.5 seconds per test
- **Total Runtime**: Usually under 5 seconds

**Never cancel operations** - they complete quickly and interruption can leave partial state.

### Known Issues and Workarounds

#### C Code Generation
- **Issue**: C++ aggregate initialization syntax in generated C code
- **Fix**: Update boilerplate files to use `= {0}` instead of `{}`
- **Location**: `src/struct_frame/boilerplate/c/*.h`

#### Checksum Validation
- **Issue**: Mismatch between encoding and validation checksum calculation
- **Fix**: Ensure both use same data length (`msg_size + 1` to include message ID)
- **Location**: `basic_frame_validate_packet()` function

#### Floating Point Comparisons
- **Issue**: Exact equality fails due to precision
- **Fix**: Use tolerance-based comparison with `fabsf()` and `FLOAT_TOLERANCE`
- **Pattern**: `assert(fabsf(actual - expected) < FLOAT_TOLERANCE)`

#### Array Serialization
- **Issue**: Complex array structures may serialize only partial data
- **Limitation**: Known limitation in struct-frame serialization system
- **Workaround**: Basic types work perfectly; arrays have architectural limitations

### Test Result Interpretation

The test runner provides detailed results categorized by:
- **Code Generation**: Should always pass (validates proto parsing)
- **Compilation**: May fail if compilers unavailable (GCC, TSC)
- **Basic Types**: Should pass for all languages (core functionality)
- **Arrays**: Python passes; C/TS may have limitations
- **Serialization**: Tests cross-language binary compatibility

**Success Criteria:**
- **80%+ pass rate**: Full success
- **30%+ with core working**: Partial success (acceptable)
- **<30% pass rate**: Needs attention

### Environment Dependencies

#### Required Always
- Python 3.8+ with `proto-schema-parser`

#### Optional (graceful degradation)
- **GCC**: For C compilation and execution
- **TypeScript/Node.js**: For TypeScript compilation and execution
- **MinGW** (Windows): Provides GCC compiler

#### Directory Structure
- Tests automatically create `tests/generated/` for output
- Boilerplate files copied from `src/struct_frame/boilerplate/`
- Binary test files written to language-specific directories

### Extending the Framework

#### Adding New Languages
1. Create boilerplate directory: `src/struct_frame/boilerplate/newlang/`
2. Implement generator: `src/struct_frame/newlang_gen.py`
3. Add test directory: `tests/newlang/`
4. Update test runner with compilation and execution logic

#### Adding New Features
1. Update proto definitions with new syntax
2. Implement in all language generators
3. Add comprehensive test cases
4. Verify cross-language compatibility

### Best Practices for AI Agents

1. **Always run full test suite** after making changes
2. **Test incrementally** - add one feature at a time
3. **Verify all languages** - don't assume changes work universally  
4. **Check boilerplate files** - many issues stem from template problems
5. **Use verbose mode** when debugging: `python tests/run_tests.py --verbose`
6. **Preserve working tests** - ensure changes don't break existing functionality

### Quick Reference Commands

```bash
# Full test suite
python test_all.py

# Code generation only
python tests/run_tests.py --generate-only

# Skip problematic languages
python tests/run_tests.py --skip-c --skip-ts

# Debug specific issue
python tests/run_tests.py --verbose

# Clean and retry
rm -rf tests/generated/ && python test_all.py
```

This testing framework ensures struct-frame maintains high quality across all supported languages while providing clear feedback for development and debugging.