# Package ID Support

This document describes the package ID feature for extended message addressing and importing proto files.

## Overview

Package IDs enable 16-bit message addressing (package_id << 8 | msg_id) instead of 8-bit, allowing:
- Up to 256 packages × 256 messages = 65,536 unique message IDs
- Message namespace separation between packages
- Better organization for large multi-package systems
- Import and reuse of message definitions across files

## Message ID Ranges and Validation

The generator enforces strict validation rules for message IDs based on whether a package has a package ID:

### With Package ID (option pkgid = N)
- **Package ID range**: 0-255
- **Message ID range**: 0-255 (8 bits)
- **Combined ID**: `(package_id << 8) | msg_id` (16 bits total)
- **Generated constants**: `uint16_t MSG_ID` with combined value

Example:
```protobuf
package sensor_data;
option pkgid = 1;

message SensorReading {
  option msgid = 1;  // Valid: 0 <= 1 < 256
  // ...
}
// Generated constant: SENSOR_READING_MSG_ID = 257 (0x0101)
// Where: (1 << 8) | 1 = 257
```

### Without Package ID
- **Message ID range**: 0-65535 (16 bits)
- **Generated constants**: Plain message ID value

Example:
```protobuf
package simple_messages;
// No pkgid option

message Command {
  option msgid = 1000;  // Valid: 0 <= 1000 < 65536
  // ...
}
// Generated constant: COMMAND_MSG_ID = 1000
```

### Frame Format Restrictions

When a package has a package ID OR any message ID is >= 256, the generator automatically filters available frame formats:

**Allowed frame formats (Extended types only):**
- `ExtendedMsgIds`: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC]
- `Extended`: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC]
- `ExtendedMinimal`: [PKG_ID] [MSG_ID] [PACKET]
- `ExtendedMultiSystemStream`: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC]
- `ExtendedLength`: [LEN16] [MSG_ID] [PACKET] [CRC]

**Blocked frame formats:**
- `Minimal`, `Default`, `SysComp`, `Seq`, `MultiSystemStream`
- Profiles: `ProfileStandard`, `ProfileSensor`, `ProfileIPC`

**Allowed profiles:**
- `ProfileBulk` (uses Extended)
- `ProfileNetwork` (uses ExtendedMultiSystemStream)

## Importing Proto Files

Proto files can import other proto files using standard protobuf import syntax:

```protobuf
import "path/to/other_file.proto";
```

### Package ID Inheritance

When a proto file without a package ID is imported by a file with a package ID, the imported file **inherits** the package ID from the importing file. This allows shared type definitions to be used across projects without explicitly assigning package IDs to utility files.

```protobuf
// common_types.proto - No package ID defined
package common_types;

enum Status {
  IDLE = 0;
  ACTIVE = 1;
  ERROR = 2;
}

message Timestamp {
  option msgid = 1;
  uint64 seconds = 1;
  uint32 nanoseconds = 2;
}
```

```protobuf
// my_messages.proto
package my_app;
option pkgid = 1;  // common_types will inherit pkgid=1

import "common_types.proto";

message MyMessage {
  option msgid = 1;
  Timestamp created_at = 1;  // Uses Timestamp from common_types
  Status status = 2;          // Uses Status from common_types
}
```

In this example:
- `my_app` has `pkgid = 1`
- `common_types` has no explicit `pkgid`, so it inherits `pkgid = 1` from `my_app`
- Both packages share the same message ID space (pkgid=1)
- All generated files (my_app.sf.*, common_types.sf.*) are created separately

### Same Package Imports

Files can be split into multiple proto files within the same package. All files in the same package must use the same package ID:

```protobuf
// sensor_types.proto
package sensor_data;
option pkgid = 2;

enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
}
```

```protobuf
// sensor_messages.proto
package sensor_data;
option pkgid = 2;  // Same package, same ID

import "sensor_types.proto";

message SensorReading {
  option msgid = 1;
  SensorType type = 1;  // Uses type from imported file
  float value = 2;
}
```

