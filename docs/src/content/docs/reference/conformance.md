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
| `fixed_string<N>` / `fixed_bytes<N>` | Exactly N bytes, NUL-padded           |
| `string<N>` / `bytes<N>` | 1 length byte (≤ N), then N bytes (length-prefixed; trailing bytes are unspecified) |
| `array<T, N>`              | N elements packed back-to-back                   |
| `vector<T, N>`             | 1 count byte (≤ N), then N elements              |
| Nested message | The nested struct, packed inline (no header, no CRC)        |
| `oneof` (envelope) | A 1-byte discriminator followed by the selected variant. The discriminator is the *field number* of the active variant (default), or the *msgid* of the active variant with `[discriminator = msgid]`, or absent with `[discriminator = none]` (in which case the active variant is implied by message length / context). |
| Extension fields (an `extensions { }` block) | Encoded after the base fields, in declaration order. Older parsers MAY truncate the payload to `base_size` and still decode successfully (see [§ 5](#5-wire-evolution)). |

Multi-byte integers are little-endian on the wire in *all* reference implementations.
Structs are packed with no implicit padding; the generator emits
`#pragma pack(push, 1)` in C/C++ unless `--no-packed` is passed.

**Host byte order.** The Python, TypeScript/JavaScript, Rust and C# runtimes encode
multi-byte values explicitly and are correct on any host (C# arrays are byte-swapped
on big-endian hosts). The generated **C and C++** payload codecs copy values in host
byte order, so they require a little-endian host; `--no-packed` changes alignment
handling only, not byte order. The C/C++ runtime headers refuse to compile on a
big-endian target (`#error`) rather than silently corrupt data; define
`STRUCT_FRAME_ASSUME_LITTLE_ENDIAN` to override the check on a toolchain that does
not expose the byte-order macros.

## 3. Message IDs and package IDs

* For `Standard` / `Sensor` / `IPC` profiles, `MSG_ID` is a single byte in the
  range 0–255.
* For `Bulk` / `Network` profiles, the wire carries two adjacent bytes
  `PKG_ID` (high) and `MSG_ID` (low). The encoder derives `PKG_ID` as the
  high byte of the message's full 16-bit ID: `PKG_ID = (MSG_ID >> 8) & 0xFF`.
  This matches the C++ reference encoder and is required of any conforming
  implementation.
* `package name @N;` sets the high byte; `message Name @M { … }` sets the
  low byte. A message's effective 16-bit id is `(pkgid << 8) | msgid`.

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

**Extension-aware variant.** When the message has an `extensions { }` block,
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
2. **Appending extension fields** (inside the message's or a oneof's
   `extensions { }` block) is **non-breaking**:
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
| 5 | Handle `extensions { }` blocks per [§ 5](#5-wire-evolution) (base/extension CRC split, magic from base only) | `tests/test_wire_evolution.py` |
| 6 | Derive `PKG_ID` for Bulk/Network as the high byte of the 16-bit msgid | per-language `test_extended` |
| 7 | Truncate variable-length arrays correctly for `[variable]` messages | per-language `test_variable_flag` |
| 8 | Cross-decode files produced by every other reference implementation | `tests/run_tests.py` cross-platform matrix |
| 9 | Produce byte-deterministic generator output (no timestamps, no hash-set ordering) | `tests/check_determinism.py` |
| 10 | Carry and demultiplex system frames per [§ 9](#9-system-frames) (header validation, hidden by default, separate sequence space) | `tests/test_system_frames.py`, `tests/test_system_frames_runtimes.py`, `tests/test_stream_cross_lang.py` |

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

## 9. System frames

A *system frame* carries one of struct-frame's own messages (heartbeat, ping,
link tests, RPC envelopes) on the same link as the application's frames. The
messages are declared in the built-in schema
[`sf_system.sf`](https://github.com/mylonics/struct-frame/blob/main/src/struct_frame/builtin/sf_system.sf),
whose package name `sf_system` is reserved.

### 9.1 Layout

A system frame uses payload type **9**, so its payload-type start byte is
**`0x79`**. It travels after the header of the profile in use, and only
headers that encode the payload type can carry it:

| Header | System frame |
|--------|--------------|
| Basic (`Standard`, `Bulk`, `Network`) | `[0x90] [0x79] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [SYS_MSG_ID] [PAYLOAD…] [CRC1] [CRC2]` |
| Tiny (`Sensor`) | `[0x79] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [SYS_MSG_ID] [PAYLOAD…] [CRC1] [CRC2]` |
| None (`IPC`), UBX, MAVLink | Not supported: a `0x79` byte is ordinary data. |

The layout after the start bytes is the same for every profile, whatever the
profile's own payload type is (a `Sensor` link has no CRC on its application
frames, but its system frames do).

* `SEQ` — the sender's system-frame sequence number. It is a separate sequence
  space from the application frames'.
* `SYS`, `COMP` — the sender's system and component ids.
* `LEN` — little-endian uint16, the length of `PAYLOAD`.
* `SYS_MSG_ID` — a system message id. System ids are their own id space and
  never collide with application ids: `0x01`–`0x7F` struct-frame core,
  `0x80`–`0xEF` reserved, `0xF0`–`0xFF` vendor use.
* `PAYLOAD` — the message's fixed fields (encoded as in [§ 2](#2-payload-encoding)),
  followed for some messages by a raw **tail** of `LEN − fixed size` bytes
  (at most `MAX_TAIL` = 1024).
* `CRC1`, `CRC2` — Fletcher-16 over `SEQ` … end of `PAYLOAD` with the system
  message's magic bytes mixed in after the data ([§ 4](#4-checksum)). There is
  no extension split.

| `SYS_MSG_ID` | Message | Fixed size | Magic | Tail |
|---|---|---|---|---|
| `0x01` | Heartbeat | 18 | 58, 250 | no |
| `0x02` | LinkStats | 40 | 88, 134 | no |
| `0x10` | Ping | 14 | 28, 82 | yes |
| `0x11` | Pong | 14 | 25, 56 | yes |
| `0x20` | LinkTestStart | 20 | 70, 72 | no |
| `0x21` | LinkTestAck | 4 | 11, 22 | no |
| `0x22` | LinkTestData | 5 | 9, 15 | yes |
| `0x23` | LinkTestStop | 1 | 2, 2 | no |
| `0x24` | LinkTestReport | 41 | 107, 39 | no |
| `0x30` | RpcRequest | 8 | 31, 99 | yes |
| `0x31` | RpcResponse | 7 | 24, 68 | yes |

### 9.2 Reader behaviour

A conforming reader for a Basic or Tiny profile MUST:

1. **Recognise** a frame that starts with the system start bytes (`90 79` or
   `79`) as a system-frame candidate, and look for both the application start
   byte and the system start byte when it resynchronises.
2. **Validate the header before collecting the payload.** If `SYS_MSG_ID` is
   unknown, or `LEN` is below the message's fixed size or above its fixed size
   plus the largest tail it may take (zero for messages without a tail), the
   candidate is rejected: count it in `cnt_system_rejected` and resynchronise
   at once. A buffer-mode reader resumes scanning at the byte after the start
   byte, so a stray `0x79` costs nothing. A byte-by-byte reader that discards
   the rejected header bytes may lose only the frames that start inside that
   header (7 bytes after a Tiny start, 8 after a Basic one).
3. **Verify the CRC** with the system message's magic; a mismatch counts in
   `cnt_crc_failures` like any CRC failure.
4. **Hide system frames by default.** A valid system frame is counted in
   `cnt_system_frames` and not returned, so application code that only knows
   application message ids never sees one. When the application opts in
   (`deliver_system_frames` / `DeliverSystemFrames` /
   `set_deliver_system_frames`), system frames are returned flagged
   `is_system`, with `msg_id` set to the system message id.
5. **Track system sequence numbers separately**: a gap in the system-frame
   `SEQ` counts in `cnt_seq_gaps`, as a gap in the application sequence does,
   but neither stream's numbers affect the other's.

C and C++ readers can compile the support out with `SF_DISABLE_SYSTEM_FRAMES`;
`0x79` is then ordinary data.

### 9.3 Test vectors

`tests/test_system_frames.py` builds these frames from the description above
(no runtime code), and every runtime must encode and decode them byte for byte
(`tests/test_system_frames_runtimes.py`):

| Profile | Message | SEQ, SYS, COMP | Tail | Frame |
|---|---|---|---|---|
| Standard | LinkTestStop{test_id=3} | 0, 0, 0 | — | `90 79 00 00 00 01 00 23 03 2B A1` |
| Standard | Heartbeat{uptime_ms=1234, counter=5, wire_hash=0xDEADBEEF, interval_ms=1000, protocol_version=1} | 7, 4, 5 | — | `90 79 07 04 05 12 00 01 D2 04 00 00 05 00 00 00 EF BE AD DE E8 03 01 00 00 00 56 00` |
| Sensor | Heartbeat{uptime_ms=0xFFFFFFFF, counter=1, interval_ms=250, protocol_version=1, node_type=2, state=1, flags=6} | 0, 1, 2 | — | `79 00 01 02 12 00 01 FF FF FF FF 01 00 00 00 00 00 00 00 FA 00 01 02 01 06 4B 26` |
| Standard | Ping{t_send_us=0x0102030405060708, seq=9, target_sys=3, target_comp=4} | 255, 6, 7 | `AA BB CC` | `90 79 FF 06 07 11 00 10 08 07 06 05 04 03 02 01 09 00 00 00 03 04 AA BB CC 00 E2` |
| Sensor | RpcRequest{call_id=0x1234, payload_id=0x0102, payload_magic1=0x11, payload_magic2=0x22, target_sys=1, target_comp=2} | 1, 2, 3 | `00 01 … 09` | `79 01 02 03 12 00 30 34 12 02 01 11 22 01 02 00 01 02 03 04 05 06 07 08 09 76 93` |

Mixed streams of application frames, system frames, garbage and stray system
headers are decoded by every runtime and compared, hidden and delivered, at
several chunk sizes in `tests/test_stream_cross_lang.py`.

### 9.4 Wire hash

Every generated package carries a `WIRE_HASH` constant (`uint32`), a fingerprint of its
base wire contract that heartbeats report so nodes can notice a peer built from another
schema. It is FNV-1a-32 (offset basis `0x811C9DC5`, prime `0x01000193`) over:

1. the package id (one byte, 0 when the package has none), then
2. for every message with an id, in effective-id order, the little-endian record
   `effective id (u16), magic1 (u8), magic2 (u8), base size (u32), minimum size (u32),
   variable flag (u8)`, where the minimum size equals the base size for fixed messages.

Renaming, documentation, id-less structs and extension fields leave it unchanged; any
change to ids, magic bytes, base or minimum sizes, or the variable flag changes it. The
name `WIRE_HASH` is therefore reserved for constants. The built-in `sf_system` package's
value is `2865079104` (`tests/test_wire_hash.py`).
