---
title: Quick Start
description: Create a simple message, generate code, and use it in C++.
---

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

This creates `generated/example.structframe.hpp`. In C++ the types live in the `structframe::example` namespace (in C the package name is prefixed to the type name instead, e.g. `ExampleStatus`).

## 3. Use the Generated Code

Here's a simple C++ example that encodes and parses a message:

```cpp
#include "example.structframe.hpp"
#include <cstring>
#include <iostream>

using structframe::example::Status;

int main() {
    // Create and populate a message
    Status status;
    status.id = 42;
    status.value = 3.14f;

    // Serialize into a byte buffer (a plain copy of the packed struct)
    uint8_t buffer[Status::MAX_SIZE];
    size_t size = status.serialize(buffer);

    // Send buffer over serial, network, etc.
    // ...

    // On the receiving side, deserialize from the buffer
    Status received;
    received.deserialize(buffer, size);
    std::cout << "ID: " << received.id << std::endl;
    std::cout << "Value: " << received.value << std::endl;

    return 0;
}
```

Compile and run:
```bash
g++ -std=c++20 -I generated/ main.cpp -o main
./main
```

That's it! The C/C++ implementation uses packed structs that map directly to memory, so serializing is a plain copy with no per-field encoding. (This relies on a little-endian host, which every mainstream target is; the headers refuse to compile on a big-endian one.)

## Next Steps

- [Message Definitions](/basic-usage/message-definitions/) - Learn how to write proto files
- [Language Examples](/basic-usage/language-examples/) - See examples for other languages
- [Framing](/basic-usage/framing/) - Add framing for reliable communication
