# Installation

## Dependencies

**Python (required for code generation)**

```bash
pip install proto-schema-parser
```

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

1. Install the Python dependency:
   ```bash
   pip install proto-schema-parser
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/mylonics/struct-frame.git
   cd struct-frame
   ```

3. Generate code from a proto file:
   ```bash
   PYTHONPATH=src python src/main.py examples/generic_robot.proto --build_py --py_path gen/py
   ```

4. Use the generated code in your project.

## Next Steps

- Learn about [Code Generation](code-generation.md) options
- See [Language Usage](language-usage.md) for language-specific examples
- Understand [Message Definitions](../user-guide/message-definitions.md) for proto file syntax
