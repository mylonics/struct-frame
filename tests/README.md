# struct-frame Test Suite

Comprehensive test suite for struct-frame that validates code generation and serialization/deserialization across all supported languages: **C, C++, Python, TypeScript, JavaScript, C#, Rust** (and GraphQL schema generation).

For an authoritative map of which features are tested in each language, see
[`docs/src/content/docs/reference/test-coverage.md`](../docs/src/content/docs/reference/test-coverage.md).
For the wire-format spec that any new implementation must conform to, see
[`docs/src/content/docs/reference/conformance.md`](../docs/src/content/docs/reference/conformance.md).
For negative / malformed-input tests, see [`NEGATIVE_TESTS.md`](NEGATIVE_TESTS.md).

## Quick Start

Run all tests from the project root:

```bash
python tests/run_tests.py
```

Or use the wrapper script:

```bash
python test_all.py
```

## Test Output Format

The test runner provides clean, organized output showing code generation, compilation, and test execution results for each language and frame profile.

## Cross-Platform Compatibility Matrix

The test suite includes cross-platform serialization tests. Each language can encode messages, and then any language can decode and validate them, producing a compatibility matrix.

## Test Architecture

The test suite follows a consistent **three-component pattern** across all languages:

### 1. Entry Point (`test_<suite>.*`)
Minimal main function that configures and runs the test:
```
test_standard.c     →  Runs standard message tests
test_extended.c     →  Runs extended message ID tests  
test_variable_flag.c →  Runs variable-length truncation tests
```

### 2. Message Definitions (`include/*_messages.*`)
Contains three logical sections:
- **Message Definitions**: Hardcoded test messages with known values
- **Encoder**: Functions to serialize messages into a byte stream
- **Validator**: Functions to deserialize and compare with expected values

### 3. Profile Runner (`include/profile_runner.h`)
Profile-dispatch encode/decode functions and the `test_config_t` struct:
- Frame profile configuration and dispatch
- `encode_messages()` and `decode_messages()` implementations

### 4. Test Harness (`include/test_harness.h`)
Higher-level test infrastructure (includes `profile_runner.h`):
- File I/O utilities
- Command-line parsing (`run_encode`, `run_decode`, `run_test_main`)

## Test Suites

### 1. Standard Messages Test (`test_standard.*`)
**Purpose**: Validates serialization of common message types across all frame profiles.

**What it tests**:
- `SerializationTestMessage`: Magic numbers, strings, floats, bools, arrays
- `BasicTypesMessage`: All integer sizes (8/16/32/64-bit signed/unsigned), floats, doubles
- `UnionTestMessage`: Discriminated unions with nested message payloads
- `VariableSingleArray`: Variable-length arrays with different fill levels
- `Message`: Simple message with severity enum

**Frame Profiles**: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network

### 2. Extended Messages Test (`test_extended.*`)
**Purpose**: Validates message IDs greater than 255 (requiring 2-byte encoding).

**What it tests**:
- Extended message IDs (256-4095)
- Large payload messages (up to 280 bytes)
- Package ID support

**Frame Profiles**: profile_bulk, profile_network (profiles that support pkg_id)

### 3. Variable Flag Test (`test_variable_flag.*`)
**Purpose**: Validates the `variable=true` option truncates unused array space.

**What it tests**:
- Non-variable messages: Full struct size transmitted
- Variable messages: Only used array elements transmitted

**Frame Profiles**: profile_bulk

### 4. Negative Tests (`test_negative.*`)
**Purpose**: Validates parsers reject corrupted, truncated, or malformed frames.
15 uniform scenarios implemented identically in all 7 languages (plus language-specific extras) — see [`NEGATIVE_TESTS.md`](NEGATIVE_TESTS.md).

### 5. Streaming Tests (`test_streaming.*`)
**Purpose**: Validates byte-at-a-time accumulating-reader behaviour (C, Rust).

### 6. SDK Tests (`test_sdk.*`, `test_sdk_subscribe.*`, `test_envelope_sdk.*`)
**Purpose**: Validates `StructFrameSdk` subscribe/dispatch with mock transports.
Languages: C++, Python, TypeScript, JavaScript, C#, Rust.

### 7. Wire-Evolution Tests (`test_wire_evolution.*`)
**Purpose**: Validates backward-compatible message extension: unknown trailing
fields are ignored, legacy frames decode against new schemas, magic bytes are
computed only from base fields.
Top-level orchestrator: `tests/test_wire_evolution.py`. Per-language compiled
tests: C++, TS, JS, C#.

