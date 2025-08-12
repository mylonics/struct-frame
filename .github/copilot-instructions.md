# struct-frame Repository
struct-frame is a multi-language code generation framework that takes Protocol Buffer (.proto) files and generates serialization/deserialization code for C, TypeScript, and Python. It provides framing and parsing utilities for structured message communication.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Prerequisites and Dependencies
- Install Python dependencies:
  - `python3 -m pip install proto-schema-parser structured-classes`
- Install Node.js dependencies:
  - `npm install` -- takes ~1 second
- GCC is available for C compilation

### Core Build Commands
- **NEVER CANCEL**: All commands below complete in under 2 seconds unless specified
- Generate code from proto files:
  - `PYTHONPATH=src python3 src/main.py [proto_file] --build_c --build_ts --build_py --c_path gen/c --ts_path gen/ts --py_path gen/py`
  - Takes ~0.1 seconds to complete
- Compile TypeScript:
  - `npx tsc --project tsconfig.json` -- takes ~2 seconds
- Python module works via:
  - `PYTHONPATH=src python3 -c "import struct_frame; struct_frame.main()"`

### Known Working Components
- **Python code generator**: FULLY FUNCTIONAL
  - Reads .proto files and generates code for all three target languages
  - CLI interface works correctly
  - Code generation completes successfully
  - Generated Python files can be imported and used
- **TypeScript compilation**: PARTIALLY FUNCTIONAL
  - TypeScript files compile without errors
  - Generated code has runtime issues (missing method definitions in enum handling)
  - Use with caution for actual execution
- **C code generation**: GENERATES BUT HAS ISSUES
  - Headers are generated but have compilation errors
  - Conflicts between different API versions in generated macros
  - Example code in main.c is incompatible with generated headers

### Running Tests and Validation
- **Python validation**: Run `python3 test_python.py` -- validates core functionality
- **No formal test suite exists** in the repository
- Manual validation is required for TypeScript and C components

### Build Times and Timeouts
- Python dependencies install: ~30 seconds (may fail due to network timeouts)
- Code generation: ~0.1 seconds - NEVER CANCEL
- npm install: ~1 second - NEVER CANCEL  
- TypeScript compilation: ~2 seconds - NEVER CANCEL
- All operations are very fast, no long builds

## Validation Scenarios
- **ALWAYS test Python code generation** after making changes to the core generator
- **Test with the provided myl_vehicle.proto file** as the reference example
- **Validate that generated Python files import successfully**
- **DO NOT rely on TypeScript or C compilation** for validation due to known runtime/compilation issues
- Run `python3 test_python.py` to validate the core functionality works

## Common Issues and Workarounds
- **Python package build fails**: Network timeouts are common - use `PYTHONPATH=src` approach instead
- **TypeScript runtime errors**: Generated code calls undefined methods like `.myl_vehicle_type()` - this is a code generation bug
- **C compilation fails**: Generated headers have macro conflicts and syntax errors (C99 vs C++ style initialization)
- **Example code is outdated**: main.c and index.ts examples don't match current generated code APIs

## Repository Structure
```
/
├── src/struct_frame/          # Python code generator (WORKING)
│   ├── generate.py           # Main generation logic
│   ├── c_gen.py             # C code generator  
│   ├── ts_gen.py            # TypeScript code generator
│   ├── py_gen.py            # Python code generator
│   └── boilerplate/         # Template files for each language
├── myl_vehicle.proto         # Example proto file
├── index.ts                 # TypeScript example (INCOMPATIBLE with generated code)
├── main.c                   # C example (INCOMPATIBLE with generated code)  
├── package.json             # Node.js dependencies
├── tsconfig.json            # TypeScript configuration
├── pyproject.toml           # Python package configuration
└── gen/                     # Generated code output directory
```

## Critical Warnings
- **DO NOT expect C or TypeScript examples to compile/run** - they are incompatible with current generator output
- **DO NOT attempt Python package builds** - they fail due to network issues, use direct module execution
- **ALWAYS use PYTHONPATH=src** when running Python components
- **Generated code has API compatibility issues** between languages and with examples

## Quick Start for New Developers
1. Install dependencies: `python3 -m pip install proto-schema-parser structured-classes && npm install`
2. Generate code: `PYTHONPATH=src python3 src/main.py myl_vehicle.proto --build_py --py_path gen/py`  
3. Validate: `python3 test_python.py`
4. For development: Always test Python generation, ignore C/TypeScript runtime errors

## Common Tasks Reference

### Repository Root Contents
```
.clang-format       # C formatting config
.gitignore         # Git ignore rules
DEVGUIDE.md        # Basic development guide (minimal)
LICENSE            # MIT license
README.md          # Basic setup instructions (minimal)
TODO               # Single item: "Check if message id is repeated"
index.ts           # TypeScript example (broken)
main.c             # C example (broken) 
myl_vehicle.proto  # Proto definition example
package.json       # Node.js config
pyproject.toml     # Python package config
src/               # Source code
tsconfig.json      # TypeScript config
```

### Example proto file content (myl_vehicle.proto)
Contains definitions for vehicle communication messages including position, pose, heartbeat with message IDs and field types.

### Working Python Generation Command
```bash
PYTHONPATH=src python3 src/main.py myl_vehicle.proto --build_py --py_path gen/py
```