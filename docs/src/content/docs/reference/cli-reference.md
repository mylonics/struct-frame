---
title: CLI Reference
description: Complete reference for all struct-frame command-line flags and options.
---

## Basic Usage

```bash
python -m struct_frame [proto_file] [options]
python -m struct_frame diff OLD.sf NEW.sf [options]   # wire-compatibility check
```

## Code Generation Flags

| Flag | Description |
|------|-------------|
| `--build_c` | Generate C code |
| `--build_cpp` | Generate C++ code |
| `--build_ts` | Generate TypeScript code |
| `--build_py` | Generate Python code |
| `--build_js` | Generate JavaScript code |
| `--build_gql` | Generate GraphQL schema |
| `--build_csharp` | Generate C# code |
| `--build_rust` | Generate Rust code |

## Output Path Options

| Flag | Description | Default |
|------|-------------|---------|
| `--c_path PATH` | Output directory for C | `generated/c/` |
| `--cpp_path PATH` | Output directory for C++ | `generated/cpp/` |
| `--ts_path PATH` | Output directory for TypeScript | `generated/ts/` |
| `--py_path PATH` | Output directory for Python | `generated/py/` |
| `--js_path PATH` | Output directory for JavaScript | `generated/js/` |
| `--gql_path PATH` | Output directory for GraphQL | `generated/gql/` |
| `--csharp_path PATH` | Output directory for C# | `generated/csharp/` |
| `--rust_path PATH` | Output directory for Rust | `generated/rust/` |

## SDK Options

| Flag | Description |
|------|-------------|
| `--sdk` | Include full SDK with transports (C++, Python, TypeScript) |
| `--sdk_embedded` | Include embedded SDK without external dependencies (C++ only) |

## C# Options

| Flag | Description | Default |
|------|-------------|--------|
| `--csharp_namespace NS` | Root namespace for generated C# code | `StructFrame` |
| `--csharp_sdk` | Include C# transport implementations (Serial, TCP, UDP, WebSocket) | |
| `--target_framework TFM` | Target framework for generated `.csproj` | `net8.0` |

## Other Options

