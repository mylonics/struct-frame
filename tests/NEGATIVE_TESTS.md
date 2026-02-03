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

### C++ Tests (`tests/cpp/test_negative.cpp`)
- **9 test cases** covering various error scenarios
- Tests both BufferReader and AccumulatingReader APIs
- Tests multiple frame profiles (Standard, Bulk)

### Python Tests (`tests/py/test_negative.py`)
- **8 test cases** covering similar error scenarios
- Tests both buffer and streaming modes
- Uses ProfileStandardReader and ProfileStandardAccumulatingReader

## Test Scenarios

All implementations test the following scenarios:

1. **Corrupted CRC Detection**: Verifies parser rejects frames with invalid checksums
2. **Truncated Frame Detection**: Tests handling of incomplete frames
3. **Invalid Start Bytes**: Ensures parser rejects frames with wrong start markers
4. **Zero-Length Buffer**: Tests edge case of empty input
5. **Corrupted Length Field**: Verifies length validation
6. **Streaming Corrupted CRC**: Tests CRC validation in byte-by-byte streaming mode
7. **Streaming Garbage Data**: Verifies parser handles random invalid bytes
8. **Multiple Corrupted Frames**: Tests parsing when middle frame in sequence is corrupted

## Running the Tests

### Run all negative tests via test runner:
```bash
python tests/run_tests.py
```

### Run individual test files:

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

1. **C++**: Add a new test function following the pattern in `test_negative.cpp`
2. **Python**: Add a new test function following the pattern in `test_negative.py`
3. Update the test count in the main function
4. Run the test to verify it correctly detects the error condition

### Test Function Template (C++)

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

### Test Function Template (Python)

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

## Why Some Languages Are Not Included

- **C**: The C API uses a different pattern (buffer_writer_t, buffer_reader_t) that would require more complex test setup. The C++ and Python tests provide sufficient coverage of the underlying frame parsing logic.
- **TypeScript/JavaScript/C#**: Not yet implemented, but can follow the same patterns as Python.