### Multi-Package Imports with Different IDs

When importing files from different packages that have their own package IDs, each package maintains its unique ID:

```protobuf
// pkg_a.proto
package package_a;
option pkgid = 1;

enum ActionType {
  START = 0;
  STOP = 1;
}
```

```protobuf
// pkg_b.proto
package package_b;
option pkgid = 2;

import "pkg_a.proto";

message Command {
  option msgid = 1;
  ActionType action = 1;  // Uses type from package_a (pkgid=1)
  uint32 target = 2;
}
```

In this example:
- `package_a` has `pkgid = 1`
- `package_b` has `pkgid = 2`
- Types from `package_a` can be used in `package_b` messages
- Each package generates separate files with their own namespace/module

### Import Path Resolution

Import paths are resolved in the following order:
1. Relative to the directory of the importing file
2. Relative to the base path specified (if any)

## Multi-Package Validation

### Package ID Assignment Rules

1. **Inherited Package IDs**: If an imported package has no `pkgid` defined, it will inherit the package ID from the importing package
2. **Explicit Package IDs**: Packages can have explicit `pkgid` values (0-255)
3. **Package Name Conflicts**: If the same package name appears with different explicit `pkgid` values, compilation fails with an error
4. **Multiple Packages**: When multiple packages are compiled together, at least one must have an explicit `pkgid` for inheritance to work

Example of invalid configuration (package name conflict):

```protobuf
// file1.proto
package my_pkg;
option pkgid = 1;
```

```protobuf
// file2.proto  
package my_pkg;
option pkgid = 2;  // ERROR: Same package name, different ID
```

This will produce an error:
```
Error: Package 'my_pkg' has conflicting package IDs:
  Already defined as: 1
  Trying to redefine as: 2 in file2.proto
```

## Defining Package IDs

Add `option pkgid` to your proto file:

```protobuf
package my_package;

// Define package ID (0-255)
option pkgid = 5;

message MyMessage {
  option msgid = 1;
  // ... fields
}
```

## Generated Code

### C++
Messages are generated inside a namespace matching the package name:

```cpp
#include "my_package.sf.hpp"

// Access message in namespace
my_package::MyMessage msg;
msg.value = 42;

// Package ID constant
uint8_t pkg = my_package::PACKAGE_ID;  // = 5

// Message ID is 16-bit: (5 << 8) | 1 = 1281
```

### C
Package ID defined as a constant:

```c
#include "my_package.sf.h"

MyPackageMyMessage msg;
msg.value = 42;

// Package ID constant
uint8_t pkg = MY_PACKAGE_PACKAGE_ID;  // = 5
```

### TypeScript
```typescript
import { PACKAGE_ID, MyPackage_MyMessage } from './my_package.sf';

const msg = new MyPackage_MyMessage();
msg.value = 42;

console.log(PACKAGE_ID);  // 5
```

### Python
```python
from my_package_sf import PACKAGE_ID, MyPackageMyMessage, get_message_class

msg = MyPackageMyMessage(value=42)

# Get message class by 16-bit ID
# (package_id << 8) | msg_id = (5 << 8) | 1 = 1281
msg_class = get_message_class(1281)
```

### C#
```csharp
using StructFrame.MyPackage;

var msg = new MyPackageMyMessage { Value = 42 };

// Package ID
byte pkgId = PackageInfo.PackageId;  // = 5
```

### Cross-Package Type References

When using types from imported packages, the generated code automatically handles references:

**C#**: Using directives are automatically added for imported packages
```csharp
// In my_package.sf.cs
using System;
using System.Runtime.InteropServices;
using StructFrame.CommonTypes;  // Automatically added

namespace StructFrame.MyPackage
{
    public struct MyPackageMyMessage
    {
        public CommonTypesTimestamp CreatedAt;  // References imported type
        // ...
    }
}
```

