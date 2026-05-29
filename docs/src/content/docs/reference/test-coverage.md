---
title: Test Coverage
description: Maps every feature, message type, profile, and error path to its test coverage across all languages.
---

<!-- GENERATED FILE - DO NOT EDIT.
     Source of truth: tests/coverage_spec.py
     Regenerate with: python tests/gen_test_coverage.py -->

This document maps every feature, message type, frame profile, and error path to its test coverage. Each row cross-references the actual test files in `tests/`.

**This file is generated** by `tests/gen_test_coverage.py` from `tests/coverage_spec.py`. Do not edit it by hand -- update the spec and re-run the generator (`python tests/gen_test_coverage.py`). CI runs the generator in `--check` mode so the published table cannot drift from the tests that actually exist on disk.

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Tested |
| ⚠️ | Partially tested |
| ❌ | Not tested |
| N/A | Not applicable to this language |

Languages tracked: **C**, **C++**, **Python**, **TS**, **JS**, **C#**, **Rust**

---

## 1. Code Generation (Generator Smoke Tests)

These tests verify that `python -m struct_frame` generates valid, compilable output. They are exercised implicitly by every compile-and-run test.

| Feature | C | C++ | Python | TS | JS | C# | Rust | Notes |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| Generate from single proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | All test suites exercise generation |
| Generate from imported proto | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | `pkg_test_messages.sf` imports `pkg_test_a.sf` |
| Multi-package generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | `pkg_test_messages.sf` + `pkg_test_a.sf`; Rust partial |
| `--equality` flag | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | No tests verify equality operator output |
| `--generate_tests` flag | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Exercised by the Round-trip Tests phase for all seven targets |
| `--validate` flag | ❌ | ❌ | ❌ | N/A | N/A | N/A | N/A | No test validates the validate mode |
| `--no_packed` flag | ✅ | ✅ | N/A | N/A | N/A | N/A | N/A | Verified by `tests/test_no_packed.py` (CLI generation, absence of `#pragma pack`, round-trip parity) |
| Hash / `--force` caching | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | Caching logic not covered by tests |

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
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
| Fixed string (`size=N`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Variable string (`max_size=N`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.3 Arrays

| Type | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
| Enum definition and serialization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enum to string conversion | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **C/C++:** `tests/test_proto_field_types.py` compiles and runs a C/C++ binary that calls `{Pkg}{Enum}_to_string()` / `{Enum}_to_string()`. **Python:** `.name` attribute verified in the same standalone test. **TS/JS:** reverse-mapping (`Priority[Priority.High]` / key-lookup) verified in `test_standard.ts/.js`. **C#:** `Priority.HIGH.ToString()` verified in `test_standard.cs`. **Rust:** `format!("{:?}", Priority::HIGH)` verified in `tests/rust/src/main.rs`.

### 2.5 Nested Messages

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| Nested struct round-trip | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 2.6 Oneof / Union Types

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| `oneof` with `msgid` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `field_order` discriminator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `oneof` with `discriminator = none` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple `oneof` fields in one message | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Envelope messages (`is_envelope`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **All gaps closed.** `discriminator = none` and multi-oneof encode/decode tested in all 7 languages: Python via `tests/test_proto_field_types.py`; C and C++ via compiled binaries in the same file; TS/JS via `checkDiscriminatorNone()`/`checkMultiOneof()` in their standard test helpers; C# via `CheckDiscriminatorNone()`/`CheckMultiOneof()` in `tests/csharp/include/StandardMessages.cs`; Rust via the `test_oneof_special` runner in `tests/rust/src/main.rs`.

### 2.7 Message Options

| Option | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| `msgid` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `variable = true` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pkgid` (package ID) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `is_envelope` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `flatten` | ✅ | N/A | ✅ | N/A | N/A | N/A | N/A |

> **C/Python `flatten`:** Verified by `tests/test_proto_field_types.py` -- Python `to_dict()` inlines inner fields; C generates the struct inline (compile test). **Rust envelope:** `tests/rust/src/main.rs` `test_envelope_sdk` runner tests `CommandEnvelope` (msgid discriminator) and `RawDataEnvelope` (field_order discriminator) round-trips.

---

## 3. Frame Profiles

### 3.1 Standard Test Suite (`test_standard.*`)

Tests all five profiles with a standard set of messages.

| Profile | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| `profile_standard` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_sensor` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_ipc` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_bulk` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `profile_network` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_standard.*`

### 3.2 Extended Test Suite (`test_extended.*`)

Tests extended message IDs (> 255) requiring Bulk/Network profiles.

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| Extended msg ID (> 255) + `profile_bulk` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Extended msg ID (> 255) + `profile_network` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Payload > 255 bytes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_extended.*`  
Proto: `tests/proto/extended_messages.sf`

### 3.3 Variable-Flag Test Suite (`test_variable_flag.*`)

Tests `option variable = true` truncation behaviour with `profile_bulk`.

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| `variable = true` truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Single bounded array truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nested variable struct (variable parent + nested struct with variable fields) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple bounded arrays truncation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mixed fixed + variable fields | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_variable_flag.*`

### 3.4 Profiling / Performance Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
| Encode/decode throughput | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |
| Packed vs unpacked struct comparison | N/A | ✅ | N/A | N/A | N/A | N/A | N/A |

Files: `tests/cpp/test_profiling.cpp`, `tests/cpp/test_profiling_generated.cpp`

> **Gap (Low):** Performance baseline tests only exist for C++. No benchmarks for Python, TypeScript, or Rust.

### 3.5 Per-Message Round-trip Tests (`test_roundtrip_<pkg>.*`)

Generated by `--generate_tests` and run by the **Round-trip Tests** phase of `tests/run_tests.py`. For every message in every `.sf` file, fields are populated with deterministic dummy values, the message is encoded through every frame profile, decoded via the streaming reader, and compared against the original. (msg, profile) pairs that are intentionally incompatible (e.g. `MSG_ID > 255` on a profile without `pkg_id`, or payload exceeding `Config::max_payload`) are reported as **skipped** rather than failures.

| Profile | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
| C | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| C++ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| TypeScript | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| JavaScript | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Rust | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |

Cross-platform testing is driven by the encode/validate/decode matrix phases in `tests/run_tests.py`.

---

## 5. Error Handling / Negative Tests

Test files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_negative.*`

See `tests/NEGATIVE_TESTS.md` for full scenario descriptions.

Each language's `test_negative.*` file runs 13 uniform scenarios. The test names printed at runtime are the canonical identifiers used across all languages:

| Error Scenario (test name) | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|--------|--------|--------|--------|--------|--------|
| `StructFrameSdk` subscribe/dispatch | N/A | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Serial transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| TCP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| UDP transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| WebSocket transport | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | N/A |
| Async transport (Python) | N/A | N/A | ❌ | N/A | N/A | N/A | N/A |

> **Closed.** `StructFrameSdk` subscribe/dispatch is now tested with mock transports in six languages:
> - **C++** -- `tests/cpp/test_sdk_subscribe.cpp` (7 tests)
> - **Python** -- `tests/py/test_sdk.py` (11 tests)
> - **TypeScript** -- `tests/ts/test_sdk.ts` (10 tests)
> - **C#** -- `tests/csharp/TestSdkSubscribe.cs` (14 tests)
> - **JavaScript** -- `tests/js/test_sdk.js` (10 tests)
> - **Rust** -- `tests/rust/src/main.rs` `test_sdk_subscribe` runner (9 tests)
>
> **Gap (Low):** Transport-level tests (serial, TCP, UDP, WebSocket) remain uncovered.

---

## 7. Import / Multi-Package Tests

| Feature | C | C++ | Python | TS | JS | C# | Rust |
|--------|--------|--------|--------|--------|--------|--------|--------|
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
|--------|--------|
| Duplicate `msgid` within package | ⚠️ |
| Duplicate `pkgid` across packages | ⚠️ |
| Duplicate field numbers within message | ⚠️ |
| Missing `size`/`max_size` on array | ⚠️ |
| Missing `size`/`max_size` on string | ⚠️ |
| Missing `element_size` on string array | ⚠️ |
| `max_size` > 255 on array count | ⚠️ |
| Envelope with zero oneofs | ⚠️ |
| Envelope with non-message oneof fields | ⚠️ |
| Envelope with `msgid` discriminator and messages missing `msgid` | ⚠️ |
| Invalid `discriminator` option value | ⚠️ |
| Field number zero | ⚠️ |
| Circular import detection | ⚠️ |
| Multi-package without `pkgid` | ✅ |

> **Partially addressed:** `tests/test_generator_validation.py` documents intended rejection behaviour for every `⚠️` row above as a TODO test. Tests whose generator-side rejection is already implemented (or trivially inherited from the proto parser) are reported as `PASS`; the rest print `TODO` and exit 0, deferring the actual rejection logic in `src/struct_frame/` to follow-up PRs.

---

## 9. Wire-Evolution Tests

Tests that verify backward-compatible message handling: unknown fields are ignored, fields with new defaults are decoded correctly from older binaries, and field reordering does not break decoding.

| Feature | Tested | File |
|--------|--------|--------|
| Unknown trailing fields ignored on decode | ✅ | `tests/test_wire_evolution.py` |
| New-field default on decode from older binary | ✅ | `tests/test_wire_evolution.py` |
| Field reorder round-trip (producer → consumer) | ✅ | `tests/test_wire_evolution.py` |

Proto source: `tests/proto/test_messages.sf` (Python generator + round-trip).

---

## 10. Magic-Byte Tests

Tests that verify the per-message start-byte constants (`magic1`/`magic2`) are correctly embedded in encoded frames and validated on decode.

| Feature | Tested | File |
|--------|--------|--------|
| Magic bytes present in encoded frame | ✅ | `tests/test_magic_bytes.py` |
| Wrong magic bytes → frame rejected | ✅ | `tests/test_magic_bytes.py` |
| Correct magic bytes → frame accepted | ✅ | `tests/test_magic_bytes.py` |
| Magic bytes absent (profile without magic) | ✅ | `tests/test_magic_bytes.py` |

---

## 11. Wireshark Dissector

| Feature | Tested |
|--------|--------|
| Lua dissector loads without errors | ❌ |
| Standard profile frame dissection | ❌ |
| Extended profile frame dissection | ❌ |

> **Gap (Low):** The `wireshark/struct_frame.lua` dissector has no automated tests.

---

## Test Coverage Triage

Every `❌` and `⚠️` cell in the tables above is converted here into a tracked, linkable GitHub issue so coverage gaps are *owned* rather than merely listed. Triage ownership, retry budgets, and quarantine rules live in the [Test Stability Policy](test-stability).

Open gaps: **28**. Each **track ↗** link opens a pre-filled issue (labels `test-gap,coverage`); replace it with the real issue URL once filed. To see issues already filed, browse [`label:test-gap`](https://github.com/mylonics/struct-frame/issues?q=is%3Aissue+label%3Atest-gap).

| ID | Priority | Area | Section | Gap | Languages | Issue |
|----|----------|------|---------|-----|-----------|-------|
| `TC-8-12B585E8` | High | Missing size/max_size on string | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-12B585E8%5D+Missing+size%2Fmax_size+on+string+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-12B585E8%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Missing+size%2Fmax_size+on+string%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-21104668` | High | Duplicate pkgid across packages | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-21104668%5D+Duplicate+pkgid+across+packages+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-21104668%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Duplicate+pkgid+across+packages%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-451433DA` | High | Field number zero | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-451433DA%5D+Field+number+zero+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-451433DA%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Field+number+zero%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-5122C606` | High | Missing element_size on string array | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-5122C606%5D+Missing+element_size+on+string+array+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-5122C606%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Missing+element_size+on+string+array%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-61A87430` | High | max_size > 255 on array count | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-61A87430%5D+max_size+%3E+255+on+array+count+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-61A87430%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+max_size+%3E+255+on+array+count%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-692822CE` | High | Missing size/max_size on array | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-692822CE%5D+Missing+size%2Fmax_size+on+array+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-692822CE%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Missing+size%2Fmax_size+on+array%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-6EC79DC6` | High | Envelope with non-message oneof fields | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-6EC79DC6%5D+Envelope+with+non-message+oneof+fields+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-6EC79DC6%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Envelope+with+non-message+oneof+fields%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-8A6B0535` | High | Circular import detection | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-8A6B0535%5D+Circular+import+detection+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-8A6B0535%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Circular+import+detection%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-A72412DA` | High | Duplicate msgid within package | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-A72412DA%5D+Duplicate+msgid+within+package+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-A72412DA%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Duplicate+msgid+within+package%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-C64EBDDC` | High | Invalid discriminator option value | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-C64EBDDC%5D+Invalid+discriminator+option+value+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-C64EBDDC%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Invalid+discriminator+option+value%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-CC8F73E9` | High | Duplicate field numbers within message | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-CC8F73E9%5D+Duplicate+field+numbers+within+message+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-CC8F73E9%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Duplicate+field+numbers+within+message%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-DA7369C3` | High | Envelope with zero oneofs | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-DA7369C3%5D+Envelope+with+zero+oneofs+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-DA7369C3%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Envelope+with+zero+oneofs%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-8-F17A01A4` | High | Envelope with msgid discriminator and messages missing msgid | §8 | ⚠️ | generator | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-8-F17A01A4%5D+Envelope+with+msgid+discriminator+and+messages+missing+msgid+%28generator%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-8-F17A01A4%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Envelope+with+msgid+discriminator+and+messages+missing+msgid%0A-+%2A%2ASection%3A%2A%2A+Validation+%2F+Generator+Error+Paths%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+generator%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+High%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-1-C9896486` | Medium | Multi-package generation | §1 | ⚠️ | Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-1-C9896486%5D+Multi-package+generation+%28Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-1-C9896486%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Multi-package+generation%0A-+%2A%2ASection%3A%2A%2A+Code+Generation+%28Generator+Smoke+Tests%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+Medium%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-7-389A1C08` | Medium | Package with missing msgid on message | §7 | ⚠️ | Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-7-389A1C08%5D+Package+with+missing+msgid+on+message+%28Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-7-389A1C08%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Package+with+missing+msgid+on+message%0A-+%2A%2ASection%3A%2A%2A+Import+%2F+Multi-Package+Tests%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+Medium%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-7-A1151398` | Medium | Circular import detection | §7 | ❌ | C, C++, Python, TS, JS, C#, Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-7-A1151398%5D+Circular+import+detection+%28C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-7-A1151398%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Circular+import+detection%0A-+%2A%2ASection%3A%2A%2A+Import+%2F+Multi-Package+Tests%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Medium%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-7-F571F759` | Medium | Multi-package with no IDs | §7 | ⚠️ | Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-7-F571F759%5D+Multi-package+with+no+IDs+%28Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-7-F571F759%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Multi-package+with+no+IDs%0A-+%2A%2ASection%3A%2A%2A+Import+%2F+Multi-Package+Tests%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9A%A0%EF%B8%8F%0A-+%2A%2APriority%3A%2A%2A+Medium%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-1-AAE18D85` | Low | --validate flag | §1 | ❌ | C, C++, Python | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-1-AAE18D85%5D+--validate+flag+%28C%2C+C%2B%2B%2C+Python%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-1-AAE18D85%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+--validate+flag%0A-+%2A%2ASection%3A%2A%2A+Code+Generation+%28Generator+Smoke+Tests%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2C+C%2B%2B%2C+Python%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-1-CFB41A77` | Low | --equality flag | §1 | ❌ | C, C++, Python, TS, JS, C#, Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-1-CFB41A77%5D+--equality+flag+%28C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-1-CFB41A77%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+--equality+flag%0A-+%2A%2ASection%3A%2A%2A+Code+Generation+%28Generator+Smoke+Tests%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-1-F41DDFBD` | Low | Hash / --force caching | §1 | ❌ | C, C++, Python, TS, JS, C#, Rust | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-1-F41DDFBD%5D+Hash+%2F+--force+caching+%28C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-1-F41DDFBD%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Hash+%2F+--force+caching%0A-+%2A%2ASection%3A%2A%2A+Code+Generation+%28Generator+Smoke+Tests%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2C+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%2C+Rust%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-11-0B951945` | Low | Standard profile frame dissection | §11 | ❌ | wireshark | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-11-0B951945%5D+Standard+profile+frame+dissection+%28wireshark%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-11-0B951945%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Standard+profile+frame+dissection%0A-+%2A%2ASection%3A%2A%2A+Wireshark+Dissector%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+wireshark%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-11-0E6FA057` | Low | Lua dissector loads without errors | §11 | ❌ | wireshark | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-11-0E6FA057%5D+Lua+dissector+loads+without+errors+%28wireshark%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-11-0E6FA057%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Lua+dissector+loads+without+errors%0A-+%2A%2ASection%3A%2A%2A+Wireshark+Dissector%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+wireshark%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-11-866A0508` | Low | Extended profile frame dissection | §11 | ❌ | wireshark | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-11-866A0508%5D+Extended+profile+frame+dissection+%28wireshark%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-11-866A0508%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Extended+profile+frame+dissection%0A-+%2A%2ASection%3A%2A%2A+Wireshark+Dissector%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+wireshark%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-6-1AA40181` | Low | WebSocket transport | §6 · 6.3 | ❌ | C++, Python, TS, JS, C# | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-6-1AA40181%5D+WebSocket+transport+%28C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-6-1AA40181%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+WebSocket+transport%0A-+%2A%2ASection%3A%2A%2A+SDK+Classes+%2F+6.3+High-Level+SDK+%28Transport+%2B+Routing%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-6-2D690115` | Low | UDP transport | §6 · 6.3 | ❌ | C++, Python, TS, JS, C# | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-6-2D690115%5D+UDP+transport+%28C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-6-2D690115%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+UDP+transport%0A-+%2A%2ASection%3A%2A%2A+SDK+Classes+%2F+6.3+High-Level+SDK+%28Transport+%2B+Routing%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-6-785BEC06` | Low | Async transport (Python) | §6 · 6.3 | ❌ | Python | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-6-785BEC06%5D+Async+transport+%28Python%29+%28Python%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-6-785BEC06%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Async+transport+%28Python%29%0A-+%2A%2ASection%3A%2A%2A+SDK+Classes+%2F+6.3+High-Level+SDK+%28Transport+%2B+Routing%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+Python%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-6-8B65C22F` | Low | TCP transport | §6 · 6.3 | ❌ | C++, Python, TS, JS, C# | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-6-8B65C22F%5D+TCP+transport+%28C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-6-8B65C22F%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+TCP+transport%0A-+%2A%2ASection%3A%2A%2A+SDK+Classes+%2F+6.3+High-Level+SDK+%28Transport+%2B+Routing%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |
| `TC-6-929E31A2` | Low | Serial transport | §6 · 6.3 | ❌ | C++, Python, TS, JS, C# | [track ↗](https://github.com/mylonics/struct-frame/issues/new?title=%5Btest-gap+TC-6-929E31A2%5D+Serial+transport+%28C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%29&labels=test-gap%2Ccoverage&body=Tracked+from+the+Test+Coverage+matrix+%28%60TC-6-929E31A2%60%29.%0A%0A-+%2A%2AArea%3A%2A%2A+Serial+transport%0A-+%2A%2ASection%3A%2A%2A+SDK+Classes+%2F+6.3+High-Level+SDK+%28Transport+%2B+Routing%29%0A-+%2A%2ALanguages+with+a+gap%3A%2A%2A+C%2B%2B%2C+Python%2C+TS%2C+JS%2C+C%23%0A-+%2A%2ACurrent+status%3A%2A%2A+%E2%9D%8C%0A-+%2A%2APriority%3A%2A%2A+Low%0A%0AAdd+or+extend+tests+until+every+cell+for+this+row+is+%E2%9C%85+%28or+documented+N%2FA%29%2C+then+update+%60tests%2Fcoverage_spec.py%60.) |

---

## 13. CI / Robustness Infrastructure

Tier B/C of the test-suite-vs-protobuf gap analysis added the following CI surfaces. Each lives in `.github/workflows/`:

| Workflow | Purpose |
|----------|---------|
| `test.yml` (extended) | Primary suite + OS matrix (Linux, macOS), Python 3.9 / 3.11 / 3.13 matrix, Node 18 / 20 / 22 matrix, .NET 8 / 10 matrix, GCC vs Clang matrix |
| `sanitizers.yml` | ASan+UBSan and TSan jobs for the C/C++ suite, plus a Valgrind memcheck job for C binaries |
| `fuzz.yml` | Short per-push libFuzzer run on the C parser harness; atheris run on the Python parser |
| `coverage.yml` | `coverage.py` instrumentation of the Python generator + Codecov upload |

Sanitizer flags are injected by exporting `CC` / `CXX` / `CFLAGS` / `CXXFLAGS` / `LDFLAGS`, which `tests/run_tests.py` honours at every C/C++ compile site. No runner changes are needed to introduce additional sanitizer or coverage jobs.

### Fuzzing harnesses

| Harness | File | Tooling |
|---------|------|---------|
| C accumulating-reader | `tests/c/fuzz_parser.c` | libFuzzer + ASan/UBSan |
| Python `AccumulatingReader` | `tests/py/fuzz_parser.py` | atheris |
| Rust `AccumulatingReader` | `tests/rust/fuzz/fuzz_targets/parser.rs` (+ `Cargo.toml`) | cargo-fuzz |

### Property-based tests

`tests/test_property_roundtrip.py` uses Hypothesis to generate random instances of selected message classes and assert that Python encode → Python decode round-trips preserve equality across the Standard, Bulk, and Network profiles. Cross-language fan-out is tracked as a follow-up.

### Stability & flake policy

Retry budgets, quarantine rules, and triage ownership for flaky tests are documented in [Test Stability Policy](test-stability).

---

*Generated from `tests/coverage_spec.py` by `tests/gen_test_coverage.py`. Do not edit this file directly -- update the spec and regenerate.*
