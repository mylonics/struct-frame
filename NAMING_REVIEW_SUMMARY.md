# Naming Convention Review - Executive Summary

**Date:** January 13, 2026  
**Status:** Complete  
**Full Review:** See `NAMING_REVIEW.md`

---

## Overview

This review examined naming conventions across all struct-frame components in 7 languages (C, C++, Python, TypeScript, JavaScript, C#, GraphQL) to ensure:
- ✓ Uniformity between languages
- ✓ Language idiom adherence  
- ✓ Clear struct-frame branding in imports

## Top 5 Issues Identified

### 1. TypeScript/JavaScript Naming Violations 🔴 CRITICAL
**Issue:** Class and enum names use incorrect casing
```typescript
// Current (WRONG):
export enum serialization_testpriority { ... }
export class serialization_test_BasicTypesMessage { ... }

// Should be:
export enum SerializationTestPriority { ... }
export class SerializationTestBasicTypesMessage { ... }
```
**Impact:** Violates TypeScript/JavaScript conventions, confuses users  
**Priority:** P1 - Fix immediately

### 2. Inconsistent Generated File Naming 🟡 HIGH
**Issue:** Python uses different pattern than all other languages
```
C:          messages.sf.h
C++:        messages.sf.hpp
TypeScript: messages.sf.ts
JavaScript: messages.sf.js
C#:         messages.sf.cs
Python:     messages_sf.py     ← Different!
```
**Impact:** Inconsistent developer experience across languages  
**Priority:** P1 - Unify pattern

### 3. C++ Generated Code Lacks Namespaces 🟡 HIGH
**Issue:** Generated structs pollute global namespace
```cpp
// Current (pollutes global scope):
struct SerializationTestBasicTypesMessage { ... };

// Recommended:
namespace StructFrame {
namespace SerializationTest {
    struct BasicTypesMessage { ... };
}
}
```
**Impact:** Name collisions, not idiomatic C++  
**Priority:** P2 - Add in next major version

### 4. Unclear Struct-Frame Branding 🟡 MEDIUM
**Issue:** Not obvious that imports are from struct-frame
```python
# Current:
from serialization_test_sf import Message  # What's "sf"?

# Better:
from struct_frame.generated.serialization_test import Message
# Or:
from serialization_test_structframe import Message
```
**Impact:** Users may not realize they're importing struct-frame code  
**Priority:** P3 - Consider for next major version

### 5. Mixed Case Conventions in Boilerplate 🟢 LOW
**Issue:** Some files use PascalCase, most use snake_case
```
C++:  frame_base.hpp ✓
      FrameProfiles.hpp ✗ (inconsistent)

C#:   frame_base.cs ✗ (should be PascalCase)
      FrameProfiles.cs ✓ (correct for C#)
```
**Impact:** Minor confusion, not following C# idioms  
**Priority:** P2 - Standardize within language conventions

---

## Quick Win Recommendations

### Immediate (Can do now, minimal breaking changes):

1. **Fix TypeScript/JavaScript casing** - Update code generators
2. **Unify Python naming** - Change `_sf.py` to `.sf.py`
3. **Fix C# test files** - Rename to PascalCase
4. **Standardize C++ boilerplate** - Rename `FrameProfiles.hpp` to `frame_profiles.hpp`

### Next Version (Breaking changes acceptable):

5. **Add C++ namespaces** - Wrap generated code
6. **Improve branding** - Consider `.structframe` extension
7. **Standardize C# files** - All boilerplate to PascalCase
8. **Add Python package** - `struct_frame.generated.*`

---

## Implementation Phases

### Phase 1: Fix Critical Issues (Week 1)
- [ ] TypeScript/JavaScript: Fix class/enum casing in generators
- [ ] Python: Change `_sf.py` to `.sf.py` in py_gen.py
- [ ] C#: Rename test files to PascalCase
- [ ] Update documentation with new patterns

### Phase 2: Language Idioms (Week 2-3)
- [ ] C++: Add namespace support in cpp_gen.py
- [ ] C++: Rename FrameProfiles.hpp → frame_profiles.hpp
- [ ] C#: Standardize all boilerplate to PascalCase
- [ ] TypeScript/JS: Consider kebab-case for files

### Phase 3: Branding Improvements (Future)
- [ ] Evaluate `.structframe` vs `.sf` extension
- [ ] Add Python package structure
- [ ] Consider npm package scoping (`@struct-frame/...`)
- [ ] Improve import path clarity

---

## Language-Specific Recommendations

| Language | Current State | Recommended Change | Priority |
|----------|--------------|-------------------|----------|
| **TypeScript** | `serialization_test_BasicTypesMessage` | `SerializationTestBasicTypesMessage` | P1 🔴 |
| **JavaScript** | `serialization_test_BasicTypesMessage` | `SerializationTestBasicTypesMessage` | P1 🔴 |
| **Python** | `messages_sf.py` | `messages.sf.py` | P1 🔴 |
| **C++** | No namespace for generated code | Add `namespace StructFrame::Package` | P2 🟡 |
| **C#** | `test_standard.cs` | `TestStandard.cs` | P2 🟡 |
| **C** | (No issues) | ✓ Already following conventions | - |

---

## Impact Assessment

### Breaking Changes Required:
- TypeScript/JavaScript class name changes (imports will break)
- Python filename changes (imports will break)
- C++ namespace additions (includes will break)

### Migration Path:
1. Update code generators
2. Regenerate all test code
3. Update documentation/examples
4. Provide migration guide for users
5. Version bump (minor or major depending on scope)

---

## Files to Modify

### Code Generators:
- `src/struct_frame/ts_gen.py` - Fix class/enum casing
- `src/struct_frame/js_gen.py` - Fix class/enum casing  
- `src/struct_frame/py_gen.py` - Change filename pattern
- `src/struct_frame/cpp_gen.py` - Add namespace support
- `src/struct_frame/csharp_gen.py` - Ensure PascalCase

### Boilerplate:
- `src/struct_frame/boilerplate/cpp/FrameProfiles.hpp` → `frame_profiles.hpp`
- `src/struct_frame/boilerplate/csharp/frame_*.cs` → `Frame*.cs` (all to PascalCase)

### Tests:
- `tests/csharp/test_*.cs` → `tests/csharp/Test*.cs`

### Documentation:
- Update all examples in `docs/getting-started/language-usage.md`
- Update `docs/getting-started/code-generation.md`
- Add migration guide

---

## Next Steps

1. **Review this summary** with maintainers
2. **Prioritize changes** based on breaking change tolerance
3. **Create issues** for each phase
4. **Implement Phase 1** (critical fixes)
5. **Update tests** and validate
6. **Release with migration guide**

---

## Questions for Maintainers

1. **Breaking changes acceptable?** Can we fix TypeScript/JavaScript casing now?
2. **Extension preference?** Keep `.sf` or change to `.structframe`?
3. **C++ namespaces?** Add now or wait for v2.0?
4. **Python package structure?** Add `struct_frame.generated.*` package?
5. **Timeline?** When can we implement these changes?

---

**Full detailed analysis available in:** `NAMING_REVIEW.md`
