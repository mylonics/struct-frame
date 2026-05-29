---
title: Conformance
description: Wire-format specification and canonical test vectors for struct-frame implementations.
---

This document is the **normative wire-format specification** for struct-frame.
Any independent implementation that interoperates with the reference
generators (C, C++, Python, TypeScript, JavaScript, C#, Rust) MUST produce
and accept frames as defined here, and MUST pass the test vectors described
in [§ 6](#6-canonical-test-vectors).

If a code generator change alters anything in this document, that change is
a **wire-format break** and must be accompanied by a version bump and a
deliberate regeneration of `tests/golden/`.

---

## 1. Frame structure

Every encoded message is exactly one *frame*. A frame is the concatenation of
three byte regions:

```
[ header ] [ payload ] [ footer ]
```

The exact layout of each region is determined by the frame *profile*. Profiles
are fixed combinations of a *header config* and a *payload config*. The five
profiles defined by the reference implementations are:

| Profile      | Frame layout (byte order, little-endian for multi-byte numeric fields) |
|--------------|------------------------------------------------------------------------|
| `Standard`   | `[0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD…] [CRC1] [CRC2]`                |
| `Sensor`     | `[0x70] [MSG_ID] [PAYLOAD…]`                                           |
| `IPC`        | `[MSG_ID] [PAYLOAD…]`                                                  |
| `Bulk`       | `[0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD…] [CRC1] [CRC2]` |
| `Network`    | `[0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD…] [CRC1] [CRC2]` |

* `LEN`, `LEN_LO`/`LEN_HI` — length of `PAYLOAD` only (not header, not footer).
  `Standard` uses a single byte; `Bulk` / `Network` use little-endian uint16.
* `MSG_ID` — single byte for `Standard` / `Sensor` / `IPC`; combined
  `PKG_ID` (high byte) + `MSG_ID` (low byte) for `Bulk` / `Network`.
  See [§ 3](#3-message-ids-and-package-ids).
* `SEQ`, `SYS_ID`, `COMP_ID` — single-byte routing fields. They are *not*
  validated against any registry by the parser; they ARE part of the
  CRC-protected region, so corrupting any of them on the wire causes the CRC
  check to fail (see negative-test scenario "Network profile: SysId/CompId
  corruption" in [`tests/NEGATIVE_TESTS.md`](https://github.com/mylonics/struct-frame/blob/main/tests/NEGATIVE_TESTS.md)).
* `CRC1` / `CRC2` — see [§ 4](#4-checksum).

`Sensor` and `IPC` carry no length field and no CRC. Parsers determine the
payload length by calling `get_message_info(msg_id)` to look up the
statically known message size; a buffer shorter than that is rejected (see
negative-test scenario "Minimal profile: Truncated frame").

## 2. Payload encoding

A *payload* is a packed C struct of the message's fields, in declaration
order, with no per-field tag or length prefix.

| Type           | Wire encoding                                                |
|----------------|--------------------------------------------------------------|
| `int8` / `uint8` / `bool` | 1 byte                                            |
| `int16` / `uint16`        | 2 bytes, little-endian                            |
| `int32` / `uint32` / `float` | 4 bytes, little-endian (IEEE-754 for `float`)  |
| `int64` / `uint64` / `double` | 8 bytes, little-endian (IEEE-754 for `double`) |
| `enum`         | Stored as the underlying integer type (default `int32`)      |
| Fixed `string size = N`    | Exactly N bytes, NUL-terminated, NUL-padded      |
| Variable `string max_size = N` | 1 length byte (≤ N), then N bytes (length-prefixed; trailing bytes are unspecified) |
| Fixed array `size = N`     | N elements packed back-to-back                   |
| Bounded array `max_size = N` | 1 count byte (≤ N), then N elements              |
| Nested message | The nested struct, packed inline (no header, no CRC)        |
| `oneof` (envelope) | A 1-byte discriminator followed by the selected variant. The discriminator is the *field number* of the active variant (default), or the *msgid* of the active variant when `option discriminator = msgid`, or absent when `option discriminator = none` (in which case the active variant is implied by message length / context). |
| Extension fields (`option extensions_start = N`) | Encoded after the base fields, in declaration order. Older parsers MAY truncate the payload to `base_size` and still decode successfully (see [§ 5](#5-wire-evolution)). |

Multi-byte integers are little-endian in *all* reference implementations.
Structs are packed with no implicit padding; the generator emits
`#pragma pack(push, 1)` in C/C++ unless `--no_packed` is passed.

## 3. Message IDs and package IDs

* For `Standard` / `Sensor` / `IPC` profiles, `MSG_ID` is a single byte in the
  range 0–255.
* For `Bulk` / `Network` profiles, the wire carries two adjacent bytes
  `PKG_ID` (high) and `MSG_ID` (low). The encoder derives `PKG_ID` as the
  high byte of the message's full 16-bit ID: `PKG_ID = (MSG_ID >> 8) & 0xFF`.
  This matches the C++ reference encoder and is required of any conforming
  implementation.
* `option pkgid = N;` on a package sets the high byte; `option msgid = M;`
  on a message sets the low byte. A message's effective 16-bit id is
  `(pkgid << 8) | msgid`.

## 4. Checksum

`Standard`, `Bulk`, and `Network` use a **Fletcher-16 with per-message
magic mixing**. The algorithm is:

```text
function fletcher_checksum(data, magic1, magic2):
    a = 0
    b = 0
    for byte in data:
        a = (a + byte) & 0xFF
        b = (b + a)    & 0xFF
    a = (a + magic1)   & 0xFF
    b = (b + a)        & 0xFF
    a = (a + magic2)   & 0xFF
    b = (b + a)        & 0xFF
    return (a, b)      // emitted as CRC1=a, CRC2=b
```

The CRC region covers every byte **after the start markers (`0x90` …) up to
but not including `CRC1`**: that is, the length field(s), any routing
fields (`SEQ`, `SYS_ID`, `COMP_ID`), `PKG_ID`, `MSG_ID`, and the entire
payload.

**Extension-aware variant.** When the message has `option extensions_start`,
the CRC is split: Fletcher is computed over the base region (header + base
payload), the two magic bytes are mixed in, *then* Fletcher continues over
the extension bytes:

```text
function fletcher_checksum_ext(data, base_len, total_len, magic1, magic2):
    a, b = 0, 0
    for byte in data[0:base_len]:        a, b = roll(a, b, byte)
    a, b = roll(a, b, magic1)
    a, b = roll(a, b, magic2)
    for byte in data[base_len:total_len]: a, b = roll(a, b, byte)
    return (a, b)
```

When `base_len == total_len` (no extensions present) this reduces exactly to
the non-extension form, so the algorithms agree for non-extended messages.

**Magic bytes.** `magic1` and `magic2` are per-message constants computed by
the generator from the message's *base* fields (extension fields and
extension oneof variants are excluded). The algorithm is:

```text
function calculate_magic_numbers(message):
    m1, m2, position = 0, 0, 0
    for field in message.base_fields + message.base_oneof_variants:
        type_code = TYPE_CODES[field.type]                      # see table below
        m1 = (m1 + type_code + position + 1) & 0xFF
        m2 = (m2 + m1)                       & 0xFF
        position += 1
    return (m1, m2)
```

Type codes (must match across implementations):

| Type | Code |
|------|------|
| `uint8`  | 1 |
| `int8`   | 2 |
| `uint16` | 3 |
| `int16`  | 4 |
| `uint32` | 5 |
| `int32`  | 6 |
| `bool`   | 7 |
| `float`  | 8 |
| `double` | 9 |
| `int64`  | 10 |
| `uint64` | 11 |
| `string` | 12 |
| `enum`   | 13 |
| nested message | `sum(ord(c) for c in type_name) % 256` |

The intent is that two messages with the same field layout produce the same
magic, and renaming a field or an enum doesn't change the wire format,
but adding, removing, reordering, or retyping a *base* field does.

## 5. Wire evolution

Compatibility rules for adding fields to an existing message:

1. **Appending base fields is a breaking change** — it changes the magic and
   therefore the CRC. Old parsers will reject new frames; new parsers will
   reject old frames.
2. **Appending extension fields** (under `option extensions_start = N;` or
   inside a `// Extension::` block on a oneof) is **non-breaking**:
   * Magic bytes are computed from base fields only, so they are unchanged.
   * The extension-aware CRC mixes magic between base and extension bytes,
     so old (extension-unaware) parsers that truncate to `base_size` still
     get a valid CRC; new (extension-aware) parsers verify the extended
     CRC and recover the extension values.
3. **Renaming a field, renaming an enum, or moving an enum inline** does not
   change the wire format.
4. **Reordering base fields** is a breaking change.

See [`tests/test_wire_evolution.py`](https://github.com/mylonics/struct-frame/blob/main/tests/test_wire_evolution.py) for the round-trip tests that
verify these rules.

## 6. Canonical test vectors

The reference test corpus is checked in under
[`tests/golden/`](https://github.com/mylonics/struct-frame/tree/main/tests/golden).
Each file is the byte-exact output of the Python reference encoder for one
`(suite, profile)` combination:

```
tests/golden/<suite>_<profile>.bin
```

A conforming implementation MUST:

1. Decode every golden file successfully (no CRC errors, no truncation
   errors, all field values match the documented test fixtures).
2. Re-encode the same fixtures and produce byte-identical output to the
   corresponding golden file.

To verify against the goldens locally:

```bash
python tests/check_golden.py            # verify
python tests/check_golden.py --update   # regenerate (deliberate change only)
```

`check_golden.py` is wired into the CI workflow alongside `check_determinism.py`,
so any unintended drift in either the wire format or the generator output
fails the build.

## 7. Conformance checklist for new implementations

To call an implementation "struct-frame conformant" it MUST:

| # | Requirement | Verified by |
|---|---|---|
| 1 | Encode/decode all five reference profiles with byte-exact framing | `tests/golden/` + per-language `test_standard` |
| 2 | Compute Fletcher-16 with per-message magic exactly as in [§ 4](#4-checksum) | `tests/test_magic_bytes.py` |
| 3 | Derive per-message magic bytes using the algorithm in [§ 4](#4-checksum) | `tests/test_magic_bytes.py` |
| 4 | Reject every scenario in [`tests/NEGATIVE_TESTS.md`](https://github.com/mylonics/struct-frame/blob/main/tests/NEGATIVE_TESTS.md) | per-language `test_negative` |
| 5 | Handle `option extensions_start` per [§ 5](#5-wire-evolution) (base/extension CRC split, magic from base only) | `tests/test_wire_evolution.py` |
| 6 | Derive `PKG_ID` for Bulk/Network as the high byte of the 16-bit msgid | per-language `test_extended` |
| 7 | Truncate variable-length arrays correctly when `option variable = true` | per-language `test_variable_flag` |
| 8 | Cross-decode files produced by every other reference implementation | `tests/run_tests.py` cross-platform matrix |
| 9 | Produce byte-deterministic generator output (no timestamps, no hash-set ordering) | `tests/check_determinism.py` |

Each row of the table corresponds to a real test (or set of tests) in the
repository — there is no "informal" conformance.

## 8. Versioning the wire format

If a future change deliberately alters anything specified in this document:

1. Update this page to describe the new format.
2. Bump the **major** version in `pyproject.toml` (any wire-format change
   is breaking, since pre-existing peers won't interoperate).
3. Run `python tests/check_golden.py --update` and commit the new golden
   files in the same commit as the version bump, with a `CHANGELOG.md`
   entry that explicitly says "wire-format change".
4. Add the previous-format goldens (if you want to keep dual-decoding
   capability) to `tests/golden/legacy/` and document a migration path.

Wire-format changes outside this process MUST be treated as bugs.
