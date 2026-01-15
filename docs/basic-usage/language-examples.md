# Language Examples

This page shows how to use generated code in each language with the standardized serialize/deserialize API.

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

## Using Frame Profiles

Frame profiles provide complete framing and parsing functionality. This is the **recommended approach** for most applications.

### Python with Profiles

```python
from generated.example import ExampleStatus
from generated.frame_profiles import (
    ProfileStandardWriter, 
    ProfileStandardAccumulatingReader
)

# Create and serialize a message
msg = ExampleStatus(id=42, value=3.14)

# Encode with frame profile
writer = ProfileStandardWriter(1024)
bytes_written = writer.write(msg)
frame_data = writer.data()

# Parse received frames
reader = ProfileStandardAccumulatingReader()
reader.add_data(frame_data)

# Deserialize using FrameMsgInfo
result = reader.next()
if result:
    decoded_msg = ExampleStatus.deserialize(result)  # Pass FrameMsgInfo directly
    print(f"ID: {decoded_msg.id}, Value: {decoded_msg.value}")
```

### TypeScript with Profiles

```typescript
import { ExampleStatus } from './generated/example.structframe';
import { 
    ProfileStandardWriter, 
    ProfileStandardAccumulatingReader 
} from './generated/frame-profiles';

// Create and serialize a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Encode with frame profile
const writer = new ProfileStandardWriter(1024);
writer.write(msg);
const frameData = writer.data();

// Parse received frames
const reader = new ProfileStandardAccumulatingReader();
reader.addData(frameData);

// Deserialize using FrameMsgInfo
const result = reader.next();
if (result) {
    const decodedMsg = ExampleStatus.deserialize(result);  // Pass FrameMsgInfo directly
    console.log(`ID: ${decodedMsg.id}, Value: ${decodedMsg.value}`);
}
```

### C++ with Profiles

```cpp
#include "example.structframe.hpp"
#include "FrameProfiles.hpp"

// Create and serialize a message
ExampleStatus msg;
msg.id = 42;
msg.value = 3.14f;

// Encode with frame profile
uint8_t buffer[1024];
FrameParsers::ProfileStandardWriter writer(buffer, sizeof(buffer));
writer.write(msg);

// Parse received frames
FrameParsers::ProfileStandardAccumulatingReader reader;
reader.add_data(buffer, writer.size());

// Deserialize using FrameMsgInfo
if (auto result = reader.next()) {
    ExampleStatus decoded_msg;
    decoded_msg.deserialize(result);  // Pass FrameMsgInfo directly
    std::cout << "ID: " << decoded_msg.id << ", Value: " << decoded_msg.value << std::endl;
}
```

### C# with Profiles

```csharp
using StructFrame;

// Create and serialize a message
var msg = new ExampleStatus {
    Id = 42,
    Value = 3.14f
};

// Encode with frame profile
var writer = new ProfileStandardWriter(1024);
writer.Write(msg);
var frameData = writer.Data();

// Parse received frames
var reader = new ProfileStandardAccumulatingReader();
reader.AddData(frameData);

// Deserialize using FrameMsgInfo
var result = reader.Next();
if (result != null) {
    var decodedMsg = ExampleStatus.Deserialize(result);  // Pass FrameMsgInfo directly
    Console.WriteLine($"ID: {decodedMsg.Id}, Value: {decodedMsg.Value}");
}
```

### JavaScript with Profiles

```javascript
const { ExampleStatus } = require('./generated/example.structframe');
const { 
    ProfileStandardWriter, 
    ProfileStandardAccumulatingReader 
} = require('./generated/frame-profiles');

// Create and serialize a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Encode with frame profile
const writer = new ProfileStandardWriter(1024);
writer.write(msg);
const frameData = writer.data();

// Parse received frames
const reader = new ProfileStandardAccumulatingReader();
reader.addData(frameData);

// Deserialize using FrameMsgInfo
const result = reader.next();
if (result) {
    const decodedMsg = ExampleStatus.deserialize(result);  // Pass FrameMsgInfo directly
    console.log(`ID: ${decodedMsg.id}, Value: ${decodedMsg.value}`);
}
```

