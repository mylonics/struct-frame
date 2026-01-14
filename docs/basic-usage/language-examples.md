# Language Examples

This page shows how to use generated code in each language.

## Proto Definition

Examples use this proto file:

```proto
package example;

message Status {
  option msgid = 1;
  uint32 id = 1;
  float value = 2;
}
```

Generate code:
```bash
python -m struct_frame status.proto --build_c --build_cpp --build_ts --build_py --build_js --build_csharp
```

## C

```c
#include "status.sf.h"

int main() {
    // Create a message
    Status msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // Message is already in binary format
    uint8_t* data = (uint8_t*)&msg;
    size_t size = sizeof(Status);
    
    // Send data over serial, network, etc.
    // ...
    
    // On receiving side, cast back to struct
    Status* received = (Status*)data;
    printf("ID: %u, Value: %.2f\n", received->id, received->value);
    
    return 0;
}
```

Compile:
```bash
gcc main.c -I generated/c/ -o main
```

## C++

```cpp
#include "status.sf.hpp"
#include <iostream>

int main() {
    // Create a message
    Status msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // Message is already in binary format
    uint8_t* data = reinterpret_cast<uint8_t*>(&msg);
    size_t size = sizeof(Status);
    
    // Send data over serial, network, etc.
    // ...
    
    // On receiving side, cast back to struct
    Status* received = reinterpret_cast<Status*>(data);
    std::cout << "ID: " << received->id << ", Value: " << received->value << std::endl;
    
    return 0;
}
```

Compile:
```bash
g++ -std=c++14 main.cpp -I generated/cpp/ -o main
```

## Python

```python
from status_sf import Status

# Create a message
msg = Status()
msg.id = 42
msg.value = 3.14

# Serialize to bytes
data = bytes(msg)

# Send data over serial, network, etc.
# ...

# Deserialize from bytes
received = Status.from_bytes(data)
print(f"ID: {received.id}, Value: {received.value}")
```

Run:
```bash
PYTHONPATH=generated/py python main.py
```

## TypeScript

```typescript
import { Status } from './generated/ts/status.sf';

// Create a message
const msg = new Status();
msg.id = 42;
msg.value = 3.14;

// Serialize to buffer
const data = msg.serialize();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = Status.deserialize(data);
console.log(`ID: ${received.id}, Value: ${received.value}`);
```

Compile and run:
```bash
npx tsc main.ts
node main.js
```

## JavaScript

```javascript
const { Status } = require('./generated/js/status.sf');

// Create a message
const msg = new Status();
msg.id = 42;
msg.value = 3.14;

// Serialize to buffer
const data = msg.serialize();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = Status.deserialize(data);
console.log(`ID: ${received.id}, Value: ${received.value}`);
```

Run:
```bash
node main.js
```

## C#

```csharp
using StructFrame;

class Program {
    static void Main() {
        // Create a message
        var msg = new Status {
            Id = 42,
            Value = 3.14f
        };
        
        // Serialize to bytes
        byte[] data = msg.ToBytes();
        
        // Send data over network, etc.
        // ...
        
        // Deserialize from bytes
        var received = Status.FromBytes(data);
        Console.WriteLine($"ID: {received.Id}, Value: {received.Value}");
    }
}
```

Compile and run:
```bash
dotnet build
dotnet run
```

## Arrays

Example with arrays:

```proto
message SensorData {
  option msgid = 2;
  repeated float readings = 1 [max_size=10];
}
```

=== "C"
    ```c
    SensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    ```

=== "C++"
    ```cpp
    SensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    ```

=== "Python"
    ```python
    data = SensorData()
    data.readings = [1.1, 2.2, 3.3]
    ```

=== "TypeScript"
    ```typescript
    const data = new SensorData();
    data.readings = [1.1, 2.2, 3.3];
    ```

=== "C#"
    ```csharp
    var data = new SensorData();
    data.Readings = new List<float> { 1.1f, 2.2f, 3.3f };
    ```

## Nested Messages

Example with nested messages:

```proto
message Position {
  double lat = 1;
  double lon = 2;
}

message Vehicle {
  option msgid = 3;
  uint32 id = 1;
  Position pos = 2;
}
```

=== "C"
    ```c
    Vehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "C++"
    ```cpp
    Vehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "Python"
    ```python
    v = Vehicle()
    v.id = 1
    v.pos.lat = 37.7749
    v.pos.lon = -122.4194
    ```

=== "TypeScript"
    ```typescript
    const v = new Vehicle();
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "C#"
    ```csharp
    var v = new Vehicle {
        Id = 1,
        Pos = new Position {
            Lat = 37.7749,
            Lon = -122.4194
        }
    };
    ```

