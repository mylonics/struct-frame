// Frame Headers - Start byte patterns and header configurations (Rust)
// Mirrors frame_headers.h from C boilerplate

/// Header type enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HeaderType {
    None,
    Tiny,
    Basic,
}

/// Constants
pub const BASIC_START_BYTE: u8 = 0x90;
pub const PAYLOAD_TYPE_BASE: u8 = 0x70;

/// Header configuration
#[derive(Debug, Clone, Copy)]
pub struct HeaderConfig {
    pub header_type: HeaderType,
    pub start_byte1: u8,
    pub num_start_bytes: u8,
    pub encodes_payload_type: bool,
}

/// Get the start byte for a Tiny frame with given payload type
pub fn get_tiny_start_byte(payload_type_value: u8) -> u8 {
    PAYLOAD_TYPE_BASE + payload_type_value
}

/// Get the second start byte for a Basic frame with given payload type
pub fn get_basic_second_start_byte(payload_type_value: u8) -> u8 {
    PAYLOAD_TYPE_BASE + payload_type_value
}

// Pre-defined header configurations

/// None header - no start bytes
pub const HEADER_NONE_CONFIG: HeaderConfig = HeaderConfig {
    header_type: HeaderType::None,
    start_byte1: 0,
    num_start_bytes: 0,
    encodes_payload_type: false,
};

/// Tiny header - 1 start byte [0x70+PayloadType]
pub const HEADER_TINY_CONFIG: HeaderConfig = HeaderConfig {
    header_type: HeaderType::Tiny,
    start_byte1: 0, // Dynamic - depends on payload type
    num_start_bytes: 1,
    encodes_payload_type: true,
};

/// Basic header - 2 start bytes [0x90] [0x70+PayloadType]
pub const HEADER_BASIC_CONFIG: HeaderConfig = HeaderConfig {
    header_type: HeaderType::Basic,
    start_byte1: BASIC_START_BYTE,
    num_start_bytes: 2,
    encodes_payload_type: true,
};
