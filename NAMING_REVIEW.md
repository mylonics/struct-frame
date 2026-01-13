# Struct-Frame Naming Convention Review

**Date:** January 13, 2026  
**Reviewer:** GitHub Copilot  
**Purpose:** Review file naming schemes, code organization, and naming conventions across all languages to ensure uniformity, language idiom adherence, and clear struct-frame branding.

---

## Executive Summary

This review analyzes naming conventions across all struct-frame components (boilerplate, generated code, tests) in seven languages: C, C++, Python, TypeScript, JavaScript, C#, and GraphQL. The review identifies several areas where improvements would enhance consistency, clarity, and adherence to language idioms.

### Key Findings

✅ **Strengths:**
- Consistent use of `struct_frame_sdk` naming for SDK directories across languages
- Good namespace isolation in C# (`StructFrame`, `StructFrame.SerializationTest`)
- Clear separation between boilerplate and generated code
- Uniform snake_case for most boilerplate filenames

⚠️ **Areas for Improvement:**
1. **Inconsistent generated file naming** - Multiple patterns (`.sf.h`, `.sf.hpp`, `.sf.ts`, `.sf.cs`, `_sf.py`)
2. **Mixed case conventions** - Some files use PascalCase, others use snake_case
3. **Unclear struct-frame branding** - Not always obvious that imports are from struct-frame
4. **Namespace inconsistencies** - TypeScript/JavaScript use lowercase package prefixes, C++/C# use PascalCase
5. **Missing language idiom adherence** - Some languages don't follow established conventions

---

## Detailed Analysis by Category

### 1. Boilerplate File Naming

#### Current State

| Language | Boilerplate Files | Pattern |
|----------|------------------|---------|
| **C** | `frame_base.h`, `frame_headers.h`, `frame_parsers.h`, `frame_profiles.h`, `payload_types.h` | snake_case |
| **C++** | `frame_base.hpp`, `frame_headers.hpp`, `frame_parsers.hpp`, `payload_types.hpp`, **`FrameProfiles.hpp`** | Mixed (mostly snake_case, one PascalCase) |
| **Python** | `frame_base.py`, `frame_headers.py`, `frame_profiles.py`, `payload_types.py` | snake_case ✓ |
| **TypeScript** | `frame_base.ts`, `frame_headers.ts`, `frame_profiles.ts`, `payload_types.ts`, `struct_base.ts` | snake_case |
| **JavaScript** | `frame_base.js`, `frame_headers.js`, `frame_profiles.js`, `payload_types.js`, `struct_base.js` | snake_case |
| **C#** | `frame_base.cs`, `frame_headers.cs`, `frame_parsers.cs`, `payload_types.cs`, **`FrameProfiles.cs`** | Mixed (mostly snake_case, one PascalCase) |

**Issues:**
- **Inconsistent C++ naming:** `FrameProfiles.hpp` uses PascalCase while all other boilerplate uses snake_case
- **Inconsistent C# naming:** `FrameProfiles.cs` uses PascalCase while all other boilerplate uses snake_case
- **Language idiom violations:**
  - C# conventionally uses PascalCase for filenames (should be `FrameBase.cs`, `FrameHeaders.cs`, etc.)
  - TypeScript/JavaScript often use kebab-case for filenames in modern projects

**Recommendations:**

**Option A: Universal snake_case (except where idioms require otherwise)**
```
C/C++: frame_base.h, frame_profiles.hpp (all snake_case)
Python: frame_base.py (already correct)
TypeScript/JS: frame-base.ts, frame-profiles.ts (kebab-case for modern idioms)
C#: FrameBase.cs, FrameProfiles.cs (PascalCase for C# idioms)
```

**Option B: Struct-frame branding prefix**
```
C/C++: sf_frame_base.h, sf_frame_profiles.hpp
Python: sf_frame_base.py
TypeScript/JS: sf-frame-base.ts, sf-frame-profiles.ts
C#: SFFrameBase.cs, SFFrameProfiles.cs
```

