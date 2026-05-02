# struct-frame – In-Depth Architecture Review

Author: Copilot Coding Agent
Scope: namespaces, include/import strategy, file linking, generated-code packaging,
language-native style-guide alignment.
Goal: provide a concrete plan to evolve struct-frame into a messaging protocol
system that can credibly compete with **Protocol Buffers** and **MAVLink**.

> This document is a review and a roadmap. It contains **no behavioural code
> changes** — only analysis, recommendations and a prioritised plan. Each
> recommendation is intended to be split into its own follow-up PR.

---

## 1. Repository at a glance

```
src/struct_frame/                 ← Python code generator package
├── generate.py                   ← CLI / orchestration (≈2 000 LOC, monolithic)
├── base.py                       ← naming-style helpers
├── c_gen.py / cpp_gen.py / ts_gen.py / js_gen.py / py_gen.py /
│   rust_gen.py / csharp_gen.py / gql_gen.py / csharp_sdk_interface_gen.py
└── boilerplate/                  ← hand-written runtime libraries copied
    ├── c/      (frame_base.h, frame_headers.h, payload_types.h, frame_parsers.h, frame_profiles.h)
    ├── cpp/    (.hpp + struct_frame_sdk/ subtree with bundled asio)
    ├── csharp/Framework/{Types,Framing,Profiles,Sdk}
    ├── js/     (CommonJS, kebab-case)
    ├── py/     (PEP-8, struct_frame_sdk subpackage)
    ├── rust/   (lib.rs, frame_*.rs)
    └── ts/     (ESM, kebab-case, struct-frame-sdk subdir)
```

The runtime “boilerplate” for each language is **copied** into the user’s output
tree by `generate.py`; user code then `#include`/`import`s the copied files
side-by-side with the generated package files. This is the single most
important architectural fact in the repository — almost every issue called out
below is downstream of it.

---

## 2. Current state — namespaces, includes & packaging

### 2.1 C (`*.structframe.h`)

- **No namespacing primitive in C.** Identifiers are disambiguated by
  prepending PascalCase package + identifier, e.g. `GenericRobotPosition`,
  `GENERIC_ROBOT_POSITION_MAX_SIZE`, `GENERIC_ROBOT_RTCM_MSG_ID`.
- Header layout:
  - `#pragma once` (good — `#pragma pack(1)` is also emitted, see § 4.1)
  - Includes `<stdbool.h>`, `<stdint.h>`, `<stddef.h>`, `frame_base.h`, plus
    `"<imported_pkg>.structframe.h"` per imported package.
  - No `extern "C"` guard — file is not safe to include from C++.
  - Defines hundreds of `#define`s in the global preprocessor namespace
    (`GENERIC_ROBOT_POSITION_MAX_SIZE`, `…_MSG_ID`, `…_MAGIC1/2`). Risk of
    collisions and IDE noise.
- Each `.structframe.h` re-emits a `static inline get_message_info()` —
  duplicated symbol across every header that includes it more than once is
  fine (it is `static inline`), but there is no aggregate “registry” header.

### 2.2 C++ (`*.structframe.hpp`)

- The most architecturally inconsistent generator:

  | Mode                                | Wrapping namespace                       | Type name                       |
  | ----------------------------------- | ---------------------------------------- | ------------------------------- |
  | Without `option pkgid = N`          | **Global namespace**                     | `GenericRobotPosition`          |
  | With `option pkgid = N`             | `namespace generic_robot { … }`          | `Position` (no prefix)          |

  This means a single repository can have *both* `mypkg::Foo` and `OtherFoo`
  living at the same scope depending on whether the proto file happened to
  declare a package id. Cross-file uses must conditionally prefix.
- Boilerplate uses a **different** namespace, `FrameParsers` / nested
  `FrameParsers::FrameHeaders` / `FrameParsers::PayloadTypes`. The SDK on top
  uses yet another root, `StructFrame` (see `struct_frame_sdk.hpp`).
  Three sibling top-level namespaces (`FrameParsers`, `StructFrame`,
  `<package>`) is a smell.
- Includes generated headers via a relative `"<pkg>.structframe.hpp"`
  pattern. There is no umbrella header — consumers must include each package
  manually.
- Bundles **vendored ASIO** under `boilerplate/cpp/struct_frame_sdk/asio-repo/`
  (≈ tens of MB) into the published wheel via `pyproject.toml` `force-include`.
  Heavy footprint; see § 4.2.

### 2.3 Python (`struct_frame/generated/<pkg>.py`)

