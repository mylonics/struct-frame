# Naming Convention Comparison Table

Quick reference showing current vs. recommended naming for all languages.

---

## Generated Files

### File Naming Patterns

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `messages.sf.h` | ✅ Keep as-is | - | No |
| C++ | `messages.sf.hpp` | ✅ Keep as-is | - | No |
| Python | `messages_sf.py` | `messages.sf.py` | **P1** | Yes |
| TypeScript | `messages.sf.ts` | ✅ Keep as-is | - | No |
| JavaScript | `messages.sf.js` | ✅ Keep as-is | - | No |
| C# | `messages.sf.cs` | ✅ Keep as-is | - | No |

**Alternative (All Languages):** Consider `messages.structframe.*` for clearer branding (P3, breaking)

---

### Class/Struct Naming

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `SerializationTestMessage` | ✅ Correct | - | No |
| C++ | `SerializationTestMessage` | ✅ Correct (but add namespace) | P2 | Yes |
| Python | `SerializationTestMessage` | ✅ Correct | - | No |
| TypeScript | `serialization_test_Message` | `SerializationTestMessage` | **P1** | Yes |
| JavaScript | `serialization_test_Message` | `SerializationTestMessage` | **P1** | Yes |
| C# | `SerializationTestMessage` | ✅ Correct | - | No |

---

### Enum Naming

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `SerializationTestStatus` | ✅ Correct | - | No |
| C++ | `SerializationTestStatus` | ✅ Correct | - | No |
| Python | `SerializationTestStatus` | ✅ Correct | - | No |
| TypeScript | `serialization_teststatus` | `SerializationTestStatus` | **P1** | Yes |
| JavaScript | `serialization_teststatus` | `SerializationTestStatus` | **P1** | Yes |
| C# | `SerializationTestStatus` | ✅ Correct | - | No |

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

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `frame_base.h` | ✅ Correct | - | No |
| C++ | `frame_base.hpp` | ✅ Correct | - | No |
| Python | `frame_base.py` | ✅ Correct | - | No |
| TypeScript | `frame_base.ts` | `frame-base.ts` (kebab-case) | P3 | No* |
| JavaScript | `frame_base.js` | `frame-base.js` (kebab-case) | P3 | No* |
| C# | `frame_base.cs` | `FrameBase.cs` | P2 | No* |

\* Not breaking if done with boilerplate regeneration

---

### Frame Profiles Files

| Language | Current | Recommended | Priority | Breaking? |
|----------|---------|-------------|----------|-----------|
| C | `frame_profiles.h` | ✅ Correct | - | No |
| C++ | **`FrameProfiles.hpp`** | `frame_profiles.hpp` | P2 | No* |
| Python | `frame_profiles.py` | ✅ Correct | - | No |
| TypeScript | `frame_profiles.ts` | `frame-profiles.ts` (kebab-case) | P3 | No* |
| JavaScript | `frame_profiles.js` | `frame-profiles.js` (kebab-case) | P3 | No* |
| C# | **`FrameProfiles.cs`** | ✅ Correct (PascalCase is C# idiom) | - | No |

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
