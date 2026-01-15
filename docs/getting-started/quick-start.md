# Quick Start

This guide shows you how to create a simple message, generate code, and use it in C++.

## 1. Create a Proto File

Create a file called `status.proto`:

```proto
package example;

message Status {
  option msgid = 1;
  uint32 id = 1;
  float value = 2;
}
```

## 2. Generate Code

Generate C++ code from the proto file:

```bash
python -m struct_frame status.proto --build_cpp --cpp_path generated/
```

This creates `generated/example.structframe.hpp` (note: package name is prefixed to the message name).

## 3. Use the Generated Code

Here's a simple C++ example that encodes and parses a message:

```cpp
#include "example.structframe.hpp"
#include <iostream>

int main() {
    // Create and populate a message (note: ExampleStatus, not Status)
    ExampleStatus status;
    status.id = 42;
    status.value = 3.14f;
    
    // The message is already in binary format - no encoding needed!
    // Just get a pointer to the struct
    uint8_t* buffer = (uint8_t*)&status;
    size_t size = sizeof(ExampleStatus);
    
    // Send buffer over serial, network, etc.
    // ...
    
    // On the receiving side, cast the buffer back to the struct
    ExampleStatus* received = (ExampleStatus*)buffer;
    std::cout << "ID: " << received->id << std::endl;
    std::cout << "Value: " << received->value << std::endl;
    
    return 0;
}
```

Compile and run:
```bash
g++ -std=c++17 -I generated/ main.cpp -o main
./main
```

That's it! The C/C++ implementation uses packed structs that map directly to memory, so there's no encoding or decoding overhead.

## Next Steps

- [Message Definitions](../basic-usage/message-definitions.md) - Learn how to write proto files
- [Language Examples](../basic-usage/language-examples.md) - See examples for other languages
- [Framing](../basic-usage/framing.md) - Add framing for reliable communication

