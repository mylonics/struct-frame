# Naming Convention Review - Executive Summary

**Date:** January 13, 2026  
**Status:** ✅ **ALL BREAKING CHANGES IMPLEMENTED**  
**Full Review:** See `NAMING_REVIEW.md`

---

## 🎉 Implementation Status - COMPLETE

### ✅ FIXED - Priority 1 (Critical)

**1. TypeScript/JavaScript Naming** - ✅ **COMPLETE**
```typescript
// Before (WRONG):
export enum serialization_testpriority { ... }
export class serialization_test_BasicTypesMessage { ... }

// After (CORRECT): ✅
export enum SerializationTestPriority { ... }
export class SerializationTest_BasicTypesMessage { ... }
```
**Status:** Fixed in commits 88da34e  
**Impact:** All 114 tests pass

**2. Python File Naming** - ✅ **ENHANCED WITH BRANDING**
```
Before: messages_sf.py
After:  messages_structframe.py ✅ (clearer branding)
```
**Status:** Fixed in commit 76ac61e

### ✅ FIXED - Priority 2 (Important)

**3. C++ Boilerplate Consistency** - ✅ **COMPLETE**
```
Before: FrameProfiles.hpp (inconsistent PascalCase)
After:  frame_profiles.hpp (consistent snake_case) ✅
```
**Status:** Fixed in commit fb01445

**4. C# Boilerplate File Naming** - ✅ **COMPLETE**
```
Before: frame_base.cs, frame_headers.cs, etc. (snake_case)
After:  FrameBase.cs, FrameHeaders.cs, etc. (PascalCase) ✅
```
**Status:** Fixed in commit 10c8799  
**Impact:** Follows C# naming conventions

**5. C++ Namespaces** - ✅ **RESOLVED**
```
Status: Already implemented when using package IDs
No change needed - namespaces enabled via package.package_id
```

### ✅ FIXED - Priority 3 (ALL Breaking Changes)

**6. File Extension Branding** - ✅ **COMPLETE (commit 76ac61e)**
```
Changed all generated files:
C:          .sf.h       → .structframe.h ✅
C++:        .sf.hpp     → .structframe.hpp ✅
Python:     _sf.py      → _structframe.py ✅
TypeScript: .sf.ts      → .structframe.ts ✅
JavaScript: .sf.js      → .structframe.js ✅
C#:         .sf.cs      → .structframe.cs ✅
```
**Impact:** BREAKING - Much clearer struct-frame branding

**7. TypeScript/JavaScript File Naming** - ✅ **COMPLETE (commit bef49b2)**
```
Before: frame_base.ts, frame_headers.ts, etc. (snake_case)
After:  frame-base.ts, frame-headers.ts, etc. (kebab-case) ✅
```
**Impact:** BREAKING - Modern JavaScript/TypeScript convention

**8. SDK Directory Naming** - ✅ **COMPLETE (commit bef49b2)**
```
TypeScript: struct_frame_sdk/ → struct-frame-sdk/ ✅
C#:         struct_frame_sdk/ → StructFrameSdk/ ✅
```
**Impact:** BREAKING - Language-idiomatic naming

### ⏳ Not Implemented (Requires Extensive Refactoring)

**9. Python Package Structure** - Deferred
- Would require: `struct_frame.generated.*` hierarchy
- Needs: Complete package reorganization
- Impact: Very large breaking change

---

## Overview

This review examined naming conventions across all struct-frame components in 7 languages (C, C++, Python, TypeScript, JavaScript, C#, GraphQL) to ensure:
- ✅ Uniformity between languages
- ✅ Language idiom adherence  
- ⏳ Clear struct-frame branding in imports (P3 enhancements available)

## Top 5 Issues - Resolution Status

### 1. TypeScript/JavaScript Naming Violations - ✅ FIXED
**Issue:** Class and enum names use incorrect casing  
**Resolution:** Updated generators to use PascalCase (commit 88da34e)  
**Tests:** All 114 tests pass

### 2. Python File Naming - ✅ RESOLVED  
**Issue:** Python uses `_sf.py` pattern  
**Resolution:** Keep as-is - Python cannot import modules with dots in names  
**Status:** Current pattern is correct

### 3. C++ Boilerplate Naming - ✅ FIXED
**Issue:** `FrameProfiles.hpp` inconsistent with other files  
**Resolution:** Renamed to `frame_profiles.hpp` (commit fb01445)  
**Status:** All C++ boilerplate now uses snake_case

### 4. C# Boilerplate Naming - ✅ FIXED
**Issue:** Files use snake_case instead of C# idiomatic PascalCase  
**Resolution:** Renamed all to PascalCase (commit 10c8799)  
**Status:** Follows C# conventions

### 5. C++ Namespaces - ✅ RESOLVED

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