- Generator emits a real package layout (`struct_frame/generated/<pkg>.py`
  plus two `__init__.py`’s) in the user’s output dir — good.
- Imports are **wildcards**: `from .other_pkg import *`. This makes static
  analysis (`pyright`, `mypy`, IDE) lose track of provenance, and generated
  classes can shadow each other silently.
- Generated boilerplate (`frame_profiles.py`, …) is *copied* into the same
  output dir, but generated message files import it via a top-level name
  (`from frame_profiles import MessageInfo`), which only resolves if the
  output dir is on `sys.path`. This breaks normal Python distribution
  semantics and conflicts with the `struct_frame` package the generator
  itself ships.
- Class names use `Pkg_Message` (with underscore) which violates **PEP 8**
  class-name guidance.

### 2.4 TypeScript / JavaScript (`*.structframe.ts/.js`)

- Generated files import from sibling files using **relative**, **kebab-case**
  paths:
  ```ts
  import { MessageBase } from './struct-base';
  import { MessageInfo } from './frame-profiles';
  import { GenericRobotPoint } from './generic_robot.structframe';
  ```
  Note the inconsistency: boilerplate is kebab-case (`struct-base`) while
  generated package files keep the underscore from the proto package name
  (`generic_robot.structframe`). The mix is deliberate but breaks naming
  convention.
- No `package.json` / `tsconfig.json` / `index.ts` is generated next to user
  output, so the artefact is **not** a self-contained npm package. Consumers
  must hand-author build glue.
- JS uses CommonJS (`require`); TS uses ESM. Neither emits an `exports` map.
- Class names mix `UpperCamel_Pascal` (`SerializationTest_BasicTypesMessage`)
  which violates the **TypeScript style guide** (no underscores in
  identifiers).

### 2.5 C# (`Framework/…` + `<PascalPkg>/Messages/*.cs`)

- The most consistent generator:
  - Always emits `namespace StructFrame.<PascalPkg>` with a configurable root
    via `--csharp_namespace`.
  - `using StructFrame;` plus `using StructFrame.<RefPkg>;` per cross-package
    dependency.
  - Generates a real `.csproj` so the artefact is a usable class library.
- Property casing is still proto `snake_case`, contrary to **.NET Framework
  Design Guidelines** (PascalCase for public members). The generator’s own
  DEVGUIDE acknowledges this.
- Discriminator enums recently switched from `DataField` to `PkgDataField`
  (controlled by `--csharp_legacy_enum_names`) — naming choices are still in
  flux, indicating an incomplete naming model.

### 2.6 Rust (`<pkg>.structframe.rs` + generated `lib.rs`/`Cargo.toml`)

- Best of all the languages structurally: real crate produced with
  `pub mod <pkg>;` per package, plus a top-level merged
  `get_message_info(msg_id: u16)`.
- `lib.rs` `pub use`s most boilerplate symbols directly at the crate root,
  defeating Rust’s module separation and forcing consumers to wildcard-import
  to discover anything.
- Field names are `_escape_rust_field_name`d (`r#type`) but message struct
  names still carry the package prefix in PascalCase, ignoring Rust idiom of
  `pkg::Position`.

### 2.7 GraphQL (`*.graphql`)

- No package/namespace concept at all in GraphQL — generator simply prefixes
  type names. There is no schema stitching or `extend type` strategy.

---

## 3. Cross-cutting findings

