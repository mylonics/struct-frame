# Struct Frame

Struct Frame converts Protocol Buffer (.proto) files into serialization code for multiple languages. It generates C, C++, TypeScript, Python, JavaScript, C#, and GraphQL code from a single source.

## Installation

Install via pip:

```bash
pip install struct-frame
```

The package name is `struct-frame`, but the Python module uses `struct_frame`:

```bash
python -m struct_frame --help
```

## Quick Start

1. Create a `.proto` file:

```proto
package example;

message Status {
  option msgid = 1;
  uint32 id = 1;
  float value = 2;
}
```

2. Generate code:

```bash
# Python
python -m struct_frame status.proto --build_py --py_path generated/

# C
python -m struct_frame status.proto --build_c --c_path generated/

# Multiple languages
python -m struct_frame status.proto --build_c --build_py --build_ts
```

3. Use the generated code in your application.

## Language Support

| Language | Code Generation | SDK |
|----------|----------------|-----|
| C | ✓ | - |
| C++ | ✓ | ✓ |
| TypeScript | ✓ | ✓ |
| JavaScript | ✓ | ✓ |
| Python | ✓ | ✓ |
| C# | ✓ | ✓ |
| GraphQL | ✓ | - |

## Next Steps

- [Define Messages](basics/message-definitions.md) - Learn proto file syntax
- [Language Examples](basics/language-examples.md) - See usage examples for each language
- [Framing Guide](basics/framing.md) - Understand message framing for reliable communication

## Documentation Structure

### Basics
Essential information for getting started and common use cases.

### Advanced
Detailed information on framing, SDKs, and advanced features.

### Reference
Build integration, testing, and development guides.
