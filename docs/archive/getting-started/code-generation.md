# Code Generation

Run the generator with your proto file to produce serialization code for your target languages.

## Basic Usage

```bash
# Generate all languages
python -m struct_frame schema.proto --build_c --build_cpp --build_ts --build_py --build_gql

# Generate specific languages
python -m struct_frame schema.proto --build_c
python -m struct_frame schema.proto --build_py --build_ts

# Custom output paths
python -m struct_frame schema.proto --build_c --c_path output/c/
python -m struct_frame schema.proto --build_py --py_path output/python/
```

Default output is `generated/<language>/`.

## Command Line Options

| Option | Description |
|--------|-------------|
| `--build_c` | Generate C code |
| `--build_cpp` | Generate C++ code |
| `--build_ts` | Generate TypeScript code |
| `--build_py` | Generate Python code |
| `--build_gql` | Generate GraphQL schema |
| `--build_js` | Generate JavaScript code |
| `--build_csharp` | Generate C# code |
| `--c_path PATH` | Output directory for C |
| `--cpp_path PATH` | Output directory for C++ |
| `--ts_path PATH` | Output directory for TypeScript |
| `--py_path PATH` | Output directory for Python |
| `--gql_path PATH` | Output directory for GraphQL |
| `--js_path PATH` | Output directory for JavaScript |
| `--csharp_path PATH` | Output directory for C# |

## Build Integration

Build integration allows generated code to automatically reflect changes to proto files during your build process.

### Make (C/C++)

```makefile
PROTO_FILES := $(wildcard proto/*.proto)
GENERATED_DIR := generated

generated/c/%.sf.h: proto/%.proto
	python -m struct_frame $< --build_c --c_path generated/c/

generated/py/%.sf.py: proto/%.proto
	python -m struct_frame $< --build_py --py_path generated/py/

all: $(PROTO_FILES:proto/%.proto=generated/c/%.sf.h)
```

### CMake (C/C++)

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

### npm scripts (TypeScript)

Add to package.json:

```json
{
  "scripts": {
    "generate": "python -m struct_frame proto/messages.proto --build_ts --ts_path src/generated/",
    "build": "npm run generate && tsc",
    "watch": "tsc --watch"
  }
}
```

### Python setuptools

Add to setup.py or pyproject.toml:

```python
# setup.py
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

## Generated Output

The generator creates the following files:

| Language | Output Files |
|----------|--------------|
| C | `<name>.sf.h`, `struct_frame_parser.h` |
| C++ | `<name>.sf.hpp`, `struct_frame.hpp` |
| TypeScript | `<name>.sf.ts`, `struct_frame_parser.ts` |
| Python | `<name>_sf.py`, `struct_frame_parser.py` |
| GraphQL | `<name>.sf.graphql` |
| JavaScript | `<name>.sf.js`, `struct_frame_parser.js` |
| C# | `<name>.sf.cs`, `StructFrameParser.cs` |
