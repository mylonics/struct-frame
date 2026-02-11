# Code Generation

Generate serialization code from proto files using the struct-frame command-line tool.

## Basic Usage

```bash
# Generate Python code
python -m struct_frame messages.proto --build_py

# Generate C code
python -m struct_frame messages.proto --build_c

# Generate multiple languages
python -m struct_frame messages.proto --build_c --build_cpp --build_py --build_ts
```

## Language Flags

| Flag | Language | Output |
|------|----------|--------|
| `--build_c` | C | `<name>.structframe.h` |
| `--build_cpp` | C++ | `<name>.structframe.hpp` |
| `--build_ts` | TypeScript | `<name>.structframe.ts` |
| `--build_py` | Python | `<name>.py` (in `struct_frame/generated/`) |
| `--build_js` | JavaScript | `<name>.structframe.js` |
| `--build_csharp` | C# | `<name>.structframe.cs` |
| `--build_gql` | GraphQL | `<name>.structframe.graphql` |

## Output Paths

Default output is `generated/<language>/`. Customize with path options:

```bash
# Custom C output
python -m struct_frame messages.proto --build_c --c_path src/generated/

# Multiple languages, different paths
python -m struct_frame messages.proto \
  --build_c --c_path firmware/generated/ \
  --build_py --py_path server/generated/
```

## Common Patterns

### Single Language

```bash
python -m struct_frame robot.proto --build_cpp --cpp_path include/
```

### Embedded + Server

```bash
python -m struct_frame messages.proto \
  --build_c --c_path embedded/messages/ \
  --build_py --py_path server/messages/
```

### Frontend + Backend

```bash
python -m struct_frame api.proto \
  --build_ts --ts_path frontend/src/generated/ \
  --build_py --py_path backend/generated/
```

### All Languages

```bash
python -m struct_frame messages.proto \
  --build_c --build_cpp --build_ts --build_py --build_js --build_csharp --build_gql
```

### Without Packed Structs (C/C++)

By default, generated C and C++ code uses `#pragma pack(1)` for struct definitions, allowing direct memory-mapped serialization via `memcpy`. Use `--no_packed` to disable this and generate field-by-field serialize/deserialize functions instead:

```bash
python -m struct_frame messages.proto --build_c --build_cpp --no_packed
```

This is useful when:

- Your platform or compiler does not support packed structs
- You want to avoid unaligned memory access penalties
- You need portable code that does not rely on compiler-specific packing behavior

When `--no_packed` is used, all non-variable messages get the same field-by-field serialization approach that variable messages already use. The wire format remains identical, so no_packed and packed code can interoperate.

## Generated Files

Each language generates:

- Message/struct definitions
- Serialization code (where applicable)
- Frame parsing utilities (if using framing)
- SDK files (if `--sdk` flag used)

See [CLI Reference](../reference/cli-reference.md) for complete details.