## Direct Message Serialization

For cases where you need direct access to message bytes without framing:

### Python

```python
from generated.example import ExampleStatus

# Create a message
msg = ExampleStatus(id=42, value=3.14)

# Serialize to bytes
data = msg.serialize()

# Send data over serial, network, etc.
# ...

# Deserialize from bytes
received = ExampleStatus.deserialize(data)
print(f"ID: {received.id}, Value: {received.value}")
```

### TypeScript

```typescript
import { ExampleStatus } from './generated/example.structframe';

// Create a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Serialize to buffer
const data = msg.serialize();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = ExampleStatus.deserialize(data);
console.log(`ID: ${received.id}, Value: ${received.value}`);
```

### JavaScript

```javascript
const { ExampleStatus } = require('./generated/example.structframe');

// Create a message
const msg = new ExampleStatus();
msg.id = 42;
msg.value = 3.14;

// Serialize to buffer
const data = msg.serialize();

// Send data over network, etc.
// ...

// Deserialize from buffer
const received = ExampleStatus.deserialize(data);
console.log(`ID: ${received.id}, Value: ${received.value}`);
```

### C++

```cpp
#include "example.structframe.hpp"
#include <iostream>

int main() {
    // Create a message
    ExampleStatus msg;
    msg.id = 42;
    msg.value = 3.14f;
    
    // Serialize to buffer
    uint8_t buffer[1024];
    msg.serialize(buffer);
    size_t size = sizeof(ExampleStatus);
    
    // Send data over serial, network, etc.
    // ...
    
    // Deserialize from buffer
    ExampleStatus received;
    received.deserialize(buffer, size);
    std::cout << "ID: " << received.id << ", Value: " << received.value << std::endl;
    
    return 0;
}
```

### C#

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
        byte[] data = msg.Serialize();
        
        // Send data over network, etc.
        // ...
        
        // Deserialize from bytes
        var received = ExampleStatus.Deserialize(data);
        Console.WriteLine($"ID: {received.Id}, Value: {received.Value}");
    }
}
```

## Communication Examples

### Serial Communication (Python)

```python
import serial
from generated.example import ExampleStatus
from generated.frame_profiles import ProfileStandardAccumulatingReader

# Setup serial connection
ser = serial.Serial('/dev/ttyUSB0', 115200)
reader = ProfileStandardAccumulatingReader()

while True:
    if ser.in_waiting:
        # Read available data
        data = ser.read(ser.in_waiting)
        reader.add_data(data)
        
        # Process all complete frames
        while True:
            result = reader.next()
            if result is None or not result.valid:
                break
            
            # Deserialize using FrameMsgInfo
            msg = ExampleStatus.deserialize(result)
            print(f"Received: ID={msg.id}, Value={msg.value}")
```

### Streaming Parser (C++)

```cpp
#include "example.structframe.hpp"
#include "FrameProfiles.hpp"

// Byte-by-byte streaming parser for UART/serial
FrameParsers::ProfileStandardAccumulatingReader reader;

void on_byte_received(uint8_t byte) {
    if (auto result = reader.push_byte(byte)) {
        // Complete message received - result is valid due to operator bool()
        ExampleStatus msg;
        msg.deserialize(result);
        std::cout << "ID: " << msg.id << std::endl;
    }
}
```

### TCP Socket (TypeScript)

```typescript
import * as net from 'net';
import { ExampleStatus } from './generated/example.structframe';
import { ProfileStandardAccumulatingReader } from './generated/frame-profiles';

const client = net.createConnection({ port: 8080 });
const reader = new ProfileStandardAccumulatingReader();

client.on('data', (data: Buffer) => {
    reader.addData(data);
    
    let result;
    while ((result = reader.next()) && result.valid) {
        const msg = ExampleStatus.deserialize(result);
        console.log(`ID: ${msg.id}, Value: ${msg.value}`);
    }
});
```

### WebSocket (JavaScript)

```javascript
const { ExampleStatus } = require('./generated/example.structframe');
const { ProfileStandardAccumulatingReader } = require('./generated/frame-profiles');
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8080');
const reader = new ProfileStandardAccumulatingReader();

