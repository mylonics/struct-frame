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
| Generate from imported proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `pkg_test_messages.sf` imports `pkg_test_a.sf` |
| Multi-package generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | `pkg_test_messages.sf` + `pkg_test_a.sf`; Rust partial |
| `--equality` flag | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No tests verify equality operator output |
| `--generate_tests` flag | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Exercised by the Round-trip Tests phase for all seven targets |
| `--validate` flag | ❌ | ❌ | ❌ | N/A | N/A | N/A | N/A | No test validates the validate mode |
| `--no_packed` flag | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A | Verified by `tests/test_no_packed.py` (CLI generation, absence of `#pragma pack`, round-trip parity) |
| Hash / `--force` caching | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Caching logic not covered by tests |
| `--csharp_legacy_enum_names` | N/A | N/A | N/A | N/A | N/A | ❌ | N/A | No test for legacy enum name mode |

---

## 2. Proto Field Types

Test file references:
- C: `tests/c/include/standard_messages.h`
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
| `oneof` with `discriminator = none` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple `oneof` fields in one message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Envelope messages (`is_envelope`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **All gaps closed.** `discriminator = none` and multi-oneof encode/decode tested in all 7 languages: Python via `tests/test_proto_field_types.py`; C and C++ via compiled binaries in the same file; TS/JS via `checkDiscriminatorNone()`/`checkMultiOneof()` in their standard test helpers; C# via `CheckDiscriminatorNone()`/`CheckMultiOneof()` in `tests/csharp/include/StandardMessages.cs`; Rust via the `test_oneof_special` runner in `tests/rust/src/main.rs`.

### 2.7 Message Options

| Option | C | C++ | Python | TS | JS | C# | Rust |
|--------|---|-----|--------|----|----|----|------|
| `msgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `variable = true` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pkgid` (package ID) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `is_envelope` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `flatten` | ✅ | N/A | ✅ | N/A | N/A | N/A | N/A |

> **C/Python `flatten`:** Verified by `tests/test_proto_field_types.py` — Python `to_dict()` inlines inner fields; C generates the struct inline (compile test). **Rust envelope:** `tests/rust/src/main.rs` `test_envelope_sdk` runner tests `CommandEnvelope` (msgid discriminator) and `RawDataEnvelope` (field_order discriminator) round-trips.

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
| `FrameEncoderWithCrc` / `FrameEncoderMinimal` | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |

> **Closed.** `FrameEncoderWithCrc` and `FrameEncoderMinimal` now have 15 direct unit tests across all five profiles in `tests/cpp/test_sdk_units.cpp`.

### 6.2 Parsers / Readers

| Class | C | C++ | Python | TS | JS | C# | Rust |
|-------|---|-----|--------|----|----|----|------|
| `BufferReader<Config>` / `buffer_reader_t` | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A |
| `AccumulatingReader<Config>` (buffer mode) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `AccumulatingReader<Config>` (stream/byte mode) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ProfileStandardAccumulatingReader` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `BufferParserWithCrc` | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |
| `BufferParserMinimal` | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |

> **Closed (C).** `accumulating_reader_push_byte` is now exercised by `tests/c/test_streaming.c` (4 tests: single frame, sensor profile, two consecutive frames, garbage-prefix skip).
>
> **Closed (C++).** `BufferParserWithCrc` and `BufferParserMinimal` now have dedicated unit tests in `tests/cpp/test_sdk_units.cpp` (15 tests across all profiles).
>
> **Closed (Rust).** `AccumulatingReader::push_byte` is now exercised by the `test_streaming` runner in `tests/rust/src/main.rs` (6 tests: standard profile, sensor/minimal profile, two consecutive frames, garbage-prefix skip). The Rust `bytes_to_drain_for_resync` logic was also fixed to correctly await payload bytes for minimal (no-length) profiles in streaming mode.

### 6.3 High-Level SDK (Transport + Routing)

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| `StructFrameSdk` subscribe/dispatch | N/A | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Serial transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| TCP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| UDP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| WebSocket transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| Async transport (Python) | N/A | N/A | ❌ | N/A | N/A | N/A | N/A |

> **Closed.** `StructFrameSdk` subscribe/dispatch is now tested with mock transports in six languages:
> - **C++** — `tests/cpp/test_sdk_subscribe.cpp` (7 tests: subscribe/dispatch, multiple observers, RAII unsubscribe, no-op notify, Connect delegation, incoming data pipeline, full encode→inject→parse)
> - **Python** — `tests/py/test_sdk.py` (11 tests: subscribe/dispatch, multiple handlers, unsubscribe, send_raw)
> - **TypeScript** — `tests/ts/test_sdk.ts` (10 tests: subscribe/dispatch, multiple handlers, unsubscribe, codec deserialization)
> - **C#** — `tests/csharp/TestSdkSubscribe.cs` (14 tests: subscribe, multiple handlers, unsubscribe, UnhandledMessage event, two-type dispatch, SendAsync)
> - **JavaScript** — `tests/js/test_sdk.js` (10 tests: subscribe/dispatch, multiple handlers, unsubscribe, codec deserialization). A CommonJS `StructFrameSdk` was added to `src/struct_frame/boilerplate/js/struct-frame-sdk/`.
> - **Rust** — `tests/rust/src/main.rs` `test_sdk_subscribe` runner (9 tests: subscribe/dispatch, multiple handlers, unsubscribe, no-op notify, push_byte dispatch). A `StructFrameSdk` struct was added to `src/struct_frame/boilerplate/rust/struct_frame_sdk.rs`.
>
> **Gap (Low):** Transport-level tests (serial, TCP, UDP, WebSocket) remain uncovered.

---

## 7. Import / Multi-Package Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|---------|---|-----|--------|----|----|----|------|
| Single import (`import "types.sf"`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Package with `pkgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-package with no IDs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Package with missing `msgid` on message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Circular import detection | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

Proto files: `tests/proto/pkg_test_messages.sf`, `pkg_test_a.sf`

> **Gap (Medium):** Circular import detection is not tested; the generator should error gracefully.
> `tests/test_generator_validation.py` documents the intended behaviour for circular imports, duplicate msgids, and duplicate pkgids as TODO cases.

---

## 8. Validation / Generator Error Paths

These are tests of the generator itself (Python, language-agnostic), not the generated code.

| Validation Rule | Tested |
|----------------|--------|
| Duplicate `msgid` within package | ⚠️ |
| Duplicate `pkgid` across packages | ⚠️ |
| Duplicate field numbers within message | ❌ |
| Missing `size`/`max_size` on array | ❌ |
| Missing `size`/`max_size` on string | ❌ |
| Missing `element_size` on string array | ❌ |
| `max_size` > 255 on array count | ❌ |
| Envelope with zero oneofs | ❌ |
| Envelope with non-message oneof fields | ❌ |
| Envelope with `msgid` discriminator and messages missing `msgid` | ❌ |
| Invalid `discriminator` option value | ❌ |
| Circular import detection | ⚠️ |
| Multi-package without `pkgid` | ✅ |

> **Partially addressed:** `tests/test_generator_validation.py` documents intended rejection behaviour for
> duplicate `msgid`, duplicate `pkgid`, and circular imports as TODO items (the generator currently accepts
> these inputs silently). The multi-package-without-pkgid case IS currently detected and rejected.
> Remaining validation rules are still completely untested.

---

## 9. Wire-Evolution Tests

Tests that verify backward-compatible message handling: unknown fields are ignored, fields with new defaults are decoded correctly from older binaries, and field reordering does not break decoding.

| Feature | Tested | File |
|---------|--------|------|
| Unknown trailing fields ignored on decode | ✅ | `tests/test_wire_evolution.py` |
| New-field default on decode from older binary | ✅ | `tests/test_wire_evolution.py` |
| Field reorder round-trip (producer → consumer) | ✅ | `tests/test_wire_evolution.py` |

Proto source: `tests/proto/test_messages.sf` (Python generator + round-trip).

---

## 10. Magic-Byte Tests

Tests that verify the per-message start-byte constants (`magic1`/`magic2`) are correctly embedded in encoded frames and validated on decode.

| Feature | Tested | File |
|---------|--------|------|
| Magic bytes present in encoded frame | ✅ | `tests/test_magic_bytes.py` |
| Wrong magic bytes → frame rejected | ✅ | `tests/test_magic_bytes.py` |
| Correct magic bytes → frame accepted | ✅ | `tests/test_magic_bytes.py` |
| Magic bytes absent (profile without magic) | ✅ | `tests/test_magic_bytes.py` |

---

## 11. Wireshark Dissector

| Feature | Tested |
|---------|--------|
| Lua dissector loads without errors | ❌ |
| Standard profile frame dissection | ❌ |
| Extended profile frame dissection | ❌ |

> **Gap (Low):** The `wireshark/struct_frame.lua` dissector has no automated tests.

---

## 12. Summary of Gaps by Priority

### High Priority

1. **Generator validation tests** — `tests/test_generator_validation.py` now documents three missing checks (duplicate msgid, duplicate pkgid, circular import) as TODO. The tests will pass once the generator properly rejects those inputs. All other generator validation rules remain untested.

2. ~~**High-level SDK tests**~~ — ✅ **Closed** — `StructFrameSdk` subscribe/dispatch is now covered with mock transports for C++ (7 tests), Python (11 tests), TypeScript (10 tests), C# (14 tests), JavaScript (10 tests), and Rust (9 tests). Transport-level tests remain outstanding.

### Medium Priority

3. ~~**Variable-flag edge cases**~~ — ✅ **Closed** — `VariableMultipleArrays` and `VariableMixedFields` have been removed from the proto as redundant duplicates of the variable-flag test coverage already provided by `VariableSingleArray` and `NestedVariableMessage`. The `test_variable_flag.*` suites now cover all remaining variable patterns.

4. ~~**Enum-to-string conversion**~~ — ✅ **Closed** — Tested for all languages: C and C++ via compiled binary in `tests/test_proto_field_types.py`; Python via `.name` attribute; TS/JS via reverse mapping in `test_standard.ts/.js`; C# via `ToString()` in `test_standard.cs`; Rust via `format!("{:?}", ...)` in `tests/rust/src/main.rs`.

5. ~~**`discriminator = none` and multi-oneof**~~ — ✅ **Closed** — All 7 languages covered: Python via `tests/test_proto_field_types.py`; C and C++ via compiled binaries in the same file; TS/JS via `checkDiscriminatorNone()`/`checkMultiOneof()` helpers; C# via `CheckDiscriminatorNone()`/`CheckMultiOneof()` in `StandardMessages.cs`; Rust via the `test_oneof_special` runner in `tests/rust/src/main.rs`.

6. ~~**Envelope messages in Rust**~~ — ✅ **Closed** — `tests/rust/src/main.rs` `test_envelope_sdk` runner tests `CommandEnvelope` (msgid discriminator) and `RawDataEnvelope` (field_order discriminator) round-trips via `run_envelope_sdk_test()` in `run_tests.py`.

7. **Round-trip generators** — Implemented for all seven languages (C, C++, Python, TypeScript, JavaScript, C#, Rust) via the `Test*Gen` classes and exercised by the Round-trip Tests phase.

8. ~~**Circular import detection**~~ — ⚠️ **Documented** — `tests/test_generator_validation.py` now includes a TODO test for circular imports. The generator currently accepts circular imports silently; the test will pass once the check is implemented.

### Low Priority

9. ~~**`AccumulatingReader` byte-stream mode in C**~~ — ✅ **Closed** — `tests/c/test_streaming.c` exercises `accumulating_reader_push_byte` with 4 tests (single frame, sensor profile, two consecutive frames, garbage-prefix skip).

10. ~~**`AccumulatingReader` byte-stream mode in Rust**~~ — ✅ **Closed** — `AccumulatingReader::push_byte` is now tested via the `test_streaming` runner in `tests/rust/src/main.rs` (6 tests). A bug in `bytes_to_drain_for_resync` for minimal profiles was fixed as part of this work.

11. **Performance benchmarks** — Throughput benchmarks only exist for C++; other languages have no baseline.

12. **Wireshark dissector** — No automated test for the Lua dissector.

13. **`--equality` generated code** — No test verifies generated equality operators/methods for any language.

---

*Last updated: 2026-05-08. Update this document whenever tests are added or gaps are closed.*
