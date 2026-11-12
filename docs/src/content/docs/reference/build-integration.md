---
title: Build Integration
description: Integrate code generation into Make, CMake, npm scripts, setuptools and MSBuild with a structframe.toml file.
---

Integrate code generation into your build system so generated code automatically reflects changes to schema files. The generator caches its output (an unchanged schema, option set and generator are not regenerated), so it is cheap to run on every build.

## Put the options in `structframe.toml`

Keep the schema, languages and output paths in one file next to your schema instead of repeating them in each build script:

```toml
# structframe.toml
schema = "proto/robot.sf"
lang = ["c", "py"]
out = "build/gen"            # build/gen/c, build/gen/py
c-path = "firmware/src/gen"  # override one language
equality = true
```

Relative paths are resolved against the file's directory. Run `struct-frame` in that directory, or `struct-frame --config path/to/structframe.toml` from anywhere. Every option and the file format are listed in the [CLI Reference](/reference/cli-reference/#config-file-structframetoml).

The generator exits non-zero on schema errors, so every integration below fails the build when the schema is wrong.

## Make (C/C++)

```makefile
SCHEMAS := $(wildcard proto/*.sf)

# One run generates every package imported by robot.sf; the stamp is the
# generation hash file, which is rewritten on every real regeneration.
firmware/src/gen/.structframe.hash: $(SCHEMAS) structframe.toml
	struct-frame --quiet

all: firmware/src/gen/.structframe.hash
```

## CMake (C/C++)

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(SF_OUT ${CMAKE_BINARY_DIR}/gen)
file(GLOB SF_SCHEMAS ${CMAKE_SOURCE_DIR}/proto/*.sf)

add_custom_command(
    OUTPUT ${SF_OUT}/c/structframe_all.h
    COMMAND ${Python3_EXECUTABLE} -m struct_frame ${CMAKE_SOURCE_DIR}/proto/robot.sf
            --lang c --out ${SF_OUT} --quiet
    DEPENDS ${SF_SCHEMAS}
)
add_custom_target(generate_structs DEPENDS ${SF_OUT}/c/structframe_all.h)

add_executable(app main.c)
add_dependencies(app generate_structs)
target_include_directories(app PRIVATE ${SF_OUT}/c)
```

`structframe_all.h` (and `structframe_all.hpp` for C++) is generated on every run and includes every package header, which makes it a convenient `OUTPUT`.

## npm scripts (TypeScript)

Add to `package.json`:

```json
{
  "scripts": {
    "generate": "struct-frame proto/messages.sf --lang ts --ts-path src/generated/ --quiet",
    "build": "npm run generate && tsc",
    "watch": "tsc --watch"
  }
}
```

The output folder has an `index.ts` that exports the runtime and one namespace per package: `import { messages, BufferWriter } from './generated'`.

## Python setuptools

Add to `setup.py`:

```python
import subprocess
import sys

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithGenerate(build_py):
    def run(self):
        subprocess.run([sys.executable, '-m', 'struct_frame', 'proto/messages.sf',
                        '--lang', 'py', '--py-path', 'src/generated/', '--quiet'],
                       check=True)  # fail the build on schema errors
        super().run()


setup(
    cmdclass={'build_py': BuildWithGenerate},
    # ...
)
```

From Python code you can also call the generator directly: `from struct_frame import main; main([...])` returns the exit status.

## .NET (C#)

Add to `.csproj` file:

```xml
<Target Name="GenerateStructFrame" BeforeTargets="BeforeBuild">
  <Exec Command="struct-frame proto/messages.sf --lang csharp --csharp-path $(ProjectDir)Generated/ --quiet" />
</Target>
```

`Exec` fails the build when the command exits non-zero.
