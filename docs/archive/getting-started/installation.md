# Installation

## Install via pip (Recommended)

Install struct-frame from PyPI:

```bash
pip install struct-frame
```

This installs the `struct_frame` package and makes the code generator available as a Python module.

!!! note "Module name uses underscore"
    The package is named `struct-frame` (with hyphen) on PyPI, but the Python module uses an underscore: `struct_frame`. Use `python -m struct_frame` to run the code generator.

## Language-Specific Requirements

=== "C"

    GCC or compatible C compiler:
    
    ```bash
    # Ubuntu/Debian
    sudo apt install gcc
    
    # macOS
    xcode-select --install
    
    # Windows (MinGW)
    # Download from https://www.mingw-w64.org/
    ```

=== "C++"

    G++ with C++14 support:
    
    ```bash
    # Ubuntu/Debian
    sudo apt install g++
    
    # macOS
    xcode-select --install
    
    # Windows (MinGW)
    # Included with MinGW-w64
    ```

=== "TypeScript"

    Node.js and npm:
    
    ```bash
    # Ubuntu/Debian
    sudo apt install nodejs npm
    
    # macOS
    brew install node
    
    # Windows
    # Download from https://nodejs.org/
    ```

=== "Python"

    Python 3.8 or later (already required for code generation).

=== "GraphQL"

    GraphQL schemas can be used with any GraphQL server implementation.

## Quick Start

1. Install struct-frame:
   ```bash
   pip install struct-frame
   ```

2. Create a proto file (e.g., `robot.proto`):
   ```proto
   package robot;
   
   message Status {
     option msgid = 1;
     uint32 robot_id = 1;
     float battery_level = 2;
   }
   ```

3. Generate code for your target language:
   ```bash
   # Python
   python -m struct_frame robot.proto --build_py --py_path generated/py
   
   # C
   python -m struct_frame robot.proto --build_c --c_path generated/c
   
   # TypeScript
   python -m struct_frame robot.proto --build_ts --ts_path generated/ts
   
   # Multiple languages
   python -m struct_frame robot.proto --build_c --build_py --build_ts
   ```

4. Use the generated code in your project.

## Next Steps

- Learn about [Code Generation](code-generation.md) options
- See [Language Usage](language-usage.md) for language-specific examples
- Understand [Message Definitions](../user-guide/message-definitions.md) for proto file syntax
