# Struct Frame

[![Tests](https://github.com/mylonics/struct-frame/actions/workflows/test.yml/badge.svg)](https://github.com/mylonics/struct-frame/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/mylonics/struct-frame/branch/main/graph/badge.svg)](https://codecov.io/gh/mylonics/struct-frame)
[![Fuzz](https://github.com/mylonics/struct-frame/actions/workflows/fuzz.yml/badge.svg)](https://github.com/mylonics/struct-frame/actions/workflows/fuzz.yml)
[![PyPI](https://img.shields.io/pypi/v/struct-frame)](https://pypi.org/project/struct-frame/)

Struct Frame generates fixed-layout message types and framing code from one schema, for
**C, C++, Python, TypeScript, JavaScript, C# and Rust** (plus a GraphQL schema). It is built for
links where bytes arrive in a stream and both ends must agree on every one of them: UART and
serial, CAN-style buses, UDP/TCP between a device and a PC, inter-process pipes.

- **Fixed, packed layouts.** In C and C++ a message is a packed struct, so encoding a fixed
  message is a `memcpy`. Variable-length strings and arrays are optional per message.
- **Framing included.** Five ready-made frame profiles, from a 1-byte header for trusted links
  to sequence numbers, system/component IDs and 16-bit lengths for networks. Every runtime has
  the same writer and a streaming reader that resynchronises after corruption.
- **Checked compatibility.** On the checksummed profiles each message's checksum is seeded with
  bytes derived from its layout, so peers with different schemas reject each other's frames
  instead of misreading them. Fields can be appended under `extensions_start`, and
  `struct-frame diff` tells you whether a schema change is wire-compatible.
- **Same bytes everywhere.** Every runtime is tested against shared known-answer vectors and
  against each other on clean, corrupt and noisy streams.

Compared with Protocol Buffers, messages have a fixed size and no tag/varint encoding, which suits
microcontrollers and hard real-time code. Compared with MAVLink, messages can nest, contain arrays
and strings, and be split across packages.

## Install

```bash
pip install struct-frame
```

The generator needs Python 3.9 or later. The generated code and its runtime are copied into
your output directory and need nothing beyond each language's standard library (TypeScript and
JavaScript use Node's `Buffer`; the optional SDK transports have a few dependencies).

## Example

`robot.sf` (`.sf` is the preferred extension; `.proto` files with the same syntax also work):

```proto
package robot;

enum Mode { IDLE = 0; DRIVE = 1; }

message Status {
  option msgid = 1;
  uint32 uptime_ms = 1;
  float battery_v = 2;
  Mode mode = 3;
}
```

Generate C and Python into `gen/`:

```bash
struct-frame robot.sf --lang c,py --out gen
```

Send from C:

```c
#include "robot.structframe.h"   /* also brings in frame_profiles.h */

uint8_t tx[64];
buffer_writer_t writer;
buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, tx, sizeof tx);

RobotStatus status = {.uptime_ms = 1200, .battery_v = 12.4f, .mode = MODE_DRIVE};
RobotStatus_write(&writer, &status);          /* frame + checksum */
uart_send(tx, buffer_writer_size(&writer));
```

Receive in Python, feeding bytes as they arrive:

```python
from structframe.frame_profiles import AccumulatingReader, PROFILE_STANDARD_CONFIG
from structframe.robot import Status, get_message_info

reader = AccumulatingReader(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info)
reader.add_data(serial_port.read(256))
while (frame := reader.try_next()) is not None:
    if frame.valid and frame.msg_id == Status.MSG_ID:
        print(Status.deserialize(frame).battery_v)
```

Complete programs for C, Python and TypeScript are in [`examples/basic/`](examples/basic/); the
test suite builds and runs them. The [Language Examples](https://struct-frame.mylonics.com/basic-usage/language-examples/)
page has the same steps for every language.

## Languages

| | C | C++ | Python | TypeScript | JavaScript | C# | Rust |
|---|---|---|---|---|---|---|---|
| Messages, enums, nested messages, arrays, strings | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Variable-length messages and `oneof` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Frame writer and streaming reader | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SDK (transports, message routing) | | Serial, UDP, TCP | Serial, sockets, WebSocket | Serial, UDP, TCP, WebSocket | same as TS | Serial, UDP, TCP, WebSocket | |

`--build-gql` also writes a GraphQL schema of the same types. See the
[SDK overview](https://struct-frame.mylonics.com/extended-features/sdk-overview/) for transports.

## Frame profiles

| Profile | Layout | Overhead | Use |
|---|---|---|---|
| Standard | `90 71 LEN ID payload CRC CRC` | 6 | Serial links (recommended default) |
| Sensor | `70 ID payload` | 2 | Low-bandwidth sensors, fixed-size messages |
| IPC | `ID payload` | 1 | Trusted in-process or local links |
| Bulk | `90 74 LEN LEN PKG ID payload CRC CRC` | 8 | Large payloads, package IDs |
| Network | `90 78 SEQ SYS COMP LEN LEN PKG ID payload CRC CRC` | 11 | Multi-node networks |

The checksum is Fletcher-16 over everything after the start bytes, seeded with two per-message
bytes; readers therefore take the generated `get_message_info`. See
[Framing](https://struct-frame.mylonics.com/basic-usage/framing/) for every header and payload type.

## Command line

```bash
struct-frame robot.sf --lang c,cpp,py,ts --out gen     # several languages under gen/<lang>
struct-frame robot.sf --build-c --c-path firmware/gen  # one language, explicit directory
struct-frame robot.sf --validate                       # check against every language, write nothing
struct-frame diff old.sf new.sf                        # is the change wire-compatible?
struct-frame                                           # options from ./structframe.toml
```

Outputs are cached: an unchanged schema is not regenerated (`--force` overrides). See the
[CLI reference](https://struct-frame.mylonics.com/reference/cli-reference/) for every option and the
`structframe.toml` format, and [Build Integration](https://struct-frame.mylonics.com/reference/build-integration/)
for CMake, Make, npm and MSBuild.

## Documentation

- [Quick start](https://struct-frame.mylonics.com/getting-started/quick-start/)
- [Message definitions](https://struct-frame.mylonics.com/basic-usage/message-definitions/): types, arrays, strings, `oneof`, defaults, wire evolution
- [Framing](https://struct-frame.mylonics.com/basic-usage/framing/) and [framing details](https://struct-frame.mylonics.com/basic-usage/framing-details/)
- [Conformance](https://struct-frame.mylonics.com/reference/conformance/): the wire format, for writing your own implementation
- [Wireshark dissector](wireshark/README.md) (experimental)
- [Changelog](CHANGELOG.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: `pip install -e ".[test]"`, `npm ci`, then
`python test_all.py` runs generation, compilation and the cross-language tests for every toolchain
on your machine.

## License

MIT; see [LICENSE](LICENSE).