### 8. Cross-Cutting Generator Tests (top-level `tests/test_*.py`)
- `test_magic_bytes.py` — magic-byte derivation + enforcement
- `test_proto_field_types.py` — enum-to-string, flatten, `discriminator=none`, multi-oneof
- `test_generator_validation.py` — `.sf` semantic rejection (duplicates, cycles)
- `test_no_packed.py` — `--no_packed` flag
- `check_determinism.py` — generator output must be byte-deterministic
- `check_golden.py` — wire-format regression against checked-in golden bytes

## Test Organization

```
tests/
├── run_tests.py              # Main test runner
├── README.md                 # This file
├── NEGATIVE_TESTS.md         # Negative / malformed-frame tests
├── check_determinism.py      # Verifies generator output is byte-deterministic
├── check_golden.py           # Verifies wire bytes against checked-in goldens
├── test_generator_validation.py  # Generator-validation (.sf input) tests
├── test_magic_bytes.py           # Magic-byte computation / enforcement tests
├── test_no_packed.py             # `--no_packed` C/C++ output tests
├── test_proto_field_types.py     # Proto field-type coverage tests
├── test_wire_evolution.py        # Backward-compat / extension-field tests
├── proto/                    # .sf message definitions used by all suites
│   ├── test_messages.sf          # Standard / serialization test messages
│   ├── pkg_test_messages.sf      # Package-ID test messages
│   ├── pkg_test_a.sf             # Imported by pkg_test_messages.sf
│   ├── extended_messages.sf      # Message IDs > 255
│   ├── envelope_messages.sf      # Envelope (oneof) messages
│   ├── wire_evolution_messages.sf
│   └── common_types.sf
├── golden/                   # Canonical wire bytes (see check_golden.py)
├── c/                        # C tests (test_standard.c, test_extended.c,
│   │                         #  test_variable_flag.c, test_negative.c,
│   │                         #  test_streaming.c)
│   └── include/              # Shared message defs + profile_runner + test_harness
├── cpp/                      # C++ tests (adds test_profiling*, test_sdk_*,
│                             #  test_wire_evolution.cpp)
├── py/                       # Python tests (adds test_sdk.py)
├── ts/                       # TypeScript tests (adds test_sdk.ts, test_wire_evolution.ts)
├── js/                       # JavaScript tests (adds test_sdk.js, test_wire_evolution.js)
├── csharp/                   # C# tests (adds TestSdkSubscribe.cs, test_envelope_sdk.cs,
│                             #  test_wire_evolution.cs)
├── rust/                     # Rust tests (single binary with subcommands)
└── generated/                # Generated code output (git-ignored)
    ├── c/  cpp/  py/  ts/  js/  csharp/  gql/
```

## How Tests Work

### Encode Phase
1. Create hardcoded test messages with known values
2. Serialize messages in order using a BufferWriter
3. Write encoded byte stream to a file

### Decode Phase
1. Read encoded byte stream from file
2. Parse frames using an AccumulatingReader
3. Deserialize each message and compare with expected values
4. Report PASS if all messages match, FAIL otherwise

### Cross-Platform Validation
The test runner orchestrates encode/decode across languages:
1. Language A encodes messages to a file
2. Language B decodes that file and validates
3. Matrix shows which combinations work

## Command Line Options

```bash
python tests/run_tests.py [options]

Options:
  --verbose, -v       Enable verbose output for debugging
  --skip-lang LANG    Skip specific language (can be used multiple times)
  --only-generate     Only run code generation, skip compilation and tests
  --only-compile      Only run code generation and compilation, skip tests
  --check-tools       Only check tool availability
  --no-clean          Skip cleaning generated files (faster iteration)
  --profile NAME      Only test specific profile (e.g., ProfileStandard)
  --no-parallel       Disable parallel compilation
  --no-color          Disable colored output

Examples:
  python tests/run_tests.py                      # Run all tests
  python tests/run_tests.py --no-clean           # Skip cleaning for faster iteration
  python tests/run_tests.py --profile ProfileStandard  # Test only one profile
  python tests/run_tests.py --only-compile       # Stop after compilation
  python tests/run_tests.py --skip-lang ts       # Skip TypeScript tests
  python tests/run_tests.py --verbose            # Show detailed output
```

## Prerequisites

**Python 3.8+** with packages:
```bash
pip install proto-schema-parser
```

**For C tests**:
- GCC compiler

