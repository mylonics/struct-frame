// struct-frame Rust SDK
// This library provides frame encoding/decoding utilities for struct-frame messages.

pub mod frame_base;
pub mod frame_headers;
pub mod payload_types;
pub mod frame_profiles;
pub mod struct_frame_sdk;

pub use frame_base::{
    fletcher_checksum, fletcher_checksum_ext, FrameChecksum, FrameMsgInfo, FrameMsgStatus,
    MessageInfo, ParserDiagnostics, StructFrameMessage,
};
pub use frame_headers::{
    get_basic_second_start_byte, get_tiny_start_byte, HeaderConfig, HeaderType,
    BASIC_START_BYTE, HEADER_BASIC_CONFIG, HEADER_NONE_CONFIG, HEADER_TINY_CONFIG,
    PAYLOAD_TYPE_BASE,
};
pub use payload_types::{
    PayloadConfig, PayloadType, PAYLOAD_DEFAULT_CONFIG, PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG, PAYLOAD_MINIMAL_CONFIG,
};
pub use frame_profiles::{
    AccumulatingReader, BufferReader, BufferWriter, ProfileConfig,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,
    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,
    encode_message, encode_message_crc, encode_message_minimal, encode_minimal,
    encode_with_crc, encode_with_crc_ext,
    parse_frame, parse_minimal, parse_with_crc,
    new_bulk_reader, new_bulk_writer, new_ipc_reader, new_ipc_writer,
    new_network_reader, new_network_writer, new_sensor_reader, new_sensor_writer,
    new_standard_reader, new_standard_writer,
};
pub use struct_frame_sdk::{MessageHandler, SendResult, Subscription, StructFrameSdk};
