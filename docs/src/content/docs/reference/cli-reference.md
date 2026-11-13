---
title: CLI Reference
description: Complete reference for all struct-frame command-line flags, the structframe.toml config file and the diff subcommand.
---

## Basic Usage

```bash
struct-frame [options] [SCHEMA]
struct-frame diff OLD NEW [options]   # wire-compatibility check (alias: schema-diff)
```

`struct-frame` is installed with the package; `python -m struct_frame` is the same program. `SCHEMA` is a `.sf` file (`.proto` files with the same syntax are accepted too); its imports are followed. It may be left out when a [config file](#config-file-structframetoml) names it.

The generator exits with status `0` on success (including when generation is skipped because nothing changed), `1` when the schema cannot be parsed or fails validation (syntax errors, duplicate declarations, unknown options, name collisions) and `2` for usage errors such as an unknown option, no language selected, or a bad config file. Errors are written to stderr, so it is safe to use as a build step.

Every option is spelled in kebab-case (`--build-c`, `--c-path`). The older snake_case spellings (`--build_c`, `--c_path`, `--no_packed`, ...) are still accepted and behave identically.

```bash
struct-frame --version     # print the version and exit
struct-frame --help        # every option, grouped
```

## Choosing Languages

| Option | Description |
|--------|-------------|
| `--lang LANGS` | Comma-separated languages: `c`, `cpp`, `py`, `ts`, `js`, `csharp`, `gql`, `rust`, or `all`. May be repeated. `python`, `typescript`, `javascript`, `c++`, `cs` and `graphql` are accepted as aliases. |
| `--build-c` | Generate C |
| `--build-cpp` | Generate C++ |
| `--build-py` | Generate Python |
| `--build-ts` | Generate TypeScript |
| `--build-js` | Generate JavaScript |
| `--build-csharp` | Generate C# |
| `--build-gql` | Generate a GraphQL schema |
| `--build-rust` | Generate Rust |

`--lang c,py` and `--build-c --build-py` are equivalent and can be combined.

## Output Locations

| Option | Description | Default |
|--------|-------------|---------|
| `--out DIR` | Root output directory. Each language is written to `DIR/<lang>` (`DIR/c`, `DIR/py`, ...) unless its own path option is given. | `generated` |
| `--c-path DIR` | Output directory for C | `OUT/c` |
| `--cpp-path DIR` | Output directory for C++ | `OUT/cpp` |
| `--py-path DIR` | Output directory for Python | `OUT/py` |
| `--ts-path DIR` | Output directory for TypeScript | `OUT/ts` |
| `--js-path DIR` | Output directory for JavaScript | `OUT/js` |
| `--csharp-path DIR` | Output directory for C# | `OUT/csharp` |
| `--gql-path DIR` | Output directory for GraphQL | `OUT/gql` |
| `--rust-path DIR` | Output directory for Rust | `OUT/rust` |
| `--catalog-path DIR` | Directory for the editor type catalog `sf_compile.json`, which maps every message and enum to its generated file and name in each language | The directory shared by the enabled outputs: `OUT` with `--out`, `generated/` with the default layout, otherwise the common parent of the output paths (or the first output directory when they share nothing narrower than the working directory) |
| `--hash-path DIR` | Directory for the generation hash `.structframe.hash` | The first enabled output directory, in the order C, C++, Python, TypeScript, JavaScript, C#, GraphQL, Rust |

```bash
struct-frame robot.sf --lang c,py,ts --out build/gen           # build/gen/c, build/gen/py, build/gen/ts
struct-frame robot.sf --lang c,py --out build/gen --c-path fw   # C goes to fw/ instead
```

## Generated Code Options

| Option | Description |
|--------|-------------|
| `--sdk` | Also copy the SDK (transports and message routing) for C++, Python, TypeScript and JavaScript. C# and Rust always receive their SDK core; C has no SDK. |
| `--sdk-embedded` | Copy the embedded C++ SDK (serial transport only, no ASIO). Honoured by C++ only; for other languages the full SDK is copied and a note is printed to stderr. |
| `--equality` | Generate equality operators/methods for messages |
| `--generate-tests` | Generate round-trip test programs with dummy values for every message |
| `--no-packed` | Generate code without packed structs (see [below](#--no-packed)) |
| `--csharp-namespace NS` | Root namespace for generated C# code (default `StructFrame`) |
| `--py-package NAME` | Name of the Python package that holds the generated modules and the runtime, created inside the Python output directory (default `structframe`). It cannot be `struct_frame`, the generator's own package. |
| `--name-overrides FILE` | JSON file with explicit per-language name overrides for generated identifiers (see [Generated Names](/basic-usage/message-definitions/#generated-names)) |

The generated `StructFrame.csproj` targets `net10.0` (override with `-p:TargetFrameworks=...`, plural, or a `Directory.Build.props`). The transport implementations under `Framework/Sdk/Transports/` are always copied but only compiled when the matching MSBuild property is set: `-p:IncludeSerialTransport=true` adds the serial transport (and `System.IO.Ports`), and `-p:IncludeNetCoreServer=true` adds the TCP/UDP/WebSocket transports.

## Run Control

| Option | Description |
|--------|-------------|
| `--validate` | Check the schema without writing files. With no language selected, it is checked against every language, so a schema that passes cannot fail later when a language is enabled. |
| `--force` | Regenerate even when nothing changed. The generation hash covers the schema structure **and** documentation (comments that reach generated output), the options, the `--name-overrides` file and the generator itself, so editing a comment regenerates without `--force`. Generation also runs when an expected output directory is missing. |
| `--config FILE` | Read options from a TOML file (see below) |
| `-q`, `--quiet` | Print only warnings and errors |
| `--debug` | Print the parsed model and cache decisions |

## Config File (`structframe.toml`)

Instead of repeating options in every build script, put them in a TOML file. `struct-frame` with no `SCHEMA` reads `./structframe.toml`; `--config FILE` reads any file.

```toml
# structframe.toml
schema = "proto/robot.sf"
lang = ["c", "py", "ts"]
out = "build/gen"
c-path = "firmware/src/gen"   # any option, without the leading dashes
equality = true
```

- Keys are the long option names without the dashes (`c-path` and `c_path` both work), plus `schema`.
- Flags (`equality`, `sdk`, `no-packed`, ...) take `true`/`false`; `lang` takes a string or a list; everything else takes a string.
- Relative paths are resolved against the directory of the config file, so the build can run from anywhere.
- Command-line options override the file; `--lang` adds to the configured languages.
- Unknown keys and wrongly typed values are errors (exit status 2). Python 3.9 and 3.10 need the `tomli` package to read the file; it is installed with struct-frame on those versions.

## Using the Generator from Python

```python
from struct_frame import main

status = main(["robot.sf", "--lang", "c,py", "--out", "gen", "--quiet"])
```

`main()` takes the same arguments as the command line and returns the exit status. It can be called repeatedly in one process. Usage errors raise `SystemExit`, as with any argparse program.

## Stale outputs

Each output directory also holds `.structframe-manifest.json`, which records the files every root schema generated there. When a schema is generated again, files it produced last time but no longer produces (a renamed or removed message or package) are deleted and reported as `Removed stale output ...`. Files that another schema generated into the same directory are kept, and the Rust `lib.rs` / `Cargo.toml` are rebuilt to match. Commit the manifest along with the generated code if you check generated code in.

## Error messages

Schema errors start with `path:line:` (for example `robot.sf:12: field 'x' is declared twice in message Pose`), the form most editors and CI log viewers turn into links. Errors go to stderr and the exit code is 1.

## `--no-packed`

```bash
struct-frame messages.sf --build-c --no-packed
```

The C/C++ generators omit the `#pragma pack(push, 1)` / `#pragma pack(pop)` directives around the struct definitions, and every message is treated as if it had been declared with `option variable = true`. The generated `<Type>_serialize` / `<Type>_deserialize` (and the C++ `serialize` / `deserialize` methods) then read and write each field individually instead of relying on the in-memory layout of the struct. This makes the generated code portable across platforms that lack support for packed structs or have different alignment requirements. It does **not** add byte-order handling: the C and C++ payload codecs still copy values in host byte order, and the wire format is little-endian (see [Conformance](/reference/conformance/)).

## Schema Diff (Wire-Compatibility Check)

```bash
struct-frame diff OLD.sf NEW.sf [--format text|json] [--fail-on breaking|rename|any] [--write-snapshot PATH]
```

Compares two schema revisions and reports whether the wire format is still compatible. Each side can be a `.sf` file (imports are followed) or a snapshot `.json` written by `--write-snapshot`, so a checked-in baseline can replace a second checkout. `--debug` may precede `diff`. Differences are reported in separate groups:

| Group | Meaning | Examples |
|-------|---------|----------|
| **Wire-breaking** | The wire format changes | Changed message ID or package ID, changed magic bytes, field type/size/number changes, removed fields, fields added to the base layout, reordered fields or oneof variants (discriminator values follow declaration order), changed enum values, removed messages/enums/enum values, changed `variable`/discriminator/`max_size` options |
| **Wire-compatible** | Additive changes that older receivers tolerate | New messages and enums, new enum values, fields and oneof variants appended after `extensions_start`, changed defaults and `min_size` |
| **Source-only renames** | Same wire identity (message ID, field number, enum value, variant position), different source name | Renamed messages, fields, enums, enum values, oneofs and variants |
| **File moves** | A declaration moved to another source file | Splitting a schema into imported files |

Comments, documentation and the declaration order of messages and enums are ignored. A renamed message is reported as a rename, but because magic bytes include the *name* of embedded message types, messages that embed it also report a changed magic bytes value (breaking).

Exit status: `0` when nothing in the failing groups was found, `1` otherwise, `2` when a schema or snapshot cannot be loaded. By default only wire-breaking changes fail; `--fail-on rename` also fails on source-only renames and `--fail-on any` also fails on additive changes. File moves never fail.

```bash
# Gate a pull request on wire compatibility
struct-frame diff main/messages.sf messages.sf

# Keep a baseline instead of a second checkout
struct-frame diff messages.sf messages.sf --write-snapshot baseline.json
struct-frame diff baseline.json messages.sf --format json
```

## Generated Files

Every language also receives `.structframe.hash` (in the hash directory) and `.structframe-manifest.json`.

### C
- `<package>.structframe.h` - Message structs, `_serialize` / `_deserialize`, typed frame writers `<Type>_write(writer, &msg)` / `<Type>_write_ext(...)`, and `<package>_get_message_info`
- `structframe_all.h` - Includes every package header and defines `structframe_all_get_message_info`, which looks an ID up across all packages
- Frame runtime (`frame_base.h`, `frame_headers.h`, `payload_types.h`, `frame_profiles.h`, `frame_parsers.h`)

### C++
- `<package>.structframe.hpp` - Message structs in `structframe::<package>`, plus `get_message_info`
- `structframe_all.hpp` - Includes every package header and defines `structframe::get_message_info` across all packages
- Frame runtime (`frame_base.hpp`, `frame_headers.hpp`, `frame_profiles.hpp`, ...)
- `struct_frame_sdk/` - SDK files (with `--sdk` or `--sdk-embedded`)

### TypeScript
- `<package>.structframe.ts` - Message classes, `getMessageInfo` and `decodeMessage` (file names are kebab-case, e.g. `pkg-test-a.structframe.ts`)
- `index.ts` - The runtime's exports plus one namespace per package (`import { hello, BufferWriter } from './gen/ts'`), and `package.json`
- Frame runtime (`frame-base.ts`, `frame-headers.ts`, `frame-profiles.ts`, ...)
- `struct-frame-sdk/` - SDK files (with `--sdk`)

### JavaScript
- `<package>.structframe.js` - Message classes, `getMessageInfo` and `decodeMessage` (kebab-case file names)
- `index.js` - The runtime's exports plus one property per package
- Frame runtime, compiled from the TypeScript runtime

### Python
Everything is in one package, `PY_PATH/structframe/` (see `--py-package`), whose modules import each other relatively, so the package also works nested inside your own package:
- `structframe/<package>.py` - Message classes, `get_message_info` and `decode_message`
- `structframe/__init__.py` - The runtime's exports plus each schema package as a submodule (`import structframe; structframe.robot.Status`)
- `structframe/frame_base.py`, `frame_profiles.py`, ... - Frame runtime
- `structframe/struct_frame_sdk/` - SDK files (with `--sdk`)

Put `PY_PATH` on `sys.path` (or generate into a directory that already is) and import `from structframe.robot import Status`, `from structframe.frame_profiles import AccumulatingReader`. Schema packages cannot be named after a runtime module (`frame_base`, `frame_headers`, `payload_types`, `frame_profiles`, `struct_frame_sdk`).

Versions 0.10.x and earlier wrote `PY_PATH/struct_frame/generated/<package>.py` with the runtime at the top of `PY_PATH`; when upgrading, delete the old `struct_frame/` directory and the runtime files (`frame_*.py`, `payload_types.py`, `__init__.py`, `struct_frame_sdk/`) from `PY_PATH`, and change imports from `struct_frame.generated.<package>` / `frame_profiles` to `structframe.<package>` / `structframe.frame_profiles`.

### GraphQL
- `<package>.graphql` - GraphQL schema definitions, one file per package
- `schema.graphql` - All packages combined into one self-contained schema

### C#
- `<PackageName>/Enums/<EnumName>.cs` - Enum definitions (one per enum)
- `<PackageName>/Messages/<MessageName>.cs` - Message classes (one per message)
- `<PackageName>/MessageDefinitions.cs` - Message registry, `GetMessageInfo` and `Deserialize(FrameMsgInfo)`
- `<PackageName>/SdkInterface.cs` - SDK interface (always generated)
- `Framework/` - Framing, profiles, types, and SDK core
- `Framework/Sdk/Transports/` - Transport implementations (always copied; compiled according to the `.csproj` properties above)
- `StructFrame.csproj` - Project file (always generated)

### Rust
- `<package>.structframe.rs` - Message structs with `StructFrameMessage` trait impl
- `Cargo.toml` - Crate manifest (always generated)
- `lib.rs` - Crate root re-exporting all modules, a `prelude`, and a merged `get_message_info` (always generated)
- Frame runtime: `frame_base.rs`, `frame_headers.rs`, `payload_types.rs`, `frame_profiles.rs`
