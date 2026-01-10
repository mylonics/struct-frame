# struct-frame Repository

struct-frame is a multi-language code generation framework that converts Protocol Buffer (.proto) files into serialization/deserialization code for C, C++, TypeScript, Python, JavaScript, GraphQL, and C#. It provides framing and parsing utilities for structured message communication.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Prerequisites and Dependencies

- Install Python dependencies:
  - `pip install proto-schema-parser`
- Install Node.js dependencies (for TypeScript):
  - `npm install`
- For C tests: GCC compiler
- For C++ tests: G++ compiler with C++20 support
- For TypeScript tests: Node.js + `cd tests/ts && npm install`
- For C# tests: .NET SDK

### Core Build Commands

- **NEVER CANCEL**: All commands below complete quickly
- Generate code for all languages:
  - `PYTHONPATH=src python3 src/main.py [proto_file] --build_c --build_cpp --build_ts --build_py --build_gql --build_csharp`
- Run the full test suite:
  - `python test_all.py` or `python tests/run_tests.py`
- Python module works via:
  - `PYTHONPATH=src python3 -c "import struct_frame; struct_frame.main()"`

### Known Working Components

- **Code Generator**: FULLY FUNCTIONAL for C, C++, Python, TypeScript, JavaScript, GraphQL, C#
  - Reads .proto files and generates code for all target languages
  - CLI interface works correctly
  - Code generation completes successfully
- **Test Suite**: COMPREHENSIVE
  - Located in `tests/` directory with modular runner architecture
  - Validates code generation, compilation, and serialization across all languages
  - Includes cross-platform compatibility matrix tests

### Running Tests and Validation

- **Use the test suite** for validation:
  ```bash
  python test_all.py                           # Run all tests
  python tests/run_tests.py --verbose          # Verbose output
  python tests/run_tests.py --skip-lang ts     # Skip TypeScript tests
  python tests/run_tests.py --only-generate    # Only generate code
  python tests/run_tests.py --check-tools      # Check tool availability
  python tests/run_tests.py --clean            # Clean generated files
  ```
- Test proto files are in `tests/proto/` (test_messages.proto, sensor_messages.proto, etc.)
- Generated test code goes to `tests/generated/`

### Build Times and Timeouts

- Code generation: ~0.1 seconds - NEVER CANCEL
- npm install: ~1 second - NEVER CANCEL
- TypeScript compilation: ~2 seconds - NEVER CANCEL
- Full test suite: Varies by available compilers
- All operations are very fast, no long builds

## Validation Scenarios

- **Run the test suite** after making changes to generators
- **Use test proto files** in `tests/proto/` for validation
- **Check test output** for cross-platform compatibility matrix
- Example proto files in `examples/` are for demonstration (array_test.proto, frame_formats.proto, generic_robot.proto)

## Repository Structure

