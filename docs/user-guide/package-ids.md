# Package ID Support

This document describes the package ID feature for extended message addressing.

## Overview

Package IDs enable 16-bit message addressing (package_id << 8 | msg_id) instead of 8-bit, allowing:
- Up to 256 packages × 256 messages = 65,536 unique message IDs
- Message namespace separation between packages
- Better organization for large multi-package systems

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

- Package IDs must be unique across all packages
- Package IDs must be in range 0-255
- Message IDs within a package must still be 0-255
- Package ID collisions are detected and reported at build time

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