**C++**: Types from all packages are available within their respective namespaces
```cpp
#include "my_package.sf.hpp"
#include "common_types.sf.hpp"

my_package::MyMessage msg;
msg.created_at = common_types::Timestamp{};  // Cross-package reference
```

**Python**: Import from respective modules
```python
from my_package_sf import MyPackageMyMessage
from common_types_sf import CommonTypesTimestamp

msg = MyPackageMyMessage(created_at=CommonTypesTimestamp(seconds=123, nanoseconds=456))
```

**TypeScript**: Import from respective modules
```typescript
import { MyPackage_MyMessage } from './my_package.sf';
import { CommonTypes_Timestamp } from './common_types.sf';

const timestamp = new CommonTypes_Timestamp();
const msg = new MyPackage_MyMessage();
// Note: Struct field assignments in TypeScript depend on the struct_base API
```

## File Generation

Each proto file generates its own output files, regardless of package relationships:

- `my_package.proto` → `my_package.sf.{h,hpp,ts,py,cs}` 
- `common_types.proto` → `common_types.sf.{h,hpp,ts,py,cs}`
- `pkg_a.proto` → `pkg_a.sf.{h,hpp,ts,py,cs}`

This modular approach allows:
- Clear separation of concerns
- Reusable type libraries
- Independent versioning of proto files
- Easy package management

## Frame Format Compatibility

Package IDs require frame formats with a package_id field:

- **EXTENDED_MSG_IDS**: `[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- **EXTENDED**: `[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- **EXTENDED_MULTI_SYSTEM_STREAM**: `[SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`

Basic frame formats (without PKG_ID field) can still be used for single-package systems without package IDs.

## Message ID Encoding

| Mode | Message ID Size | Encoding | Range |
|------|----------------|----------|-------|
| Without pkgid | 8-bit | msg_id | 0-255 |
| With pkgid | 16-bit | (package_id << 8) \| msg_id | 0-65535 |

## Validation Rules

- **Package ID Range**: Package IDs must be in range 0-255
- **Message ID Range**: Message IDs within a package must be 0-255
- **Package ID Uniqueness**: Explicit package IDs should be unique unless packages are meant to share the same message ID space
- **Package ID Inheritance**: Imported packages without explicit pkgid inherit from the importing package
- **Package Name Conflicts**: The same package name cannot have different explicit pkgid values
- **Cross-Package References**: Types from any imported package can be used in message definitions

### Validation Error Examples

**Package name with conflicting IDs:**
```
Error: Package 'common_types' has conflicting package IDs:
  Already defined as: 1
  Trying to redefine as: 2 in file2.proto
```

**Multiple packages without IDs:**
```
Error: Multiple packages are being compiled, but the following packages 
do not have package IDs assigned:
  - package_a
  - package_b

When compiling multiple packages, each package must specify 'option pkgid = N;'
where N is 0-255.
```

Note: This error occurs when multiple packages exist and none have explicit package IDs. To fix, add `option pkgid = N;` to at least one package, and imported packages will inherit if needed.

## Example: Multi-Package System

See `examples/package_id_example.proto` for a complete example showing:
- Multiple packages with different package IDs
- Message namespace separation
- C++ namespace usage
- Python message dictionary with 16-bit keys
- Frame format structure

## Migration from 8-bit to 16-bit

Existing code without package IDs continues to work unchanged. To migrate:

1. Add `option pkgid = N;` to proto files
2. Update frame format to EXTENDED_MSG_IDS or compatible format
3. Update message routing code to use 16-bit message IDs
4. For C++, update code to use namespace qualifiers

## Benefits

- **Scalability**: Support systems with >255 messages
- **Organization**: Clear package boundaries and namespaces
- **Versioning**: Assign different package IDs to different versions
- **Multi-Project**: Combine messages from multiple projects without ID conflicts