### 2. Generated Code File Naming

#### Current State

| Language | Generated Files | Pattern | Example |
|----------|----------------|---------|---------|
| **C** | `<proto_name>.sf.h` | `.sf.h` suffix | `serialization_test.sf.h` |
| **C++** | `<proto_name>.sf.hpp` | `.sf.hpp` suffix | `serialization_test.sf.hpp` |
| **Python** | `<proto_name>_sf.py` | `_sf.py` suffix | `serialization_test_sf.py` |
| **TypeScript** | `<proto_name>.sf.ts` | `.sf.ts` suffix | `serialization_test.sf.ts` |
| **JavaScript** | `<proto_name>.sf.js` | `.sf.js` suffix | `serialization_test.sf.js` |
| **C#** | `<proto_name>.sf.cs` | `.sf.cs` suffix | `serialization_test.sf.cs` |

**Issues:**
- **Inconsistent patterns:** Python uses underscore (`_sf.py`) while all others use dot (`.sf.ext`)
- **Proto naming not uniform:** Proto file `test_messages.proto` → `serialization_test.sf.*` (package name used, not file name)
- **Unclear branding:** `.sf.` doesn't clearly indicate "struct-frame" to new users
- **File extension ambiguity:** `.sf.ts` could be confused as a custom file type rather than TypeScript

**Recommendations:**

**Option A: Consistent dot notation with clearer suffix**
```
C: <proto_name>.structframe.h
C++: <proto_name>.structframe.hpp
Python: <proto_name>.structframe.py (or <proto_name>_structframe.py for Python idioms)
TypeScript: <proto_name>.structframe.ts
JavaScript: <proto_name>.structframe.js
C#: <proto_name>.structframe.cs
```

**Option B: Keep current but unify Python**
```
All languages: <proto_name>.sf.<ext>
Python change: test_messages_sf.py → test_messages.sf.py
```

**Option C: Clearer abbreviation**
```
All languages: <proto_name>.sfgen.<ext>
or: <proto_name>.generated.<ext>
```

### 3. Namespace and Import Patterns

#### Current State

**C++:**
```cpp
namespace FrameParsers { ... }  // Boilerplate
struct SerializationTestBasicTypesMessage { ... }  // Generated (no namespace, global scope)
```

**C#:**
```csharp
namespace StructFrame { ... }  // Boilerplate
namespace StructFrame.SerializationTest { ... }  // Generated
```

**Python:**
```python
# Boilerplate
from frame_base import fletcher_checksum
from frame_profiles import ProfileStandardReader

# Generated
from serialization_test_sf import SerializationTestBasicTypesMessage
```

**TypeScript:**
```typescript
// Boilerplate
import { MessageBase } from './struct_base';
import { fletcher_checksum } from './frame_base';

// Generated
export class serialization_test_BasicTypesMessage extends MessageBase { ... }
export enum serialization_testpriority { ... }
```

**JavaScript:**
```javascript
// Boilerplate
const { MessageBase } = require('./struct_base');

// Generated
class serialization_test_BasicTypesMessage extends MessageBase { ... }
const serialization_testpriority = Object.freeze({ ... });
```

**Issues:**

1. **Inconsistent package prefixing:**
   - TypeScript/JavaScript: `serialization_test_BasicTypesMessage` (snake_case prefix)
   - C++: `SerializationTestBasicTypesMessage` (PascalCase prefix)
   - Python: `SerializationTestBasicTypesMessage` (PascalCase prefix, no prefix in class name)

2. **TypeScript/JavaScript lowercase enums:**
   - `serialization_testpriority` violates TypeScript convention (should be `SerializationTestPriority`)

3. **No clear struct-frame branding in imports:**
   - Python: `from serialization_test_sf import ...` - `_sf` suffix is subtle
   - TypeScript: `import * as msg from './messages.sf'` - `.sf` is subtle
   - C: `#include "messages.sf.h"` - `.sf` is subtle

