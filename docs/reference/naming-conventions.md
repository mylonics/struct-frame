# Naming Conventions

This document describes the naming conventions used throughout the struct-frame codebase for consistency across languages.

## Boilerplate SDK Files

The struct-frame SDK provides frame parsing and encoding functionality. Boilerplate files follow language-specific conventions:

### C
- **Convention**: snake_case (idiomatic for C)
- **Files**: `frame_base.h`, `frame_headers.h`, `frame_profiles.h`, `payload_types.h`
- **Naming Pattern**: Descriptive snake_case names

### C++
- **Convention**: Mixed (PascalCase for main files, snake_case for utilities)
- **Files**: `FrameProfiles.hpp`, `frame_base.hpp`, `frame_headers.hpp`, `payload_types.hpp`
- **Naming Pattern**: Main SDK file uses PascalCase, utility files use snake_case
- **Note**: Consider prefixing with `StructFrame` for clarity in future versions

### C#
- **Convention**: Mixed (PascalCase for main files, snake_case for utilities)
- **Files**: `FrameProfiles.cs`, `frame_base.cs`, `frame_headers.cs`, `payload_types.cs`
- **Naming Pattern**: Main SDK file uses PascalCase, utility files use snake_case
- **Namespace**: `StructFrame`

### TypeScript/JavaScript
- **Convention**: snake_case (consistent with Node.js ecosystem)
- **Files**: `frame_base.ts`, `frame_headers.ts`, `frame_profiles.ts`, `payload_types.ts`
- **Export File**: `index.ts` / `index.js`

### Python
- **Convention**: snake_case (PEP 8 compliant)
- **Files**: `frame_base.py`, `frame_headers.py`, `frame_profiles.py`, `payload_types.py`
- **Package File**: `__init__.py`

## Generated Code Files

Code generated from `.proto` files follows these naming patterns:

- **Python**: `{package_name}_sf.py` (e.g., `my_messages_sf.py`)
- **TypeScript**: `{package_name}.sf.ts` (e.g., `my_messages.sf.ts`)
- **JavaScript**: `{package_name}.sf.js`
- **C**: `{package_name}.sf.h`
- **C++**: `{package_name}.sf.hpp`
- **C#**: `{package_name}.sf.cs`

The `.sf` suffix (short for "struct-frame") clearly identifies generated files.

**Note**: Python uses underscore separator (`_sf`) while other languages use dot separator (`.sf`) to align with language conventions.

## Profile Naming

Frame profiles combine headers and payload types. Naming follows this pattern:

- **Profile Names**: `ProfileBasic`, `ProfileSensor`, `ProfileIPC`, `ProfileBulk`, `ProfileNetwork`
- **Function Names**: `profile_basic`, `profile_sensor`, `profile_ipc`, `profile_bulk`, `profile_network`
- **Constants**: `PROFILE_BASIC_CONFIG`, `PROFILE_SENSOR_CONFIG`, etc.

### Profile Purpose

- **ProfileBasic**: General-purpose serial/UART communication (formerly ProfileBasic)
- **ProfileSensor**: Low-bandwidth sensors
- **ProfileIPC**: Inter-process communication
- **ProfileBulk**: Large data transfers
- **ProfileNetwork**: Multi-system networked communication

## Class and Type Naming

### C++
- **Enums**: `enum class ProfileType` (scoped enums)
- **Structs**: `struct MessageBase`, `struct FrameMsgInfo`
- **Classes**: `class ProfileBasicReader`, `class BufferWriter`
- **Namespace**: `StructFrame` or `FrameParsers`

### C#
- **Enums**: `public enum ProfileType`
- **Classes**: `public class ProfileBasicReader`
- **Interfaces**: `public interface IMessage`
- **Namespace**: `StructFrame` for SDK, `StructFrame.{PackageName}` for generated code

### TypeScript
- **Enums**: `export enum ProfileType`
- **Classes**: `export class ProfileBasicReader`
- **Interfaces**: `export interface MessageInit`
- **Types**: `export type FrameConfig`

### Python
- **Classes**: `class ProfileBasicReader` (PascalCase per PEP 8)
- **Functions**: `def parse_frame_buffer` (snake_case per PEP 8)
- **Constants**: `PROFILE_BASIC_CONFIG` (UPPER_SNAKE_CASE per PEP 8)
- **Modules**: `struct_frame` (snake_case per PEP 8)

### C
- **Structs**: `typedef struct FrameMsgInfo`
- **Enums**: `typedef enum HeaderType`
- **Functions**: `fletcher_checksum`, `parse_frame_buffer` (snake_case)
- **Constants**: `PROFILE_BASIC_CONFIG` (UPPER_SNAKE_CASE)

## Test File Naming

Test files follow a consistent pattern across languages:

- **Basic Tests**: `test_basic.{ext}` - Tests fundamental message types (msg_id < 256)
- **Extended Tests**: `test_extended.{ext}` - Tests extended message IDs (msg_id > 255)
- **Test Data**: `{test_type}_test_data.{ext}` - Test configuration and data

Example filenames:
- C: `test_basic.c`, `basic_test_data.h`
- C++: `test_basic.cpp`, `basic_test_data.hpp`  
- Python: `test_basic.py`, `basic_test_data.py`
- TypeScript: `test_basic.ts`, `basic_test_data.ts`

## Language-Specific Idioms

### Casing Conventions

- **C**: snake_case for everything
- **C++**: PascalCase for types, snake_case for functions and variables
- **C#**: PascalCase for public members, camelCase for private, PascalCase for files
- **Python**: snake_case for modules/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants
- **TypeScript/JavaScript**: camelCase for variables/functions, PascalCase for classes/interfaces

### File Extensions

- C: `.h` (header), `.c` (source)
- C++: `.hpp` (header), `.cpp` (source)
- C#: `.cs` (combined header/source)
- Python: `.py`
- TypeScript: `.ts`
- JavaScript: `.js`

## Import Clarity

To make it clear when users are importing struct-frame code:

### C++
```cpp
#include "FrameProfiles.hpp"  // Clearly a struct-frame SDK file
#include "my_messages.sf.hpp" // .sf indicates generated code
using namespace StructFrame;   // Namespace indicates struct-frame
```

### C#
```csharp
using StructFrame;                    // Namespace indicates struct-frame
using StructFrame.MyMessages;         // Generated code
```

### Python
```python
from frame_profiles import ProfileBasicReader  # From generated directory
from my_messages_sf import MyMessage            # _sf indicates generated
```

### TypeScript
```typescript
import { ProfileBasicReader } from './frame_profiles';  // SDK import
import { MyMessage } from './my_messages.sf';           // .sf indicates generated
```

## Consistency Goals

1. **Cross-Language Uniformity**: Similar concepts use similar names across languages
2. **Language Idioms**: Each language follows its community conventions
3. **Clear Attribution**: Users can identify struct-frame code by naming patterns
4. **Minimal Surprise**: Names match user expectations for each language ecosystem

## Future Considerations

Potential improvements for future major versions:

1. Add `struct_frame_` or `StructFrame` prefix to all boilerplate files
2. Standardize generated file naming to `{package}.struct_frame.{ext}` (full name instead of "sf")
3. Consider namespace/module reorganization for clearer SDK boundaries
