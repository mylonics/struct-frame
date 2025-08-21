
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

## Field options (flatten)

You can control flattening of nested message fields using a protobuf field option. This affects code generation in Python and GraphQL.

- Syntax (recommended): `field_type name = N [flatten=true];`
- Also supported (qualified): `[(sf.flatten)=true]` or `[(struct_frame.flatten)=true]`

Behavior:
- Python: `to_dict()` merges the nested message's keys into the parent dict instead of nesting under the field name.
- GraphQL: the parent type inlines the child fields.
- Collisions: if any inlined child field name matches an existing field name in the parent, validation fails and generation aborts with a clear error.

Example:

```proto
message RobotStatusEntry{
	int32 time = 1;
	RobotStatus status = 2 [flatten=true];
}
```

Notes:
- Flatten applies only to message-typed fields (not primitives or enums).
- If you encounter a collision, rename the parent or child field, or remove flatten for that field.
