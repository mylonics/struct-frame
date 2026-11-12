---
title: Code Generation
description: Generate serialization code from proto files using the struct-frame command-line tool.
---

Generate serialization code from proto files using the struct-frame command-line tool.

## Basic Usage

```bash
# Generate Python code
struct-frame messages.proto --build-py

# Generate C code
struct-frame messages.proto --build-c

# Generate multiple languages
struct-frame messages.proto --build-c --build-cpp --build-py --build-ts
```

## Language Flags

| Flag | Language | Output |
|------|----------|--------|
| `--build-c` | C | `<name>.structframe.h` |
| `--build-cpp` | C++ | `<name>.structframe.hpp` |
| `--build-ts` | TypeScript | `<name>.structframe.ts` (kebab-case file names, e.g. `pkg-test-a.structframe.ts`) |
| `--build-py` | Python | `<name>.py` (in the `structframe/` package) |
| `--build-js` | JavaScript | `<name>.structframe.js` (kebab-case file names) |
| `--build-csharp` | C# | `<PackageName>/Messages/*.cs`, `<PackageName>/Enums/*.cs` |
| `--build-gql` | GraphQL | `<package>.graphql` per package, plus a combined `schema.graphql` |
| `--build-rust` | Rust | `<name>.structframe.rs` |

### GraphQL type mapping

`uint8`/`int8`/`uint16`/`int16`/`int32` map to `Int`, `float`/`double` to `Float`, `bool` to `Boolean` and `string`/`bytes` to `String`. GraphQL's `Int` is a signed 32-bit integer, so `uint32`, `int64` and `uint64` map to the custom scalars `UInt32`, `Int64` and `UInt64`, which every generated schema document declares (`scalar UInt32`, ...); serialize them as strings or numbers in your resolvers as appropriate. Types are named `<Package><Type>`, message-scoped enums `<Package><Message><Enum>`.

## Output Paths

Default output is `generated/<language>/`. Customize with path options:

```bash
# Custom C output
struct-frame messages.proto --build-c --c-path src/generated/

# Multiple languages, different paths
struct-frame messages.proto \
  --build-c --c-path firmware/generated/ \
  --build-py --py-path server/generated/
```

## Common Patterns

### Single Language

```bash
struct-frame robot.proto --build-cpp --cpp-path include/
```

### Embedded + Server

```bash
struct-frame messages.proto \
  --build-c --c-path embedded/messages/ \
  --build-py --py-path server/messages/
```

### Frontend + Backend

```bash
struct-frame api.proto \
  --build-ts --ts-path frontend/src/generated/ \
  --build-py --py-path backend/generated/
```

### All Languages

```bash
struct-frame messages.proto \
  --build-c --build-cpp --build-ts --build-py --build-js --build-csharp --build-gql
```

## Generated Files

Each language generates:

- Message/struct definitions
- Serialization code (where applicable)
- Frame parsing utilities (if using framing)
- SDK files (if `--sdk` flag used)

See [CLI Reference](/reference/cli-reference/) for complete details.

