## Naming Conventions

struct-frame follows language-specific naming conventions while maintaining consistency in core concepts across all supported languages.

### File Naming

#### Boilerplate Files
Each language follows its idiomatic file naming convention:

- **C/C++**: `frame_base.h/.hpp`, `frame_headers.h/.hpp`, `frame_profiles.h/.hpp` (snake_case)
- **Python**: `frame_base.py`, `frame_headers.py`, `frame_profiles.py` (snake_case, per PEP 8)
- **TypeScript/JavaScript**: `frame-base.ts/.js`, `frame-headers.ts/.js` (kebab-case, Node.js style)
- **C#**: `FrameBase.cs`, `FrameHeaders.cs`, `FrameProfiles.cs` (PascalCase, per .NET conventions)

#### Generated Files
Generated message definitions use the `.structframe.` pattern to clearly distinguish them from hand-written code:

- **C**: `{package_name}.structframe.h` (e.g., `serialization_test.structframe.h`)
- **C++**: `{package_name}.structframe.hpp` (e.g., `serialization_test.structframe.hpp`)
- **TypeScript**: `{package_name}.structframe.ts` (e.g., `serialization_test.structframe.ts`)
- **JavaScript**: `{package_name}.structframe.js` (e.g., `serialization_test.structframe.js`)
- **C#**: `{package_name}.structframe.cs` (e.g., `serialization_test.structframe.cs`)
- **Python**: `{package_name}.py` in `struct_frame/generated/` directory (uses directory structure instead)

The `.structframe.` extension makes it immediately obvious that a file contains struct-frame generated code.

### Class and Type Naming

#### Boilerplate Classes
Core struct-frame types use PascalCase consistently across all languages:

- `FrameMsgInfo` - Parse result structure
- `FrameChecksum` - Checksum result
- `MessageBase` - Base class for messages (C++/TypeScript/Python)
- `ProfileStandardWriter`, `ProfileSensorWriter`, etc. - Frame encoder/writer classes

#### Generated Message Types
Message types are prefixed with the package name in PascalCase:

**C++:**
```cpp
struct SerializationTestBasicTypesMessage : MessageBase<...> { ... }
enum class SerializationTestPriority : uint8_t { ... }
```

**Python:**
```python
class SerializationTest_BasicTypesMessage:
    pass

class SerializationTestPriority(Enum):
    pass
```

**TypeScript:**
```typescript
export class SerializationTest_BasicTypesMessage extends MessageBase { ... }
export enum SerializationTestPriority { ... }
```

**C#:**
```csharp
public class SerializationTestBasicTypesMessage : IStructFrameMessage { ... }
public enum SerializationTestPriority : byte { ... }
```

*Note: Python and TypeScript include an underscore (`_`) separator while C++ and C# do not. This is a historical artifact that may be unified in a future major version.*

### Function and Method Naming

Functions follow language-specific conventions:

- **C/C++/Python**: `fletcher_checksum()`, `parse_buffer()` (snake_case)
- **C#**: `FletcherChecksum()`, `ParseBuffer()` (PascalCase, per .NET conventions)
- **TypeScript/JavaScript**: Currently mixed; standardization to camelCase is planned

### Field and Property Naming

Proto field names are preserved in snake_case across all languages:

```protobuf
message Example {
    int32 small_int = 1;
    uint32 medium_uint = 2;
}
```

Becomes:

**C/C++/Python/TypeScript/JavaScript:**
```
small_int, medium_uint  // snake_case preserved
```

**C#:**
```csharp
public int small_int { get; set; }  // Currently snake_case
// Note: Future versions may use PascalCase (SmallInt) for .NET conventions
```

### Namespace and Package Structure

#### C++
```cpp
namespace FrameParsers {
    // Boilerplate code (parsers, encoders, utilities)
}

// Generated message structs in global namespace
struct SerializationTestBasicTypesMessage { ... }
```

#### Python
```python
# Boilerplate package
from frame_profiles import ProfileStandardWriter

# Generated code in nested package
from struct_frame.generated.serialization_test import SerializationTest_BasicTypesMessage
```

#### C#
```csharp
namespace StructFrame
{
    // Boilerplate code
}

namespace StructFrame.SerializationTest
{
    // Generated messages for serialization_test.proto
}
```

