---
title: Rust SDK
description: Using the generated Rust code and frame SDK for encoding and decoding struct-frame messages.
---

struct-frame can generate Rust message structs and a complete frame parsing SDK. The generated crate is self-contained with no external runtime dependencies beyond the Rust standard library.

## Requirements

- Rust stable (1.60+)
- Cargo

## Generating Rust Code

```bash
python -m struct_frame messages.proto --build_rust --rust_path generated/rust/
```

### Generated Output

```
generated/rust/
├── Cargo.toml                    # Crate manifest (always generated)
├── lib.rs                        # Crate root re-exporting all modules
├── <package>.structframe.rs      # Message structs (one file per package)
├── frame_base.rs                 # FrameMsgInfo, StructFrameMessage trait, fletcher_checksum
├── frame_headers.rs              # Header configurations (None, Tiny, Basic)
├── payload_types.rs              # Payload configurations and types
└── frame_profiles.rs             # Profiles, encoders, parsers, BufferWriter/Reader, AccumulatingReader
```

### Cargo Dependency

In your consuming crate's `Cargo.toml`, add:

```toml
[dependencies]
struct_frame_sdk = { path = "generated/rust" }
```

Then in your source:

```rust
use struct_frame_sdk::example::ExampleStatus;
use struct_frame_sdk::{
    encode_message_crc, AccumulatingReader,
    PROFILE_STANDARD_CONFIG,
};
```

## Message Structs

Each message is generated as a plain Rust struct implementing the `StructFrameMessage` trait:

```rust
pub struct ExampleStatus {
    pub id: u32,
    pub value: f32,
}
```

### StructFrameMessage Trait

```rust
pub trait StructFrameMessage: Default {
    const MSG_ID: u8;
    const MAX_SIZE: usize;
    const MAGIC1: u8;
    const MAGIC2: u8;
    const IS_VARIABLE: bool;

    fn pack(&self, buffer: &mut [u8]) -> usize;
    fn pack_max_size(buffer: &mut [u8]) -> usize;
    fn unpack(buffer: &[u8]) -> Option<Self> where Self: Sized;
}
```

`pack` serializes the message into `buffer` and returns the number of bytes written. `unpack` deserializes from a byte slice and returns the struct.

## Frame Profiles

Five pre-built profiles cover the most common framing configurations:

| Constant | Header | Payload | Use Case |
|----------|--------|---------|----------|
| `PROFILE_STANDARD_CONFIG` | Basic | Default | General serial / UART |
| `PROFILE_SENSOR_CONFIG` | Tiny | Minimal | Low-bandwidth sensors |
| `PROFILE_IPC_CONFIG` | None | Minimal | Trusted inter-process |
| `PROFILE_BULK_CONFIG` | Basic | Extended | Large data transfers |
| `PROFILE_NETWORK_CONFIG` | Basic | ExtendedMultiSystemStream | Multi-system networking |

## Encoding

### Single Message

```rust
use struct_frame_sdk::example::ExampleStatus;
use struct_frame_sdk::{encode_message_crc, PROFILE_STANDARD_CONFIG};

let msg = ExampleStatus { id: 42, value: 3.14 };

let mut buffer = [0u8; 1024];
let written = encode_message_crc(&PROFILE_STANDARD_CONFIG, &mut buffer, &msg, 0);

// buffer[..written] contains the complete framed message
send_bytes(&buffer[..written]);
```

### Minimal (No CRC / No Length)

```rust
use struct_frame_sdk::{encode_message_minimal, PROFILE_IPC_CONFIG};

let written = encode_message_minimal(&PROFILE_IPC_CONFIG, &mut buffer, &msg);
```

### Encoding Multiple Messages with BufferWriter

```rust
use struct_frame_sdk::{BufferWriter, PROFILE_STANDARD_CONFIG};

let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 4096);

writer.write_crc(&msg1, 0);
writer.write_crc(&msg2, 0);
writer.write_crc(&msg3, 0);

send_bytes(writer.data());
```

## Decoding

### Buffer Mode (Recommended)

`AccumulatingReader` handles partial frames across buffer boundaries:

