
# Struct Frame

A multi-language code generation framework that converts Protocol Buffer (.proto) files into serialization/deserialization code for C, TypeScript, Python, and GraphQL. It provides framing and parsing utilities for structured message communication.

## Quick Start

### Installation
```bash
# Install Python dependencies
pip install proto-schema-parser structured-classes

# Install Node.js dependencies (for TypeScript)
npm install
```

### Basic Usage
```bash
# Generate code for all languages
PYTHONPATH=src python3 src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql

# Run comprehensive test suite
python test_all.py

# Generated files will be in the generated/ directory
```

### Test Suite

The project includes a comprehensive test suite that validates code generation, compilation, and serialization across all supported languages:

```bash
# Run all tests
python test_all.py

# Run with verbose output
python tests/run_tests.py --verbose

# Skip specific languages
python tests/run_tests.py --skip-ts --skip-c

# Generate code only (no compilation/execution)
python tests/run_tests.py --generate-only
```

See `tests/README.md` for detailed test documentation.

### Language-Specific Examples

#### Python
```bash
python src/main.py examples/myl_vehicle.proto --build_py
# Use generated Python classes directly
```

#### TypeScript
```bash
python src/main.py examples/myl_vehicle.proto --build_ts
npx tsc examples/index.ts --outDir generated/
node generated/examples/index.js
```

#### C
```bash
python src/main.py examples/myl_vehicle.proto --build_c
gcc examples/main.c -I generated/c -o main
./main
```

#### GraphQL
```bash
python src/main.py examples/myl_vehicle.proto --build_gql
# Use generated .graphql schema files
```

## Feature Compatibility Matrix

| Feature | C | TypeScript | Python | GraphQL | Status |
|---------|---|------------|--------|---------|--------|
| **Core Types** | ✓ | ✓ | ✓ | ✓ | Stable |
| **String** | ✓ | ✓ | ✓ | ✓ | Stable |
| **Enums** | ✓ | ✓ | ✓ | ✓ | Stable |
| **Nested Messages** | ✓ | ✓ | ✓ | ✓ | Stable |
| **Message IDs** | ✓ | ✓ | ✓ | N/A | Stable |
| **Message Serialization** | ✓ | ✓ | ✓ | N/A | Stable |
| **Flatten** | N/A | N/A | ✓ | ✓ | Partial |
| **Arrays** | ✓ | ✓ | ✓ | ✓ | Stable |

**Legend:**
- **✓** - Feature works as documented
- **Partial** - Basic functionality works, some limitations  
- **✗** - Feature not yet available
- **N/A** - Not applicable for this language

## Project Structure

- `src/struct_frame/` - Core code generation framework
  - `generate.py` - Main parser and validation logic
  - `*_gen.py` - Language-specific code generators
  - `boilerplate/` - Runtime libraries for each language
- `examples/` - Example .proto files and usage demos
  - `main.c` - C API demonstration (encoding/decoding, parsing)
  - `index.ts` - TypeScript API demonstration (similar functionality)  
  - `*.proto` - Protocol Buffer definitions for examples
- `generated/` - Output directory for generated code (git-ignored)

## Protocol Buffer Schema Reference

### Supported Data Types

| Type | Size (bytes) | Description | Range/Notes |
|------|--------------|-------------|-------------|
| **Integers** |
| `int8` | 1 | Signed 8-bit integer | -128 to 127 |
| `uint8` | 1 | Unsigned 8-bit integer | 0 to 255 |
| `int16` | 2 | Signed 16-bit integer | -32,768 to 32,767 |
| `uint16` | 2 | Unsigned 16-bit integer | 0 to 65,535 |
| `int32` | 4 | Signed 32-bit integer | -2.1B to 2.1B |
| `uint32` | 4 | Unsigned 32-bit integer | 0 to 4.3B |
| `int64` | 8 | Signed 64-bit integer | Large integers |
| `uint64` | 8 | Unsigned 64-bit integer | Large positive integers |
| **Floating Point** |
| `float` | 4 | Single precision (IEEE 754) | 7 decimal digits |
| `double` | 8 | Double precision (IEEE 754) | 15-17 decimal digits |
| **Other** |
| `bool` | 1 | Boolean value | `true` or `false` |
| `string` | Variable | UTF-8 encoded string | Length-prefixed |
| `EnumType` | 1 | Custom enumeration | Defined in .proto |
| `MessageType` | Variable | Nested message | User-defined structure |

> **Note:** All types use little-endian byte order for cross-platform compatibility.

### Array Support

Arrays (repeated fields) support all data types - primitives, enums, and messages across all target languages.

| Array Type | Syntax | Memory Usage | Use Case |
|------------|--------|--------------|----------|
| **Fixed** | `repeated type field = N [size=X];` | `sizeof(type) * X` | Matrices, buffers (always full) |  
| **Bounded** | `repeated type field = N [max_size=X];` | 1 byte (count) + `sizeof(type) * X` | Dynamic lists with limits |
| **String Arrays** | `repeated string field = N [max_size=X, element_size=Y];` | 1 byte (count) + `X * Y` bytes | Text collections with size limits |