```
/
├── src/                      # Source code directory
│   ├── main.py              # CLI entry point
│   └── struct_frame/        # Code generators
│       ├── generate.py      # Main generation logic
│       ├── c_gen.py         # C code generator
│       ├── cpp_gen.py       # C++ code generator
│       ├── ts_gen.py        # TypeScript code generator
│       ├── js_gen.py        # JavaScript code generator
│       ├── py_gen.py        # Python code generator
│       ├── gql_gen.py       # GraphQL code generator
│       ├── csharp_gen.py    # C# code generator
│       ├── frame_formats/   # Frame format definitions (Python module)
│       └── boilerplate/     # SDK templates for each language
│           ├── c/           # C SDK boilerplate
│           ├── cpp/         # C++ SDK boilerplate (FrameProfiles.hpp, etc.)
│           ├── csharp/      # C# SDK boilerplate
│           ├── js/          # JavaScript SDK boilerplate
│           ├── py/          # Python SDK boilerplate
│           └── ts/          # TypeScript SDK boilerplate
├── tests/                   # Comprehensive test suite
│   ├── run_tests.py         # Main test runner entry point
│   ├── runner.py            # Test runner orchestration
│   ├── plugins.py           # Test plugins (Standard, CrossPlatformMatrix)
│   ├── languages.py         # Language configuration
│   ├── test_config.json     # Test configuration
│   ├── test_suites.json     # Test suite definitions
│   ├── test_messages.json   # Expected values for validation
│   ├── proto/               # Test proto definitions
│   │   ├── test_messages.proto
│   │   ├── sensor_messages.proto
│   │   ├── common_types.proto
│   │   └── package_*.proto  # Package ID test protos
│   ├── c/                   # C test files + build/
│   ├── cpp/                 # C++ test files + build/
│   ├── py/                  # Python test files
│   ├── ts/                  # TypeScript test files + package.json
│   ├── csharp/              # C# test files + project
│   ├── js/                  # JavaScript test files
│   └── generated/           # Generated code output (c/, cpp/, py/, ts/, gql/, csharp/, js/)
├── examples/                # Example proto files
│   ├── array_test.proto
│   ├── frame_formats.proto
│   ├── generic_robot.proto
│   ├── package_id_example.proto
│   ├── import_example.proto
│   ├── frame_format_profiles.py  # Python example
│   ├── minimal_frames_example.py # Minimal frames example
│   ├── index.ts             # TypeScript example
│   └── main.c               # C example
├── docs/                    # MkDocs documentation
│   ├── index.md             # Documentation home
│   ├── getting-started/     # Installation, code generation, language usage
│   ├── user-guide/          # SDK docs, framing, message definitions
│   │   ├── cpp-sdk.md
│   │   ├── python-sdk.md
│   │   ├── typescript-sdk.md
│   │   ├── csharp-sdk.md
│   │   ├── framing.md
│   │   └── ...
│   └── reference/           # Development and testing guides
├── wireshark/               # Wireshark dissector plugin
│   ├── struct_frame.lua     # Lua dissector
│   └── README.md
├── gen/                     # Generated code output directory
├── test_all.py              # Test suite wrapper script
├── mkdocs.yml               # MkDocs configuration
├── pyproject.toml           # Python package configuration
└── package.json             # Node.js dependencies
```

## Quick Start for New Developers

1. Install dependencies: `pip install proto-schema-parser && npm install`
2. Run the test suite: `python test_all.py`
3. Generate code: `PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_py --py_path gen/py`
4. For development: Run tests after changes to validate generators

## Test Suite Architecture

The test runner uses a modular architecture defined in `tests/`:

- **`run_tests.py`**: Main entry point
- **`runner.py`**: Orchestrates test execution
- **`plugins.py`**: StandardTestPlugin, CrossPlatformMatrixPlugin
- **`languages.py`**: Language-specific configuration
- **`test_config.json`**: General test configuration
- **`test_suites.json`**: Defines which tests to run per language

## Common Tasks Reference

### Generate Code for a Specific Language

```bash
# Python only
PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_py --py_path gen/py

# All languages
PYTHONPATH=src python3 src/main.py examples/generic_robot.proto --build_c --build_cpp --build_ts --build_py --build_gql --build_csharp
```

### Run Specific Test Types

```bash
python tests/run_tests.py --only-generate  # Just generate code
python tests/run_tests.py --check-tools    # Check available tools
python tests/run_tests.py --skip-lang c    # Skip C tests
```

### Adding New Tests

1. Add entry to `tests/test_suites.json` under the appropriate language
2. Create test files: `tests/<lang>/test_<name>.<ext>`
3. Use standard output format for validation
4. Return exit code 0 on success, 1 on failure

## C++ SDK Architecture

The C++ boilerplate in `src/struct_frame/boilerplate/cpp/` provides a comprehensive framing and parsing SDK:

### Core Components