```rust
use struct_frame_sdk::{AccumulatingReader, MessageInfo, PROFILE_STANDARD_CONFIG};

let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 4096);

// Feed received data (may contain partial or multiple frames)
reader.add_data(&received_bytes);

// Drain all complete messages
let get_info = |id: u16| -> Option<MessageInfo> {
    match id {
        i if i == ExampleStatus::MSG_ID => Some(ExampleStatus::message_info()),
        _ => None,
    }
};
while let Some(info) = reader.next(&get_info) {
    if info.valid {
        if let Some(msg) = ExampleStatus::unpack(&info.payload) {
            println!("ID: {}, Value: {}", msg.id, msg.value);
        }
    }
}
```

### Stream Mode (Byte-by-Byte)

Useful when receiving from a serial port or UART one byte at a time:

```rust
let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 4096);
let get_info = |id: u16| -> Option<MessageInfo> {
    match id {
        i if i == ExampleStatus::MSG_ID => Some(ExampleStatus::message_info()),
        _ => None,
    }
};

for byte in uart.bytes() {
    reader.add_data(&[byte?]);
    if let Some(info) = reader.next(&get_info) {
        if info.valid {
            if let Some(msg) = ExampleStatus::unpack(&info.payload) {
                // handle message
            }
        }
    }
}
```

### Parsing Multiple Messages with BufferReader

For pre-loaded buffers containing multiple complete frames:

```rust
use struct_frame_sdk::{BufferReader, MessageInfo, PROFILE_STANDARD_CONFIG};

let get_info = |id: u16| -> Option<MessageInfo> {
    match id {
        i if i == ExampleStatus::MSG_ID => Some(ExampleStatus::message_info()),
        _ => None,
    }
};
let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data.to_vec());

while let Some(info) = reader.next(&get_info) {
    if info.valid {
        match info.msg_id {
            i if i == ExampleStatus::MSG_ID => {
                if let Some(msg) = ExampleStatus::unpack(&info.payload) {
                    // handle
                }
            }
            _ => {}
        }
    }
}
```

## FrameMsgInfo

`AccumulatingReader::next(&get_info)` and `BufferReader::next(&get_info)` return a `FrameMsgInfo`:

```rust
pub struct FrameMsgInfo {
    pub valid: bool,       // CRC check passed (always true for minimal profiles)
    pub msg_id: u16,       // Message identifier
    pub msg_len: usize,    // Payload length in bytes
    pub frame_size: usize, // Total frame size including headers + footer
    pub package_id: u8,    // Package identifier (0 if not present)
    pub sequence: u8,      // Sequence counter (0 if not present)
    pub system_id: u8,     // System ID (Network profile only)
    pub component_id: u8,  // Component ID (Network profile only)
    pub payload: Vec<u8>,  // Raw message bytes; pass to M::unpack()
}
```

## Discriminating Message Types

When a buffer may contain different message types, match on `msg_id`:

```rust
use struct_frame_sdk::example::{ExampleStatus, ExampleCommand};

let get_info = |id: u16| -> Option<MessageInfo> {
    match id {
        i if i == ExampleStatus::MSG_ID  => Some(ExampleStatus::message_info()),
        i if i == ExampleCommand::MSG_ID => Some(ExampleCommand::message_info()),
        _ => None,
    }
};
while let Some(info) = reader.next(&get_info) {
    if !info.valid { continue; }
    match info.msg_id {
        i if i == ExampleStatus::MSG_ID  => {
            if let Some(msg) = ExampleStatus::unpack(&info.payload) { handle_status(msg); }
        }
        i if i == ExampleCommand::MSG_ID => {
            if let Some(msg) = ExampleCommand::unpack(&info.payload) { handle_command(msg); }
        }
        _ => { /* unknown message */ }
    }
}
```

## Build Integration

Add a `build.rs` to regenerate Rust code whenever the proto file changes:

```rust
// build.rs
fn main() {
    println!("cargo:rerun-if-changed=proto/messages.proto");
    std::process::Command::new("python")
        .args(["-m", "struct_frame", "proto/messages.proto",
               "--build_rust", "--rust_path", "generated/rust/"])
        .status()
        .expect("struct-frame code generation failed");
}
```
