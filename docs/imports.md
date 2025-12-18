# Proto File Imports

struct-frame supports importing proto files to enable code reuse and modular message definitions.

## Basic Usage

### Importing Files

Use the `import` statement to include definitions from other proto files:

```proto
package my_package;

import "common_types.proto";

message MyMessage {
  CommonType field = 1;  // Type defined in common_types.proto
}
```

## Import Behavior

### Same Package Imports

When importing a file into the same package, all types are merged into a single package:

**common_types.proto:**
```proto
package shared;

enum Status {
  INACTIVE = 0;
  ACTIVE = 1;
}
```

**extended_types.proto:**
```proto
package shared;

import "common_types.proto";

message StatusMessage {
  Status status = 1;  // Uses enum from common_types.proto
}
```

Both files contribute to the `shared` package, and all types are available to each other.

### Cross-Package Imports

When importing a file from a different package, types from the imported package become available:

**base.proto:**
```proto
package base;

option package_id = 10;  // Required for multi-package compilation

message Timestamp {
  int64 seconds = 1;
  int32 nanoseconds = 2;
}
```

**app.proto:**
```proto
package app;

option package_id = 20;  // Required for multi-package compilation

import "base.proto";

message Event {
  Timestamp time = 1;  // Uses Timestamp from base package
  string description = 2 [max_size=100];
}
```

## Package IDs

### When Package IDs are Required

When compiling multiple packages together (via imports), each package **must** have a unique `package_id`:

```proto
package my_package;

option package_id = 10;  // Required when importing other packages
```

### When Package IDs are Optional

Single-package proto files do not require a `package_id`:

```proto
package standalone;

message SimpleMessage {
  uint32 id = 1;
}
```

### Package ID Rules

1. **Single package**: No `package_id` required
2. **Multiple packages**: All packages must have unique `package_id` values
3. **Validation**: struct-frame will error if:
   - Multiple packages exist without `package_id` assignments
   - Duplicate `package_id` values are found

## Import Resolution

### Path Resolution

Imports are resolved relative to the directory containing the importing file:

```
project/
  ├── common/
  │   └── types.proto
  └── app/
      └── messages.proto  # Contains: import "../common/types.proto"
```

### Circular Dependencies

Circular imports are detected and will cause a validation error:

**file_a.proto:**
```proto
import "file_b.proto";
```

**file_b.proto:**
```proto
import "file_a.proto";  // ERROR: Circular dependency
```

## Examples

### Example 1: Shared Enums and Types

Create a common types file that can be imported by multiple applications:

**common.proto:**
```proto
package common;

option package_id = 1;

enum Priority {
  LOW = 0;
  MEDIUM = 1;
  HIGH = 2;
}

message Address {
  string street = 1 [max_size=100];
  string city = 2 [max_size=50];
  string zip = 3 [size=10];
}
```

**customer.proto:**
```proto
package customer;

option package_id = 100;

import "common.proto";

message CustomerMessage {
  option msgid = 1;
  
  uint32 customer_id = 1;
  string name = 2 [max_size=100];
  Address address = 3;
  Priority priority = 4;
}
```

### Example 2: Modular Package Organization

**sensors/base.proto:**
```proto
package sensors;

option package_id = 10;

message SensorReading {
  uint32 sensor_id = 1;
  float value = 2;
  int64 timestamp = 3;
}
```

**sensors/temperature.proto:**
```proto
package sensors;

import "base.proto";

message TemperatureSensor {
  option msgid = 100;
  
  SensorReading reading = 1;
  float calibration_offset = 2;
  string unit = 3 [size=1];  // 'C' or 'F'
}
```

## Code Generation

When generating code from proto files with imports, struct-frame will:

1. Parse all imported files recursively
2. Generate code for all discovered packages
3. Create separate output files for each package

**Example:**

```bash
python -m struct_frame app.proto --build_py --py_path generated/

# Generates:
# - generated/app_sf.py
# - generated/base_sf.py  (from imported base.proto)
```

## Command Line Usage

The import functionality works with all existing struct-frame commands:

```bash
# Validate proto with imports
python -m struct_frame sensor_data.proto --validate

# Generate code for all languages
python -m struct_frame sensor_data.proto \
  --build_c --c_path gen/c \
  --build_py --py_path gen/py \
  --build_ts --ts_path gen/ts

# Debug mode shows all imported packages
python -m struct_frame sensor_data.proto --validate --debug
```

## Best Practices

1. **Use Package IDs**: Even if not immediately required, assign `package_id` values to facilitate future multi-package scenarios
2. **Organize by Domain**: Group related types into packages (e.g., `common`, `sensors`, `control`)
3. **Avoid Circular Dependencies**: Design your type hierarchy to be acyclic
4. **Document Dependencies**: Comment import statements to explain why each import is needed
5. **Relative Paths**: Use relative paths for imports to make proto files portable

## Troubleshooting

### Error: "Cannot find imported file"

The import path is resolved relative to the importing file's directory. Check that:
- The path is correct relative to the importing file
- The file exists at the specified location

### Error: "Package does not have a package_id assigned"

When importing files from different packages, all packages need `package_id`:

```proto
option package_id = 10;  // Add this to each package
```

### Error: "Duplicate package_id"

Each package must have a unique `package_id`:

```proto
package pkg1;
option package_id = 10;

// In another file:
package pkg2;
option package_id = 20;  // Must be different from pkg1
```

### Error: "Recursion Error" / "cyclical dependancy"

Your imports create a circular dependency. Restructure your types to break the cycle.
