# Installation and Usage

## Dependencies

**Python (required for code generation)**
```
pip install proto-schema-parser structured-classes
```

## Code Generation

Run the generator with your proto file:

```bash
# Generate all languages
python src/main.py schema.proto --build_c --build_cpp --build_ts --build_py --build_gql

# Generate specific languages
python src/main.py schema.proto --build_c
python src/main.py schema.proto --build_py --build_ts

# Custom output paths
python src/main.py schema.proto --build_c --c_path output/c/
python src/main.py schema.proto --build_py --py_path output/python/
```

Default output is `generated/<language>/`.

## Build Integration

Build integration allows generated code to automatically reflect changes to proto files during your build process. When proto files change, the build system regenerates the corresponding code.

### Make (C/C++)

```makefile
PROTO_FILES := $(wildcard proto/*.proto)
GENERATED_DIR := generated

generated/c/%.sf.h: proto/%.proto
	python src/main.py $< --build_c --c_path generated/c/

generated/py/%.sf.py: proto/%.proto
	python src/main.py $< --build_py --py_path generated/py/

all: $(PROTO_FILES:proto/%.proto=generated/c/%.sf.h)
```

### CMake (C/C++)

```cmake
find_package(Python3 REQUIRED)

set(PROTO_FILES
    proto/messages.proto
)

foreach(PROTO_FILE ${PROTO_FILES})
    get_filename_component(PROTO_NAME ${PROTO_FILE} NAME_WE)
    set(GENERATED_HEADER "${CMAKE_BINARY_DIR}/generated/c/${PROTO_NAME}.sf.h")
    
    add_custom_command(
        OUTPUT ${GENERATED_HEADER}
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/src/main.py
            ${CMAKE_SOURCE_DIR}/${PROTO_FILE}
            --build_c --c_path ${CMAKE_BINARY_DIR}/generated/c/
        DEPENDS ${PROTO_FILE}
    )
    list(APPEND GENERATED_HEADERS ${GENERATED_HEADER})
endforeach()

add_custom_target(generate_structs DEPENDS ${GENERATED_HEADERS})
```

### npm scripts (TypeScript)

Add to package.json:

```json
{
  "scripts": {
    "generate": "python src/main.py proto/messages.proto --build_ts --ts_path src/generated/",
    "build": "npm run generate && tsc",
    "watch": "tsc --watch"
  }
}
```

### Python setuptools

Add to setup.py or pyproject.toml:

```python
# setup.py
from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess

class BuildWithGenerate(build_py):
    def run(self):
        subprocess.run([
            'python', 'src/main.py', 'proto/messages.proto',
            '--build_py', '--py_path', 'src/generated/'
        ])
        super().run()

setup(
    cmdclass={'build_py': BuildWithGenerate},
    # ...
)
```

## Language-Specific Usage

### C

Include the generated header and parser boilerplate:

```c
#include "messages.sf.h"
#include "struct_frame_parser.h"

// Create a message
VehicleStatus status = {0};
status.vehicle_id = 1234;
status.speed = 55.5f;
status.engine_on = true;

// Encode to frame
uint8_t buffer[256];
size_t size = basic_frame_encode(buffer, VEHICLE_STATUS_MSG_ID, 
                                  (uint8_t*)&status, sizeof(status));

// Parse incoming data
packet_state_t parser = {0};
// ... initialize parser ...

for (size_t i = 0; i < size; i++) {
    msg_info_t info = parse_char(&parser, buffer[i]);
    if (info.valid) {
        VehicleStatus* msg = (VehicleStatus*)info.msg_loc;
        printf("Vehicle %d: %.1f\n", msg->vehicle_id, msg->speed);
    }
}
```

Compile:
```bash
gcc main.c -I generated/c -o main
```

### C++

Include the generated header and struct_frame boilerplate:

