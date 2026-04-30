// Frame Base - Core utilities for struct-frame (Rust)
// Mirrors frame_base.hpp from C++ boilerplate

/// Checksum result - two bytes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct FrameChecksum {
    pub byte1: u8,
    pub byte2: u8,
}

/// Calculate Fletcher-16 checksum over the given data slice.
///
/// # Arguments
/// * `data` - Buffer to checksum
/// * `magic1` - First magic number (mixed in after data)
/// * `magic2` - Second magic number (mixed in after magic1)
pub fn fletcher_checksum(data: &[u8], magic1: u8, magic2: u8) -> FrameChecksum {
    let mut b1: u8 = 0;
    let mut b2: u8 = 0;
    for &byte in data {
        b1 = b1.wrapping_add(byte);
        b2 = b2.wrapping_add(b1);
    }
    b1 = b1.wrapping_add(magic1);
    b2 = b2.wrapping_add(b1);
    b1 = b1.wrapping_add(magic2);
    b2 = b2.wrapping_add(b1);
    FrameChecksum { byte1: b1, byte2: b2 }
}

/// Result from frame parsing.
#[derive(Debug, Clone, Default)]
pub struct FrameMsgInfo {
    pub valid: bool,
    pub msg_id: u16,
    pub msg_len: usize,
    pub frame_size: usize,
    pub package_id: u8,
    pub sequence: u8,
    pub system_id: u8,
    pub component_id: u8,
    /// The raw message payload bytes (excluding framing overhead).
    pub payload: Vec<u8>,
}

impl FrameMsgInfo {
    pub fn invalid() -> Self {
        Self::default()
    }
}

/// Message metadata used for parsing (size + magic numbers)
#[derive(Debug, Clone, Copy)]
pub struct MessageInfo {
    pub size: usize,
    pub magic1: u8,
    pub magic2: u8,
}

impl MessageInfo {
    pub fn new(size: usize, magic1: u8, magic2: u8) -> Self {
        MessageInfo { size, magic1, magic2 }
    }
}

/// Trait for messages that can be packed/unpacked to/from bytes
pub trait StructFrameMessage {
    const MSG_ID: u16;
    const MAX_SIZE: usize;
    const MAGIC1: u8;
    const MAGIC2: u8;
    /// True if the message uses variable-length encoding for bounded fields.
    const IS_VARIABLE: bool;

    /// Serialize using variable-length encoding (actual data only for bounded fields).
    fn pack(&self, buf: &mut [u8]) -> usize;
    /// Serialize using fixed-size encoding (always MAX_SIZE bytes).
    fn pack_max_size(&self, buf: &mut [u8]) -> usize;
    /// Deserialize. For variable messages dispatches based on buf.len().
    fn unpack(buf: &[u8]) -> Option<Self>
    where
        Self: Sized;

    fn message_info() -> MessageInfo {
        MessageInfo::new(Self::MAX_SIZE, Self::MAGIC1, Self::MAGIC2)
    }
}
