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
| Generate from imported proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `sensor_with_import.sf` used |
| Multi-package generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | `package_a/b.sf`; Rust partial |
| `--equality` flag | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No tests verify equality operator output |
| `--generate_tests` flag | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Exercised by the Round-trip Tests phase for all seven targets |
| `--validate` flag | ❌ | ❌ | ❌ | N/A | N/A | N/A | N/A | No test validates the validate mode |
| `--no_packed` flag | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A | Verified by `tests/test_no_packed.py` (CLI generation, absence of `#pragma pack`, round-trip parity) |
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

Proto source: `tests/proto/test_messages.sf` (`BasicTypesMessage`, `ComprehensiveArrayMessage`, `SerializationTestMessage`)

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

Test file: `ComprehensiveArrayMessage` in `tests/proto/test_messages.sf`

### 2.4 Enums

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Enum definition and serialization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enum to string conversion | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **C/C++:** `tests/test_proto_field_types.py` compiles and runs a C/C++ binary that calls `{Pkg}{Enum}_to_string()` / `{Enum}_to_string()`. **Python:** `.name` attribute verified in the same standalone test. **TS/JS:** reverse-mapping (`Priority[Priority.High]` / key-lookup) verified in `test_standard.ts/.js`. **C#:** `Priority.HIGH.ToString()` verified in `test_standard.cs`. **Rust:** `format!("{:?}", Priority::HIGH)` verified in `tests/rust/src/main.rs`.

### 2.5 Nested Messages

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Nested struct round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.6 Oneof / Union Types

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `oneof` with `msgid` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `field_order` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `discriminator = none` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Multiple `oneof` fields in one message | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Envelope messages (`is_envelope`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

> **Gap (Partial):** `discriminator = none` and multi-oneof encode/decode tested in Python via `tests/test_proto_field_types.py`. C, C++, TS, JS, C#, Rust coverage still missing. Envelope tests still missing in Rust.

### 2.7 Message Options

| Option | C | C++ | Python | TS | JS | C# | Rust |
|--------|---|-----|--------|----|----|----|------|
| `msgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `variable = true` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pkgid` (package ID) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `is_envelope` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `flatten` | ✅ | N/A | ✅ | N/A | N/A | N/A | N/A |

> **C/Python `flatten`:** Verified by `tests/test_proto_field_types.py` — Python `to_dict()` inlines inner fields; C generates the struct inline (compile test). `is_envelope` still missing in Rust.

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
Proto: `tests/proto/extended_messages.sf`

### 3.3 Variable-Flag Test Suite (`test_variable_flag.*`)

Tests `option variable = true` truncation behaviour with `profile_bulk`.

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `variable = true` truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Single bounded array truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nested variable struct (variable parent + nested struct with variable fields) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple bounded arrays truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mixed fixed + variable fields | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_variable_flag.*`

### 3.4 Profiling / Performance Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Encode/decode throughput | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |
| Packed vs unpacked struct comparison | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |

Files: `tests/cpp/test_profiling.cpp`, `tests/cpp/test_profiling_generated.cpp`

> **Gap (Low):** Performance baseline tests only exist for C++. No benchmarks for Python, TypeScript, or Rust.

### 3.5 Per-Message Round-trip Tests (`test_roundtrip_<pkg>.*`)

Generated by `--generate_tests` and run by the **Round-trip Tests** phase of `tests/run_tests.py`.
For every message in every `.sf` file, fields are populated with deterministic dummy values,
the message is encoded through every frame profile, decoded via the streaming reader, and
compared against the original. (msg, profile) pairs that are intentionally incompatible
(e.g. `MSG_ID > 255` on a profile without `pkg_id`, or payload exceeding `Config::max_payload`)
are reported as **skipped** rather than failures.

| Profile | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `profile_standard` round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_sensor` round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_ipc` round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_bulk` round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_network` round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Generated files: `tests/generated/<lang>/test_roundtrip_<pkg>.{c,cpp,py,ts,js,cs,rs}` for all seven targets.

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

Each language's `test_negative.*` file runs 13 uniform scenarios. The test names printed at
runtime are the canonical identifiers used across all languages:

| Error Scenario (test name) | C | C++ | Python | TS | JS | C# | Rust |
|---------------------------|---|-----|--------|----|----|----|------|
| Bulk profile: Corrupted CRC | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrupted CRC detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Corrupted length field detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invalid message ID rejection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invalid start bytes detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Minimal profile: Truncated frame | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple frames: Corrupted middle frame | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Network profile: SysId/CompId corruption | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Partial frame across buffer boundary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Streaming: Corrupted CRC detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Streaming: Garbage data handling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Truncated frame detection | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zero-length buffer handling | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

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
| Single import (`import "types.sf"`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Package with `pkgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-package with no IDs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Package with missing `msgid` on message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Circular import detection | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Proto files: `tests/proto/package_a.sf`, `package_b.sf`, `pkg_test_*.sf`

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

1. **Generator validation tests** — All generator-level error rules (duplicate IDs, missing size options, invalid envelope definitions, etc.) are untested. A Python-based unit test file (`tests/py/test_generator.py` or similar) should cover these.

2. **High-level SDK tests** — `StructFrameSdk`, transport classes, and message routing have no automated tests in any language. Integration tests with mock transports are needed.

### Medium Priority

3. **Variable-flag edge cases** — `VariableMultipleArrays` and `VariableMixedFields` messages are defined in the proto but not exercised by `test_variable_flag.*` in any language.

4. ~~**Enum-to-string conversion**~~ — ✅ **Closed** — Tested for all languages: C and C++ via compiled binary in `tests/test_proto_field_types.py`; Python via `.name` attribute; TS/JS via reverse mapping in `test_standard.ts/.js`; C# via `ToString()` in `test_standard.cs`; Rust via `format!("{:?}", ...)` in `tests/rust/src/main.rs`.

5. **`discriminator = none` and multi-oneof** — ⚠️ **Partially closed** — Python encode/decode verified in `tests/test_proto_field_types.py`. C, C++, TS, JS, C#, Rust coverage still missing.

6. **Envelope messages in Rust** — Rust lacks envelope SDK test coverage.

7. **Round-trip generators** — Implemented for all seven languages (C, C++, Python, TypeScript, JavaScript, C#, Rust) via the `Test*Gen` classes and exercised by the Round-trip Tests phase.

8. **Circular import detection** — Not validated by any test.

### Low Priority

9. **`AccumulatingReader` byte-stream mode in C and Rust** — Only buffer-mode `add_data()` is tested; byte-by-byte `push_byte()` not exercised.

10. **Performance benchmarks** — Throughput benchmarks only exist for C++; other languages have no baseline.

11. **Wireshark dissector** — No automated test for the Lua dissector.

12. **`--equality` generated code** — No test verifies generated equality operators/methods for any language.

---

*Last updated: 2026-05-27. Update this document whenever tests are added or gaps are closed.*
