# Native tools plan: system messages, heartbeat, latency, RPC, link tests

This is the working plan for the struct-frame native tools. It is written so an agent or developer
can pick up the next phase without the conversation that produced it. Read sections 1 to 4 before
starting any phase.

- Last updated: 2026-11-20.
- Base commit: `6c5730d` on branch `new_version` (feat!: native schema language, defaults, system
  frames and wire hash).

## Contents

1. [Status](#1-status)
2. [Decisions (do not re-open)](#2-decisions-do-not-re-open)
3. [Working rules and gotchas](#3-working-rules-and-gotchas)
4. [Verification](#4-verification)
5. [Phase C2: move system messages to message id 0](#5-phase-c2-move-system-messages-to-message-id-0)
6. [Phase E: node runtime and heartbeat](#6-phase-e-node-runtime-and-heartbeat)
7. [Phase F1: ping/pong latency](#7-phase-f1-pingpong-latency)
8. [Phase D: request/response (RPC)](#8-phase-d-requestresponse-rpc)
9. [Phase F2: throughput, integrity and the CLI](#9-phase-f2-throughput-integrity-and-the-cli)
10. [Phase A6: VS Code extension parser](#10-phase-a6-vs-code-extension-parser)
11. [Smaller open items](#11-smaller-open-items)
12. [Provisional choices to confirm with the user](#12-provisional-choices-to-confirm-with-the-user)

Phase order: **C2 → E → F1 → D → F2 → A6**. E comes before D because E builds the node runtime
and the cross-language node test harness that RPC reuses.

---

## 1. Status

| Phase | Content | State |
|---|---|---|
| 0 | IR/output goldens (`tests/ir_golden/`), `FrameMsgInfo` seq/sys/comp/pkg fields, C Tiny+CRC fix, custom-profile tests | Done; SDK items moved to E (see 6.8) |
| A | Native schema language (`src/struct_frame/schema/`), `migrate`, `fmt`, all schemas converted, consts in every language | Done except A6 |
| B | Array/struct/byte defaults, `reset`/`is_default`/per-field helpers in all 7 languages | Done |
| C | Built-in `sf_system` schema, system frames on start byte `0x79`, `WIRE_HASH`, vectors, goldens, fuzz, Wireshark, docs | Done, but the framing is being replaced (C2) |
| **C2** | System messages carried as application message id 0 in any profile | **Next** |
| E | `SystemNode` runtime + heartbeat, 7 languages | Not started |
| F1 | Ping responder (7) + latency initiator (5 host languages) | Not started |
| D | RPC: `service` codegen, server (7), client (5 host languages) | Not started; `service` is error `SF0390` in `schema/lower.py:657` |
| F2 | PRBS, throughput/integrity, `struct-frame link-test` CLI | Not started |
| A6 | VS Code extension parser port | Not started |

Language terms used below:

- **All 7:** C, C++, Python, TypeScript, JavaScript (compiled from TS), C#, Rust.
- **Host languages (5):** Python, TS/JS, C#, C++, Rust. They get initiators and clients.
- C gets responders and servers only.

Last full run before C2: `pytest tests/` gave 1080 passed and 1 failed. The failure is
`test_changelog_documents_unreleased_or_current_changes`, which failed before this work. The user's
uncommitted 0.11.1 CHANGELOG changes may fix it; check before treating it as known.

---

## 2. Decisions (do not re-open)

Made with the user:

- **Schema:** clean break to a type-first C-like language. Long and short primitive names are both
  accepted. Sized types are ETL style: `array`/`arr`, `vector`/`vec`, `string<N>`, `bytes<N>`,
  `fixed_string`/`fstring`, `fixed_bytes`/`fbytes`.
- **Comments:** `///` doc comments reach generated code.
- **Enums and consts:** enum values are explicit; `const` is typed.
- **Language scope:** codec, heartbeat, RPC server and link-test responder in all 7 languages.
  Initiators and clients in the 5 host languages, plus a Python CLI.
- **Defaults:** hardened, with array and nested defaults and runtime helpers.
- **System messages (2026-11-20, replaces the `0x79` frame):** a system message is an ordinary
  frame of the active profile whose message id is **0**. Its payload starts with a one-byte
  `SYS_MSG_ID`. It works with every header and payload type, including header None (IPC).
- **History:** the user does not want sibling-repo history preserved when consolidating.

---

## 3. Working rules and gotchas

**Process**

- **Commits:** don't commit unless the user asks. Use conventional commits (`feat!:` for breaking
  changes) and end the message with the `Co-Authored-By` line the session gives you.
- **Changelog:** never hand-edit `CHANGELOG.md`; it is generated at release.
- **Python modules:** run with `PYTHONPATH=src`, otherwise `python -m struct_frame` imports the
  site-packages install.
- **JavaScript:** JS runtime files are compiled from TS. Edit `boilerplate/ts/*.ts`, then run
  `npx tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json`. The serialport typing error it
  prints is pre-existing.
- **Built-in schema:** after editing `src/struct_frame/builtin/sf_system.sf` or any generator, run
  `python -m struct_frame.builtin --write`. `--check` is gated by `tests/test_builtin_sync.py`. The
  generator copies boilerplate over its output, so builtin generation uses a filtered runtime copy
  (`builtin/__init__.py`); keep that.
- **Subset compilers:** scripts that compile a runtime subset must include the system modules: C#
  `Framework/SfSystem`, Rust `system_frames.rs` + `sf_system.rs`. This covers KAT tests, fuzz
  drivers and stream drivers.
- **IR goldens:** regenerate with `python tests/ir_golden/ir_oracle.py --update` when generated
  output changes on purpose. Review the diff first.
- **C warnings:** C must build with `-std=c11 -Wall -Wextra -Werror -pedantic`. Initialise
  `frame_msg_info_t` with `frame_msg_info_empty()`, never positionally.

**Tooling**

- **Escapes in files:** Bash heredocs mangle backslashes. Write code that contains escapes with the
  file-editing tools, not heredocs.
- **Module eviction:** tests evict `struct_frame*` from `sys.modules` (`test_equality`). Schema
  modules must import each other eagerly.
- **Windows Node output:** decode Node stdout as UTF-8 in tests.
- **C# csproj:** if about 26 C# tests fail at once, check that the C# test csproj still has its
  `ProjectReference`. Concurrent agents have stripped it before.
- **Sanitizers and fuzzing:** clang 18, ASan/UBSan, libFuzzer and tshark 4.2.2 live in WSL
  (user-local). Call `wsl` from PowerShell.

---

## 4. Verification

Run all of these before calling a phase done:

1. `python test_all.py --require-langs c,cpp,py,ts,js,csharp,rust`
2. `pytest tests/`
3. `python tests/check_golden.py`
4. `python tests/check_determinism.py`
5. `python tests/gen_test_coverage.py --check`. It renders `tests/coverage_spec.py` into
   `docs/.../reference/test-coverage.md`; add a section for every new feature.
6. `python src/struct_frame/language_facts.py --check`
7. `python -m struct_frame.builtin --check`
8. The npm and Python API checks: additions only, unless the phase is a declared break.
9. ASan/UBSan smoke and libFuzzer runs for C and C++ in WSL, when C/C++ readers change.
10. `wireshark/test_dissector.py` with tshark in WSL, when the wire format changes.
11. `npm test` in `editors/vscode`, when language facts or the extension change.

---

## 5. Phase C2: move system messages to message id 0

### 5.1 Wire format

```
<profile header> <profile payload header with MSG_ID = 0x00> [SYS_MSG_ID] fixed fields [tail] <profile CRC, if any>
```

**The payload**

- **Contents:** `SYS_MSG_ID` + the system message's fixed fields + an optional raw tail.
- **Length field:** where the profile has one, it counts the whole payload (1 + fixed + tail),
  exactly like any other message.

**Header fields**

- **Package byte:** on profiles that have one (Extended, ExtendedMsgIds,
  ExtendedMultiSystemStream), a system message has **PKG_ID = 0 and MSG_ID = 0**. A frame with
  MSG_ID 0 and a non-zero package byte is an unknown message (see 5.3).
- **Sequence:** the system message uses the profile's own SEQ field. The sender uses the same tx
  sequence counter as its application frames. **There is no separate system sequence space any
  more.**
- **Sender identity:** taken from the profile's SYS/COMP fields. On profiles without them the
  sender is `(0, 0)`, meaning the node at the other end of this link. Point-to-point links work;
  shared buses need a profile with SYS/COMP, which is also true for application frames.

**CRC**

- **Algorithm:** the profile's normal Fletcher-16, unchanged.
- **Magic:** the magic bytes mixed in are those of the *system message*, found by
  `SYS_MSG_ID` = payload[0]. This keeps cross-schema protection.

**Tails**

- **Tail messages:** Ping, Pong, LinkTestData, RpcRequest, RpcResponse.
  `struct_frame.builtin.TAIL_MESSAGES` is the single source.
- **Length-less profiles:** a tail needs a length field. On length-less profiles (Minimal, and
  header None with Minimal) only messages with an empty tail can be sent. Their size is
  `1 + fixed_size`, looked up from `SYS_MSG_ID`. Every other system message works, including Ping
  and Pong without padding.
- **Tail limit:** `min(MAX_TAIL = 1024, profile_max_payload - 1 - fixed_size)`. A 1-byte length
  gives `profile_max_payload = 255`.
- **Encoders:** they refuse, never truncate:
  - a tail on a length-less profile;
  - a tail over the limit;
  - an unknown `SYS_MSG_ID`.

### 5.2 Reserved application id

The **low byte of every effective message id must be non-zero**.

- **Effective id:** `pkg_id × 256 + msg_id` with a package id, else the declared id.
- **Why the low byte:** on profiles with a package byte, the encoder writes `pkg = id >> 8` and
  `msg = id & 0xFF` (`boilerplate/py/frame_profiles.py:363`). An id such as 256 in a package
  without `@pkgid` would therefore put MSG_ID 0 on the wire. Without a package byte the encoder
  already refuses ids > 255, so the low-byte rule covers both cases.

Generator changes:

- **Validation:** `generate.py` package validation, around line 1904, rejects `@0`, and any id
  whose low byte is 0, with a new diagnostic code. Suggested text:
  `message id 0 is reserved for struct-frame system messages` /
  `the low byte of a message id must be non-zero (id 512 = package byte 2, message byte 0)`.
  Add it to the diagnostics table and docs. Lowering in `schema/lower.py` is an equally good place
  if it already has the id; keep one check.
- **Ranges:** change `language_facts.MSGID_RANGE` to `(1, 65535)` and `MSGID_RANGE_WITH_PKGID` to
  `(1, 255)`. Then regenerate the extension facts JSON
  (`editors/vscode/server/src/facts/language-facts.json`) with `language_facts.py`.
- **Example schema:** `examples/generic_robot.sf:32` declares `message Reserved @0 {}`. Remove it
  and regenerate the IR goldens.
- **Migration:** `struct-frame migrate` warns about and comments out `@0` messages in legacy
  input.
- **Tests:** add the new negative cases to `tests/test_generator_validation.py`.

### 5.3 Reader behaviour (all 7 runtimes)

The reader parses a frame exactly as it does today, then:

| Case | Behaviour |
|---|---|
| MSG_ID 0 and PKG 0 (or no PKG byte), length profile | After normal length/CRC handling, validate: `len ≥ 1`, payload[0] is a known `SYS_MSG_ID`, and `len − 1` is in `[fixed, fixed + tail_cap]`, where `tail_cap` is 0 for non-tail messages. Valid: a system message. Invalid: count `cnt_system_rejected` and drop the frame. Framing stays aligned; no resync needed. |
| Same, length-less profile | After MSG_ID 0, read one more byte (`SYS_MSG_ID`). Known non-tail message: size is `1 + fixed`. Unknown, or a tail message: count `cnt_system_rejected` and resync as for any unknown id. |
| MSG_ID 0 with PKG ≠ 0 | Unknown message: today's unknown-id path and counters. |
| CRC failure on an id-0 frame | Ordinary `crc_failures`. The magic used comes from the claimed `SYS_MSG_ID`; an unknown one counts as rejected. |
| `SF_DISABLE_SYSTEM_FRAMES` (C/C++) | Id 0 takes the unknown-id path. A length profile stays in sync, which is what an older runtime does. |

Delivery and the reader API:

- **Hidden by default:** valid system messages are counted in `cnt_system_frames` and not
  returned.
- **Opt-in:** with `deliver_system_frames` on (existing setters, names unchanged), the frame comes
  back with:
  - `is_system = true`;
  - `msg_id = SYS_MSG_ID`;
  - the payload view starting *after* the `SYS_MSG_ID` byte, i.e. fixed fields + tail.

  The existing `decode(frame) -> (message, tail)` helpers keep working.
- **`FrameMsgInfo`:** sequence, system_id, component_id and package_id come from the profile
  header, as for application frames.

### 5.4 What to remove and what to keep

Remove from all 7 runtimes:

- `PayloadType SYSTEM = 9`, `PAYLOAD_SYSTEM_CONFIG` and every "system profile" derivation:
  - Python: `system_config`, `_system_profile`;
  - TS: `systemProfileConfig`, `systemProfileOf`;
  - C: `profile_system_config`, `profile_system_header_size`;
  - C++: `ProfileConfig::supports_system_frames`, `using SystemConfig`;
  - C#: `ConfigFor`;
  - Rust: `config_for`.
- The start byte `0x79` and the dual start-byte resync scans:
  - Python: `_find_start`, `_is_system_start`;
  - TS: `findStart`, `isSystemStart`;
  - C: `_sf_find_start`, `_sf_is_system_start`;
  - C++: `system_frames::find_start`, `is_system_start`;
  - C#: `FindStart`, `IsSystemStart`;
  - Rust: `next_start`, `is_system_start`, `next_start_after_head`.
- The separate system header check before payload collection: `_system_header_ok`,
  `systemHeaderOk`, `_sf_system_header_check`, `header_check`, `HeaderCheck`, `header_ok`.
- Separate system sequence tracking.
- The "Basic/Tiny only" restriction: `supports_system_frames` either goes or returns true for
  every profile.

Keep:

- The `sf_system` schema, ids and generated code.
- `sf_system_info.h` / `sf_system_info.hpp` (fixed sizes, magic, tail flags).
- `cnt_system_frames` / `cnt_system_rejected`, the `is_system` flag and the delivery setters.
- `SF_DISABLE_SYSTEM_FRAMES`.
- `WIRE_HASH`.
- The encode/decode helper names. The encoder signature stays
  `encode(config, message, tail, seq, sys_id, comp_id)`, but now works for any profile.

**Files**

| Language | Files |
|---|---|
| Python | `boilerplate/py/system_frames.py`, `boilerplate/py/frame_profiles.py` (lines ~937–994 and the reader states), `payload_types.py`, `frame_base.py` |
| TS → JS | `boilerplate/ts/system-frames.ts`, `frame-profiles.ts`, `payload-types.ts`, `frame-base.ts`, `index.ts`; recompile JS |
| C | `boilerplate/c/frame_profiles.h` (system helpers ~l.541 `profile_encode_system_frame`, `_sf_parse_system`, accumulating reader `collecting_system`), `payload_types.h`, `frame_base.h` |
| C++ | `boilerplate/cpp/frame_profiles.hpp` (`structframe::system_frames`, `handle_collecting_header<C>`), `payload_types.hpp`, `frame_base.hpp` |
| C# | `Framework/Framing/SystemFrames.cs`, `AccumulatingReader.cs`, `BufferReader.cs`, `Profiles/PayloadTypes.cs` |
| Rust | `boilerplate/rust/system_frames.rs`, `frame_profiles.rs`, `payload_types.rs` |
| Generator | `src/struct_frame/builtin/__init__.py` (`SYSTEM_PAYLOAD_TYPE` and `SYSTEM_START_BYTE` go; info tables stay); the `sf_system.sf` header comment (lines 3–13) |
| Wireshark | `wireshark/struct_frame.lua`: drop payload type 9 and the `0x70`–`0x79` range change; decode id 0 as a system message under every payload type |

Removing these is not an API break: none of it has been released. 0.11.1 predates `6c5730d`.

### 5.5 Tests and artifacts to redo

**Spec and runtimes**

- `tests/test_system_frames.py`:
  - rewrite the layout spec and vectors;
  - recompute the hand-computed vector for Basic + Default;
  - add one vector each for Tiny + Default, header None + Minimal (IPC, Heartbeat), Extended
    (PKG 0) and MultiSystemStream (sys/comp from the header).
- `tests/test_system_frames_runtimes.py`: known-answer encode plus stream decode in every runtime,
  for every vector above.

**Stream differential and fuzzing**

- **Corpus:** `tests/fuzz/corpus.py` (`system_stream`, `_system_message`, `_stray_system_header`,
  `SYSTEM_PROFILES`):
  - replace the stray-`0x79` cases with: id 0 with an unknown `SYS_MSG_ID`, id 0 with a bad
    length, id 0 truncated, id 0 with a tail on Minimal, and PKG ≠ 0 with MSG 0;
  - extend `SYSTEM_PROFILES` to all payload types.
- **Drivers:** keep the 4th `system` argument and the `msg_id + 65536` output convention.
  Re-check the diagnostics row.
- **Differential test:** `tests/test_stream_cross_lang.py` (`system_streams`,
  `test_system_frames_in_streams`, `test_system_frame_goldens_decode_everywhere`).
- **Fuzzing:** the seeds in `tests/fuzz/make_seed_corpus.py`, and the stream-mode passes in
  `tests/c/fuzz_parser.c`, `tests/cpp/fuzz_parser.cpp`, `tests/py/fuzz_parser.py` and
  `tests/rust/fuzz/fuzz_targets/parser.rs`.

**Goldens and docs**

- **Goldens:** regenerate `tests/golden/system_basic.bin`, `system_tiny.bin` and
  `mixed_network_system.bin` through `check_golden.system_goldens()`. Add
  `system_ipc.bin` (header None). Update `tests/golden/README.md`.
- **Scenario tables:** `tests/NEGATIVE_TESTS.md` (system section) and `tests/coverage_spec.py`
  section 3.4.
- **Docs:**
  - `docs/.../reference/conformance.md` § 9.1–9.4: layout, reader table, vectors and the reserved
    id rule. The wire-hash part is unchanged. `test_system_frames.py` checks the page vectors.
  - `docs/.../extended-features/system-frames.md`.
  - `basic-usage/message-definitions.md`: the reserved id rule.
- **Wireshark:** `wireshark/test_dissector.py` system-frame tests.

**New tests**

- The reserved-id validation errors.
- A runtime built with `SF_DISABLE_SYSTEM_FRAMES` stays in sync across id-0 frames on a length
  profile. This stands in for older runtimes.
- Encode refusals: a tail on Minimal, a tail over the limit, an unknown id.
- An application frame and a system frame interleaved share one sequence space: a gap is detected
  across both.

**Done when** section 4 passes and the stream differential agrees in all 6 drivers, with system
messages hidden and delivered.

---

## 6. Phase E: node runtime and heartbeat

### 6.1 `SystemNode`: sans-IO core, one per link endpoint

The node owns an `AccumulatingReader` with delivery on, the tx sequence counter, the node's
`(sys_id, comp_id)` and a write callback. Application frames pass through. System messages go to
the registered services.

**Python reference, `boilerplate/py/system_node.py`:**

```python
class SystemNode:
    def __init__(self, config, get_message_info, write, *, sys_id=0, comp_id=0, wire_hash=0): ...
    def feed(self, data: bytes, now_ms: int) -> list[FrameMsgInfo]: ...   # app frames only
    def poll(self, now_ms: int) -> None: ...                              # timers: heartbeat, timeouts, downlink
    def send(self, msg, *, seq=None) -> bool: ...                         # application message, shares tx seq
    def send_system(self, msg, tail=b"") -> bool: ...                     # id-0 frame via active profile
    def addressed_to_me(self, target_sys, target_comp) -> bool: ...       # 0 = wildcard
    capabilities: int                                                     # Capability bits, set by enabled services
    events: NodeEvents                                                    # callbacks (6.3)
    diagnostics                                                           # reader diagnostics + tx_frames/tx_bytes
```

**Write callback and time**

- **`write(bytes) -> bool`:** returns False for "would block". Each service decides whether to
  retry:
  - a heartbeat is skipped;
  - downlink test data is retried on the next `poll`;
  - an RPC response is queued.
- **Time:** an `int` in milliseconds; a µs clock only for latency (7). Nodes do all time math as
  wrap-safe u32 (see 6.4) so C can pass `uint32_t` tick counts. The node never reads a clock
  itself.

**Ports**

| Language | File | Shape |
|---|---|---|
| Python | `boilerplate/py/system_node.py` | class; add to `PY_RUNTIME_MODULES` in `generate.py` |
| TS → JS | `boilerplate/ts/system-node.ts` | class; export from `index.ts`; recompile JS |
| C | `boilerplate/c/sf_node.h` | header-only, no heap: caller provides peer storage, tx buffer size `SF_NODE_TX_BUF` (default: largest fixed message + profile tail limit + framing) |
| C++ | `boilerplate/cpp/sf_node.hpp` | template on profile config and peer capacity, no heap, no virtuals |
| C# | `boilerplate/csharp/Framework/Node/SystemNode.cs` | class |
| Rust | `boilerplate/rust/system_node.rs` | struct, generic over a `Write`-like callback; add to `lib.rs` and `rust_gen.generate_lib_rs` |

C API sketch:

```c
typedef struct {
  bool (*write)(void* ctx, const uint8_t* data, size_t len);
  void (*on_peer_up)(void* ctx, const sf_peer_t*);
  void (*on_peer_down)(void* ctx, const sf_peer_t*);
  void (*on_restart)(void* ctx, const sf_peer_t*);
  void (*on_state_change)(void* ctx, const sf_peer_t*, uint8_t old_state);
  void (*on_schema_mismatch)(void* ctx, const sf_peer_t*, uint32_t their_hash);
  void (*on_link_stats)(void* ctx, const sf_peer_t*, const sf_system_link_stats_t*);
  void* ctx;
} sf_node_callbacks_t;

void sf_node_init(sf_node_t*, const profile_config_t*, get_message_info_fn, sf_node_callbacks_t,
                  uint8_t sys_id, uint8_t comp_id, sf_peer_t* peers, uint8_t max_peers);
frame_msg_info_t sf_node_push_byte(sf_node_t*, uint8_t byte, uint32_t now_ms); /* app frames */
void sf_node_poll(sf_node_t*, uint32_t now_ms);
bool sf_node_send_system(sf_node_t*, uint8_t sys_msg_id, const void* fixed, size_t fixed_len,
                         const uint8_t* tail, size_t tail_len);
```

Services register handlers on the node by `SYS_MSG_ID`. In C/C++ this is a small fixed dispatch,
a switch over enabled services, not a dynamic table.

### 6.2 Heartbeat sender

Configuration:

| Field | Default |
|---|---|
| `enabled` | False (see 12) |
| `interval_ms` | 1000 (u16) |
| `node_type` | 0 |
| `state` | `NodeState.BOOT`; the app changes it |
| `stats_every` | 0 (LinkStats off) |

Message fields:

- **`counter`:** starts at 0 and increments after each heartbeat (u32 wrap).
- **`uptime_ms`:** `now − start`, where `start` is the first `poll` (u32 wrap).
- **`wire_hash`:** the node's `wire_hash` (0 = unknown).
- **`protocol_version`:** `PROTOCOL_VERSION`.
- **`flags`:** `capabilities`.

Cadence:

- The first heartbeat goes on the first `poll`; `next = t0 + interval`.
- A poll with `now ≥ next` sends one heartbeat. Then:
  - if it was late by `≥ interval`: `next = now + interval` (no burst catch-up);
  - otherwise: `next += interval` (no drift).
- If `stats_every = N > 0`, a `LinkStats` goes right after every heartbeat whose `counter % N == 0`.

LinkStats fields:

- `rx_*`, `crc_failures`, `sync_recoveries`, `seq_gaps` and `len_errors` come from the reader
  diagnostics.
- `tx_*` come from the node's counters.

### 6.3 Peer table and events

A peer is keyed by `(sys, comp)` from the frame header; `(0, 0)` is used when the profile has no
ids.

- **Peer record:** `up`, `last_ms`, `counter`, `uptime_ms`, `interval_ms` (the peer's advertised
  interval), `state`, `wire_hash`, `node_type`, `flags`, `lost`, `last_link_stats`.
- **Capacity:** C/C++ use caller-provided storage; the others default to 16. A new peer when the
  table is full is ignored and counted in `peers_dropped`. Peers never expire from the table, only
  go down.

On each received Heartbeat, check in this order:

1. **New peer:** insert it; `peer_up`.
2. **Restart:** `u32_diff(hb.counter, peer.counter) < 0` **or**
   `u32_diff(hb.uptime_ms, peer.uptime_ms) < 0`. Raise `restart`. A restart does not count as lost
   heartbeats.
3. **Otherwise, if the peer is up:** `lost += max(0, u32_diff(hb.counter, peer.counter) − 1)`.
4. **State change:** if the state differs from the previous one, raise
   `state_change(old, new)`.
5. **Schema mismatch:** if both hashes are non-zero and differ, raise `schema_mismatch` once per
   change of the peer's hash. It is informational only and never blocks traffic.
6. **Update and come up:** update the record and `last_ms = now`. If the peer was down: `peer_up`.

On `poll`, for every up peer: if `u32_diff(now, last_ms) > k × peer.interval_ms`, with
`k = timeout_factor` (default 3), the peer goes down and `peer_down` fires.

- **Boundary:** it is `>`, not `≥`. The exact boundary `k × interval` is still up; one ms later is
  down. Test both.

LinkStats received from a peer is stored on the peer and raises `link_stats`.

Event payloads must be identical in every language, because the node driver prints them (6.5).

### 6.4 Wrap-safe math

```python
def u32_diff(a, b):           # signed a − b
    d = (a - b) & 0xFFFFFFFF
    return d - (1 << 32) if d & 0x80000000 else d
```

All time and counter comparisons use it, in every language. C/C++/Rust/C# cast to `int32_t` after
unsigned subtraction.

### 6.5 Cross-language node drivers

The model is the stream drivers in `tests/fuzz/drivers/`. Each language gets a node driver that
replays a script on stdin and prints a transcript on stdout. The test diffs every transcript
against Python's.

**Script lines**

| Line | Meaning |
|---|---|
| `profile <name>` | Profile to use, e.g. `profile standard` |
| `node sys=1 comp=1 wire_hash=0x12345678` | Node identity |
| `heartbeat interval=1000 k=3 stats_every=0 node_type=0 max_peers=4` | Heartbeat configuration |
| `state 1` | Set the node's state |
| `feed <now_ms> <hex bytes>` | Feed bytes at a time |
| `poll <now_ms>` | Run timers at a time |
| `writefail <n>` | The next n writes return False |

**Transcript lines**

| Line | Meaning |
|---|---|
| `tx <hex frame>` | A frame the node wrote |
| `app <msg_id> <hex payload>` | An application frame returned by `feed` |
| `event <name> <sys> <comp> <args...>` | An event |
| `diag <counters...>` | Diagnostics, at the end |

**Files**

- Drivers go in `tests/node/drivers/` (`node_driver.c`, `.cpp`, `.py`, `.js`, `csharp/`,
  `rust/`). The scripts go in `tests/node/scripts/*.txt`.
- New test: `tests/test_node_cross_lang.py`. Python's transcript is the reference.
- The same drivers grow commands in F1, D and F2 (`ping`, `rpc_call`, `linktest_start`, …).

Scripts must cover:

- heartbeat cadence and the no-burst rule;
- the exact `k × interval` boundary;
- a restart by counter and a restart by uptime;
- counter wrap (`counter` near `0xFFFFFFFF`) and time wrap (`now` near `2^32`) without false
  restarts or timeouts;
- state change and schema mismatch;
- LinkStats every N;
- a full peer table;
- write failure;
- peers on a profile without sys/comp (`(0, 0)`);
- interleaved application frames with a shared sequence;
- a corrupted frame between heartbeats.

### 6.6 Python unit tests

`tests/test_system_node.py` covers everything in 6.2–6.4 on a simulated clock. It checks event
order and counter values. Add Hypothesis properties:

- no `peer_down` while heartbeats arrive within `k × interval`, under arbitrary jitter below the
  interval;
- `restart` iff the counter or uptime went backwards.

### 6.7 Relay harness (end of E)

- **`tests/harness/relay.py`:** a frame-aware relay between two processes. Its seeded fault
  schedule can drop, duplicate, reorder and delay frames, and corrupt bytes.
- **`tests/harness/<lang>/sf_node_harness`:** per-language programs that run a `SystemNode`
  over binary stdin/stdout.
  - Windows needs binary stdio: `_setmode` in C/C++, `Console.OpenStandardInput` in C#, raw
    buffers in Node.
  - The harnesses host the heartbeat now, and the RPC test service (D) and link responder (F1/F2)
    later.
- **Tests:**
  - total drop → `peer_down`;
  - harness restart → `restart`;
  - recovery → `peer_up`.
- **Registration:** in `tests/run_tests.py` (`base_runners`/`sdk_runners`, `SDK_APPLICABILITY`),
  C# `TestRunner.cs` and `tests/rust/src/main.rs`.

### 6.8 SDK integration (carried over from Phase 0b)

- **C++ SDK:** rebase `cpp/struct_frame_sdk/struct_frame_sdk.hpp` (`ParseBuffer` ~l.580) from
  `BufferParserWithCrc` onto `AccumulatingReader`.
- **SDK `send`:** in TS and C++, accept seq / sys / comp. The node supplies seq.
- **Diagnostics:** expose reader diagnostics from every SDK. Add `cnt_valid_frames` to the
  diagnostics in all 7 runtimes, plus the stream-driver diagnostics row.
- **System messages:** each SDK optionally owns a `SystemNode`, routes system messages to it before
  any user msg_id lookup, and drives `poll` from its timer:

  | SDK | Timer |
  |---|---|
  | Python | thread or asyncio task |
  | TS | `setInterval` |
  | C# | `Timer` |
  | C++ | user-driven `poll` |

### 6.9 Docs

- A new page, `docs/.../extended-features/heartbeat.md`, linked from the sidebar in
  `docs/astro.config.mjs`. Code fences in languages other than Python are marked `no-compile`
  where they are fragments.
- A section in conformance § 9: the heartbeat cadence, peer rules and event definitions, so
  third-party implementations match.
- A new section in `coverage_spec.py`.

---

## 7. Phase F1: ping/pong latency

### 7.1 Responder (all 7)

- **When it answers:** on `Ping` where `addressed_to_me(target_sys, target_comp)`.
- **What it sends:**
  `send_system(Pong(t_send_us = ping.t_send_us, seq = ping.seq, max_tail = <this profile's tail limit>), tail = ping_tail)`.
- **No clock needed:** it reads no clock.
- **Too-long tails:** if the echoed tail doesn't fit (asymmetric limits), reply with an empty tail.
  `max_tail` tells the initiator the limit.

### 7.2 Initiator (host languages)

A `LatencyProbe(node, target=(0, 0), padding=0, timeout_us=1_000_000)`, sans-IO:

- **`send(now_us)`:** sends a `Ping` with `seq` incrementing from 0 (u32), and records
  `outstanding[seq] = now_us`.
- **On `Pong`:** if `seq` is outstanding, `rtt = now_us − t_send_us` (u64 µs; no wrap handling
  needed) is recorded in send order. An unknown or expired `seq` counts in `late`.
- **`expire(now_us)`:** outstanding pings older than `timeout_us` count as `lost`.

`report()` returns:

| Field | Formula |
|---|---|
| `sent`, `received`, `lost`, `late` | counts |
| `min_us`, `max_us` | min and max RTT |
| `mean_us` | arithmetic mean (float) |
| `p50_us`, `p95_us`, `p99_us` | nearest rank: sort RTTs ascending; index `ceil(p/100 × n) − 1` |
| `jitter_us` | mean of `|rtt[i] − rtt[i−1]|` over consecutive received pings in seq order (0 if fewer than 2) |

The formulas must be the same in every language. Python is the reference and the node-driver
script compares the report output exactly. Print floats with fixed precision.

SDK wrapper:

- **Python:** `LinkSession.latency(count, interval_ms, padding)`, sync and async.
- **Others:** a method on the SDK object.

**Tests**

- Node-driver scripts: ping/pong round trip, a padded echo, a tail too long for the responder, a
  wrong target ignored, loss, a late pong.
- A unit test of the statistics against hand-computed values.
- Every initiator against the C and Python harnesses through the relay.

**Docs:** a page `extended-features/link-tests.md`, shared with F2.

---

## 8. Phase D: request/response (RPC)

### 8.1 Schema and IR

`service` already parses (`schema/parser.py`) and lowers to the point of error `SF0390`
(`schema/lower.py:657`). Replace the error with new IR `Service(name, rpcs, line, col)` and
`Rpc(name, request, response | None, idempotent, line, col)`.

Validation, in `validate_packages`:

- the request and response types are messages with ids;
- each request message type is the request of **exactly one** rpc in the whole build (see 12);
- request effective ids are unique across packages;
- service and rpc names don't collide with each other, or with reserved names in any target
  (`naming.py`);
- no arrow means an acknowledgement-only rpc.

`schema_diff`:

- add `services` to the snapshot and bump `SNAPSHOT_VERSION`;
- adding an rpc is compatible; removing one, or changing its types, is breaking.

`language_facts`: add the keywords and hover text, then regenerate the extension facts.

### 8.2 Wire

A call is a system message `RpcRequest` (`0x30`), and the answer is `RpcResponse` (`0x31`). Both
are tail messages.

**Request fields**

- `call_id`: u16, chosen by the client.
- `payload_id`: the request message's effective id (u16).
- `payload_magic1/2`: the request message's magic bytes.
- `target_sys/comp`: 0 means any.
- Tail: the request message's encoded payload, with the same bytes as its normal frame payload.

**Response fields**

- `call_id`: repeated from the request.
- `payload_id`: the response message's effective id (0 for acknowledgement-only or a failure).
- `payload_magic1/2`: the response message's magic bytes (0 for acknowledgement-only or a failure).
- `status`: an `RpcStatus`.
- Tail: the response payload (empty for acknowledgement-only or a failure).

**Status, in the order the server checks**

| Check | Status |
|---|---|
| Not addressed to me | No response; ignore |
| Unknown `payload_id` | `UNKNOWN_METHOD` |
| Magic differs | `SCHEMA_MISMATCH` |
| Tail fails to decode, using the existing truncation/extension rules | `DECODE_ERROR` |
| Handler raised or returned an error | `HANDLER_ERROR` |
| Dedup or deferred storage full | `BUSY` |
| Otherwise | `OK` |

The tail limit (5.1) caps request and response sizes. Codegen emits a compile-time or
generate-time warning when a message used in an rpc exceeds the limit on 1-byte-length profiles.

### 8.3 Server (all 7)

- **Dedup cache:** keyed by `(sender sys, sender comp, call_id)`, where the sender is
  `(0, 0)` on profiles without ids. It holds the encoded response. Capacity defaults to 32, LRU;
  C/C++ use caller storage.
- **Repeats:**
  - a repeat of a completed call replays the cached response and does not run the handler;
  - a repeat while the call is still pending (deferred) is ignored.
- **Eviction:** once an entry is evicted, a repeat runs again. That is acceptable only for
  `[idempotent]` rpcs. For the others, the doc states that the at-most-once guarantee lasts for
  the dedup window.
- **Deferred responses:** a handler may return `Deferred`. The app later calls
  `respond(call, status, response)`. Pending calls are bounded by capacity; when full, the status
  is `BUSY`. This matters on MCUs, e.g. for flash writes.
- **Capabilities:** the server sets `Capability.RPC_SERVER`.

### 8.4 Client (host languages)

- **`RpcClient(node)`:** `call(request, response_type | None, target=(0, 0), timeout, retries)`.
- **Call ids:**
  - `call_id` starts at 0 (deterministic for tests) and increments u16, skipping ids still in
    flight;
  - retries resend the same `call_id`.
- **Matching:** a response matches by `call_id`, and also by sender when the target was non-zero.
  The client checks the response `payload_id` and magic against the expected type; a mismatch
  raises the `SchemaMismatch` error on the client side.
- **Concurrency:** concurrent calls are allowed, and out-of-order responses are fine.
- **Errors:** typed per status — `UnknownMethod`, `SchemaMismatch`, `DecodeError`, `HandlerError`,
  `Busy`, `Timeout`.

### 8.5 Codegen per language

Example: `service Device { rpc get_config(GetConfig) -> DeviceConfig; rpc reboot(Reboot) [idempotent]; }`.

| Language | Server | Client |
|---|---|---|
| C | `<pkg>_<svc>_handlers_t` struct of function pointers returning `sf_rpc_result_t` (OK / DEFERRED / error) + generated `<pkg>_<svc>_serve(sf_node_t*, const handlers*, dedup storage, capacity)` and `sf_rpc_respond(...)` | — |
| C++ | handler struct / CRTP, no virtuals, `serve<Svc>(node, impl)` | callback + poll client |
| Python | `class DeviceServer(Protocol)` + `serve_device(node, impl, dedup=32)` | `DeviceClient` (sync) + `AsyncDeviceClient` |
| TS/JS | `interface DeviceServer` + `serveDevice(node, impl)` | promise client `DeviceClient` |
| C# | `interface IDeviceServer` + `ServeDevice` | async client; extend `csharp_sdk_interface_gen.SdkInterfaceGen` |
| Rust | `trait DeviceServer` + `serve_device` | poll-based client |

- Generated code goes in the package's normal output files. The shared machinery
  (`RpcServer`, `RpcClient`, dedup) lives in the runtime next to `system_node`.
- The existing predicate-based `request()` in the SDKs stays.
- Reserve the new generated names in `naming.py`.

### 8.6 Tests

- **Validation:** negatives for every rule in 8.1.
- **Codegen:** compile tests of a two-service schema in all 7 languages.
- **Unit tests:**
  - every status code;
  - timeout and retry with dedup, where the handler runs exactly once;
  - eviction and re-execution;
  - out-of-order concurrent calls;
  - `call_id` wrap;
  - deferred responses and `BUSY`;
  - addressing;
  - acknowledgement-only rpcs.
- **Cross-language:** node-driver scripts for the server side, and a matrix of 5 clients × 7
  servers through the relay with a seeded drop/duplicate/reorder schedule.
- **Hypothesis:** fault schedules on a simulated link. Invariants:
  - at most one execution per call within the dedup window;
  - every response matches its request.

**Docs:** a page `extended-features/rpc.md`, the service grammar in `message-definitions.md`, and
conformance § 9.

---

## 9. Phase F2: throughput, integrity and the CLI

### 9.1 PRBS (all 7, known-answer vectors)

```python
U32 = 0xFFFFFFFF
def splitmix32(x):
    x = (x + 0x9E3779B9) & U32
    x ^= x >> 16; x = (x * 0x85EBCA6B) & U32
    x ^= x >> 13; x = (x * 0xC2B2AE35) & U32
    x ^= x >> 16
    return x

def prbs(seed, test_id, seq, n):
    x = splitmix32(splitmix32(seed ^ test_id) ^ seq) or 0x9E3779B9   # never zero
    out = bytearray(n)
    for i in range(n):
        x ^= (x << 13) & U32; x ^= x >> 17; x ^= (x << 5) & U32
        out[i] = x & 0xFF
    return bytes(out)
```

Pin vectors in `tests/test_prbs.py` and check them in every runtime.

### 9.2 Session protocol

1. The initiator sends `LinkTestStart`.
2. The responder answers `LinkTestAck`:
   - `TOO_LARGE` if `payload_size` exceeds its tail limit;
   - `BUSY` if a session is already running;
   - `UNSUPPORTED` for a mode it lacks;
   - otherwise `OK`, with its `max_tail`.
3. Data frames are `LinkTestData{seq from 0, test_id}`, with a tail of
   `prbs(seed, test_id, seq, payload_size)`:

   | Mode | Sender | Counter |
   |---|---|---|
   | `UPLINK` | initiator | responder |
   | `DOWNLINK` | responder, from `poll`, paced at `rate_hz` (0 = as fast as `write` accepts) | initiator |
   | `ECHO` | initiator; the responder sends each one back unchanged | initiator |

   The sender stops after `frame_count` frames or `duration_ms`, whichever comes first; 0 means
   unlimited. A frame that `write` refuses is retried on the next poll, never skipped.
4. `LinkTestStop{test_id}` comes from the initiator; the counting side answers `LinkTestReport`.
   The responder also ends a session on its own after `duration_ms + 2 s` without data.

The responder sets `Capability.LINK_TEST`.

### 9.3 Counting algorithm (identical everywhere)

State:

- `highest` (−1 at start);
- a bitmap window of the last **W = 256** sequence numbers below and including `highest`;
- `missing`;
- the counters in `LinkTestReport`;
- the reader-diagnostics snapshot taken at Start.

For each data frame with a matching `test_id`:

1. **Corrupted:** if the tail ≠ `prbs(...)`, `frames_corrupted += 1` and stop. A corrupted frame
   isn't counted as received, and its seq isn't marked.
2. **New highest:** if `seq > highest`, `missing += seq − highest − 1`, then mark the seq and
   `highest = seq`.
3. **Inside the window, not yet seen:** `frames_reordered += 1`, `missing −= 1`, mark it.
4. **Inside the window, already seen:** `frames_duplicate += 1`. Stop.
5. **Older than the window:** `frames_duplicate += 1`. This is a documented limitation. Stop.
6. **Received:** after steps 2 and 3,
   - `frames_received += 1`;
   - `bytes_received +=` the frame's wire length;
   - update the first and last receive times, then `first_to_last_us`.

At Stop:

- `frames_lost = missing`, plus `frame_count − (highest + 1)` when `frame_count` was set.
- `crc_failures` and `sync_recoveries` are the diagnostics deltas since Start.

Throughput, computed by the initiator from the report:

- `bytes_received × 1e6 / first_to_last_us` B/s;
- frames/s the same way;
- goodput: `frames_received × payload_size`.

### 9.4 Initiators and the CLI

- **Initiators (host languages):** `LinkTestRunner` with `throughput(mode, …)` and
  `integrity(…)`. Integrity is throughput with a pass/fail on corrupted, lost and duplicate
  frames.
- **CLI:** `src/struct_frame/link_cli.py`, wired into `build_parser()`.
  - Commands: `struct-frame link-test {latency, throughput, integrity, serve, monitor}`.
    `monitor` prints heartbeat peers and events.
  - It imports the Python runtime as the package `struct_frame.boilerplate.py`, through a new
    `struct_frame/runtime.py` alias. It never adds that directory to `sys.path`.
  - Transport URLs:

    | URL | Transport |
    |---|---|
    | `serial://COM3?baud=115200` | serial port |
    | `tcp://host:port` | TCP client |
    | `tcp-listen://0.0.0.0:9000` | TCP server |
    | `udp://host:port` | UDP |
    | `ws://host:port/path` | WebSocket |
    | `stdio:` | stdin/stdout |

  - New Python server-side transports: TCP listener, UDP bind, stdio, WebSocket server.
  - `--profile`, `--sys`, `--comp`, `--json`. Thresholds such as `--max-loss`, `--max-p99-us`,
    `--min-throughput` set the exit code: 0 pass, 1 threshold failed, 2 error or timeout.
  - The JSON output has a documented schema, checked by a test.

**Tests**

- PRBS vectors.
- Scripted fault patterns giving exact lost/duplicate/reordered/corrupted counts, including
  window-edge cases.
- Every initiator against the C and Python harnesses.
- CLI: `serve stdio:` ↔ `latency stdio:`, and TCP/UDP/WebSocket loopback.
- A Linux PTY for serial (WSL/CI).
- The JSON schema and the threshold exit codes.
- A wheel smoke test: `struct-frame link-test --help` from a built wheel.

**Docs:** `extended-features/link-tests.md`, and `reference/cli-reference.md`.

---

## 10. Phase A6: VS Code extension parser

The extension in `editors/vscode/` still uses its old regex parser, so it doesn't understand the
new syntax.

- **Parser:** port `src/struct_frame/schema/` (lexer, parser, diagnostics) to TS in
  `editors/vscode/server/src/sfparse/`, producing the same AST and diagnostics. Python stays the
  reference.
- **Shared corpus:** `tests/schema_corpus/{valid,invalid}/`, with `.ast.json` and `.diag.json`
  files generated by Python. Both parsers must match it in CI. `tests/schema_corpus/legacy/`
  already exists for migrate.
- **Server:** move `server.ts` (completion, hover, definition, references, rename, validation)
  onto the AST, then retire `parser.ts`.
- **Highlighting:** rewrite `syntaxes/sf.tmLanguage.json`, with token snapshot tests. Register the
  `sf` grammar with Shiki in `docs/astro.config.mjs`.
- **Editing features:**
  - a "Migrate legacy file" code action;
  - a warning on renaming a struct, because its name feeds the magic bytes of every message that
    embeds it.
- **Tests:** `npm test` (`lsp.test.ts`). The `publish-vscode.yml` lockstep publishing is
  unchanged.

---

## 11. Smaller open items

- **Combined `WIRE_HASH`:** a value over all packages, in the C/C++ umbrella header, the TS/JS
  barrel, Python `__init__` and the C#/Rust equivalents. Also a runtime helper that combines
  per-package values in a documented order (sorted by package id, then name; FNV-1a-32 over the
  little-endian u32 values). A heartbeat should carry the combined value.
- **`__pycache__` in output:** the generator copies boilerplate `__pycache__` folders into its
  output. Exclude them in `copy_all_files`.
- **Rust doc comments:** generated Rust may emit `////` doc comments for some `///` inputs.
  Verify; if it's real, fix it in `rust_gen.py` and update the IR goldens.
- **Comment cleanup (A5):** make sure Python `#//` and the invalid multi-line comment rendering
  are gone. Grep the generated output.
- **Stale instructions:** `.github/copilot-instructions.md` still describes the old syntax.

---

## 12. Provisional choices to confirm with the user

These are the defaults this plan assumes. Ask before building on them if they matter to the work
at hand.

1. **Heartbeats are off until enabled.** The default interval is 1000 ms and the timeout factor 3.
   With the id-0 design, older length-profile receivers skip id-0 frames safely, so the original
   reason for "off" is weaker; on-by-default for CRC profiles is a candidate.
2. **An rpc is identified by its request message's effective id.** So a message type can be the
   request of only one rpc. The alternative is a separate method number.
3. **No RPC client in C.** That follows "initiators on host languages only". A small poll-based C
   client would allow device-to-device calls.
4. **The link-test window is 256 sequence numbers,** and frames older than the window count as
   duplicates.
