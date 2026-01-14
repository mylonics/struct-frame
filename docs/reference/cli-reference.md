# CLI Reference

## Basic Usage

```bash
python -m struct_frame [proto_file] [options]
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

## SDK Options

| Flag | Description |
|------|-------------|
| `--sdk` | Include full SDK with network transports (C++, Python, TypeScript) |
| `--sdk_embedded` | Include embedded SDK without external dependencies (C++ only) |

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

## Generated Files

### C
- `<name>.sf.h` - Message definitions
- `struct_frame_parser.h` - Frame parsing utilities (if using framing)

### C++
- `<name>.sf.hpp` - Message definitions
- `FrameProfiles.hpp` - Frame parsing utilities (if using framing)
- `struct_frame_sdk/` - SDK files (if `--sdk` or `--sdk_embedded` used)

### TypeScript
- `<name>.sf.ts` - Message definitions and classes
- `struct_frame_parser.ts` - Frame parsing utilities (if using framing)
- `struct_frame_sdk/` - SDK files (if `--sdk` used)

### Python
- `<name>_sf.py` - Message definitions and classes
- `struct_frame_parser.py` - Frame parsing utilities (if using framing)
- `struct_frame_sdk/` - SDK files (if `--sdk` used)

### JavaScript
- `<name>.sf.js` - Message definitions and classes
- `struct_frame_parser.js` - Frame parsing utilities (if using framing)

### GraphQL
- `<name>.sf.graphql` - GraphQL schema definitions

### C#
- `<name>.sf.cs` - Message definitions and classes
- `StructFrameParser.cs` - Frame parsing utilities (if using framing)