4. **C++ lacks namespace for generated code:**
   - Generated structs pollute global namespace
   - Should be in a package-specific namespace

**Recommendations:**

**For TypeScript/JavaScript:**
```typescript
// Current (problematic):
export enum serialization_testpriority { LOW = 0, ... }
export class serialization_test_BasicTypesMessage { ... }

// Recommended (follows TS/JS idioms):
export enum SerializationTestPriority { LOW = 0, ... }
export class SerializationTestBasicTypesMessage { ... }

// Or with namespace clarity:
export namespace SerializationTest {
    export enum Priority { LOW = 0, ... }
    export class BasicTypesMessage { ... }
}
```

**For C++:**
```cpp
// Current (problematic):
struct SerializationTestBasicTypesMessage { ... };

// Recommended (namespaced):
namespace StructFrame {
namespace SerializationTest {
    struct BasicTypesMessage { ... };
    enum class Priority : uint8_t { ... };
}
}

// Or with package name namespace:
namespace SerializationTest {
    struct BasicTypesMessage { ... };
}
```

**For Python:**
```python
# Current:
from serialization_test_sf import SerializationTestBasicTypesMessage

# Recommended (clearer branding):
from struct_frame.generated.serialization_test import BasicTypesMessage, Priority
# Or at minimum:
from serialization_test_structframe import BasicTypesMessage
```

**For C:**
```c
// Current:
#include "messages.sf.h"

// Recommended (clearer):
#include "messages.structframe.h"
// Or with prefix:
#include "sf_messages.h"
```

### 4. SDK Directory Structure

#### Current State

All languages use `struct_frame_sdk/` subdirectory:
```
src/struct_frame/boilerplate/
├── c/
├── cpp/
│   └── struct_frame_sdk/
├── csharp/
│   └── struct_frame_sdk/
├── js/
├── py/
│   └── struct_frame_sdk/
└── ts/
    └── struct_frame_sdk/
```

**Issues:**
- **Inconsistent:** C and JavaScript lack `struct_frame_sdk/` subdirectory
- **Not language idiomatic:** 
  - C# typically uses PascalCase directory names
  - TypeScript/JavaScript modern projects use kebab-case

**Recommendations:**

**Option A: Universal struct_frame_sdk with language idioms**
```
C: struct_frame_sdk/ (add it)
C++: struct_frame_sdk/ (keep as-is)
Python: struct_frame_sdk/ (keep as-is)
TypeScript: struct-frame-sdk/ (kebab-case)
JavaScript: struct-frame-sdk/ (kebab-case)
C#: StructFrameSdk/ (PascalCase)
```

**Option B: Keep current, add to C only**
```
Only add struct_frame_sdk/ to C to match other languages
Keep naming as-is for consistency
```

### 5. Test File Naming

#### Current State

| Language | Test Files | Helper Files |
|----------|-----------|--------------|
| **C** | N/A (compile tests) | `standard_test_data.h`, `test_codec.h`, `extended_test_data.h` |
| **C++** | `test_standard.cpp`, `test_extended.cpp` | `standard_test_data.hpp`, `test_codec.hpp` |
| **Python** | `test_standard.py`, `test_extended.py` | `standard_test_data.py`, `test_codec.py` |
| **TypeScript** | `test_standard.ts`, `test_extended.ts` | `standard_test_data.ts`, `test_codec.ts` |
| **JavaScript** | `test_standard.js`, `test_extended.js` | `standard_test_data.js`, `test_codec.js` |
| **C#** | `test_standard.cs`, `test_extended.cs` | `StandardTestData.cs`, `TestCodec.cs`, `ExtendedTestData.cs` |

**Issues:**
- **Inconsistent C# naming:** Test files use snake_case (`test_standard.cs`) but helper files use PascalCase (`StandardTestData.cs`)
- **Not language idiomatic:**
  - C# should use PascalCase for all files
  - Python test files should typically have `test_` prefix (already has it ✓)
  - TypeScript/JavaScript modern projects often use kebab-case