ws.on('message', (data) => {
    reader.addData(Buffer.from(data));
    
    let result;
    while ((result = reader.next()) && result.valid) {
        const msg = ExampleStatus.deserialize(result);
        console.log(`ID: ${msg.id}, Value: ${msg.value}`);
    }
});
```

## Frame Profiles

Different profiles for different use cases:

- **ProfileStandard**: General purpose (Basic header + Default payload)
- **ProfileSensor**: Low-bandwidth sensors (Tiny header + Minimal payload)
- **ProfileIPC**: Trusted inter-process (No header + Minimal payload)
- **ProfileBulk**: Large data transfers (Basic header + Extended payload)
- **ProfileNetwork**: Multi-system networks (Basic header + Extended Multi-System Stream payload)

All profiles support the same API - just change the class name!

## Arrays

Example with arrays:

```proto
message SensorData {
  option msgid = 2;
  repeated float readings = 1 [max_size=10];
}
```

Creating messages with arrays works the same way across languages:

=== "C"
    ```c
    ExampleSensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    
    // Serialize/deserialize works the same as simple messages
    // Just use msg.serialize() / deserialize(data)
    ```

=== "C++"
    ```cpp
    ExampleSensorData data;
    data.readings_count = 3;
    data.readings[0] = 1.1f;
    data.readings[1] = 2.2f;
    data.readings[2] = 3.3f;
    
    // Serialize/deserialize works the same as simple messages
    // Just use msg.serialize() / deserialize(data)
    ```

=== "Python"
    ```python
    data = ExampleSensorData()
    data.readings_count = 3
    data.readings[0] = 1.1
    data.readings[1] = 2.2
    data.readings[2] = 3.3
    
    # Serialize/deserialize works the same as simple messages
    # Just use msg.serialize() / deserialize(data)
    ```

=== "TypeScript"
    ```typescript
    const data = new ExampleSensorData();
    data.readings_count = 3;
    data.readings[0] = 1.1;
    data.readings[1] = 2.2;
    data.readings[2] = 3.3;
    
    // Serialize/deserialize works the same as simple messages
    // Just use msg.serialize() / deserialize(data)
    ```

=== "C#"
    ```csharp
    var data = new ExampleSensorData {
        ReadingsCount = 3
    };
    data.Readings[0] = 1.1f;
    data.Readings[1] = 2.2f;
    data.Readings[2] = 3.3f;
    
    // Serialize/deserialize works the same as simple messages
    // Just use msg.Serialize() / Deserialize(data)
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

Nested messages are accessed naturally in all languages:

=== "C"
    ```c
    ExampleVehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    
    // Serialize/deserialize works the same - nested messages are handled automatically
    ```

=== "C++"
    ```cpp
    ExampleVehicle v;
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    
    // Serialize/deserialize works the same - nested messages are handled automatically
    ```

=== "Python"
    ```python
    v = ExampleVehicle(id=1)
    v.pos.lat = 37.7749
    v.pos.lon = -122.4194
    
    # Serialize/deserialize works the same - nested messages are handled automatically
    ```

=== "TypeScript"
    ```typescript
    const v = new ExampleVehicle();
    v.id = 1;
    v.pos.lat = 37.7749;
    v.pos.lon = -122.4194;
    
    // Serialize/deserialize works the same - nested messages are handled automatically
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
    
    // Serialize/deserialize works the same - nested messages are handled automatically
    ```

## Key Takeaways

1. **Consistent API**: All languages use `serialize()` / `deserialize()` (case varies by language convention)
2. **Frame Profiles**: Use ProfileStandardWriter/Reader for complete framing and parsing
3. **FrameMsgInfo**: Pass frame parser results directly to `deserialize()` - no manual extraction needed
4. **Variable Messages**: Transparent handling - same API for fixed and variable-length messages
5. **Arrays & Nested Messages**: Automatically handled by serialize/deserialize