```cpp
#include "messages.sf.hpp"
#include "struct_frame.hpp"

// Create a message
VehicleStatus status{};
status.vehicle_id = 1234;
status.speed = 55.5f;
status.engine_on = true;

// Encode to frame
uint8_t buffer[256];
StructFrame::BasicPacket format;
StructFrame::EncodeBuffer encoder(buffer, sizeof(buffer));

encoder.encode(&format, VEHICLE_STATUS_MSG_ID, &status, sizeof(status));

// Parse incoming data
StructFrame::FrameParser parser(&format, [](size_t msg_id, size_t* size) {
    return StructFrame::get_message_length(msg_id, size);
});

for (size_t i = 0; i < encoder.size(); i++) {
    auto info = parser.parse_byte(buffer[i]);
    if (info.valid) {
        auto* msg = reinterpret_cast<VehicleStatus*>(info.msg_location);
        std::cout << "Vehicle " << msg->vehicle_id << std::endl;
    }
}
```

Compile:
```bash
g++ -std=c++17 main.cpp -I generated/cpp -o main
```

### Python

Import the generated module:

```python
from messages_sf import VehicleStatus
from struct_frame_parser import FrameParser, BasicPacket

# Create a message
msg = VehicleStatus()
msg.vehicle_id = 1234
msg.speed = 55.5
msg.engine_on = True

# Encode to frame
packet = BasicPacket()
frame_bytes = packet.encode_msg(msg)

# Parse incoming data
parser = FrameParser({0x90: BasicPacket()}, {VEHICLE_STATUS_MSG_ID: VehicleStatus})
for byte in frame_bytes:
    result = parser.parse_char(byte)
    if result:
        print(f"Vehicle {result.vehicle_id}: {result.speed}")
```

Run:
```bash
PYTHONPATH=generated/py python main.py
```

### TypeScript

Import the generated module:

```typescript
import * as msg from './generated/ts/messages.sf';
import { struct_frame_buffer, parse_char } from './generated/ts/struct_frame_parser';

// Create message
let status = new msg.VehicleStatus();
status.vehicle_id = 1234;
status.speed = 55.5;
status.engine_on = true;

// Encode to frame
let tx_buffer = new struct_frame_buffer(256);
msg.VehicleStatus_encode(tx_buffer, status);

// Parse incoming data
let rx_buffer = new struct_frame_buffer(256);
for (let i = 0; i < tx_buffer.size; i++) {
    if (parse_char(rx_buffer, tx_buffer.data[i])) {
        let decoded = msg.VehicleStatus_decode(rx_buffer.msg_data);
        console.log(`Vehicle ${decoded.vehicle_id}: ${decoded.speed}`);
    }
}
```

Compile and run:
```bash
npx tsc main.ts --outDir build/
node build/main.js
```

### GraphQL

Generated GraphQL schemas define types for use with GraphQL servers:

```graphql
type VehicleStatus {
  vehicle_id: Int!
  speed: Float!
  engine_on: Boolean!
}
```

Use with your preferred GraphQL server implementation.

## Serial Communication Example

Python example reading from a serial port:

```python
import serial
from messages_sf import VehicleStatus, VEHICLE_STATUS_MSG_ID
from struct_frame_parser import FrameParser, BasicPacket

ser = serial.Serial('/dev/ttyUSB0', 115200)
parser = FrameParser(
    {0x90: BasicPacket()},
    {VEHICLE_STATUS_MSG_ID: VehicleStatus}
)

while True:
    if ser.in_waiting:
        byte = ser.read(1)[0]
        result = parser.parse_char(byte)
        if result:
            handle_message(result)
```

## TCP Socket Example

TypeScript example with TCP:

```typescript
import * as net from 'net';
import { struct_frame_buffer, parse_char } from './generated/ts/struct_frame_parser';

const client = net.createConnection({port: 8080});
let rx_buffer = new struct_frame_buffer(1024);

client.on('data', (data: Buffer) => {
    for (let byte of data) {
        if (parse_char(rx_buffer, byte)) {
            handleMessage(rx_buffer.msg_data);
        }
    }
});
```
