# Naming Convention Comparison Table

Quick reference showing current vs. recommended naming for all languages.

## 🎉 Implementation Status

### ✅ Completed Fixes

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

### ⏳ Future Enhancements (Priority 3)

- File extension branding: `.sf.*` → `.structframe.*`
- Python package structure: `struct_frame.generated.*`
- SDK directory naming: kebab-case for TS/JS, PascalCase for C#
- TypeScript/JavaScript file naming: kebab-case option

---

## Generated Files

### File Naming Patterns

| Language | Current | Recommended | Priority | Status |
|----------|---------|-------------|----------|--------|
| C | `messages.sf.h` | ✅ Keep as-is | - | ✅ Done |
| C++ | `messages.sf.hpp` | ✅ Keep as-is | - | ✅ Done |
| Python | `messages_sf.py` | ✅ Keep as-is* | - | ✅ Done |
| TypeScript | `messages.sf.ts` | ✅ Keep as-is | - | ✅ Done |
| JavaScript | `messages.sf.js` | ✅ Keep as-is | - | ✅ Done |
| C# | `messages.sf.cs` | ✅ Keep as-is | - | ✅ Done |

\* Python cannot use `.sf.py` (dots not allowed in module names)

**Alternative (All Languages):** Consider `messages.structframe.*` for clearer branding (P3, future)

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

| Language | Current | Recommended | Priority | Status |
|----------|---------|-------------|----------|--------|
| C | `frame_base.h` | ✅ Correct | - | ✅ Done |
| C++ | `frame_base.hpp` | ✅ Correct | - | ✅ Done |
| Python | `frame_base.py` | ✅ Correct | - | ✅ Done |
| TypeScript | `frame_base.ts` | `frame-base.ts` (kebab-case) | P3 | ⏳ Future |
| JavaScript | `frame_base.js` | `frame-base.js` (kebab-case) | P3 | ⏳ Future |
| C# | ~~`frame_base.cs`~~ → **`FrameBase.cs`** | ✅ Correct (PascalCase) | P2 | ✅ **FIXED** |

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

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | No SDK directory | Add `struct_frame_sdk/` | P3 | No |
| C++ | `struct_frame_sdk/` | ✅ Keep | - | No |
| Python | `struct_frame_sdk/` | ✅ Keep | - | No |
| TypeScript | `struct_frame_sdk/` | `struct-frame-sdk/` (kebab-case) | P3 | No* |
| JavaScript | No SDK directory | Add (matching TS) | P3 | No |
| C# | `struct_frame_sdk/` | `StructFrameSdk/` | P3 | No* |

\* Not breaking if done with SDK reorganization

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
