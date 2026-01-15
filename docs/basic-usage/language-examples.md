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
#include "example.structframe.h"

int main() {
    // Create a message
    ExampleStatus msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // Message is already in binary format
    uint8_t* data = (uint8_t*)&msg;
    size_t size = sizeof(ExampleStatus);
    
    // Send data over serial, network, etc.
    // ...
    
    // On receiving side, cast back to struct
    ExampleStatus* received = (ExampleStatus*)data;
    printf("ID: %u, Value: %.2f\n", received->id, received->value);
    
    return 0;
}
```

Compile:
```bash
gcc main.c -I generated/ -o main
```

## C++

```cpp
#include "example.structframe.hpp"
#include <iostream>

int main() {
    // Create a message
    ExampleStatus msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // Message is already in binary format
    uint8_t* data = reinterpret_cast<uint8_t*>(&msg);
    size_t size = sizeof(ExampleStatus);
    
    // Send data over serial, network, etc.
    // ...
    
    // On receiving side, cast back to struct
    ExampleStatus* received = reinterpret_cast<ExampleStatus*>(data);
    std::cout << "ID: " << received->id << ", Value: " << received->value << std::endl;
    
    return 0;
}
```

Compile:
```bash
g++ -std=c++17 main.cpp -I generated/ -o main
```

## Python

```python
from struct_frame.generated.example import ExampleStatus

# Create a message
msg = ExampleStatus(id=42, value=3.14)

# Serialize to bytes
data = msg.pack()

# Send data over serial, network, etc.
# ...

# Deserialize from bytes
received = ExampleStatus.create_unpack(data)
print(f"ID: {received.id}, Value: {received.value}")
```

Run:
```bash
PYTHONPATH=generated/ python main.py
```

## TypeScript

```typescript
import { ExampleStatus } from './generated/example.structframe';

// Create a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Get binary data
const data = msg.data();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = new ExampleStatus(data);
console.log(`ID: ${received.id}, Value: ${received.value}`);
```

Compile and run:
```bash
npx tsc main.ts
node main.js
```

## JavaScript

```javascript
const { ExampleStatus } = require('./generated/example.structframe');

// Create a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Get binary data
const data = msg.data();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = new ExampleStatus(data);
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
        var msg = new ExampleStatus {
            Id = 42,
            Value = 3.14f
        };
        
        // Serialize to bytes
        byte[] data = msg.ToBytes();
        
        // Send data over network, etc.
        // ...
        
        // Deserialize from bytes
        var received = ExampleStatus.FromBytes(data);
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
    ExampleSensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    ```

=== "C++"
    ```cpp
    ExampleSensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    ```

=== "Python"
    ```python
    data = ExampleSensorData()
    data.readings_count = 3
    data.readings[0] = 1.1
    data.readings[1] = 2.2
    data.readings[2] = 3.3
    ```

=== "TypeScript"
    ```typescript
    const data = new ExampleSensorData();
    data.readings_count = 3;
    data.readings[0] = 1.1;
    data.readings[1] = 2.2;
    data.readings[2] = 3.3;
    ```

=== "C#"
    ```csharp
    var data = new ExampleSensorData {
        ReadingsCount = 3
    };
    data.Readings[0] = 1.1f;
    data.Readings[1] = 2.2f;
    data.Readings[2] = 3.3f;
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
    ExampleVehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "C++"
    ```cpp
    ExampleVehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "Python"
    ```python
    v = ExampleVehicle(id=1)
    v.pos.lat = 37.7749
    v.pos.lon = -122.4194
    ```

=== "TypeScript"
    ```typescript
    const v = new ExampleVehicle();
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    ```

=== "C#"
    ```csharp
    var v = new ExampleVehicle {
        Id = 1,
        Pos = new ExamplePosition {
            Lat = 37.7749,
            Lon = -122.4194
        }
    };
    ```
