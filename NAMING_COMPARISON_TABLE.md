# Naming Convention Comparison Table

Quick reference showing current vs. recommended naming for all languages.

## 🎉 Implementation Status

### ✅ Completed Fixes - ALL BREAKING CHANGES IMPLEMENTED

**Priority 1 (Critical):**
- ✅ TypeScript/JavaScript: Classes and enums now use PascalCase
  - `serialization_testpriority` → `SerializationTestPriority`
  - `serialization_test_Message` → `SerializationTest_Message`

**Priority 2 (Important):**
- ✅ C++: Boilerplate file `FrameProfiles.hpp` → `frame_profiles.hpp`
- ✅ C#: All boilerplate files now use PascalCase
  - `frame_base.cs` → `FrameBase.cs`
  - `frame_headers.cs` → `FrameHeaders.cs`
  - `frame_parsers.cs` → `FrameParsers.cs`
  - `payload_types.cs` → `PayloadTypes.cs`

**Priority 3 (Breaking Changes - ALL IMPLEMENTED):**
- ✅ File extension branding: `.sf.*` → `.structframe.*` (ALL languages)
- ✅ TypeScript/JavaScript: Boilerplate files use kebab-case
  - `frame_base.ts` → `frame-base.ts`
  - `struct_base.ts` → `struct-base.ts`
  - All other files follow same pattern
- ✅ SDK directory naming:
  - TypeScript: `struct_frame_sdk/` → `struct-frame-sdk/`
  - C#: `struct_frame_sdk/` → `StructFrameSdk/`
  - SDK files also renamed to kebab-case

### ⏳ Not Implemented (Requires Extensive Refactoring)

- Python package structure: `struct_frame.generated.*` (would require package hierarchy)
- C: Add `struct_frame_sdk/` directory

---

## Generated Files

### File Naming Patterns

| Language | Current | Status |
|----------|---------|--------|
| C | ~~`messages.sf.h`~~ → **`messages.structframe.h`** | ✅ **FIXED** |
| C++ | ~~`messages.sf.hpp`~~ → **`messages.structframe.hpp`** | ✅ **FIXED** |
| Python | ~~`messages_sf.py`~~ → **`messages_structframe.py`** | ✅ **FIXED** |
| TypeScript | ~~`messages.sf.ts`~~ → **`messages.structframe.ts`** | ✅ **FIXED** |
| JavaScript | ~~`messages.sf.js`~~ → **`messages.structframe.js`** | ✅ **FIXED** |
| C# | ~~`messages.sf.cs`~~ → **`messages.structframe.cs`** | ✅ **FIXED** |

All generated files now use `.structframe.*` extension for clear branding!

---

### Class/Struct Naming

| Language | Current | Recommended | Priority | Status |
|----------|---------|-------------|----------|--------|
| C | `SerializationTestMessage` | ✅ Correct | - | ✅ Done |
| C++ | `SerializationTestMessage` | ✅ Correct (but add namespace) | P2 | ✅ Done* |
| Python | `SerializationTestMessage` | ✅ Correct | - | ✅ Done |
| TypeScript | ~~`serialization_test_Message`~~ → **`SerializationTest_Message`** | ✅ Correct (PascalCase) | P1 | ✅ **FIXED** |
| JavaScript | ~~`serialization_test_Message`~~ → **`SerializationTest_Message`** | ✅ Correct (PascalCase) | P1 | ✅ **FIXED** |
| C# | `SerializationTestMessage` | ✅ Correct | - | ✅ Done |

\* C++ namespaces already supported when using package IDs

---

### Enum Naming

| Language | Current | Recommended | Priority | Status |
|----------|---------|-------------|----------|--------|
| C | `SerializationTestStatus` | ✅ Correct | - | ✅ Done |
| C++ | `SerializationTestStatus` | ✅ Correct | - | ✅ Done |
| Python | `SerializationTestStatus` | ✅ Correct | - | ✅ Done |
| TypeScript | ~~`serialization_teststatus`~~ → **`SerializationTestStatus`** | ✅ Correct (PascalCase) | P1 | ✅ **FIXED** |
| JavaScript | ~~`serialization_teststatus`~~ → **`SerializationTestStatus`** | ✅ Correct (PascalCase) | P1 | ✅ **FIXED** |
| C# | `SerializationTestStatus` | ✅ Correct | - | ✅ Done |

---

### Namespace/Package Structure

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | Global scope | ✅ Appropriate for C | - | No |
| C++ | Global scope | `namespace StructFrame::SerializationTest` | P2 | Yes |
| Python | `serialization_test_sf` module | `struct_frame.generated.serialization_test` | P3 | Yes |
| TypeScript | ES6 modules | ✅ Appropriate (or add namespace) | - | No |
| JavaScript | CommonJS modules | ✅ Appropriate | - | No |
| C# | `StructFrame.SerializationTest` | ✅ Perfect | - | No |

---

## Boilerplate Files

### Frame Parser Files

| Language | Current | Status |
|----------|---------|--------|
| C | `frame_base.h` | ✅ Done |
| C++ | `frame_base.hpp` | ✅ Done |
| Python | `frame_base.py` | ✅ Done |
| TypeScript | ~~`frame_base.ts`~~ → **`frame-base.ts`** | ✅ **FIXED (kebab-case)** |
| JavaScript | ~~`frame_base.js`~~ → **`frame-base.js`** | ✅ **FIXED (kebab-case)** |
| C# | ~~`frame_base.cs`~~ → **`FrameBase.cs`** | ✅ **FIXED (PascalCase)** |