| Flag | Description |
|------|-------------|
| `--equality` | Generate equality comparison operators/methods for messages |
| `--force` | Force regeneration even if hash matches previous generation. The generation hash covers the schema structure **and** documentation (comments that reach generated output), the CLI parameters and the `--name_overrides` file, so editing a comment regenerates without `--force`. |
| `--hash_path PATH` | Path to store the generation hash file |
| `--generate_tests` | Generate test code with dummy values for round-trip verification |
| `--no_packed` | Generate code without packed structs. Treats every message as variable so that serialization is performed field-by-field. Useful on platforms that do not support struct packing or have different endianness/alignment requirements. |
| `--name_overrides FILE` | JSON file with explicit per-language name overrides for generated identifiers (see [Generated Names](/basic-usage/message-definitions/#generated-names)) |
| `--validate` | Validate the proto file without generating code |
| `--debug` | Enable debug output during code generation |
| `--catalog_path PATH` | Directory for the LSP type catalog file (`sf_compile.json`); default `generated/` |

## Schema Diff (Wire-Compatibility Check)

```bash
python -m struct_frame diff OLD.sf NEW.sf [--format text|json] [--fail-on breaking|rename|any] [--write-snapshot PATH]
```

Compares two schema revisions and reports whether the wire format is still compatible. Each side can be a `.sf` file (imports are followed) or a snapshot `.json` written by `--write-snapshot`, so a checked-in baseline can replace a second checkout. Differences are reported in separate groups:

| Group | Meaning | Examples |
|-------|---------|----------|
| **Wire-breaking** | The wire format changes | Changed message ID or package ID, changed magic bytes, field type/size/number changes, removed fields, fields added to the base layout, reordered fields or oneof variants (discriminator values follow declaration order), changed enum values, removed messages/enums/enum values, changed `variable`/discriminator/`max_size` options |
| **Wire-compatible** | Additive changes that older receivers tolerate | New messages and enums, new enum values, fields and oneof variants appended after `extensions_start`, changed defaults and `min_size` |
| **Source-only renames** | Same wire identity (message ID, field number, enum value, variant position), different source name | Renamed messages, fields, enums, enum values, oneofs and variants |
| **File moves** | A declaration moved to another source file | Splitting a schema into imported files |

Comments, documentation and the declaration order of messages and enums are ignored. A renamed message is reported as a rename, but because magic bytes include the *name* of embedded message types, messages that embed it also report a changed magic bytes value (breaking).

Exit status: `0` when nothing in the failing groups was found, `1` otherwise, `2` when a schema or snapshot cannot be loaded. By default only wire-breaking changes fail; `--fail-on rename` also fails on source-only renames and `--fail-on any` also fails on additive changes. File moves never fail.

```bash
# Gate a pull request on wire compatibility
python -m struct_frame diff main/messages.sf messages.sf

# Keep a baseline instead of a second checkout
python -m struct_frame diff messages.sf messages.sf --write-snapshot baseline.json
python -m struct_frame diff baseline.json messages.sf --format json
```

## Examples

Generate C code:
```bash
python -m struct_frame messages.proto --build_c
```

Generate multiple languages:
```bash
python -m struct_frame messages.proto --build_c --build_cpp --build_py
```

Custom output paths:
```bash
python -m struct_frame messages.proto --build_c --c_path src/generated/
```

Generate with SDK:
```bash
python -m struct_frame messages.proto --build_cpp --sdk
```

Generate without packed structs (portable encoding):
```bash
python -m struct_frame messages.proto --build_c --no_packed
```

When `--no_packed` is used, the C/C++ generators omit the `#pragma pack(push, 1)` /
`#pragma pack(pop)` directives around the struct definitions, and every message is
treated as if it had been declared with `option variable = true`. The generated
`<Type>_serialize` / `<Type>_deserialize` (and the C++ `serialize` / `deserialize`
methods) then read and write each field individually instead of relying on the
in-memory layout of the struct. This makes the generated code portable across
platforms that lack support for packed structs or have different
endianness/alignment requirements.

## Generated Files

### C
- `<name>.structframe.h` - Message definitions
- Frame utilities (frame_base.h, frame_headers.h, frame_profiles.h, etc.)

### C++
- `<name>.structframe.hpp` - Message definitions
- Frame utilities (frame_base.hpp, frame_headers.hpp, frame_profiles.hpp, etc.)
- `struct_frame_sdk/` - SDK files (if `--sdk` or `--sdk_embedded` used)

### TypeScript
- `<name>.structframe.ts` - Message definitions and classes
- Frame utilities (frame-base.ts, frame-headers.ts, frame-profiles.ts, etc.)
- `struct-frame-sdk/` - SDK files (if `--sdk` used)

### Python
- `struct_frame/generated/<name>.py` - Message definitions and classes
- Frame utilities (__init__.py, frame_base.py, frame_profiles.py, etc.)
- `struct_frame_sdk/` - SDK files (if `--sdk` used)

### JavaScript
- `<name>.structframe.js` - Message definitions and classes
- Frame parsing utilities

### GraphQL
- `<name>.structframe.graphql` - GraphQL schema definitions

### C#
- `<PackageName>/Enums/<EnumName>.cs` - Enum definitions (one per enum)
- `<PackageName>/Messages/<MessageName>.cs` - Message classes (one per message)
- `<PackageName>/MessageDefinitions.cs` - Message registry
- `<PackageName>/SdkInterface.cs` - SDK interface (always generated)
- `Framework/` - Framing, profiles, types, and SDK core
- `Framework/Sdk/Transports/` - Transport implementations (if `--csharp_sdk` used)
- `StructFrame.csproj` - Project file (always generated)

### Rust
- `<name>.structframe.rs` - Message structs with `StructFrameMessage` trait impl
- `Cargo.toml` - Crate manifest (always generated)
- `lib.rs` - Crate root re-exporting all modules (always generated)
- Frame SDK files: `frame_base.rs`, `frame_headers.rs`, `payload_types.rs`, `frame_profiles.rs`