```proto
message ArrayExample {
  repeated float matrix = 1 [size=9];                        // 3x3 matrix (always 9 elements)
  repeated string names = 2 [max_size=10, element_size=32];  // Up to 10 strings, each max 32 chars
  repeated int32 values = 3 [max_size=100];                  // Up to 100 integers (variable count)
}
```

**Generated Output** (all languages now supported):
- **Python**: `matrix: list[float]`, `names: list[str]`, `values: list[int]`
- **C**: `float matrix[9]`, `struct { uint8_t count; char data[10][32]; } names`
- **TypeScript**: `Array('matrix', 'Float32LE', 9)`, `Array('names_data', 'String', 10)`  
- **GraphQL**: `matrix: [Float!]!`, `names: [String!]!`, `values: [Int!]!`

> **Important**: String arrays require both `max_size` (or `size`) AND `element_size` parameters because they are "arrays of arrays" - you need to specify both how many strings AND the maximum size of each individual string. This ensures predictable memory layout and prevents buffer overflows.

### String Type

Strings are a special case of bounded character arrays with built-in UTF-8 encoding and null-termination handling across all target languages.

| String Type | Syntax | Memory Usage | Use Case |
|-------------|--------|--------------|----------|
| **Fixed String** | `string field = N [size=X];` | `X` bytes | Fixed-width text fields |
| **Variable String** | `string field = N [max_size=X];` | 1 byte (length) + `X` bytes | Text with known maximum length |

```proto
message StringExample {
  string device_name = 1 [size=16];              // Exactly 16 characters (pad with nulls)
  string description = 2 [max_size=256];         // Up to 256 characters (length-prefixed)
  string error_msg = 3 [max_size=128];           // Up to 128 characters for error messages
}
```

**String Benefits:**
- **Simplified Schema**: No need to specify `repeated uint8` for text data
- **Automatic Encoding**: UTF-8 encoding/decoding handled by generators  
- **Null Handling**: Proper null-termination and padding for fixed strings
- **Type Safety**: Clear distinction between binary data and text
- **Cross-Language**: Consistent string handling across C, TypeScript, and Python

### Message Options

**Message ID (`msgid`)** - Required for serializable messages:
```proto
message MyMessage {
  option msgid = 42;  // Must be unique within package (0-65535)
  string content = 1;
}
```

### Field Options

**Flatten (`flatten=true`)** - Merge nested message fields into parent:
```proto
message Position {
  double lat = 1;
  double lon = 2;
}

message Status {
  Position pos = 1 [flatten=true];  // lat, lon become direct fields  
  float battery = 2;
}
```

**Array Options** - Control array behavior:
```proto
message Data {
  repeated int32 fixed_buffer = 1 [size=256];                       // Always 256 integers  
  repeated int32 var_buffer = 2 [max_size=256];                     // Up to 256 integers
  repeated string messages = 3 [max_size=10, element_size=64];      // Up to 10 strings, each max 64 chars
  string device_name = 4 [size=32];                                 // Always 32 characters
  string description = 5 [max_size=256];                            // Up to 256 characters
}
```

## Complete Example

```proto
package sensor_system;

enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
  PRESSURE = 2;
}

message Position {
  double lat = 1;
  double lon = 2;
  float alt = 3;
}

message SensorReading {
  option msgid = 1;
  
  uint32 device_id = 1;
  int64 timestamp = 2;
  SensorType type = 3;
  
  // Device name (fixed 16-character string)  
  string device_name = 4 [size=16];
  
  // Sensor location (flattened)
  Position location = 5 [flatten=true];
  
  // Measurement values (up to 8 readings)
  repeated float values = 6 [max_size=8];
  
  // Calibration matrix (always 3x3 = 9 elements)
  repeated float calibration = 7 [size=9];
  
  // Error message (up to 128 characters)
  string error_msg = 8 [max_size=128];
  
  bool valid = 9;
}

message DeviceStatus {
  option msgid = 2;
  
  uint32 device_id = 1;
  repeated SensorReading recent_readings = 2 [max_size=10];
  float battery_level = 3;
}
```

## Schema Validation Rules

- **Message IDs**: Must be unique within package (0-65535)
- **Field numbers**: Must be unique within message  
- **Array requirements**: All `repeated` fields must specify `[size=X]` (fixed) or `[max_size=X]` (bounded)
- **String requirements**: All `string` fields must specify `[size=X]` (fixed) or `[max_size=X]` (variable)
- **String array requirements**: `repeated string` fields must specify both array size AND `[element_size=Y]`
- **Flatten constraints**: No field name collisions after flattening
- **Size limits**: Arrays limited to 255 elements maximum

## Code Generation

```bash
# Generate all languages
python src/main.py schema.proto --build_c --build_ts --build_py --build_gql

# Language-specific paths
python src/main.py schema.proto --build_py --py_path output/python/
python src/main.py schema.proto --build_c --c_path output/c/
python src/main.py schema.proto --build_ts --ts_path output/typescript/
python src/main.py schema.proto --build_gql --gql_path output/graphql/
```

## Additional Documentation

- **[Array Implementation Guide](ARRAY_IMPLEMENTATION.md)** - Comprehensive documentation of array features, syntax, and generated code examples across all languages