- **`frame_base.hpp`**: Base types (`FrameMsgInfo`, `FrameChecksum`, `MessageBase`, `fletcher_checksum`)
- **`frame_headers.hpp`**: Header configurations (None, Tiny, Basic) with compile-time constants
- **`payload_types.hpp`**: Payload configurations (Minimal, Default, Extended, etc.)
- **`frame_parsers.hpp`**: Low-level parser implementations
- **`FrameProfiles.hpp`**: Main SDK file with profiles, encoders, parsers, readers, and writers

### Frame Profiles

Pre-defined combinations of header + payload for common use cases:

| Profile           | Header | Payload                   | Use Case                             |
| ----------------- | ------ | ------------------------- | ------------------------------------ |
| `ProfileStandard` | Basic  | Default                   | General serial/UART                  |
| `ProfileSensor`   | Tiny   | Minimal                   | Low-bandwidth sensors                |
| `ProfileIPC`      | None   | Minimal                   | Trusted inter-process communication  |
| `ProfileBulk`     | Basic  | Extended                  | Large data transfers                 |
| `ProfileNetwork`  | Basic  | ExtendedMultiSystemStream | Multi-system networked communication |

### SDK Classes

**Encoders:**

- `FrameEncoderWithCrc<Config>`: Encode frames with CRC
- `FrameEncoderMinimal<Config>`: Encode minimal frames (no length/CRC)

**Parsers:**

- `BufferParserWithCrc<Config>`: Parse complete frames with CRC validation
- `BufferParserMinimal<Config>`: Parse minimal frames (requires msg_length callback)

**Readers/Writers:**

- `BufferReader<Config>`: Iterate through buffer parsing multiple frames
- `BufferWriter<Config>`: Encode multiple frames with automatic offset tracking
- `AccumulatingReader<Config, BufferSize>`: **Unified parser** for both buffer and streaming modes

### AccumulatingReader

The `AccumulatingReader` is the recommended class for parsing. It supports:

1. **Buffer Mode** - Process chunks of data with partial message handling:

   ```cpp
   AccumulatingReader<ProfileStandardConfig> reader;
   reader.add_data(chunk, size);
   while (auto result = reader.next()) {
       // Process complete messages
   }
   ```

2. **Stream Mode** - Byte-by-byte processing (UART/serial):
   ```cpp
   AccumulatingReader<ProfileStandardConfig> reader;
   while (receiving) {
       if (auto result = reader.push_byte(read_byte())) {
           // Complete message received
       }
   }
   ```

**Key features:**

- Stack-allocated internal buffer (default 1024 bytes, configurable via template)
- State machine tracks parsing progress to avoid re-parsing
- Handles partial messages across buffer boundaries
- For minimal profiles, pass `get_message_length` callback to constructor

### Convenience Type Aliases

```cpp
// BufferReader/Writer
ProfileStandardReader, ProfileStandardWriter
ProfileSensorReader, ProfileSensorWriter
ProfileIPCReader, ProfileIPCWriter
ProfileBulkReader, ProfileBulkWriter
ProfileNetworkReader, ProfileNetworkWriter

// AccumulatingReader
ProfileStandardAccumulatingReader
ProfileSensorAccumulatingReader
ProfileIPCAccumulatingReader
ProfileBulkAccumulatingReader
ProfileNetworkAccumulatingReader
```

## Python SDK Overview

The Python SDK (`src/struct_frame/boilerplate/py/`) provides:

- **Frame encoding/decoding** with configurable profiles
- **Streaming parser** for byte-by-byte processing
- **Buffer parser** for chunk processing
- Example usage in `examples/frame_format_profiles.py` and `examples/minimal_frames_example.py`

## TypeScript SDK Overview

The TypeScript SDK (`src/struct_frame/boilerplate/ts/`) provides:

- **Frame encoding/decoding** classes
- **Buffer-based parsing** for Node.js and browser
- See `docs/user-guide/typescript-sdk.md` for details

## C# SDK Overview

The C# SDK (`src/struct_frame/boilerplate/csharp/`) provides:

- **Frame encoding/decoding** with .NET integration
- **Interface-based design** for message handling
- See `docs/user-guide/csharp-sdk.md` for details
