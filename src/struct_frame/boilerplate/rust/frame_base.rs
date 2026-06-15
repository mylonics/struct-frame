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

/// Extension-aware Fletcher-16 checksum.
/// Computes: Fletcher(base_data) -> mix magic1/magic2 -> Fletcher(ext_data).
/// When ext_data is empty the result is identical to fletcher_checksum.
///
/// # Arguments
/// * `base_data` - Non-extension portion of the payload
/// * `ext_data` - Extension portion of the payload (may be empty)
/// * `magic1` - First magic number (mixed in after base_data)
/// * `magic2` - Second magic number (mixed in after magic1)
pub fn fletcher_checksum_ext(base_data: &[u8], ext_data: &[u8], magic1: u8, magic2: u8) -> FrameChecksum {
    let mut b1: u8 = 0;
    let mut b2: u8 = 0;
    for &byte in base_data {
        b1 = b1.wrapping_add(byte);
        b2 = b2.wrapping_add(b1);
    }
    b1 = b1.wrapping_add(magic1);
    b2 = b2.wrapping_add(b1);
    b1 = b1.wrapping_add(magic2);
    b2 = b2.wrapping_add(b1);
    for &byte in ext_data {
        b1 = b1.wrapping_add(byte);
        b2 = b2.wrapping_add(b1);
    }
    FrameChecksum { byte1: b1, byte2: b2 }
}

/// Parser status indicating the reason a FrameMsgInfo is not valid.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum FrameMsgStatus {
    #[default]
    None = 0,
    WaitingForStart = 1,
    Collecting = 2,
    CrcFailure = 3,
    SyncRecovery = 4,
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
    /// Use `get_payload_span()` for a zero-copy slice or `extract_payload()` to move the data out.
    pub msg_data: Vec<u8>,
    /// Status indicating the reason this result is not valid (only meaningful when valid is false).
    pub status: FrameMsgStatus,
}

impl FrameMsgInfo {
    pub fn invalid() -> Self {
        Self::default()
    }

    /// Return a zero-copy slice of the payload bytes.
    #[inline]
    pub fn get_payload_span(&self) -> &[u8] {
        &self.msg_data
    }

    /// Move the payload bytes out, consuming this field's allocation.
    #[inline]
    pub fn extract_payload(self) -> Vec<u8> {
        self.msg_data
    }
}

/// Diagnostic counters for AccumulatingReader (stream mode).
///
/// All counters accumulate over the reader's lifetime.
/// Call `reset_diagnostics()` to clear them.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ParserDiagnostics {
    /// Number of complete frames received with a bad CRC.
    /// Indicates noise or corruption on the line.
    pub cnt_crc_failures: u32,

    /// Number of times the parser discarded bytes and re-searched for a frame start.
    /// Indicates lost bytes or buffer overflows.
    pub cnt_sync_recoveries: u32,

    /// Total number of bytes discarded during sync recovery.
    /// Complements cnt_sync_recoveries with a byte-level view of data loss.
    pub cnt_failed_bytes: u32,

    /// Number of frames where the header length field does not match the expected
    /// message-struct size from the message-info callback.
    /// Vital for detecting mismatched definitions on profiles that carry an explicit length.
    pub cnt_len_errors: u32,

    /// Number of sequence-number gaps detected.
    /// Only incremented on profiles that carry a sequence field (e.g. ProfileNetwork).
    /// Indicates dropped packets.
    pub cnt_seq_gaps: u32,
}

/// Message metadata used for parsing (size + magic numbers)
#[derive(Debug, Clone, Copy)]
pub struct MessageInfo {
    pub size: usize,
    pub magic1: u8,
    pub magic2: u8,
    pub base_size: usize,  // Non-extension portion size (== size when no extensions)
    /// Minimum valid wire payload length (< size only for variable messages).
    pub min_size: usize,
}

impl MessageInfo {
    pub fn new(size: usize, magic1: u8, magic2: u8) -> Self {
        MessageInfo { size, magic1, magic2, base_size: size, min_size: size }
    }

    pub fn new_with_base_size(size: usize, magic1: u8, magic2: u8, base_size: usize) -> Self {
        MessageInfo { size, magic1, magic2, base_size, min_size: size }
    }

    pub fn new_variable(size: usize, magic1: u8, magic2: u8, base_size: usize, min_size: usize) -> Self {
        MessageInfo { size, magic1, magic2, base_size, min_size }
    }
}

/// Trait for messages that can be packed/unpacked to/from bytes
pub trait StructFrameMessage {
    const MSG_ID: u16;
    const MAX_SIZE: usize;
    const MAGIC1: u8;
    const MAGIC2: u8;
    /// Non-extension portion size. Equal to MAX_SIZE for messages with no extensions.
    const BASE_SIZE: usize = Self::MAX_SIZE;
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
