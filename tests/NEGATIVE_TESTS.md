# Negative Tests

This directory contains negative tests for the struct-frame parser implementations. These tests verify that the parsers correctly handle invalid, corrupted, or malformed data.

## Purpose

Negative tests are critical for ensuring robust error handling. They verify that the parser:
- Detects corrupted CRC/checksums
- Rejects truncated frames
- Handles invalid start bytes
- Manages zero-length or malformed buffers
- Properly validates data integrity

## Test Files

### C Tests (`tests/c/test_negative.c`)
- **6 test cases** covering error scenarios
- Tests buffer reader and accumulating reader APIs
- Uses ProfileStandard configuration

### C++ Tests (`tests/cpp/test_negative.cpp`)
- **9 test cases** covering various error scenarios
- Tests both BufferReader and AccumulatingReader APIs
- Tests multiple frame profiles (Standard, Bulk)

### Python Tests (`tests/py/test_negative.py`)
- **8 test cases** covering similar error scenarios
- Tests both buffer and streaming modes
- Uses ProfileStandardReader and ProfileStandardAccumulatingReader

### TypeScript Tests (`tests/ts/test_negative.ts`)
- **8 test cases** covering error scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Bulk)

### JavaScript Tests (`tests/js/test_negative.js`)
- **8 test cases** identical to TypeScript
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Bulk)

### C# Tests (`tests/csharp/TestNegative.cs`)
- **8 test cases** covering error scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Bulk)

## Test Scenarios

All implementations test the following scenarios:

1. **Corrupted CRC Detection**: Verifies parser rejects frames with invalid checksums
2. **Truncated Frame Detection**: Tests handling of incomplete frames
3. **Invalid Start Bytes**: Ensures parser rejects frames with wrong start markers
4. **Zero-Length Buffer**: Tests edge case of empty input
5. **Corrupted Length Field**: Verifies length validation
6. **Streaming Corrupted CRC**: Tests CRC validation in byte-by-byte streaming mode
7. **Streaming Garbage Data**: Verifies parser handles random invalid bytes
8. **Bulk/Multiple Profile Tests**: Tests error handling across different frame profiles

## Running the Tests

### Run all negative tests via test runner:
```bash
python tests/run_tests.py
```

### Run individual test files:

**C:**
```bash
# Compile
gcc -I"tests/generated/c" -o "tests/c/build/test_negative" "tests/c/test_negative.c" -lm

# Run
./tests/c/build/test_negative
```

**C++:**
```bash
# Compile
g++ -std=c++20 -I"tests/generated/cpp" -I"tests/cpp/include" \
    -o "tests/cpp/build/test_negative" "tests/cpp/test_negative.cpp"

# Run
./tests/cpp/build/test_negative
```

**Python:**
```bash
python tests/py/test_negative.py
```

**TypeScript:**
```bash
npx ts-node tests/ts/test_negative.ts
```

**JavaScript:**
```bash
node tests/js/test_negative.js
```

**C#:**
```bash
# Via test runner
dotnet run --project tests/csharp/StructFrameTests.csproj -- --runner test_negative
```

## Expected Results

All negative tests should **PASS**, which means:
- Invalid input is correctly detected and rejected
- Parser returns `valid=false` for corrupted/malformed data
- No crashes or undefined behavior occurs
- Error handling is consistent across implementations

## Test Output Format

Each test prints:
- Test name and status (PASS/FAIL)
- Summary of tests run, passed, and failed
- Exit code 0 if all tests pass, 1 if any fail

Example output:
```
========================================
NEGATIVE TESTS - C++ Parser
========================================

Testing error handling for invalid frames:

  [TEST] Corrupted CRC detection... PASS
  [TEST] Truncated frame detection... PASS
  ...

========================================
RESULTS
========================================
Tests run:    9
Tests passed: 9
Tests failed: 0
========================================
```

## Integration with Test Suite

The negative tests are automatically integrated into the main test suite:
- Compiled during the compilation phase
- Executed in the "Negative Tests" phase
- Results included in test summary
- Counted toward total pass/fail metrics

## Adding New Negative Tests

To add a new negative test scenario:

1. **C**: Add a new test function following the pattern in `test_negative.c`
2. **C++**: Add a new test function following the pattern in `test_negative.cpp`
3. **Python**: Add a new test function following the pattern in `test_negative.py`
4. **TypeScript**: Add a new test function following the pattern in `test_negative.ts`
5. **JavaScript**: Add a new test function following the pattern in `test_negative.js`
6. **C#**: Add a new test method following the pattern in `TestNegative.cs`

Update the test count in the main function and run to verify.

### Test Function Templates

**C++:**
```cpp
bool test_new_scenario() {
  // 1. Set up test data
  std::vector<uint8_t> buffer(1024);
  
  // 2. Create invalid/corrupted data
  // ... corrupt buffer in specific way ...
  
  // 3. Try to parse
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), size, get_message_info);
  auto result = reader.next();
  
  // 4. Expect parsing to fail
  return !result.valid;
}
```

**Python:**
```python
def test_new_scenario():
    """Test: Description of scenario"""
    # 1. Set up test data
    writer = ProfileStandardWriter(capacity=1024)
    
    # 2. Create invalid/corrupted data
    # ... corrupt buffer in specific way ...
    
    # 3. Try to parse
    reader = ProfileStandardReader(buffer=bytes(buffer), get_message_info=get_message_info)
    result = reader.next()
    
    # 4. Expect parsing to fail
    return not result.valid
```

**TypeScript/JavaScript:**
```typescript
function testNewScenario(): boolean {
  // 1. Set up test data
  const writer = new ProfileStandardWriter(1024);
  
  // 2. Create invalid/corrupted data
  // ... corrupt buffer in specific way ...
  
  // 3. Try to parse
  const reader = new ProfileStandardReader(buffer, get_message_info);
  const result = reader.next();
  
  // 4. Expect parsing to fail
  return !result.valid;
}
```

**C#:**
```csharp
private static bool TestNewScenario()
{
    // 1. Set up test data
    var writer = new ProfileStandardWriter();
    
    // 2. Create invalid/corrupted data
    // ... corrupt buffer in specific way ...
    
    // 3. Try to parse
    var reader = new ProfileStandardReader(GetMessageInfo);
    reader.SetBuffer(buffer, size);
    var result = reader.Next();
    
    // 4. Expect parsing to fail
    return !result.valid;
}
```

