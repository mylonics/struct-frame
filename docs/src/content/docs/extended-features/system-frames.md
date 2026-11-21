---
title: System Frames
description: struct-frame's own messages (heartbeat, ping, link tests, RPC) on the same link as your frames.
---

System frames carry struct-frame's own messages next to your application's frames:
heartbeats, ping/pong probes, link-test traffic and RPC envelopes. They use their own
payload type (9, start byte `0x79`) and their own message-id space, so they can never be
mistaken for one of your messages, and every reader in every language understands them.

The messages are declared in the built-in schema
[`sf_system.sf`](https://github.com/mylonics/struct-frame/blob/main/src/struct_frame/builtin/sf_system.sf)
and are pre-generated into each runtime, so there is nothing to generate. The package name
`sf_system` is reserved.

## Where they work

System frames travel with the header of the profile you already use:

| Profile | System frame starts with |
|---|---|
| Standard, Bulk, Network (Basic header) | `90 79` |
| Sensor (Tiny header) | `79` |
| IPC (no header) | not supported |

Every system frame carries a sequence number, the sender's system and component ids, a
16-bit length and a CRC, whatever the profile's own frames carry. The exact layout is in
[Conformance § 9](/struct-frame/reference/conformance/#9-system-frames).

## Receiving

Readers recognise system frames on their own. By default they **hide** them: the frame is
consumed and counted in the reader's diagnostics (`cnt_system_frames`), and your code never
sees it. Turn delivery on to receive them; a delivered frame has `is_system` set and its
message id is a system message id.

A header that cannot be a system frame (unknown system message id, impossible length) is
rejected as soon as it is complete and counted in `cnt_system_rejected`, so a stray `0x79`
byte on a noisy line does not swallow your frames.

### Python

```python
from structframe import frame_profiles, sf_system, system_frames

reader = frame_profiles.AccumulatingReader(frame_profiles.PROFILE_STANDARD_CONFIG,
                                           get_message_info=get_message_info,
                                           deliver_system_frames=True)
reader.add_data(data)
while (frame := reader.try_next()) is not None:
    if frame.valid and frame.is_system:
        message, tail = system_frames.decode(frame)
        if isinstance(message, sf_system.Heartbeat):
            print(frame.system_id, message.uptime_ms)
```

### TypeScript / JavaScript

```ts no-compile
import { AccumulatingReader, ProfileStandardConfig, decodeSystemMessage, sfSystem } from './index';

const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024, true);
reader.addData(data);
let frame;
while ((frame = reader.tryNext()) !== null) {
  if (frame.valid && frame.isSystem) {
    const { message, tail } = decodeSystemMessage(frame);
    if (message instanceof sfSystem.Heartbeat) console.log(frame.systemId, message.uptimeMs);
  }
}
```

### C

```c no-compile
uint8_t internal[1100];
accumulating_reader_t reader;
accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal, sizeof internal, get_message_info);
accumulating_reader_set_deliver_system_frames(&reader, true);
accumulating_reader_add_data(&reader, data, len);
frame_msg_info_t frame;
while (accumulating_reader_try_next(&reader, &frame)) {
    if (frame.valid && frame.is_system && frame.msg_id == SF_SYSTEM_HEARTBEAT_MSG_ID) {
        SfSystemHeartbeat hb;
        SfSystemHeartbeat_deserialize(frame.msg_data, frame.msg_len, &hb);
    }
}
```

### C++

```cpp no-compile
ProfileReader<ProfileStandardConfig, 1100> reader(mypkg::get_message_info);
reader.set_deliver_system_frames(true);
reader.add_data(data, len);
FrameMsgInfo frame;
while (reader.try_next(frame)) {
  if (frame.valid && frame.is_system && frame.msg_id == sf_system::Heartbeat::MSG_ID) {
    sf_system::Heartbeat hb;
    hb.deserialize(frame.msg_data, frame.msg_len);
    size_t tail_size = 0;
    const uint8_t* tail = system_frames::tail(frame, tail_size);
  }
}
```

### C#

```csharp no-compile
var reader = new AccumulatingReader(Profiles.Standard, 1100, MessageDefinitions.GetMessageInfo)
{
    DeliverSystemFrames = true,
};
reader.AddData(data);
while (reader.TryNext(out var frame))
{
    if (frame.Valid && frame.IsSystem)
    {
        var (message, tail) = SystemFrames.Decode(frame);
    }
}
```

### Rust

```rust no-compile
let mut reader = AccumulatingReader::with_message_info(PROFILE_STANDARD_CONFIG, 1100, get_message_info);
reader.set_deliver_system_frames(true);
reader.add_data(&data);
while let Some(frame) = reader.next_frame() {
    if frame.valid && frame.is_system {
        if let Some((hb, _tail)) = system_frames::decode::<sf_system::Heartbeat>(&frame) {
            println!("{} {}", frame.system_id, hb.uptime_ms);
        }
    }
}
```

## Sending

Each runtime encodes a system message for the header of your profile. Ping, Pong,
LinkTestData, RpcRequest and RpcResponse take an optional raw *tail* after their fields (at
most `MAX_TAIL` = 1024 bytes); the other messages take none. A reader that must receive
the largest frames needs an internal buffer of at least 1048 bytes.

```python
frame = system_frames.encode(frame_profiles.PROFILE_STANDARD_CONFIG,
                             sf_system.Ping(t_send_us=now_us, seq=1), tail=b"padding",
                             seq=tx_seq, sys_id=1, comp_id=1)
```

```ts no-compile
const frame = encodeSystemMessage(ProfileStandardConfig, new sfSystem.Ping({ tSendUs: nowUs, seq: 1 }),
                                  { tail: padding, seq: txSeq, sysId: 1, compId: 1 });
```

```c no-compile
SfSystemPing ping = {0};
ping.seq = 1;
uint8_t buf[64];
uint8_t* fixed = buf + profile_system_header_size(&PROFILE_STANDARD_CONFIG);
size_t fixed_size = SfSystemPing_serialize(&ping, fixed);  /* serialized in place */
size_t n = profile_encode_system_frame(&PROFILE_STANDARD_CONFIG, buf, sizeof buf, tx_seq, 1, 1,
                                       SF_SYSTEM_PING_MSG_ID, fixed, fixed_size, NULL, 0);
```

```cpp no-compile
sf_system::Ping ping{};
ping.seq = 1;
uint8_t buf[64];
size_t n = system_frames::encode<ProfileStandardConfig>(buf, sizeof buf, ping, nullptr, 0, tx_seq, 1, 1);
```

```csharp no-compile
byte[] frame = SystemFrames.Encode(Profiles.Standard, new Ping { Seq = 1 }, padding, txSeq, 1, 1);
```

```rust no-compile
let mut buf = [0u8; 64];
let n = system_frames::encode(&PROFILE_STANDARD_CONFIG, &mut buf, &sf_system::Ping { seq: 1, ..Default::default() },
                              &[], tx_seq, 1, 1);
```

Use your own sequence counter for system frames: readers track their sequence numbers
separately from your application frames'.

## Compiling the support out

C and C++ readers drop the system-frame support when `SF_DISABLE_SYSTEM_FRAMES` is defined;
`0x79` is then ordinary data and `cnt_system_frames` stays zero.
