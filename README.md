
# Struct Frame

A framework for serializing data with headers

## Quick Start

### Python Usage
```bash
# Install dependencies
pip install -e .

# Generate code from proto file
python src/main.py examples/myl_vehicle.proto --build_c --build_ts --build_py

# Generated files will be in the generated/ directory
```

### TypeScript Example
```bash
# Install TypeScript dependencies
npm i -D typescript typed-struct @types/node

# Generate TypeScript code first
python src/main.py examples/myl_vehicle.proto --build_ts

# Compile and run the example
npx tsc examples/index.ts --outDir generated/
node generated/examples/index.js
```

### C Example
```bash
# Generate C code first  
python src/main.py examples/myl_vehicle.proto --build_c

# Compile the C example
gcc examples/main.c -I generated/c -o main
./main
```

## Project Structure

- `src/` - Source code for the struct-frame library
- `examples/` - Example usage and demo files
- `generated/` - Generated output files (ignored by git)
