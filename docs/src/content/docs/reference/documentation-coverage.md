---
title: Documentation Coverage
description: Maps every user-facing feature to its documentation status, identifies gaps, and provides a prioritised action plan.
---

This document maps every user-facing feature area to its documentation status, identifies gaps, and proposes priorities for follow-up work. **Keep this file updated** as new features are added or gaps are closed.

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Documented with examples |
| 📄 | Documented, no examples |
| ⚠️ | Partially documented |
| ❌ | Not documented |

---

## 1. Code Generation

### 1.1 Language Flags

| Feature | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| `--build_c` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--build_cpp` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--build_ts` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--build_py` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--build_js` | ✅ [CLI Reference](/reference/cli-reference/) | ⚠️ | JS has no dedicated language guide beyond the CLI table | Medium |
| `--build_csharp` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--build_gql` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No GraphQL usage guide or example | Medium |
| `--build_rust` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ [Rust SDK](/extended-features/rust-sdk/) | — | — |

### 1.2 Output Path Options

| Feature | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| `--c_path` | ✅ | ✅ | — | — |
| `--cpp_path` | ✅ | ✅ | — | — |
| `--ts_path` | ✅ | ✅ | — | — |
| `--py_path` | ✅ | ✅ | — | — |
| `--js_path` | ✅ | ⚠️ | No dedicated JS guide | Medium |
| `--gql_path` | ✅ | ❌ | No GraphQL guide | Medium |
| `--csharp_path` | ✅ | ✅ | — | — |
| `--rust_path` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ [Rust SDK](/extended-features/rust-sdk/) | — | — |
| `--catalog_path` | ✅ [CLI Reference](/reference/cli-reference/) | 📄 | `sf_compile.json` catalog mentioned; full schema not documented | Low |

### 1.3 SDK & Advanced Flags

| Feature | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| `--sdk` | ✅ [SDK Overview](/extended-features/sdk-overview/) | ✅ | — | — |
| `--sdk_embedded` | ✅ [C++ SDK](/extended-features/cpp-sdk/) | ✅ | — | — |
| `--equality` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No usage example showing equality operator output | Low |
| `--force` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | Example showing hash-based caching would help | Low |
| `--hash_path` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No example | Low |
| `--generate_tests` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No explanation of output format | Medium |
| `--validate` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No example showing validation errors | Low |
| `--debug` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No example of debug output | Low |
| `--no_packed` | ✅ [CLI Reference](/reference/cli-reference/), [Message Definitions](/basic-usage/message-definitions/) | ✅ | — | — |
| `--csharp_namespace` | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| `--csharp_sdk` | ✅ [C# SDK](/extended-features/csharp-sdk/) | ✅ | — | — |
| `--target_framework` | ✅ [CLI Reference](/reference/cli-reference/) | ❌ | No example showing framework targeting | Low |
| `--csharp_legacy_enum_names` | ❌ | ❌ | Migration flag not documented | Medium |

---

## 2. Proto Field Types

| Type | Docs | Examples | Gap | Priority |
|------|------|----------|-----|----------|
| `int8` | ✅ [Message Definitions](/basic-usage/message-definitions/) | ✅ | — | — |
| `int16` | ✅ | ✅ | — | — |
| `int32` | ✅ | ✅ | — | — |
| `int64` | ✅ | ✅ | — | — |
| `uint8` | ✅ | ✅ | — | — |
| `uint16` | ✅ | ✅ | — | — |
| `uint32` | ✅ | ✅ | — | — |
| `uint64` | ✅ | ✅ | — | — |
| `float` | ✅ | ✅ | — | — |
| `double` | ✅ | ✅ | — | — |
| `bool` | ✅ | ✅ | — | — |
| `string` (fixed) | ✅ | ✅ | — | — |
| `string` (variable, `max_size`) | ✅ | ✅ | — | — |
| `repeated` (fixed array) | ✅ | ✅ | — | — |
| `repeated` (bounded array) | ✅ | ✅ | — | — |
| `repeated string` | ✅ | ✅ | — | — |
| `repeated <message>` | ✅ | ✅ | — | — |
| `enum` | ✅ | ✅ | — | — |
| Nested messages | ✅ | ✅ | — | — |
| `oneof` (union) | ✅ | ✅ | — | — |
| `oneof` with `discriminator` option | ✅ | ✅ | — | — |
| Envelope messages (`is_envelope`) | ✅ | ✅ | — | — |
| `import` statements | ✅ | ✅ | — | — |
| `flatten` option | ⚠️ [Message Definitions](/basic-usage/message-definitions/#flatten-option) | ❌ | Documented for Python/GraphQL only; no cross-language example | Medium |

### 2.1 Message Options

| Option | Docs | Examples | Gap | Priority |
|--------|------|----------|-----|----------|
| `msgid` | ✅ | ✅ | — | — |
| `variable` | ✅ | ✅ | — | — |
| `pkgid` | ✅ | ✅ | — | — |
| `is_envelope` | ✅ | ✅ | — | — |

---

## 3. Framing System

### 3.1 Header Types

| Header | Docs | Examples | Gap | Priority |
|--------|------|----------|-----|----------|
| Basic (2 bytes) | ✅ [Framing Details](/basic-usage/framing-details/) | ✅ | — | — |
| Tiny (1 byte) | ✅ | ✅ | — | — |
| None (0 bytes) | ✅ | ✅ | — | — |

### 3.2 Payload Types

| Payload | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| Minimal | ✅ | ✅ | — | — |
| Default | ✅ | ✅ | — | — |
| Extended | ✅ | ✅ | — | — |
| ExtendedMultiSystemStream | ✅ | ⚠️ | Network profile shown but multi-node routing not exemplified | Medium |
| Other payload variants (SysComp, Seq, etc.) | ❌ | ❌ | Additional payload variants in `payload_types.hpp` are not documented | Low |

### 3.3 Frame Profiles

| Profile | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| Standard | ✅ | ✅ | — | — |
| Sensor | ✅ | ✅ | — | — |
| IPC | ✅ | ✅ | — | — |
| Bulk | ✅ | ✅ | — | — |
| Network | ✅ | ⚠️ | SysId/CompId/Seq fields usage not exemplified end-to-end | Medium |
| Custom profile creation | ⚠️ [Custom Features](/extended-features/custom-features/) | ❌ | Mentions concept but no code example for creating a custom profile | Medium |

### 3.4 Checksum

| Feature | Docs | Examples | Gap | Priority |
|---------|------|----------|-----|----------|
| Fletcher-16 algorithm | ✅ [Framing Details](/basic-usage/framing-details/) | ❌ | Algorithm explanation exists; no walkthrough | Low |
| Checksum failure handling | ⚠️ | ❌ | Negative test scenarios not described in docs | Medium |

---

## 4. SDK Classes

### 4.1 Encoders / Writers

| Class | Language | Docs | Examples | Gap | Priority |
|-------|----------|------|----------|-----|----------|
| `FrameEncoderWithCrc` | C++ | ⚠️ | ❌ | Not mentioned by name in docs | Medium |
| `FrameEncoderMinimal` | C++ | ⚠️ | ❌ | Not mentioned by name in docs | Medium |
| `BufferWriter<Config>` | C++ | ✅ | ✅ | — | — |
| `ProfileStandardWriter` et al. | C++ | ✅ | ✅ | — | — |
| `ProfileStandardWriter` | Python | ✅ | ✅ | — | — |
| `ProfileStandardWriter` | TypeScript | ✅ | ✅ | — | — |
| `FrameEncoder<TProfile>` | C# | ⚠️ [C# SDK](/extended-features/csharp-sdk/) | ❌ | Constructor usage not shown | Medium |

### 4.2 Parsers / Readers

| Class | Language | Docs | Examples | Gap | Priority |
|-------|----------|------|----------|-----|----------|
| `BufferParserWithCrc` | C++ | ❌ | ❌ | Not documented | Medium |
| `BufferParserMinimal` | C++ | ❌ | ❌ | Not documented | Medium |
| `BufferReader<Config>` | C++ | ✅ | ✅ | — | — |
| `AccumulatingReader<Config>` | C++ | ✅ | ✅ | — | — |
| `ProfileStandardAccumulatingReader` | C++ | ✅ | ✅ | — | — |
| `ProfileStandardAccumulatingReader` | Python | ✅ | ✅ | — | — |
| `ProfileStandardAccumulatingReader` | TypeScript | ✅ | ✅ | — | — |
| `AccumulatingReader` | Rust | ✅ [Rust SDK](/extended-features/rust-sdk/) | ✅ | — | — |
| `FrameDecoder` / parsers | C# | ⚠️ | ❌ | Types exist but not shown by name | Medium |

### 4.3 High-Level SDK

| Class | Language | Docs | Examples | Gap | Priority |
|-------|----------|------|----------|-----|----------|
| `StructFrameSdk` | C++ | ✅ [C++ SDK](/extended-features/cpp-sdk/) | ✅ | — | — |
| `StructFrameSdk` | Python | ✅ [Python SDK](/extended-features/python-sdk/) | ✅ | — | — |
| `StructFrameSdk` | TypeScript | ✅ [TypeScript SDK](/extended-features/typescript-sdk/) | ✅ | — | — |
| `StructFrameSdk` | C# | ✅ [C# SDK](/extended-features/csharp-sdk/) | ✅ | — | — |

### 4.4 Transports

| Transport | C++ | Python | TypeScript | C# | Gap | Priority |
|-----------|-----|--------|------------|----|-----|----------|
| Serial | ✅ | ✅ | ✅ | ✅ | — | — |
| TCP | ✅ | ✅ | ✅ | ✅ | — | — |
| UDP | ✅ | ✅ | ✅ | ✅ | — | — |
| WebSocket | ✅ | ⚠️ | ✅ | ✅ | Python WebSocket only mentioned; no example | Low |
| Async (Python) | ✅ [Python SDK](/extended-features/python-sdk/) | ✅ | N/A | N/A | — | — |

---

## 5. Language-Specific Generated Code

| Feature | C | C++ | Python | TypeScript | JavaScript | C# | GraphQL | Rust | Gap | Priority |
|---------|---|-----|--------|------------|------------|-----|---------|------|-----|----------|
| Message struct/class | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| Serialize / encode | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | — | — |
| Deserialize / decode | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | — | — |
| Enum to string | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ❌ | Rust not documented | Medium |
| Equality operators (`--equality`) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | N/A | ❌ | No docs for any language | Medium |
| `get_message_info` function | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | ❌ | Rust not documented | Medium |

---

## 6. Getting Started

| Topic | Docs | Examples | Gap | Priority |
|-------|------|----------|-----|----------|
| Installation | ✅ [Installation](/getting-started/installation/) | ✅ | — | — |
| Quick start | ✅ [Quick Start](/getting-started/quick-start/) | ✅ | — | — |
| Proto file basics | ✅ [Message Definitions](/basic-usage/message-definitions/) | ✅ | — | — |
| First code generation | ✅ [Code Generation](/basic-usage/code-generation/) | ✅ | — | — |

---

## 7. Reference

| Topic | Docs | Examples | Gap | Priority |
|-------|------|----------|-----|----------|
| CLI reference | ✅ [CLI Reference](/reference/cli-reference/) | ✅ | — | — |
| Build integration | ✅ [Build Integration](/reference/build-integration/) | ✅ | — | — |
| Development guide | ✅ [Development](/reference/development/) | ✅ | — | — |
| Testing guide | ✅ [Testing](/reference/testing/) | ✅ | — | — |
| Wireshark dissector | ❌ | ❌ | `wireshark/` directory and Lua dissector not documented in docs site | Low |

---

## 8. Summary of Gaps by Priority

### High Priority

1. **JavaScript guide** — JS generation is documented only via the CLI table; there is no language usage guide comparable to the Python/TypeScript pages.

2. **GraphQL guide** — No usage guide or example for `--build_gql` / GraphQL schema output.

### Medium Priority

3. **`--csharp_legacy_enum_names`** — Migration flag not documented anywhere.

4. **`--generate_tests` output format** — Flag is listed but the format of the generated test code is not explained.

5. **`BufferParserWithCrc` / `BufferParserMinimal`** — These lower-level C++ parser classes are not described by name or exemplified.

6. **Network profile end-to-end example** — The SysId/CompId/Seq fields in `ExtendedMultiSystemStream` payloads are not exemplified in a multi-node scenario.

7. **`flatten` option cross-language** — Currently noted as Python/GraphQL only; should clarify which languages support it.

8. **Equality operators** — `--equality` flag is listed but generated code examples are not shown for any language.

9. **Rust `enum_to_string` / `get_message_info`** — Minor Rust coverage gaps; core encode/decode is documented.

### Low Priority

10. **Custom payload variants** — `SysComp`, `Seq`, and other non-profile payload types in `payload_types.hpp` are not documented.

11. **`sf_compile.json` full schema** — The `--catalog_path` flag is now documented in the CLI reference but the full JSON schema is not described.

12. **Wireshark dissector** — The `wireshark/struct_frame.lua` dissector is present but not linked from the docs site.

13. **Fletcher-16 walkthrough** — Algorithm is named but no byte-level walkthrough is provided.

14. **`--equality`, `--force`, `--hash_path`, `--validate`, `--debug`, `--target_framework`** — Each of these flags lacks a code example showing the effect.

---

*Last updated: 2026-05-04. Update this document whenever a gap is closed or a new feature is added.*
