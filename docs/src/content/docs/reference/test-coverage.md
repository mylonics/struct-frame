---
title: Test Coverage
description: Maps every feature, message type, profile, and error path to its test coverage across all languages.
---

This document maps every feature, message type, frame profile, and error path to its test coverage. Each row cross-references the actual test files in `tests/`. **Keep this file updated** as new tests are added or coverage gaps are closed.

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Tested |
| ⚠️ | Partially tested |
| ❌ | Not tested |
| N/A | Not applicable to this language |

Languages tracked: **C**, **C++**, **Python**, **TypeScript (TS)**, **JavaScript (JS)**, **C#**, **Rust**

---

## 1. Code Generation (Generator Smoke Tests)

These tests verify that `src/main.py` generates valid, compilable output. They are exercised implicitly by every compile-and-run test.

| Feature | C | C++ | Python | TS | JS | C# | Rust | Notes |
|---------|---|-----|--------|----|----|----|------|-------|
| Generate from single proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | All test suites exercise generation |
| Generate from imported proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `sensor_with_import.proto` used |
| Multi-package generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | `package_a/b.proto`; Rust partial |
| `--equality` flag | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No tests verify equality operator output |
| `--generate_tests` flag | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Not tested in CI |
| `--validate` flag | ❌ | ❌ | ❌ | N/A | N/A | N/A | N/A | No test validates the validate mode |
| Hash / `--force` caching | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Caching logic not covered by tests |
| `--csharp_legacy_enum_names` | N/A | N/A | N/A | N/A | N/A | ❌ | N/A | No test for legacy enum name mode |

---

## 2. Proto Field Types

Test file references:
- C: `tests/c/include/standard_test_data.h`
- C++: `tests/cpp/include/standard_messages.hpp`
- Python: `tests/py/include/standard_messages.py`
- TS/JS: `tests/ts/include/standard_messages.ts` / `tests/js/include/standard_messages.js`
- C#: `tests/csharp/include/StandardMessages.cs`
- Rust: `tests/rust/src/main.rs`

Proto source: `tests/proto/test_messages.proto` (`BasicTypesMessage`, `ComprehensiveArrayMessage`, `SerializationTestMessage`)

### 2.1 Primitive Types

| Type | C | C++ | Python | TS | JS | C# | Rust |
|------|---|-----|--------|----|----|----|------|
| `int8` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `int16` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `int32` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `int64` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `uint8` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `uint16` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `uint32` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `uint64` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `float` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `double` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `bool` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.2 String Types