**Recommendations:**

**For C#:**
```csharp
// Current:
tests/csharp/test_standard.cs
tests/csharp/include/StandardTestData.cs

// Recommended:
tests/csharp/TestStandard.cs
tests/csharp/include/StandardTestData.cs
```

**For TypeScript/JavaScript (optional modernization):**
```
// Current:
test_standard.ts
standard_test_data.ts

// Modern convention:
test-standard.ts
standard-test-data.ts
```

### 6. Class and Variable Naming

#### Current State

**Python:**
```python
class SerializationTestBasicTypesMessage:
    msg_size = 204
    msg_id = 201
    
    def __init__(self, small_int: int = None, ...):
        self.small_int = small_int
```
✓ Follows Python conventions (PascalCase for classes, snake_case for variables)

**TypeScript:**
```typescript
export class serialization_test_BasicTypesMessage extends MessageBase {
  static readonly _size: number = 204;
  static readonly _msgid: number = 201;
}
```
✗ Should be `SerializationTestBasicTypesMessage` (PascalCase)
✗ `_size` should be `SIZE` or `size` (not private convention)

**JavaScript:**
```javascript
class serialization_test_BasicTypesMessage extends MessageBase {
  static _size = 204;
  static _msgid = 201;
}
```
✗ Same issues as TypeScript

**C++:**
```cpp
struct SerializationTestBasicTypesMessage : FrameParsers::MessageBase<...> {
    int8_t small_int;
    static constexpr size_t MSG_SIZE = 204;
    static constexpr uint16_t MSG_ID = 201;
};
```
✓ Follows C++ conventions (PascalCase for types, snake_case for members, UPPER_CASE for constants)

**C#:**
```csharp
public class SerializationTestBasicTypesMessage : IMessage {
    public const int MsgSize = 204;
    public const ushort MsgId = 201;
    
    public byte SmallInt { get; set; }
}
```
✓ Follows C# conventions (PascalCase throughout)

**C:**
```c
typedef struct SerializationTestBasicTypesMessage {
    int8_t small_int;
} SerializationTestBasicTypesMessage;

#define SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_SIZE 204
```
✓ Follows C conventions (snake_case for members, UPPER_CASE for macros)

**Issues:**
- **TypeScript/JavaScript class names:** Using snake_case prefix violates language conventions
- **TypeScript/JavaScript enum names:** Lowercase enum names violate conventions
- **Underscore prefix inconsistency:** `_size`, `_msgid` suggest private fields but they're public static

**Recommendations:**

**TypeScript/JavaScript:**
```typescript
// Current:
export enum serialization_testpriority { ... }
export class serialization_test_BasicTypesMessage { ... }

// Recommended:
export enum SerializationTestPriority { ... }
export class SerializationTestBasicTypesMessage {
  static readonly MSG_SIZE: number = 204;
  static readonly MSG_ID: number = 201;
  // Or:
  static readonly size: number = 204;
  static readonly msgId: number = 201;
}
```

### 7. Import Clarity and Struct-Frame Branding

#### Current User Experience

**Python:**
```python
# User imports - unclear this is struct-frame
from serialization_test_sf import SerializationTestMessage
from frame_profiles import ProfileStandardReader
```

**TypeScript:**
```typescript
// User imports - unclear this is struct-frame
import * as msg from './messages.sf';
import { ProfileStandardReader } from './frame_profiles';
```

**C++:**
```cpp
// User includes - unclear this is struct-frame
#include "messages.sf.hpp"
#include "FrameProfiles.hpp"
```

**C#:**
```csharp
// User imports - CLEAR this is struct-frame ✓
using StructFrame;
using StructFrame.SerializationTest;
```

**Issues:**
- Only C# makes it immediately clear that imports are from struct-frame
- Other languages require users to understand `.sf` suffix or file location
- No consistent branding across languages