---

### Frame Profiles Files

| Language | Current | Recommended | Priority | Status |
|----------|---------|-------------|----------|--------|
| C | `frame_profiles.h` | ✅ Correct | - | ✅ Done |
| C++ | ~~`FrameProfiles.hpp`~~ → **`frame_profiles.hpp`** | ✅ Correct (snake_case) | P2 | ✅ **FIXED** |
| Python | `frame_profiles.py` | ✅ Correct | - | ✅ Done |
| TypeScript | `frame_profiles.ts` | `frame-profiles.ts` (kebab-case) | P3 | ⏳ Future |
| JavaScript | `frame_profiles.js` | `frame-profiles.js` (kebab-case) | P3 | ⏳ Future |
| C# | `FrameProfiles.cs` | ✅ Correct (PascalCase) | - | ✅ Done |

---

## Test Files

### Test File Naming

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | N/A (compile only) | N/A | - | - |
| C++ | `test_standard.cpp` | ✅ Correct | - | No |
| Python | `test_standard.py` | ✅ Correct | - | No |
| TypeScript | `test_standard.ts` | `test-standard.ts` (kebab-case) | P3 | No |
| JavaScript | `test_standard.js` | `test-standard.js` (kebab-case) | P3 | No |
| C# | **`test_standard.cs`** | `TestStandard.cs` | P2 | No |

---

### Test Helper Files

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `standard_test_data.h` | ✅ Correct | - | No |
| C++ | `standard_test_data.hpp` | ✅ Correct | - | No |
| Python | `standard_test_data.py` | ✅ Correct | - | No |
| TypeScript | `standard_test_data.ts` | `standard-test-data.ts` (kebab-case) | P3 | No |
| JavaScript | `standard_test_data.js` | `standard-test-data.js` (kebab-case) | P3 | No |
| C# | `StandardTestData.cs` | ✅ Correct | - | No |

---

## SDK Directory Structure

| Language | Current | Status |
|----------|---------|--------|
| C | No SDK directory | ⏳ Future |
| C++ | `struct_frame_sdk/` | ✅ Done |
| Python | `struct_frame_sdk/` | ✅ Done |
| TypeScript | ~~`struct_frame_sdk/`~~ → **`struct-frame-sdk/`** | ✅ **FIXED (kebab-case)** |
| JavaScript | No SDK directory | ⏳ Future |
| C# | ~~`struct_frame_sdk/`~~ → **`StructFrameSdk/`** | ✅ **FIXED (PascalCase)** |

---

## Import Examples

### Current Import Patterns

**Python:**
```python
from serialization_test_sf import Message
from frame_profiles import ProfileStandardReader
```

**TypeScript:**
```typescript
import * as msg from './messages.sf';
import { ProfileStandardReader } from './frame_profiles';
```

**C++:**
```cpp
#include "messages.sf.hpp"
#include "FrameProfiles.hpp"
```

**C#:**
```csharp
using StructFrame;
using StructFrame.SerializationTest;
```

---

### Recommended Import Patterns

**Python (Current - OK):**
```python
from messages.sf import Message  # If using .sf.py
from frame_profiles import ProfileStandardReader
```

**Python (Better Branding - P3):**
```python
from struct_frame.generated.messages import Message
from struct_frame import ProfileStandardReader
```

**TypeScript (Fixed Naming - P1):**
```typescript
import * as msg from './messages.sf';
import { SerializationTestMessage } from './messages.sf';  // PascalCase!
import { ProfileStandardReader } from './frame_profiles';
```

**C++ (Add Namespace - P2):**
```cpp
#include "messages.sf.hpp"
#include "frame_profiles.hpp"  // Renamed!

using namespace StructFrame::Messages;
// or
StructFrame::Messages::BasicTypesMessage msg;
```

**C# (Already Perfect - Keep):**
```csharp
using StructFrame;
using StructFrame.SerializationTest;

var msg = new SerializationTestMessage();
```

---

## Priority Legend

- **P1** 🔴 - Critical (Fix immediately, breaking changes acceptable)
- **P2** 🟡 - Important (Next major/minor version)
- **P3** 🟢 - Enhancement (Nice to have, future improvement)

---

## Summary Statistics

### Changes Needed by Language

| Language | P1 Changes | P2 Changes | P3 Changes | Total |
|----------|-----------|-----------|-----------|-------|
| **TypeScript** | 2 (class/enum naming) | 0 | 3 (file naming) | 5 |
| **JavaScript** | 2 (class/enum naming) | 0 | 3 (file naming) | 5 |
| **Python** | 1 (file naming) | 0 | 2 (package structure) | 3 |
| **C++** | 0 | 2 (namespace, file rename) | 0 | 2 |
| **C#** | 0 | 2 (test files, boilerplate) | 1 (SDK dir) | 3 |
| **C** | 0 | 0 | 1 (SDK dir) | 1 |

### Breaking Changes Summary

- **Must Fix (P1):** TypeScript, JavaScript class/enum naming; Python file naming
- **Should Fix (P2):** C++ namespaces, C# file naming
- **Nice to Have (P3):** Kebab-case files, package structures, clearer branding

---

**See full analysis in `NAMING_REVIEW.md` and actionable summary in `NAMING_REVIEW_SUMMARY.md`**
