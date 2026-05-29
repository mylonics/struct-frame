---
title: Testing
description: Running and understanding the struct-frame test suite.
---

The struct-frame test suite is designed to be on par with mature
multi-language serialization projects: every supported language is exercised
by the same scenarios, parsers are stress-tested with malformed input, and
generated code is regression-checked for wire-format and byte-determinism
drift.

This page is the user-facing entry point. Deeper documents:

| Document | Purpose |
| --- | --- |
| [`tests/README.md`](https://github.com/mylonics/struct-frame/blob/main/tests/README.md) | Repository-local quickstart, file layout, suite-by-suite overview |
| [Test Coverage](./test-coverage) | The authoritative feature × language matrix — every ✅/⚠️/❌ entry, kept in sync with the code |
| [Conformance](./conformance) | Wire-format spec + canonical test vectors a new implementation must pass |
| [`tests/NEGATIVE_TESTS.md`](https://github.com/mylonics/struct-frame/blob/main/tests/NEGATIVE_TESTS.md) | The 13 malformed-frame scenarios run in every language |

## Running Tests

From the project root:

```bash
# Run everything
python test_all.py

# Or invoke the runner directly with options
python tests/run_tests.py
```

### Runner options

```text
python tests/run_tests.py [options]

  --verbose, -v       Show detailed output
  --quiet, -q         Suppress failure output
  --skip-lang LANG    Skip a language (c, cpp, py, ts, js, csharp, rust, gql)
                      May be passed multiple times.
  --only-generate     Generate code only; skip compile and test
  --only-compile      Stop after compilation; don't run tests
  --check-tools       Check tool availability only
  --no-clean          Skip cleaning generated files (faster iteration)
  --profile NAME      Only test specific profile(s) (e.g. ProfileStandard)
  --no-parallel       Disable parallel compilation
  --no-color          Disable colored output
```

### Wire-format and determinism checks

These are separate from `run_tests.py` and run in CI:

```bash
# Fails if any generator output is non-deterministic between runs
python tests/check_determinism.py

# Fails if encoded bytes drift from the checked-in golden vectors
python tests/check_golden.py

# Regenerate goldens after a deliberate wire-format change
python tests/check_golden.py --update
```

### Cross-cutting generator tests

These do not need the full multi-language toolchain — only Python:

```bash
python tests/test_magic_bytes.py
python tests/test_proto_field_types.py
python tests/test_generator_validation.py
python tests/test_no_packed.py
python tests/test_wire_evolution.py
```

## Test Prerequisites

| Need | Install |
| --- | --- |
| Python 3.8+ + `proto-schema-parser` | `pip install proto-schema-parser` |
| C tests | GCC (`apt install gcc`) |
| C++ tests | G++ with C++20 (`apt install g++`) |
| TypeScript / JavaScript | Node.js + `cd tests/ts && npm install` |
| C# tests | .NET SDK 8.0+ |
| Rust tests | `rustc` / `cargo` stable |

## Test Suites

The same suites are implemented in every per-language directory under
`tests/<lang>/`. See [Test Coverage](./test-coverage) for the per-feature matrix.

| Suite | Purpose | Languages |
| --- | --- | --- |
| `test_standard` | Primitive types, fixed/bounded arrays, strings, unions, enums | C, C++, Py, TS, JS, C#, Rust |
| `test_extended` | Message IDs > 255, multi-byte msg-id encoding, `pkgid` | C, C++, Py, TS, JS, C#, Rust |
| `test_variable_flag` | `option variable=true` truncates unused array slots | C, C++, Py, TS, JS, C#, Rust |
| `test_negative` | 13 malformed-frame / corruption scenarios | C, C++, Py, TS, JS, C#, Rust |
| `test_streaming` | `AccumulatingReader::push_byte` byte-at-a-time mode | C, Rust |
| `test_sdk*` | `StructFrameSdk` subscribe/dispatch with mock transports | C++, Py, TS, JS, C#, Rust |
| `test_envelope_sdk` | `oneof` envelopes via SDK dispatch | C#, Rust |
| `test_wire_evolution` | Extension fields, legacy-frame compatibility | Py, C++, TS, JS, C# |
| `test_profiling` | Throughput / latency benchmarks | C++ only |

## Running a Single Test

Once `python tests/run_tests.py --only-compile` has produced the binaries,
each language's tests are independently runnable:

### C / C++

```bash
# Standard suite, "both" encodes + decodes in one process
./tests/c/build/test_standard both standard
./tests/cpp/build/test_negative
```

### Python

```bash
python tests/py/test_standard.py both standard
python tests/py/test_negative.py
```

### TypeScript

```bash
cd tests/ts && npx tsx test_standard.ts both standard
cd tests/ts && npx tsx test_negative.ts
```

### JavaScript

```bash
node tests/js/test_standard.js both standard
node tests/js/test_negative.js
```

### C#

```bash
# All C# suites share one TestRunner that selects the suite by name
dotnet run --project tests/csharp/StructFrameTests.csproj -- --runner test_standard both standard
dotnet run --project tests/csharp/StructFrameTests.csproj -- --runner test_negative
```

### Rust

```bash
# Rust ships one binary with subcommands per suite
cd tests/rust && cargo build
./tests/rust/target/debug/struct_frame_rust_tests test_standard both standard
./tests/rust/target/debug/struct_frame_rust_tests test_negative
./tests/rust/target/debug/struct_frame_rust_tests test_streaming
./tests/rust/target/debug/struct_frame_rust_tests test_sdk_subscribe
./tests/rust/target/debug/struct_frame_rust_tests test_envelope_sdk
```

The first positional argument is `encode`, `decode`, or `both`; the second
is the profile name (e.g. `standard`, `sensor`, `ipc`, `bulk`, `network`).
For `encode` and `decode` a third positional argument is the file path.

## Test Output Format

Every per-language test obeys the same protocol so `run_tests.py` can scrape
results from any of them:

```text
[TEST START] <Language> <Profile> <Mode>
... per-test diagnostics ...
[TEST END] <Language> <Profile> <Mode>: PASS
```

Exit code 0 means pass; any non-zero code is a failure. The runner aggregates
these into an encode × decode × language compatibility matrix at the end.

## Cross-Platform Compatibility

`run_tests.py` orchestrates a three-phase matrix that proves wire compatibility:

1. **Encode phase** — every language encodes a fixed set of messages to a
   per-language binary file under `tests/<lang>/build/` (or `tests/<lang>/`
   for scripted languages).
2. **Validate phase** — every encoded file is byte-validated.
3. **Decode phase** — every other language is asked to decode every encoded
   file; results form an N×N compatibility matrix.

This matrix is what makes a feature claim like *"struct-frame is wire-compatible
across all seven languages"* defensible. See [Test Coverage](./test-coverage)
for the per-suite results.

## Wire-Format Regression Detection

`tests/golden/` contains canonical encoded bytes for every (suite × profile)
combination, produced by the Python reference encoder. `tests/check_golden.py`
re-encodes and compares; CI fails on any drift. This is the project's
equivalent of a protobuf `testdata/` directory.

If a change to the generator legitimately alters the wire format, update the
goldens in a separate, well-described commit:

```bash
python tests/check_golden.py --update
git add tests/golden/
git commit -m "wire: regenerate goldens for <reason>"
```

## Adding a New Test

1. Add proto definitions to `tests/proto/<name>.sf`.
2. For each language under `tests/<lang>/`, add a `test_<name>.<ext>` entry
   point whose CLI is `<binary> encode|decode|both <profile> <file>`, and
   shared message helpers under `tests/<lang>/include/<name>_messages.<ext>`.
3. Add the suite to the dispatch table in `tests/run_tests.py`.
4. Update [`tests/README.md`](https://github.com/mylonics/struct-frame/blob/main/tests/README.md)
   and [Test Coverage](./test-coverage) in the same PR.
5. If the suite changes encoded bytes, run `python tests/check_golden.py --update`.

## CI Integration

GitHub Actions runs the full suite on every push to `main`/`develop` and every
pull request (`.github/workflows/test.yml`). Generated artefacts are kept for
five days for debugging. Determinism and golden-file checks run in the same
job so wire-format and reproducibility regressions block the PR.