**Recommendations:**

**Python - Add package structure:**
```python
# Recommended:
from struct_frame.generated.serialization_test import BasicTypesMessage
from struct_frame import ProfileStandardReader

# Or with clearer suffix:
from serialization_test_structframe import BasicTypesMessage
```

**TypeScript - Add namespace or clear naming:**
```typescript
// Option 1: Namespace
import * as StructFrame from '@struct-frame/core';
import * as Messages from './messages.structframe';

// Option 2: Clearer suffix
import * as msg from './messages.structframe';
import { ProfileStandardReader } from './struct-frame';
```

**C++ - Add namespace:**
```cpp
// Recommended:
#include "messages.structframe.hpp"  // or messages.sf.hpp
namespace StructFrame {
    namespace Messages {
        struct BasicTypesMessage { ... };
    }
}
```

---

## Summary of Recommendations

### Priority 1: Critical for Uniformity

1. **Unify generated file naming:**
   - Change Python from `_sf.py` to `.sf.py` OR
   - Change all to `.structframe.<ext>` for clarity

2. **Fix TypeScript/JavaScript naming:**
   - Change class names from snake_case to PascalCase
   - Change enum names from lowercase to PascalCase

3. **Fix C# test file naming:**
   - Change from `test_standard.cs` to `TestStandard.cs`

### Priority 2: Important for Language Idioms

4. **Adopt language-specific conventions:**
   - C#: Use PascalCase for all files
   - TypeScript/JS: Consider kebab-case for files
   - C++: Add namespaces for generated code

5. **Fix boilerplate inconsistencies:**
   - C++: Rename `FrameProfiles.hpp` to `frame_profiles.hpp`
   - C#: Either rename all to PascalCase or keep `FrameProfiles.cs` as exception

### Priority 3: Nice to Have for Clarity

6. **Improve struct-frame branding:**
   - Consider renaming `.sf` to `.structframe` for clarity
   - Add package/namespace prefixes where appropriate
   - Consider `struct-frame` or `StructFrame` in import paths

7. **Standardize SDK directories:**
   - Add `struct_frame_sdk/` to C
   - Consider language-idiomatic naming (kebab-case for TS/JS, PascalCase for C#)

---

## Proposed Changes Summary

### Minimal Changes (Quick Wins)

1. Python: `test_messages_sf.py` → `test_messages.sf.py`
2. C++: `FrameProfiles.hpp` → `frame_profiles.hpp`
3. C#: `FrameProfiles.cs` → `frame_profiles.cs` OR all others to PascalCase
4. TypeScript/JavaScript: Fix all class and enum names to PascalCase
5. C#: `test_standard.cs` → `TestStandard.cs`

### Medium Changes (Better Idioms)

6. Add namespaces to C++ generated code
7. Standardize C# filenames to PascalCase
8. Consider kebab-case for TypeScript/JavaScript files

### Major Changes (Better Branding)

9. Consider `.sf` → `.structframe` for all generated files
10. Add `struct_frame` package structure for Python
11. Consider namespace/package prefixes for better import clarity

---

## Implementation Priority

### Phase 1: Fix Breaking Inconsistencies
- TypeScript/JavaScript: class and enum casing
- Python: generated file suffix unification
- C#: test file naming

### Phase 2: Language Idiom Adherence
- C++ namespaces for generated code
- C# file naming consistency
- C++ boilerplate file naming

### Phase 3: Branding Improvements
- Consider `.structframe` extension
- Package structure improvements
- Import path clarity

---

## Conclusion

The struct-frame codebase has good overall structure but suffers from inconsistencies that could confuse users and violate language idioms. The recommended changes focus on:

1. **Uniformity** - Same patterns across languages where appropriate
2. **Language Idioms** - Following established conventions for each language
3. **Clear Branding** - Making it obvious that code is from struct-frame

Implementing these changes will improve developer experience, reduce confusion, and make the codebase more maintainable.