| # | Finding | Severity |
|---|---------|----------|
| F1 | **Two independent disambiguation strategies** coexist (PascalCase prefix vs language namespace), and the choice depends on whether `option pkgid` is set. | High |
| F2 | **No umbrella include / barrel module** is generated for any language. Every consumer must enumerate generated files manually. | High |
| F3 | **Boilerplate is copied, not packaged.** No language has a real first-class runtime library distributed via its native package manager (apart from C#’s `.csproj` and Rust’s synthesized `Cargo.toml`). There is no published crate, no `npm` package, no `pip install struct-frame-runtime`. | Critical |
| F4 | **Imports use wildcards** in Python (`from .x import *`) and re-exports in Rust/TS. Hides provenance and breaks tooling. | High |
| F5 | **Identifier conventions diverge from each language’s style guide** in Python (`Pkg_Message`), TypeScript (`Pkg_Message`), C# (`snake_case` properties), Rust (`PkgPosition` rather than `pkg::Position`). | High |
| F6 | **No stable wire/IDL versioning**: `version = "0.0.1"` hard-coded in `base.py` whilst `pyproject.toml` is on `0.7.11`. Generated code stamps the wrong version and embeds `time.asctime()` (non-reproducible builds). | High |
| F7 | **No forward/backward compatibility model** in the wire format. MAGIC bytes derived from `(field_type, position, size)` mean any field reorder or type change silently rejects messages, and there is no concept of optional/unknown fields the way protobuf (optional/unknown fields) or MAVLink v2 (trailing-zero payload truncation plus a per-message `CRC_EXTRA` seed) provide. | Critical |
| F8 | **No reflection / descriptor format**. Both protobuf and MAVLink ship machine-readable descriptors (`FileDescriptorProto`, `*.xml`). struct-frame produces only `sf_compile.json` for IDE navigation — not a runtime reflection format. | High |
| F9 | **Generator is monolithic** — 2 000 LOC `generate.py` plus per-language files of 600–1 600 LOC each, all sharing module-level `packages = {}` and `package_imports = {}` globals. Hard to extend (e.g. to add Go, Kotlin) and hard to test in isolation. | Medium |
| F10 | **Bundled ASIO** (≈ tens of MB) inflates the wheel and pins users to a vendored copy. `--sdk` is all-or-nothing. | Medium |
| F11 | `.structframe.` infix conflicts with no convention but is also recognised by no IDE or linter — protobuf uses `*.pb.<ext>`; gRPC uses `*_pb2.py`. Adopting the conventional infix would aid discoverability. | Low |
| F12 | C headers lack `extern "C" { … }` guard and so are not includable from C++ TU’s, even though a C++ generator also exists. | Medium |
| F13 | Every C `.structframe.h` emits `#pragma pack(1)` **without a matching `#pragma pack()`** to restore prior packing — silently changes packing of any header included afterwards. | High (latent bug) |

---

## 4. Selected deeper observations

### 4.1 C: `#pragma pack(1)` leak

`src/struct_frame/boilerplate/c/`* emits `#pragma pack(1)` at file scope and
never restores. Any TU that includes a generated header followed by, say,
`<sys/stat.h>` will silently have its later types packed. The fix is one of:

- Use `__attribute__((packed))` per-struct (GCC/Clang) and `__pragma(pack…)`
  on MSVC, gated by macros.
- Or wrap with `#pragma pack(push, 1)` … `#pragma pack(pop)` exactly around
  the structs.

The latter is the minimal correct fix.

### 4.2 C++: namespace fragmentation

Today:

```
namespace FrameParsers           // frame_base.hpp, frame_profiles.hpp …
namespace FrameParsers::FrameHeaders
namespace FrameParsers::PayloadTypes
namespace StructFrame            // SDK transports
namespace <pkg>                  // generated, only when pkgid is set
(global)                         // generated, when no pkgid
```

Desired (see § 6):

```
namespace structframe                    // root, all hand-written runtime
namespace structframe::headers
namespace structframe::payloads
namespace structframe::sdk               // transports / observers
namespace structframe::gen::<pkg>        // ALL generated code, always
```

This single reorganisation removes the “pkgid changes my namespace” trap and
gives consumers one stable root to alias (`namespace sf = structframe::gen;`).

### 4.3 Python: wildcard imports

`generate.py:1191`

```python
yield 'from .%s import *\n' % pkg_name
```

Replace with explicit re-exports computed from the imported package’s
exported types (`from .other_pkg import Foo, Bar, …`) and an `__all__`
declaration in each generated module. This unlocks `pyright --strict`,
removes the “class shadowed by * import” class of bug, and lets `mypy`
discover types across packages.

### 4.4 TypeScript: no runtime package

The current artefact is a flat directory of `.ts` files. Modern TS libraries
publish a package with `package.json` containing `"type": "module"`,
`"exports"` map, `"types"`, and a tsup/rollup-built `dist/`. struct-frame
should generate a tiny `package.json` and `index.ts` in the output dir so the
folder can be `npm link`-ed or published.

---

## 5. Comparative gap analysis (protobuf, MAVLink)

| Feature | protobuf | MAVLink v2 | **struct-frame today** | Required for parity |
|---|---|---|---|---|
| IDL grammar reuse | own `.proto` | own `*.xml` | reuses `.proto` ✅ | — |
| Wire compatibility on field add/remove | tag-based, optional | trailing-zero truncation + EXTRA_CRC | none — magic bytes break on any change ❌ | F7 |
| Optional/repeated/oneof | yes | limited | partial (oneof exists) | — |
| Reflection / descriptors | `FileDescriptorProto` | XML schema available at runtime | `sf_compile.json` (IDE only) ❌ | F8 |
| Namespacing per package | yes (deep nesting) | dialect/file | inconsistent ❌ | F1, F2 |
| Cross-file imports | yes | `<include>` element | yes, recursive ✅ | — |
| Code-gen plugin model | `protoc` plugin protocol | python jinja templates | inheritance + duck typing in-tree ❌ | F9 |
| Distributed runtime libraries | `protobuf-runtime` per language | `pymavlink`, C library | none (copy-in only) ❌ | F3 |
| Stable, documented wire spec | yes | yes (xml + docs site) | implicit, in code | new doc |
| Conformance test suite | yes | yes | per-language round-trip in `tests/` only | extend |
| Field/message annotations | options | params | a few `option`s | extend |
| Schema evolution policy | documented | documented | undocumented | new doc |
| Multi-transport SDK | grpc | serial / udp / tcp | partial across langs ✅ | unify |
| Built-in tooling | `protoc`, `protoc-gen-*` | `mavgen`, `mavinspect` | one CLI | extend |

The two most painful gaps for adoption are **F3 (no real runtime libraries)**
and **F7 (no schema evolution policy/wire compatibility)**. Without those,
struct-frame cannot be a credible alternative to protobuf or MAVLink for
non-hobby use.

---

## 6. Recommendations (target architecture)

### 6.1 Single canonical namespace per language

| Language | Recommended root | Generated code | Imports/Includes |
|---|---|---|---|
| C | prefix `sf_` for runtime; per-package `sf_<pkg>_` for generated | `sf_<pkg>_position_t`, `SF_<PKG>_POSITION_MAX_SIZE` | one umbrella `<root>.structframe.h` per consumer build |
| C++ | `structframe::` (runtime), `structframe::gen::<pkg>::` (generated) — *always*, regardless of `pkgid` | `structframe::gen::generic_robot::Position` | umbrella `structframe/all.hpp` |
| C# | `StructFrame.Runtime`, `StructFrame.Gen.<PascalPkg>` | Property names PascalCase | `<rootnamespace>.csproj` (already partially done) |
| Python | runtime package = `structframe` (hyphen→underscore), generated = `structframe.gen.<pkg>` | `class Position`, no underscore prefix | explicit imports + `__all__` |
| Rust | runtime crate = `structframe`, generated = `structframe_gen` (or `structframe::gen` re-export) | `gen::generic_robot::Position` | feature-gated profiles |
| TS / JS | scoped pkg `@struct-frame/runtime`, generated pkg per project under `dist/`, files in kebab-case, classes in PascalCase | `class Position`, no underscore | `index.ts` barrel |
| GraphQL | per-package `extend schema` with `directive @package(name: …)` | type prefix only when not nested | one stitched `schema.graphql` |

The key invariant: **the language namespace is the only disambiguator; type
names should never carry the package as a prefix**. Cross-package collisions
are then impossible by construction, and identifier names match each
language’s native style guide.

### 6.2 First-class runtime libraries

Stop copying boilerplate into user output. Publish runtimes once:

- **PyPI**: `struct-frame-runtime` (the `boilerplate/py/` tree).
- **npm**: `@struct-frame/runtime` (the `boilerplate/ts/` tree, transpiled).
- **crates.io**: `struct-frame` crate (the `boilerplate/rust/` tree).
- **NuGet**: `StructFrame.Runtime` (the `boilerplate/csharp/Framework/`
  tree minus transports; transports are an opt-in companion package).
- **C/C++**: ship as a CMake package via FetchContent / vcpkg / Conan; keep
  copy-in mode only as a fallback for embedded targets that can’t fetch
  dependencies.

The generator then emits:

- a tiny `package.json` / `Cargo.toml` / `pyproject.toml` / `.csproj` /
  `CMakeLists.txt` *that depends on the runtime* and lists generated files,
  not a copy of the runtime.

This collapses the wheel size (drop bundled asio), enables versioning of
runtime independent of generator, and makes upgrades safe.

### 6.3 Wire-level evolution policy

Adopt a hybrid of MAVLink v2 truncation + protobuf optional semantics:

1. **Trailing-zero truncation on send, zero-extension on receive** — append-
   only fields are forward-compatible without bumping `MSG_ID`.
2. **EXTRA_CRC seed** computed from message *name + non-extension field
   list*, so changing extension fields is compatible but reordering or
   re-typing existing fields is detected. This is the role today’s
   `magic1/magic2` bytes already play, but they currently include *every*
   field — narrow them to non-extension fields only.
3. Introduce an `extension` keyword (proto option) marking fields as
   forward-compatible additions. Today struct-frame has no concept of this.
4. Document a deprecation policy: how to mark a field deprecated, how to
   bump `MSG_ID` for a breaking change, how to namespace v1/v2 messages.

### 6.4 Reflection / descriptor format

Promote `sf_compile.json` to a stable, versioned `*.sfdesc.json` (and
optional binary `.sfd`) shipping next to generated code. Every generated
runtime should expose `describe(msg_id) → MessageDescriptor` so generic
tooling (logging, wireshark, debug consoles) can introspect without
recompilation.

### 6.5 Code-generator architecture

Refactor `generate.py` along these lines (no behaviour change initially):

1. Pull `Enum`, `Field`, `OneOf`, `Message`, `Package` into a `model/`
   subpackage; remove module-level globals (`packages`, `package_imports`).
2. Introduce a `Generator` interface (`def emit(self, package, ctx) → dict`)
   and register concrete implementations via entry points
   (`struct_frame.generators` group). This makes adding Go / Kotlin / Java
   trivial and lets users ship out-of-tree generators.
3. Add per-generator unit tests using a few synthetic in-memory `Package`
   objects rather than re-parsing `.proto` files.
4. Replace `time.asctime()` stamps with the package version and the SHA of
   the input proto for **reproducible builds**.

### 6.6 Tooling parity

To match `protoc` / `mavgen`, ship:

- `struct_frame inspect <file>` — pretty-print the model.
- `struct_frame diff <a.proto> <b.proto>` — wire compatibility check
  (additions ok, reorder/retype not).
- `struct_frame doc <file>` — Markdown / HTML reference docs.
- A LSP server (or integration with the existing `sf_compile.json`) so IDEs
  can jump from `.proto` to generated symbols.
- The existing `wireshark/struct_frame.lua` should be promoted to consume
  the descriptor format above so it works with arbitrary user schemas.

### 6.7 Code style alignment

Mechanical fixes per language:

| Lang | Today | Fix |
|---|---|---|
| Python | `class Pkg_Message`, `from .x import *` | `class Message` in `pkg` module; explicit imports + `__all__`; black/ruff config |
| TS / JS | `class Pkg_Message`, mixed kebab/snake file names | `class Message` in `pkg.ts`; ESLint config (`@typescript-eslint`); kebab file names everywhere |
| C# | `public int small_int { get; set; }` | PascalCase properties (already a known TODO in DEVGUIDE); add `.editorconfig` |
| Rust | `pub struct PkgPosition` | `pub mod pkg { pub struct Position }`; add `#![deny(rust_2018_idioms)]`; cargo fmt |
| C | `#pragma pack(1)` leak; no `extern "C"` | `pack(push,1)/pop`; wrap with `#ifdef __cplusplus extern "C" { … }`; clang-format already present (`.clang-format`) — apply to generated output too |
| C++ | dual namespace mode | always namespace; fold `FrameParsers` into `structframe` |

All of these are mechanical and largely non-breaking if shipped behind a
`--style=v2` opt-in flag for one minor release.

---

## 7. Phased plan

### Phase P0 – Stop the bleeding (1–2 weeks)

Goal: fix latent correctness bugs. Non-breaking.

- [ ] Wrap generated C structs with `#pragma pack(push,1)` / `#pragma pack(pop)` and add `extern "C"` guard.
- [ ] Fix `version = "0.0.1"` in `base.py` to read `pyproject.toml`.
- [ ] Replace `time.asctime()` in every generator with the package version + input file SHA for reproducible builds.
- [ ] Add `__all__` to every generated Python module and replace `from .x import *` with explicit re-exports.
- [ ] Add `report_progress`/CI checks for generated-file determinism.

### Phase P1 – Style-guide alignment (2–3 weeks)

Goal: every language’s generated code passes that language’s standard linter
(clang-tidy, ruff, eslint, dotnet format, clippy) on a clean run.

- [ ] Introduce a single `--style=v2` flag turning on:
  - PascalCase types without package prefix in C++/Python/TS/Rust/C#.
  - PascalCase properties + `record`s in C# where appropriate.
  - kebab-case file names + camelCase functions in TS/JS.
- [ ] Ship a migration script (`struct_frame migrate`) that rewrites user code from v1 names to v2 names.

### Phase P2 – Namespaces & packaging (4–6 weeks)

Goal: consistent, idiomatic per-language namespacing, real runtime packages.

- [ ] Always emit C++ generated code in `structframe::gen::<pkg>` regardless of `pkgid`. Fold `FrameParsers` into `structframe::`.
- [ ] Add umbrella headers (`<output>/all.structframe.{h,hpp}`) and barrel modules (`index.ts`, `__init__.py` `*` re-exports of `__all__`, Rust `pub use` per package).
- [ ] Publish runtimes:
  - `pip install struct-frame-runtime`
  - `npm install @struct-frame/runtime`
  - `cargo add struct-frame`
  - `dotnet add package StructFrame.Runtime`
  - C/C++: `FetchContent_Declare`, vcpkg port, Conan recipe.
- [ ] Generator stops copying boilerplate by default; new `--standalone` flag preserves the old behaviour for embedded users.
- [ ] Drop bundled asio from the wheel; install via vcpkg/Conan.

### Phase P3 – Wire spec & reflection (8–12 weeks)

Goal: schema evolution and reflection on par with protobuf/MAVLink.

- [ ] Add `extension` field option; redefine `magic1/magic2` to cover only non-extension fields.
- [ ] Implement trailing-zero truncation on encode and zero-extension on decode.
- [ ] Define and publish the wire format as a normative spec document under `docs/spec/`.
- [ ] Add `*.sfdesc.json` descriptor output and runtime `describe(msg_id)` API in every language.
- [ ] Add `struct_frame diff` for compatibility checking; wire it into CI.
- [ ] Promote `wireshark/struct_frame.lua` to load the descriptor at runtime.

### Phase P4 – Generator architecture (parallel, 4 weeks)

- [ ] Extract `model/` and remove module-level globals.
- [ ] Define `Generator` interface and register existing generators via entry points.
- [ ] Add a Go generator as the proof-of-concept third-party plugin.
- [ ] Add unit tests per generator using synthetic models (no `.proto` parsing required).

### Phase P5 – Tooling (ongoing)

- [ ] `struct_frame inspect|diff|doc` subcommands.
- [ ] LSP integration consuming `sf_compile.json` / `*.sfdesc.json`.
- [ ] Public conformance test suite & cross-language round-trip vectors checked into the repo.

---

## 8. Suggested minimal first PRs (after this review)

These are intentionally tiny so they can land quickly and unblock everything
above:

1. **Fix C `#pragma pack` leak** + add `extern "C"` guards. (P0, ≈30 LOC)
2. **Fix `base.py` version** to read from package metadata; remove
   `time.asctime()` stamps. (P0, ≈40 LOC, one test)
3. **Replace Python `from .x import *`** with explicit re-exports +
   `__all__` in `py_gen.py`. (P0, ≈80 LOC, regenerate test goldens)
4. **Add an umbrella header** generation flag (`--cpp_umbrella`) producing
   `<output>/structframe.hpp` that `#include`s every package header. (P2 lite,
   ≈60 LOC)
5. **Always namespace C++ generated code** (gated behind `--cpp_namespace v2`)
   to remove the pkgid-dependent dual mode. (P1, ≈150 LOC, regenerate
   goldens)

Each of these is independently shippable and provides immediate value while
the larger phases are scoped.

---

## 9. Out of scope for this review

- Concrete syntax for the new `extension` keyword (deferred to P3 design doc).
- Performance benchmarking vs nanopb / protobuf-c / pymavlink.
- Choice between FlatBuffers-style zero-copy vs current copy-on-decode model
  (currently copy-on-decode; revisit when descriptor format lands).

---

## 10. Summary

struct-frame has a solid foundation: a clean `.proto` reuse, a profile-based
framing model that is genuinely more flexible than MAVLink v2, and consistent
test coverage across seven target languages. The blockers to compete with
protobuf and MAVLink are organisational, not algorithmic:

1. **Make namespacing uniform and idiomatic per language** (§ 6.1).
2. **Distribute the runtime via each language’s native package manager**
   (§ 6.2, F3).
3. **Define a wire-evolution policy** so user schemas can grow without
   breaking peers (§ 6.3, F7).
4. **Ship a reflection/descriptor format** the ecosystem (Wireshark,
   loggers, debug UIs) can consume (§ 6.4, F8).
5. **Refactor the generator** so the project can scale to more languages and
   accept third-party generators (§ 6.5, F9).

Done in the order above, struct-frame can credibly position itself as
**“protobuf semantics with MAVLink-style framing for embedded transports”** —
a genuine niche neither incumbent fully owns today.