#### TypeScript/JavaScript
Uses ES6 modules with exports; no explicit namespaces:
```typescript
export class MessageBase { ... }
export class SerializationTest_BasicTypesMessage { ... }
```

### SDK Directory Naming

SDK helper directories follow the same naming conventions as files:

- **C/C++**: `struct_frame_sdk/` (snake_case)
- **Python**: `struct_frame_sdk/` (snake_case)
- **TypeScript/JavaScript**: `struct-frame-sdk/` (kebab-case)
- **C#**: `StructFrameSdk/` (PascalCase)

### Import Examples

**C++:**
```cpp
#include "frame_base.hpp"
#include "serialization_test.structframe.hpp"

using namespace FrameParsers;

ProfileStandardWriter writer(buffer, buffer_size);
SerializationTestBasicTypesMessage msg;
```

**Python:**
```python
from frame_profiles import ProfileStandardWriter
from struct_frame.generated.serialization_test import (
    SerializationTest_BasicTypesMessage,
    SerializationTestPriority
)

writer = ProfileStandardWriter(buffer_size=1024)
msg = SerializationTest_BasicTypesMessage()
```

**TypeScript:**
```typescript
import { ProfileStandardWriter } from './frame-profiles';
import { 
    SerializationTest_BasicTypesMessage,
    SerializationTestPriority 
} from './serialization_test.structframe';

const writer = new ProfileStandardWriter(1024);
const msg = new SerializationTest_BasicTypesMessage();
```

**C#:**
```csharp
using StructFrame;
using StructFrame.SerializationTest;

var writer = new ProfileStandardWriter(1024);
var msg = new SerializationTestBasicTypesMessage();
```

### Rationale

The naming conventions balance three goals:

1. **Language Idioms**: Each language follows its community's established conventions
2. **Cross-Language Consistency**: Core concepts use the same names across languages (e.g., `FrameMsgInfo`, `ProfileStandard`)
3. **Clarity**: The `.structframe.` extension and package/namespace structure make it clear when importing struct-frame code

### Future Considerations

Future major versions may include:

- Standardizing message type naming (with or without underscore separator)
- C# property naming to use PascalCase per .NET conventions
- TypeScript/JavaScript function naming standardization to camelCase

## Development Guide

### Release Process (Automated)

The repository now has an automated release pipeline that handles version bumping, changelog updates, git tagging, and PyPI publishing.

**To create a new release:**

1. Navigate to the [Actions tab](https://github.com/mylonics/struct-frame/actions/workflows/release.yml) in GitHub
2. Click "Run workflow"
3. Select the version bump type:
   - **patch**: Bug fixes and minor changes (e.g., 0.0.50 → 0.0.51)
   - **minor**: New features (e.g., 0.0.50 → 0.1.0)
   - **major**: Breaking changes (e.g., 0.0.50 → 1.0.0)
4. Click "Run workflow"

The pipeline will automatically:
- Update the version in `pyproject.toml`
- Add a new entry to `CHANGELOG.md`
- Create a git tag (e.g., `v0.0.51`)
- Build the Python package
- Publish to PyPI

**Note:** This workflow requires PyPI trusted publisher to be configured on PyPI.org (not GitHub secrets). See RELEASE.md for setup instructions.

### Manual Release (Alternative)

If you need to release manually:

#### Installing
``` py -m pip install --upgrade build twine```

#### Building
Update version in pyproject.toml if needed
```py -m build```

#### Uploading
```py -m twine upload dist/*```

```py -m build; py -m twine upload dist/*```


### Running Locally

#### For Development (from source)
Install dependencies:

```py -m pip install proto-schema-parser```

Run module with example (using PYTHONPATH):

```PYTHONPATH=src python src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

Or install in editable mode:

```pip install -e .```

Then run the code generator:

```python -m struct_frame examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

#### For Users (from pip)
Install the package:
```pip install struct-frame```

Run the code generator:
```python -m struct_frame examples/myl_vehicle.proto --build_c --build_ts --build_py --build_gql```

The generated files will be placed in the `generated/` directory with subdirectories for each language (`c/`, `ts/`, `py/`, `gql/`). GraphQL schemas are written with a `.graphql` extension.

### Testing Examples
After generating code, you can test the examples:

TypeScript:
```bash
npx tsc examples/index.ts --outDir generated/
node generated/examples/index.js
```

C:
```bash
gcc examples/main.c -I generated/c -o main
./main
```