**For C++ tests**:
- G++ compiler with C++20 support

**For TypeScript tests**:
- Node.js
- Install dependencies: `cd tests/ts && npm install`

**For C# tests**:
- .NET SDK

**For Rust tests**:
- `cargo` / `rustc` (stable)

## Adding a New Test Suite

1. Add proto definitions to `tests/proto/<name>.sf` (or extend an existing file).
2. For each language under `tests/<lang>/`, add:
   - An entry point: `test_<name>.<ext>` whose CLI is
     `<binary> encode|decode|both <profile> <file>`
   - A message-definitions module under `include/` (`<name>_messages.<ext>`)
     containing the per-message creator/encoder/validator helpers
3. Wire the new suite into `tests/run_tests.py` by adding it to the suite
   list near the existing `test_standard` / `test_extended` / `test_variable_flag`
   entries (search for `"standard"` to find the dispatch table).
4. Conform to the standard test output format:
   - Print `[TEST START] <Language> <Profile> <Mode>`
   - Print `[TEST END] <Language> <Profile> <Mode>: PASS` or `FAIL`
5. Return exit code 0 on success, 1 on failure.
6. Update `docs/.../test-coverage.md` so the new feature appears in the matrix.

## Debugging Failed Tests

When a test fails, it prints detailed failure information including hex dump of the encoded data. Use `--verbose` flag to see all command output including successful operations.

## Sanitizers, fuzzing, coverage, property tests (Tier B / C)

These workflows live under `.github/workflows/` and are also runnable locally.

### Sanitizers (C / C++)

`tests/run_tests.py` honours the standard `CC` / `CXX` / `CFLAGS` /
`CXXFLAGS` / `LDFLAGS` environment variables at every compile site, so
sanitizer instrumentation is a one-line wrapper:

```bash
# ASan + UBSan
CC=clang CXX=clang++ \
  CFLAGS="-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all" \
  CXXFLAGS="$CFLAGS" \
  LDFLAGS="-fsanitize=address,undefined" \
  python test_all.py --skip-lang csharp --skip-lang rust

# ThreadSanitizer
CC=clang CXX=clang++ \
  CFLAGS="-O1 -g -fsanitize=thread" CXXFLAGS="$CFLAGS" LDFLAGS="-fsanitize=thread" \
  python test_all.py --skip-lang csharp --skip-lang rust

# Valgrind (C only; build first, then valgrind the binaries directly)
python test_all.py --only-compile
for exe in tests/c/build/test_*; do
  valgrind --error-exitcode=1 --leak-check=full "$exe"
done
```

CI runs these under `sanitizers.yml`.

### Fuzzing harnesses

| Harness                       | File                                                     | Tooling      |
|-------------------------------|----------------------------------------------------------|--------------|
| C accumulating-reader         | `tests/c/fuzz_parser.c`                                  | libFuzzer    |
| Python `AccumulatingReader`   | `tests/py/fuzz_parser.py`                                | atheris      |
| Rust `AccumulatingReader`     | `tests/rust/fuzz/fuzz_targets/parser.rs` (+ `Cargo.toml`) | cargo-fuzz   |

Local quick start (C harness):

```bash
clang -O1 -g -fsanitize=fuzzer,address,undefined \
      -I src/struct_frame/boilerplate/c \
      tests/c/fuzz_parser.c -o /tmp/fuzz_parser
/tmp/fuzz_parser -max_total_time=60 -max_len=4096
```

CI runs a 60-second smoke fuzz of the C and Python harnesses under
`fuzz.yml`.  Long-running corpus growth is intended to happen upstream
via OSS-Fuzz (follow-up).

### Property-based round-trip tests

`tests/test_property_roundtrip.py` uses Hypothesis to generate random
message instances and assert encode → decode equality across the
Standard, Bulk, and Network profiles.  It is skipped automatically when
`tests/generated/py` does not yet exist; generate it first:

```bash
python test_all.py --only-generate
pip install hypothesis pytest
python -m pytest tests/test_property_roundtrip.py -v
```

### Coverage

`coverage.yml` runs the Python generator and Python tests under
`coverage.py` and uploads `coverage.xml` to Codecov.  Locally:

```bash
pip install coverage
coverage run --source=src/struct_frame --branch test_all.py
coverage report
```

Coverage uploads for non-Python languages (`gcov`/`lcov`, `c8`/`nyc`,
`coverlet`, `cargo-llvm-cov`) plug into the same Codecov action and are
tracked as follow-ups.
