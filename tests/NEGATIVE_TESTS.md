# Negative Tests

This directory contains negative tests for the struct-frame parser implementations. These tests verify that the parsers correctly handle invalid, corrupted, or malformed data.

## Purpose

Negative tests are critical for ensuring robust error handling. They verify that the parser:
- Detects corrupted CRC/checksums
- Rejects truncated frames
- Handles invalid start bytes
- Manages zero-length or malformed buffers
- Properly validates data integrity
- Handles frames split across multiple buffer chunks
- Rejects unknown message IDs
- Validates routing fields (sys_id, comp_id) as part of CRC integrity

## Test Files

All seven language implementations share **13 identical test scenarios** (same names, same behaviour):

### C Tests (`tests/c/test_negative.c`)
- **13 test cases** covering all uniform error scenarios
- Tests buffer reader and accumulating reader (buffer mode) APIs
- Uses ProfileStandard, ProfileSensor, ProfileBulk, and ProfileNetwork configurations

### C++ Tests (`tests/cpp/test_negative.cpp`)
- **14 test cases** (includes an extra `Invalid start byte detection` alias)
- Tests both BufferReader and AccumulatingReader APIs
- Tests multiple frame profiles (Standard, Sensor, Bulk, Network)

### Python Tests (`tests/py/test_negative.py`)
- **13 test cases** covering all uniform error scenarios
- Tests both buffer and streaming modes
- Uses ProfileStandardReader, ProfileSensorReader, and ProfileNetworkReader

### TypeScript Tests (`tests/ts/test_negative.ts`)
- **13 test cases** covering all uniform error scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### JavaScript Tests (`tests/js/test_negative.js`)
- **13 test cases** identical to TypeScript
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### C# Tests (`tests/csharp/TestNegative.cs`)
- **13 test cases** covering all uniform error scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### Rust Tests (`tests/rust/src/test_negative.rs`)
- **13 test cases** covering all uniform error scenarios
- Tests BufferReader and AccumulatingReader APIs
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

## Uniform Test Scenarios

All seven languages implement the following 13 scenarios with identical names:

1. **Bulk profile: Corrupted CRC** – validates error detection on the Bulk (extended-header) profile
2. **Corrupted CRC detection** – verifies parser rejects frames with flipped CRC bytes
3. **Corrupted length field detection** – ensures length validation catches oversized claims
4. **Invalid message ID rejection** – verifies that a frame with an unknown msg_id byte (0xFF) is rejected; since get_message_info returns no magic values for unknown IDs, the CRC check fails
5. **Invalid start bytes detection** – ensures parser rejects frames with wrong start markers
6. **Minimal profile: Truncated frame** – verifies ProfileSensor (no CRC, no length) correctly rejects a buffer shorter than the expected payload size determined via get_message_info
7. **Multiple frames: Corrupted middle frame** – validates that the second of three consecutive frames is rejected when its CRC is flipped
8. **Network profile: SysId/CompId corruption** – verifies that sys_id (byte 3) is part of the CRC-protected region; corrupting it causes CRC failure, proving routing fields are integrity-checked
9. **Partial frame across buffer boundary** – verifies `AccumulatingReader` reassembles a frame that was fed in two `add_data` chunks
10. **Streaming: Corrupted CRC detection** – tests CRC validation in byte-by-byte / accumulating mode
11. **Streaming: Garbage data handling** – verifies parser handles random invalid bytes without crashing
12. **Truncated frame detection** – tests handling of incomplete frames
13. **Zero-length buffer handling** – tests edge case of empty input

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

**Rust:**
```bash
# Build
cd tests/rust && cargo build

# Run
./tests/rust/target/debug/test_negative
```

## Expected Results

All negative tests should **PASS**, which means:
- Invalid input is correctly detected and rejected
- Parser returns `valid=false` (or `None` in Rust/Python) for corrupted/malformed data
- No crashes or undefined behavior occurs
- Error handling is consistent across implementations

## Test Output Format

Each test prints a matrix with one row per scenario:
```
========================================
NEGATIVE TESTS - <Language> Parser
========================================

Test Results Matrix:

Test Name                                          Result
================================================== ======
Bulk profile: Corrupted CRC                          PASS
Corrupted CRC detection                              PASS
...

========================================
Summary: 13/13 tests passed
========================================
```

## Integration with Test Suite

The negative tests are automatically integrated into the main test suite:
- Compiled during the compilation phase
- Executed in the "Negative Tests" phase
- Results included in test summary
- Counted toward total pass/fail metrics

## Adding New Negative Tests

To add a new negative test scenario, add it to **all seven** language files:

1. **C**: Add a new test function following the pattern in `test_negative.c`
2. **C++**: Add a new test function following the pattern in `test_negative.cpp`
3. **Python**: Add a new test function following the pattern in `test_negative.py`
4. **TypeScript**: Add a new test function following the pattern in `test_negative.ts`
5. **JavaScript**: Add a new test function following the pattern in `test_negative.js`
6. **C#**: Add a new test method following the pattern in `TestNegative.cs`
7. **Rust**: Add a new test function following the pattern in `test_negative.rs`

Add the test name to the list in `main()` / `Main()` in each file, keeping the list alphabetically sorted.

Add the test name to the list in `main()` / `Main()` in each file, keeping the list alphabetically sorted.

### Test Function Templates

**Rust:**
```rust
fn test_new_scenario() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    // corrupt data in specific way ...

    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}
```

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