| Type | C | C++ | Python | TS | JS | C# | Rust |
|------|---|-----|--------|----|----|----|------|
| Fixed string (`size=N`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Variable string (`max_size=N`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.3 Arrays

| Type | C | C++ | Python | TS | JS | C# | Rust |
|------|---|-----|--------|----|----|----|------|
| Fixed array of primitives | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bounded array of primitives | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fixed array of strings | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bounded array of strings | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fixed array of enums | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bounded array of enums | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fixed array of nested messages | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bounded array of nested messages | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Test file: `ComprehensiveArrayMessage` in `tests/proto/test_messages.proto`

### 2.4 Enums

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Enum definition and serialization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enum to string conversion | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> **Gap (Medium):** No test verifies enum-to-string helpers for any language.

### 2.5 Nested Messages

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Nested struct round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.6 Oneof / Union Types

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `oneof` with `msgid` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `field_order` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `discriminator = none` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Multiple `oneof` fields in one message | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Envelope messages (`is_envelope`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

> **Gap (Medium):** `discriminator = none` and multi-oneof messages have no tests. Envelope tests missing in Rust.

### 2.7 Message Options

| Option | C | C++ | Python | TS | JS | C# | Rust |
|--------|---|-----|--------|----|----|----|------|
| `msgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `variable = true` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pkgid` (package ID) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `is_envelope` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `flatten` | ❌ | N/A | ❌ | N/A | N/A | N/A | N/A |

> **Gap (Medium):** `flatten` option not tested for Python or C.

---

## 3. Frame Profiles

### 3.1 Standard Test Suite (`test_standard.*`)

Tests all five profiles with a standard set of messages.

| Profile | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `profile_standard` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_sensor` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_ipc` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_bulk` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_network` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_standard.*`

### 3.2 Extended Test Suite (`test_extended.*`)

Tests extended message IDs (> 255) requiring Bulk/Network profiles.

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Extended msg ID (> 255) + `profile_bulk` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Extended msg ID (> 255) + `profile_network` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Payload > 255 bytes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_extended.*`  
Proto: `tests/proto/extended_messages.proto`

### 3.3 Variable-Flag Test Suite (`test_variable_flag.*`)

Tests `option variable = true` truncation behaviour with `profile_bulk`.

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `variable = true` truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Single bounded array truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple bounded arrays truncation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mixed fixed + variable fields | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_variable_flag.*`

> **Gap (Medium):** `VariableMultipleArrays` and `VariableMixedFields` message types defined in the proto are not exercised by any test.

### 3.4 Profiling / Performance Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Encode/decode throughput | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |
| Packed vs unpacked struct comparison | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |

Files: `tests/cpp/test_profiling.cpp`, `tests/cpp/test_profiling_generated.cpp`

> **Gap (Low):** Performance baseline tests only exist for C++. No benchmarks for Python, TypeScript, or Rust.

---

## 4. Cross-Language Compatibility Matrix

The test runner builds a compatibility matrix by having each language encode a frame and every other language decode it.

| Encoder \ Decoder | C | C++ | Python | TS | JS | C# | Rust |
|-------------------|---|-----|--------|----|----|----|------|
| C | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C++ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| TypeScript | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| JavaScript | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Rust | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |

Cross-platform testing is driven by the `CrossPlatformMatrixPlugin` in `tests/plugins.py`.

---

## 5. Error Handling / Negative Tests

Test files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_negative.*`

See `tests/NEGATIVE_TESTS.md` for full scenario descriptions.

Each language's `test_negative.*` file runs 10 uniform scenarios. The test names printed at
runtime are the canonical identifiers used across all languages:

| Error Scenario (test name) | C | C++ | Python | TS | JS | C# | Rust |
|---------------------------|---|-----|--------|----|----|----|------|
| Bulk profile: Corrupted CRC | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrupted CRC detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrupted length field detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invalid start bytes detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple frames: Corrupted middle frame | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Partial frame across buffer boundary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Streaming: Corrupted CRC detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Streaming: Garbage data handling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Truncated frame detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zero-length buffer handling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invalid message ID rejection | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Minimal profile (no CRC) error path | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Network profile (SysId/CompId filtering) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> **Gap (Low):** Invalid message ID rejection, Minimal-profile error paths, and
> Network-profile address filtering are not yet covered by any language.

---

## 6. SDK Classes

### 6.1 Encoders / Writers

| Class | C | C++ | Python | TS | JS | C# | Rust |
|-------|---|-----|--------|----|----|----|------|
| `BufferWriter<Config>` / `buffer_writer_t` | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A |
| `ProfileStandardWriter` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ProfileSensorWriter` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ProfileIpcWriter` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ProfileBulkWriter` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ProfileNetworkWriter` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `FrameEncoder<TProfile>` | N/A | N/A | N/A | N/A | N/A | ✅ | N/A |
| `FrameEncoderWithCrc` / `FrameEncoderMinimal` | N/A | ❌ | N/A | N/A | N/A | N/A | N/A |

> **Gap (Medium):** `FrameEncoderWithCrc` and `FrameEncoderMinimal` (low-level C++ encoders) have no direct unit tests.

### 6.2 Parsers / Readers

| Class | C | C++ | Python | TS | JS | C# | Rust |
|-------|---|-----|--------|----|----|----|------|
| `BufferReader<Config>` / `buffer_reader_t` | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A |
| `AccumulatingReader<Config>` (buffer mode) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `AccumulatingReader<Config>` (stream/byte mode) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `ProfileStandardAccumulatingReader` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `BufferParserWithCrc` | N/A | ❌ | N/A | N/A | N/A | N/A | N/A |
| `BufferParserMinimal` | N/A | ❌ | N/A | N/A | N/A | N/A | N/A |

> **Gap (Medium):** `BufferParserWithCrc` and `BufferParserMinimal` (low-level C++ parsers) have no dedicated unit tests.
>
> **Gap (Low):** C and Rust lack byte-by-byte streaming mode tests for `AccumulatingReader`.

### 6.3 High-Level SDK (Transport + Routing)

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `StructFrameSdk` subscribe/dispatch | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| Serial transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| TCP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| UDP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| WebSocket transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| Async transport (Python) | N/A | N/A | ❌ | N/A | N/A | N/A | N/A |

> **Gap (High):** The high-level SDK classes (`StructFrameSdk`, transports) have **no automated tests** in any language. These require network mocking or integration-test infrastructure.

---

## 7. Import / Multi-Package Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Single import (`import "types.proto"`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Package with `pkgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-package with no IDs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Package with missing `msgid` on message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Circular import detection | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Proto files: `tests/proto/package_a.proto`, `package_b.proto`, `pkg_test_*.proto`

> **Gap (Medium):** Circular import detection is not tested; the generator should error gracefully.

---

## 8. Validation / Generator Error Paths

These are tests of the generator itself (Python, language-agnostic), not the generated code.

| Validation Rule | Tested |
|----------------|--------|
| Duplicate `msgid` within package | ❌ |
| Duplicate `pkgid` across packages | ❌ |
| Duplicate field numbers within message | ❌ |
| Missing `size`/`max_size` on array | ❌ |
| Missing `size`/`max_size` on string | ❌ |
| Missing `element_size` on string array | ❌ |
| `max_size` > 255 on array count | ❌ |
| Envelope with zero oneofs | ❌ |
| Envelope with non-message oneof fields | ❌ |
| Envelope with `msgid` discriminator and messages missing `msgid` | ❌ |
| Invalid `discriminator` option value | ❌ |

> **Gap (High):** The generator validation rules are **completely untested**. A dedicated Python test suite for generator error paths is needed.

---

## 9. Wireshark Dissector

| Feature | Tested |
|---------|--------|
| Lua dissector loads without errors | ❌ |
| Standard profile frame dissection | ❌ |
| Extended profile frame dissection | ❌ |

> **Gap (Low):** The `wireshark/struct_frame.lua` dissector has no automated tests.

---

## 10. Summary of Gaps by Priority

### High Priority

1. **Rust negative / error-path tests** — `tests/rust/` has no `test_negative` equivalent. Every error scenario documented in `tests/NEGATIVE_TESTS.md` is missing for Rust.

2. **Generator validation tests** — All generator-level error rules (duplicate IDs, missing size options, invalid envelope definitions, etc.) are untested. A Python-based unit test file (`tests/py/test_generator.py` or similar) should cover these.

3. **High-level SDK tests** — `StructFrameSdk`, transport classes, and message routing have no automated tests in any language. Integration tests with mock transports are needed.

### Medium Priority

4. **Variable-flag edge cases** — `VariableMultipleArrays` and `VariableMixedFields` messages are defined in the proto but not exercised by `test_variable_flag.*` in any language.

5. **Enum-to-string conversion** — Not tested for any language despite generated helpers existing.

6. **`discriminator = none` and multi-oneof** — No test verifies the `none` discriminator or messages with more than one `oneof` field.

7. **Envelope messages in Rust** — Rust lacks `test_extended` coverage of envelope messages.

8. **C negative test gaps** — `tests/c/test_negative.c` covers only 6 scenarios vs 9 in C++. Missing: multiple invalid frames, invalid msg ID, malformed length, partial buffer boundary.

9. **Minimal-profile error paths** — No language tests error handling for Sensor/IPC profiles (which have no CRC or length field).

10. **Circular import detection** — Not validated by any test.

### Low Priority

11. **`discriminator = none` serialization** — Oneof with no discriminator not tested anywhere.

12. **`AccumulatingReader` byte-stream mode in C and Rust** — Only buffer-mode `add_data()` is tested; byte-by-byte `push_byte()` not exercised.

13. **Performance benchmarks** — Throughput benchmarks only exist for C++; other languages have no baseline.

14. **Wireshark dissector** — No automated test for the Lua dissector.

15. **`--equality` generated code** — No test verifies generated equality operators/methods for any language.

---

*Last updated: 2026-05-01. Update this document whenever tests are added or gaps are closed.*
