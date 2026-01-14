# Build Integration

Integrate code generation into your build system so generated code automatically reflects changes to proto files.

## Make (C/C++)

```makefile
PROTO_FILES := $(wildcard proto/*.proto)
GENERATED_DIR := generated

generated/c/%.sf.h: proto/%.proto
	python -m struct_frame $< --build_c --c_path generated/c/

generated/py/%.sf.py: proto/%.proto
	python -m struct_frame $< --build_py --py_path generated/py/

all: $(PROTO_FILES:proto/%.proto=generated/c/%.sf.h)
```

## CMake (C/C++)

```cmake
find_package(Python3 REQUIRED)

set(PROTO_FILES
    proto/messages.proto
)

foreach(PROTO_FILE ${PROTO_FILES})
    get_filename_component(PROTO_NAME ${PROTO_FILE} NAME_WE)
    set(GENERATED_HEADER "${CMAKE_BINARY_DIR}/generated/c/${PROTO_NAME}.sf.h")
    
    add_custom_command(
        OUTPUT ${GENERATED_HEADER}
        COMMAND ${Python3_EXECUTABLE} -m struct_frame
            ${CMAKE_SOURCE_DIR}/${PROTO_FILE}
            --build_c --c_path ${CMAKE_BINARY_DIR}/generated/c/
        DEPENDS ${PROTO_FILE}
    )
    list(APPEND GENERATED_HEADERS ${GENERATED_HEADER})
endforeach()

add_custom_target(generate_structs DEPENDS ${GENERATED_HEADERS})
```

## npm scripts (TypeScript)

Add to `package.json`:

```json
{
  "scripts": {
    "generate": "python -m struct_frame proto/messages.proto --build_ts --ts_path src/generated/",
    "build": "npm run generate && tsc",
    "watch": "tsc --watch"
  }
}
```

## Python setuptools

Add to `setup.py`:

```python
from setuptools import setup
from setuptools.command.build_py import build_py
import subprocess

class BuildWithGenerate(build_py):
    def run(self):
        subprocess.run([
            'python', '-m', 'struct_frame', 'proto/messages.proto',
            '--build_py', '--py_path', 'src/generated/'
        ])
        super().run()

setup(
    cmdclass={'build_py': BuildWithGenerate},
    # ...
)
```

## .NET (C#)

Add to `.csproj` file:

```xml
<Target Name="GenerateStructFrame" BeforeTargets="BeforeBuild">
  <Exec Command="python -m struct_frame proto/messages.proto --build_csharp --csharp_path $(ProjectDir)Generated/" />
</Target>
```

