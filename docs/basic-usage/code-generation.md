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

## Generated Files

Each language generates:

- Message/struct definitions
- Serialization code (where applicable)
- Frame parsing utilities (if using framing)
- SDK files (if `--sdk` flag used)

See [CLI Reference](../reference/cli-reference.md) for complete details.

