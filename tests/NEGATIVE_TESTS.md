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

All seven language implementations now share **31 identical test scenarios** (same names,
same behaviour), including a common `tryNext` drain contract, partial-pending checks,
diagnostic-counter assertions, minimal-profile resync scenarios, and a chunk-boundary
split sweep. All languages also carry the four package-corruption scenarios (bulk
`pkg_id`/`msg_id` corruption, cross-package rejection, network `pkg_id` corruption), so
every language runs **35 scenarios**; Python adds 5 status-machine/diagnostic extras (40).

### C Tests (`tests/c/test_negative.c`)
- **35 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios
- Tests buffer reader and accumulating reader (buffer mode) APIs
- Uses ProfileStandard, ProfileSensor, ProfileBulk, and ProfileNetwork configurations

### C++ Tests (`tests/cpp/test_negative.cpp`)
- **35 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios
- Tests both BufferReader and AccumulatingReader APIs
- Tests multiple frame profiles (Standard, Sensor, Bulk, Network)

### Python Tests (`tests/py/test_negative.py`)
- **40 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios + 5 Python-specific status-machine/diagnostic extras
- Tests both buffer and streaming modes
- Uses ProfileStandardReader, ProfileSensorReader, and ProfileNetworkReader

### TypeScript Tests (`tests/ts/test_negative.ts`)
- **35 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### JavaScript Tests (`tests/js/test_negative.js`)
- **35 test cases** identical to TypeScript
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### C# Tests (`tests/csharp/TestNegative.cs`)
- **35 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios
- Tests ProfileStandardWriter/Reader and AccumulatingReader
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

### Rust Tests (`tests/rust/src/test_negative.rs`)
- **35 test cases**: the 31 uniform scenarios + 4 package-corruption scenarios
- Tests BufferReader and AccumulatingReader APIs
- Tests multiple profiles (Standard, Sensor, Bulk, Network)

## Uniform Test Scenarios

All seven languages implement the following 31 scenarios with identical names:

1. **Buffer mode: recovers after CRC failure** – buffer-mode accumulating reader resyncs and returns the next valid frame after a CRC-failed frame
2. **Buffer reader: skips CRC-failed frame** – `BufferReader` advances past a CRC-failed frame instead of stalling on it
3. **Bulk profile: Corrupted CRC** – validates error detection on the Bulk (extended-header) profile
4. **Corrupted CRC detection** – verifies parser rejects frames with flipped CRC bytes
5. **Corrupted length field detection** – ensures length validation catches oversized claims
6. **Invalid message ID rejection** – frame with unknown msg_id byte (0xFF) is rejected because CRC validation no longer has valid magic values
7. **Invalid start bytes detection** – parser rejects frames with wrong start markers
8. **Minimal profile: Truncated frame** – ProfileSensor (no CRC/no length) rejects a buffer shorter than expected payload size
9. **Multiple frames: CRC error then valid frame** – CRC-failed middle frame is surfaced and parsing continues to the following valid frame
10. **Multiple frames: Corrupted middle frame** – second of three consecutive frames is rejected when its CRC is flipped
11. **Network profile: SysId/CompId corruption** – routing fields are CRC-protected; corruption causes CRC failure
12. **Partial frame across buffer boundary** – `AccumulatingReader` reassembles a frame split across two `add_data` chunks
13. **Split-buffer: CRC error status preserved** – CRC-failed frame assembled across chunks still reports explicit CRC-failure status
14. **Stream mode: recovers after garbage prefix** – byte-at-a-time mode resyncs after noise and still decodes the next valid frame
15. **Streaming: Corrupted CRC detection** – CRC validation in byte-by-byte/accumulating mode
16. **Streaming: Garbage data handling** – random invalid bytes are handled safely without crashes
17. **Truncated frame detection** – incomplete frames are rejected
18. **TryNext drain: CRC/resync + valid** – `tryNext` loop keeps making forward progress through CRC/resync events and still delivers valid frames
19. **TryNext partial pending contract** – when data is partial, `tryNext` reports no progress while exposing partial state; after completion it drains and clears partial state
20. **Zero-length buffer handling** – empty input edge case
21. **Buffer mode: CRC failure counters** – a CRC-failed frame consumed via `add_data` increments `cnt_crc_failures`, `cnt_failed_bytes` and `cnt_sync_recoveries` (same counter semantics as stream mode)
22. **Buffer mode: Sequence gap counted** – sequence gaps are detected on frames consumed via `add_data`, matching stream-mode behaviour
23. **Diagnostics: CRC failure counter** – `cnt_crc_failures` increments on a stream-mode CRC failure
24. **Diagnostics: Length error counter** – `cnt_len_errors` increments when the header length is outside the `[min_size, size]` range for the message
25. **Diagnostics: Reset diagnostics** – `reset_diagnostics()` clears all counters
26. **Diagnostics: Sequence gap counter** – `cnt_seq_gaps` increments when a sequence number is skipped (Network profile)
27. **Diagnostics: Sync recovery counter** – `cnt_sync_recoveries` increments when garbage bytes force a resync
28. **IPC buffer: unknown msg_id advances one byte** – on the None-header (IPC) profile an unknown msg_id advances exactly one byte (SyncRecovery) and the following valid frame is still delivered
29. **Sensor buffer: unknown msg_id resync** – on the Tiny-header (Sensor) profile an unknown msg_id triggers a scan to the next start byte instead of discarding the rest of the buffer
30. **Split sweep: two frames at every boundary** – two back-to-back frames are delivered intact when the stream is split into two `add_data` chunks at *every* possible offset
31. **Streaming: two frames byte-by-byte** – two back-to-back frames are both decoded in byte-at-a-time mode

### `tryNext` Contract (Unified)

- `tryNext` returns progress items while forward progress is possible:
  - valid frame
  - CRC-failed frame event
  - sync-recovery skip event
- `tryNext` returns no item only when the buffer is drained or only a trailing partial frame remains.
- Partial pending is observable through `hasPartial`/`partialSize` (or language-equivalent API).

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
- Parser returns `valid=false` for corrupted/malformed frames, and `tryNext` loops continue draining through CRC/resync events
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
Summary: 20/20 tests passed
========================================
```

(The example above shows a 24-scenario language; the exact total varies per language —
see the per-file counts under [Test Files](#test-files).)

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
