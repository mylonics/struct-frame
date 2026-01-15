# Struct Frame

Struct Frame converts Protocol Buffer (.proto) files into serialization code for multiple languages. It generates C, C++, TypeScript, Python, JavaScript, C#, and GraphQL code from a single source.

## Why Struct Frame

Struct Frame offers several advantages over other serialization systems:

- **Zero-copy encoding/decoding in C/C++**: Uses packed structs that map directly to memory. No encoding or decoding step required.
- **Flexible framing**: Multiple frame profiles for different scenarios, from zero-overhead trusted links to robust multi-node networks.
- **Nested messages and variable-length arrays**: Unlike Mavlink, supports complex message structures with nested messages and variable-length packing for arrays.
- **Smaller and simpler than Protobuf/Cap'n Proto**: Lower encoding cost and complexity. No schema evolution overhead.
- **Cross-platform**: Generate code for embedded C, server Python, and frontend TypeScript from a single proto definition.

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

## Quick Language Reference

=== "C++"
    ```cpp
    #include "example.structframe.hpp"
    
    // Create a message
    ExampleStatus msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // No encoding needed - use directly as bytes
    uint8_t* data = (uint8_t*)&msg;
    size_t size = sizeof(ExampleStatus);
    ```

=== "Python"
    ```python
    from struct_frame.generated.example import ExampleStatus
    
    # Create a message
    msg = ExampleStatus(id=42, value=3.14)
    
    # Serialize to bytes
    data = msg.pack()
    ```

=== "TypeScript"
    ```typescript
    import { ExampleStatus } from './example.structframe';
    
    // Create a message
    const msg = new ExampleStatus();
    msg.id = 42;
    msg.value = 3.14;
    
    // Get binary data
    const data = msg.data();
    ```

=== "C"
    ```c
    #include "example.structframe.h"
    
    // Create a message
    ExampleStatus msg = { .id = 42, .value = 3.14f };
    
    // Use directly as bytes
    uint8_t* data = (uint8_t*)&msg;
    size_t size = sizeof(ExampleStatus);
    ```

For detailed examples, see [Language Examples](basic-usage/language-examples.md).

## Next Steps

- [Quick Start](getting-started/quick-start.md) - Complete walkthrough with C++ example
- [Define Messages](basic-usage/message-definitions.md) - Learn proto file syntax
- [Language Examples](basic-usage/language-examples.md) - See detailed examples for each language
- [Framing Guide](basic-usage/framing.md) - Understand message framing for reliable communication

## Documentation Structure

### Getting Started
Installation and quick start guide.

### Basic Usage
Essential information for common use cases.

### Extended Features
Detailed information on framing, SDKs, and advanced features.

### Reference
Build integration, testing, and development guides.
