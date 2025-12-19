# Polyglot Parser Implementation Status

## Overview
This PR implements a polyglot parser that can detect and parse multiple frame types (Basic, Tiny, None) in the same stream, as requested in the issue.

## What Was Implemented

### Python Polyglot Parser (Complete)
- **Generator**: `src/struct_frame/polyglot_parser_py_gen.py`
- **Generated Code**: `src/struct_frame/boilerplate/py/polyglot_parser.py`
- **Test Suite**: `tests/py/test_polyglot.py`

#### Features:
1. **Frame Type Detection**: Automatically detects Basic (0x90), Tiny (0x70-0x78), or None frames
2. **Payload Type Identification**: Decodes payload type from start byte encoding
3. **State Machine**: Proper cascading through frame types as described in the issue
4. **Result Type**: `PolyglotParserResult` with frame metadata (frame_type, payload_type, format_name, msg_id, msg_data)
5. **Encoding Support**: Can encode messages in any frame/payload type combination

#### Architecture:
```python
PolyglotParser.parse_byte(byte) -> PolyglotParserResult
    |
    ├─> LOOKING_FOR_START
    |   ├─> 0x90? -> DETECTED_BASIC
    |   ├─> 0x70-0x78? -> DETECTED_TINY
    |   └─> else -> PARSING_NONE (if enabled)
    |
    ├─> DETECTED_BASIC
    |   ├─> Check second byte (0x70-0x78) for payload type
    |   ├─> Create appropriate Basic parser
    |   └─> Continue parsing until complete
    |
    └─> DETECTED_TINY
        ├─> Create appropriate Tiny parser
        └─> Continue parsing until complete
```

### Integration
- Updated `frame_parser_py_gen.py` to include polyglot parser in multi-file generation
- Updated `__init__.py` generation to export polyglot parser classes
- Added flexible import support (relative/absolute) for standalone usage
- All boilerplate files regenerated

## Critical Issue Discovered

During implementation and testing, a **fundamental mismatch** was discovered between the frame format proto definitions and the parser implementation:

### Frame Format Specification (frame_formats.proto)
```
// BASIC_DEFAULT - Basic frame with default payload (Recommended)
// Format: [START1=0x90] [START2=0x71] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
```

### Actual Parser Implementation (GenericFrameParser)
The parser state machine expects:
```
[START1] [START2] [MSG_ID] [LENGTH] [PAYLOAD] [CRC]
```

This affects **all frame formats** that have both LENGTH and MSG_ID fields (Default, Extended, etc.).

### Impact
- Polyglot parser is architecturally complete but cannot parse correctly due to this mismatch
- Existing test suite shows only 56/107 tests passing (52.3%)
- This is a pre-existing issue, not introduced by this PR

## What Needs to Be Done

### Immediate (To Complete This Feature)
1. **Decision Required**: Which specification is correct?
   - Option A: Update proto definitions to match parser (swap LEN and MSG_ID order)
   - Option B: Update parser to match proto definitions
   
2. **Apply the Fix**: Whichever option is chosen, update either:
   - `frame_formats.proto` message definitions, OR
   - `frame_parser_*_gen.py` state machine logic

3. **Test**: Once fixed, the polyglot parser should work correctly

### For Other Languages (Per Issue Requirements)
- **C++**: Needs variant-lite integration for return types (as suggested in issue)
- **TypeScript**: Can use union types for return values
- **C#**: Can use discriminated unions or inheritance
- **C**: Not required per issue ("does not need to implemented in plain c")

## Files Changed

### New Files
- `src/struct_frame/polyglot_parser_py_gen.py`
- `src/struct_frame/boilerplate/py/polyglot_parser.py`
- `tests/py/test_polyglot.py`

### Modified Files
- `src/struct_frame/frame_parser_py_gen.py` (added polyglot parser generation)
- All boilerplate files regenerated with updated generators

## Testing

Currently the test suite cannot pass due to the frame format ordering issue. Once that's resolved:

```python
# Test case example:
polyglot = PolyglotParser()
for byte in mixed_stream:
    result = polyglot.parse_byte(byte)
    if result.valid:
        print(f"Detected {result.frame_type} frame, payload type {result.payload_type}")
        print(f"Message ID: {result.msg_id}, Data: {result.msg_data}")
```

## Recommendations

1. **Fix the frame format ordering issue first** - this is blocking not just the polyglot parser but the entire frame parsing system
2. **Update proto definitions** (Option A) - easier than changing all parsers
3. **Complete testing** once the ordering is fixed
4. **Implement other languages** - C++, TypeScript, C# as per issue requirements

## Notes

- The polyglot parser implementation is sound and follows the architecture described in the issue
- Python was chosen first as the issue states "For python this should be straightforward"
- The architecture can be directly ported to other languages once the frame format issue is resolved
- No new dependencies were added for Python
- C++ will need variant-lite as mentioned in the issue
