# Cross-Platform Pipe Tests

This directory contains cross-platform tests that verify struct-frame's ability to serialize and deserialize data across different language implementations using stdin/stdout piping.

## Overview

The cross-platform test works by:
1. Encoding a test message in one language and writing binary data to stdout
2. Piping that binary data to a decoder in another language via stdin
3. Verifying the decoded data matches expected values
4. Testing all combinations: each language encodes and pipes to all languages (including itself)

## Test Modes

### 1. Struct-Based Tests (No Framing)
**Status: NOT IMPLEMENTED**

Struct-based tests would encode raw struct bytes without any packet framing (no headers, checksums, or start bytes). However, this mode is currently not implemented due to limitations in how variable-length fields (strings and arrays) are serialized:

- **Python**: The `structured-classes` library's `pack()` method doesn't include variable-length fields
- **C**: Works correctly with explicit length/count prefixes in structs
- **TypeScript**: Has code generation issues

### 2. Framed Tests (With Headers/Checksums)
**Status: WORKING (C only)**

Framed tests use the default packet framing protocol:
- Start byte (0x90)
- Message ID
- Message payload
- Fletcher checksum (2 bytes)

**Current Implementation Status:**
- ✅ C: Fully working (encoding and decoding)
- ❌ Python: Variable-length fields not properly serialized
- ❌ TypeScript: Code generation bug with Array() method

## Running the Tests

### Run All Tests
```bash
cd tests
python3 cross_platform_test.py
```

### Run with Verbose Output
```bash
python3 cross_platform_test.py --verbose
```

### Run Only Framed Tests
```bash
python3 cross_platform_test.py --framed-only
```

### Run Only Struct Tests (will show not implemented)
```bash
python3 cross_platform_test.py --struct-only
```

## Test Programs

### Encoders
Programs that create a test message, serialize it, and write binary data to stdout:
- `c/encoder_framed.c` - C encoder (compiled to `encoder_framed`)
- `py/encoder_framed.py` - Python encoder (has limitations)
- `ts/encoder_framed.js` - TypeScript encoder (has bugs)
- `c/encoder_struct.c` - Struct-only encoder (not yet created)
- `py/encoder_struct.py` - Struct-only encoder (created but limited)

### Decoders
Programs that read binary data from stdin, deserialize it, and print decoded values:
- `c/decoder_framed.c` - C decoder (compiled to `decoder_framed`)
- `py/decoder_framed.py` - Python decoder (has limitations)
- `ts/decoder_framed.js` - TypeScript decoder (has bugs)
- `c/decoder_struct.c` - Struct-only decoder (not yet created)
- `py/decoder_struct.py` - Struct-only decoder (created but limited)

## Test Message Format

All tests use the `SerializationTestMessage` from `proto/serialization_test.proto`:

```protobuf
message SerializationTestMessage {
  option msgid = 204;
  
  uint32 magic_number = 1;           // 0xDEADBEEF
  string test_string = 2 [max_size=64];  // "Hello from <Language>!"
  float test_float = 3;              // 3.14159
  bool test_bool = 4;                // true
  repeated int32 test_array = 5 [max_size=5];  // [100, 200, 300]
}
```

## Output Format

Decoders print decoded values in a standardized format for verification:
```
magic_number=0xDEADBEEF
test_string=Hello from C!
test_float=3.14159
test_bool=True
test_array=100,200,300
```

## Known Limitations

### Python
The Python implementation uses the `structured-classes` library which has limitations:
- The `pack()` method doesn't properly serialize variable-length strings and arrays
- Only fixed-size primitive fields are included in the packed output
- This prevents Python from properly encoding messages with variable-length fields
- **Impact**: Python encoders cannot produce valid cross-platform test data

### TypeScript
The TypeScript generated code has a runtime error:
- The `.Array()` method doesn't exist on the typed-struct object
- This is a code generation bug in struct-frame's TypeScript generator
- The error occurs when loading the generated serialization_test.sf.js file
- **Impact**: TypeScript encoders and decoders cannot run

### C
The C implementation works correctly:
- Properly handles variable-length fields with length/count prefixes
- Encoding and decoding both work as expected
- Can create and consume cross-platform test data
- **Status**: ✅ Fully functional

## Test Results Example

```
============================================================
🔄 CROSS-PLATFORM PIPE TEST
============================================================
✅ C encoder/decoder available
⏭️  Python encoder/decoder not available
⏭️  Typescript encoder/decoder not available

============================================================
📦 STRUCT-BASED TESTS (NO FRAMING)
============================================================
⚠️  Struct-based tests are currently NOT IMPLEMENTED
⚠️  This is due to limitations in variable-length field serialization
⚠️  in the Python structured-classes library.
❌ TEST FAILED: Struct-based tests not implemented

============================================================
📦 FRAMED TESTS (WITH HEADERS/CHECKSUMS)
============================================================
ℹ️  Testing c→c (framed)...
✅ c→c (framed): PASS

============================================================
📊 TEST RESULTS SUMMARY
============================================================
Total tests: 1
Passed: 1
Failed: 0
Pass rate: 100.0%
🎉 ALL TESTS PASSED!
```

## Future Work

To fully implement cross-platform testing:

1. **Fix Python serialization**: 
   - Modify Python generator to properly handle variable-length fields
   - Or update encoder/decoder to manually serialize these fields
   
2. **Fix TypeScript code generation**:
   - Fix the `.Array()` method generation issue
   - Ensure typed-struct usage is correct
   
3. **Implement struct-based tests**:
   - Once serialization issues are resolved
   - Create struct-only encoder/decoder programs
   - Test raw struct bytes without framing

4. **Add more proto files**:
   - Test with basic_types.proto
   - Test with comprehensive_arrays.proto
   - Test with nested_messages.proto

## Debugging Failed Tests

When a test fails, the script prints detailed information:

```
🔍 Failure Details:
  Encoded by: c
  Decoded by: python
  Raw data length: 99 bytes
  Raw data (hex): 90cc...
  Raw data (bytes): [144, 204, ...]
```

This information helps diagnose:
- **Binary data issues**: Check if encoded data has correct length and format
- **Decoding problems**: Verify the decoder can parse the binary format
- **Data corruption**: Compare hex output between working and failing combinations

## Integration with Main Test Suite

The cross-platform test can be integrated into the main test runner (`run_tests.py`) by:

1. Adding a cross-platform test section
2. Running `cross_platform_test.py` as a subprocess
3. Collecting and reporting results alongside other tests

Example:
```python
def run_cross_platform_tests(self):
    """Run cross-platform pipe tests"""
    self.log("=== Running Cross-Platform Pipe Tests ===")
    
    cmd = [sys.executable, str(self.tests_dir / "cross_platform_test.py")]
    success, stdout, stderr = self.run_command(" ".join(cmd))
    
    if success:
        self.log("Cross-platform tests passed", "SUCCESS")
        self.results['cross_platform_pipe'] = True
        return True
    else:
        self.log("Cross-platform tests failed", "ERROR")
        self.results['cross_platform_pipe'] = False
        return False
```
