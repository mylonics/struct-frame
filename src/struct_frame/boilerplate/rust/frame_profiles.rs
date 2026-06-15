// Frame Profiles - Pre-defined Header + Payload combinations (Rust)
// Mirrors frame_profiles.h from C boilerplate

use crate::frame_base::{fletcher_checksum, fletcher_checksum_ext, FrameChecksum, FrameMsgInfo, FrameMsgStatus, MessageInfo, ParserDiagnostics, StructFrameMessage};
use crate::frame_headers::{
    get_basic_second_start_byte, get_tiny_start_byte, HeaderConfig, HeaderType,
    BASIC_START_BYTE, HEADER_BASIC_CONFIG, HEADER_NONE_CONFIG, HEADER_TINY_CONFIG,
    PAYLOAD_TYPE_BASE,
};
use crate::payload_types::{
    PayloadConfig, PAYLOAD_DEFAULT_CONFIG, PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG, PAYLOAD_MINIMAL_CONFIG,
};

/// Profile configuration - combines a HeaderConfig with a PayloadConfig.
#[derive(Debug, Clone, Copy)]
pub struct ProfileConfig {
    pub header: HeaderConfig,
    pub payload: PayloadConfig,
}

impl ProfileConfig {
    pub const fn new(header: HeaderConfig, payload: PayloadConfig) -> Self {
        ProfileConfig { header, payload }
    }

    /// Total header size (start bytes + payload header fields)
    pub fn header_size(&self) -> usize {
        self.header.num_start_bytes as usize + self.payload.header_size()
    }

    /// Footer size (CRC bytes)
    pub fn footer_size(&self) -> usize {
        self.payload.footer_size()
    }

    /// Total overhead
    pub fn overhead(&self) -> usize {
        self.header_size() + self.footer_size()
    }

    /// Compute start byte1 for this profile
    pub fn computed_start_byte1(&self) -> u8 {
        if self.header.encodes_payload_type && self.header.num_start_bytes == 1 {
            get_tiny_start_byte(self.payload.payload_type as u8)
        } else {
            self.header.start_byte1
        }
    }

    /// Compute start byte2 for this profile (Basic headers only)
    pub fn computed_start_byte2(&self) -> u8 {
        if self.header.encodes_payload_type && self.header.num_start_bytes == 2 {
            get_basic_second_start_byte(self.payload.payload_type as u8)
        } else {
            0
        }
    }
}

// Pre-defined profile configurations

/// Profile Standard: Basic + Default
/// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
pub const PROFILE_STANDARD_CONFIG: ProfileConfig =
    ProfileConfig::new(HEADER_BASIC_CONFIG, PAYLOAD_DEFAULT_CONFIG);

/// Profile Sensor: Tiny + Minimal
/// Frame: [0x70] [MSG_ID] [PAYLOAD]
pub const PROFILE_SENSOR_CONFIG: ProfileConfig =
    ProfileConfig::new(HEADER_TINY_CONFIG, PAYLOAD_MINIMAL_CONFIG);

/// Profile IPC: None + Minimal
/// Frame: [MSG_ID] [PAYLOAD]
pub const PROFILE_IPC_CONFIG: ProfileConfig =
    ProfileConfig::new(HEADER_NONE_CONFIG, PAYLOAD_MINIMAL_CONFIG);

/// Profile Bulk: Basic + Extended
/// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
pub const PROFILE_BULK_CONFIG: ProfileConfig =
    ProfileConfig::new(HEADER_BASIC_CONFIG, PAYLOAD_EXTENDED_CONFIG);

/// Profile Network: Basic + ExtendedMultiSystemStream
pub const PROFILE_NETWORK_CONFIG: ProfileConfig =
    ProfileConfig::new(HEADER_BASIC_CONFIG, PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG);

// =============================================================================
// Helpers
// =============================================================================

/// Max representable payload length for a given number of length bytes.
fn max_payload_for_length_bytes(length_bytes: u8) -> usize {
    match length_bytes {
        1 => 255,
        2 => 65535,
        _ => 0,
    }
}

// =============================================================================
// encode_with_crc
// =============================================================================

/// Encode a message with CRC into a buffer.
///
/// Returns the number of bytes written, or 0 on error (buffer too small,
/// payload exceeds length-field capacity, or msg_id > 255 on a profile
/// without a pkg_id field).
pub fn encode_with_crc(
    config: &ProfileConfig,
    buffer: &mut [u8],
    seq: u8,
    sys_id: u8,
    comp_id: u8,
    pkg_id: u8,
    msg_id: u8,
    payload: &[u8],
    magic1: u8,
    magic2: u8,
) -> usize {
    // A2: reject oversized payloads before corrupting the length field
    if config.payload.has_length {
        let max_len = max_payload_for_length_bytes(config.payload.length_bytes);
        if payload.len() > max_len {
            return 0;
        }
    }

    let header_size = config.header_size();
    let footer_size = config.footer_size();
    let total_size = header_size + footer_size + payload.len();

    if buffer.len() < total_size {
        return 0;
    }

    let mut idx = 0;

    // Write start bytes
    if config.header.num_start_bytes >= 1 {
        buffer[idx] = config.computed_start_byte1();
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        buffer[idx] = config.computed_start_byte2();
        idx += 1;
    }

    let crc_start = idx;

    // Write optional fields before length
    if config.payload.has_seq {
        buffer[idx] = seq;
        idx += 1;
    }
    if config.payload.has_sys_id {
        buffer[idx] = sys_id;
        idx += 1;
    }
    if config.payload.has_comp_id {
        buffer[idx] = comp_id;
        idx += 1;
    }

    // Write length field
    if config.payload.has_length {
        if config.payload.length_bytes == 1 {
            buffer[idx] = payload.len() as u8;
            idx += 1;
        } else {
            buffer[idx] = (payload.len() & 0xFF) as u8;
            buffer[idx + 1] = ((payload.len() >> 8) & 0xFF) as u8;
            idx += 2;
        }
    }

    // Write package ID
    if config.payload.has_pkg_id {
        buffer[idx] = pkg_id;
        idx += 1;
    }

    // Write message ID
    buffer[idx] = msg_id;
    idx += 1;

    // Write payload
    buffer[idx..idx + payload.len()].copy_from_slice(payload);
    idx += payload.len();

    // Calculate and write CRC
    if config.payload.has_crc {
        let ck = fletcher_checksum(&buffer[crc_start..idx], magic1, magic2);
        buffer[idx] = ck.byte1;
        buffer[idx + 1] = ck.byte2;
        idx += 2;
    }

    idx
}

/// Encode a message with CRC and extension-aware checksum.
///
/// Same as encode_with_crc but accepts base_size for the extension-aware CRC algorithm.
/// When base_size == payload.len(), produces identical output to encode_with_crc.
#[allow(clippy::too_many_arguments)]
pub fn encode_with_crc_ext(
    config: &ProfileConfig,
    buffer: &mut [u8],
    seq: u8,
    sys_id: u8,
    comp_id: u8,
    pkg_id: u8,
    msg_id: u8,
    payload: &[u8],
    magic1: u8,
    magic2: u8,
    base_size: usize,
) -> usize {
    // A2: reject oversized payloads before corrupting the length field
    if config.payload.has_length {
        let max_len = max_payload_for_length_bytes(config.payload.length_bytes);
        if payload.len() > max_len {
            return 0;
        }
    }

    let header_size = config.header_size();
    let footer_size = config.footer_size();
    let total_size = header_size + footer_size + payload.len();

    if buffer.len() < total_size {
        return 0;
    }

    let mut idx = 0;

    if config.header.num_start_bytes >= 1 {
        buffer[idx] = config.computed_start_byte1();
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        buffer[idx] = config.computed_start_byte2();
        idx += 1;
    }

    let crc_start = idx;

    if config.payload.has_seq { buffer[idx] = seq; idx += 1; }
    if config.payload.has_sys_id { buffer[idx] = sys_id; idx += 1; }
    if config.payload.has_comp_id { buffer[idx] = comp_id; idx += 1; }

    if config.payload.has_length {
        if config.payload.length_bytes == 1 {
            buffer[idx] = payload.len() as u8; idx += 1;
        } else {
            buffer[idx] = (payload.len() & 0xFF) as u8;
            buffer[idx + 1] = ((payload.len() >> 8) & 0xFF) as u8;
            idx += 2;
        }
    }

    if config.payload.has_pkg_id { buffer[idx] = pkg_id; idx += 1; }
    buffer[idx] = msg_id; idx += 1;

    buffer[idx..idx + payload.len()].copy_from_slice(payload);
    idx += payload.len();

    if config.payload.has_crc {
        let ck = if config.payload.has_length && base_size < payload.len() {
            let overhead_in_crc = idx - crc_start - payload.len();
            let base_end = crc_start + overhead_in_crc + base_size;
            fletcher_checksum_ext(&buffer[crc_start..base_end], &buffer[base_end..idx], magic1, magic2)
        } else {
            fletcher_checksum(&buffer[crc_start..idx], magic1, magic2)
        };
        buffer[idx] = ck.byte1;
        buffer[idx + 1] = ck.byte2;
        idx += 2;
    }

    idx
}

/// Encode a minimal message (no length, no CRC) into a buffer.
///
/// Returns the number of bytes written, or 0 on error.
pub fn encode_minimal(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg_id: u8,
    payload: &[u8],
) -> usize {
    let header_size = config.header_size();
    let total_size = header_size + payload.len();

    if buffer.len() < total_size {
        return 0;
    }

    let mut idx = 0;

    // Write start bytes
    if config.header.num_start_bytes >= 1 {
        buffer[idx] = config.computed_start_byte1();
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        buffer[idx] = config.computed_start_byte2();
        idx += 1;
    }

    // Write message ID
    buffer[idx] = msg_id;
    idx += 1;

    // Write payload
    buffer[idx..idx + payload.len()].copy_from_slice(payload);
    idx += payload.len();

    idx
}

// =============================================================================
// parse_with_crc / parse_minimal
// =============================================================================

/// Parse a frame with CRC from a buffer.
///
/// Returns FrameMsgInfo with valid=true if parsing succeeded.
/// Sets status to WaitingForStart on bad start bytes, Collecting on insufficient data.
pub fn parse_with_crc(
    config: &ProfileConfig,
    buffer: &[u8],
    get_message_info: &dyn Fn(u16) -> Option<MessageInfo>,
) -> FrameMsgInfo {
    let header_size = config.header_size();
    let footer_size = config.footer_size();
    let overhead = header_size + footer_size;

    if buffer.len() < overhead {
        // B2: not enough data yet
        return FrameMsgInfo { status: FrameMsgStatus::Collecting, ..FrameMsgInfo::invalid() };
    }

    let mut idx = 0;

    // Verify start bytes — B2: WaitingForStart on mismatch
    if config.header.num_start_bytes >= 1 {
        if buffer[idx] != config.computed_start_byte1() {
            return FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() };
        }
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        if buffer[idx] != config.computed_start_byte2() {
            return FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() };
        }
        idx += 1;
    }

    let crc_start = idx;
    let mut seq = 0u8;
    let mut sys_id = 0u8;
    let mut comp_id = 0u8;

    // Skip optional fields
    if config.payload.has_seq {
        seq = buffer[idx];
        idx += 1;
    }
    if config.payload.has_sys_id {
        sys_id = buffer[idx];
        idx += 1;
    }
    if config.payload.has_comp_id {
        comp_id = buffer[idx];
        idx += 1;
    }

    // Read length field
    let msg_len = if config.payload.has_length {
        if config.payload.length_bytes == 1 {
            let l = buffer[idx] as usize;
            idx += 1;
            l
        } else {
            let l = (buffer[idx] as usize) | ((buffer[idx + 1] as usize) << 8);
            idx += 2;
            l
        }
    } else {
        0
    };

    // Read message ID (high byte is pkg_id when has_pkg_id, low byte is msg_id)
    let mut msg_id: u16 = 0;
    let mut pkg_id: u8 = 0;
    if config.payload.has_pkg_id {
        pkg_id = buffer[idx];
        msg_id = (buffer[idx] as u16) << 8;
        idx += 1;
    }
    msg_id |= buffer[idx] as u16;
    let _ = idx;  // idx no longer needed after reading msg_id

    // Verify total size — B2: Collecting if not enough data
    let total_size = overhead + msg_len;
    if buffer.len() < total_size {
        return FrameMsgInfo { status: FrameMsgStatus::Collecting, ..FrameMsgInfo::invalid() };
    }

    // Verify CRC (extension-aware)
    if config.payload.has_crc {
        let crc_len = total_size - crc_start - footer_size;
        let (magic1, magic2, base_size) = match get_message_info(msg_id) {
            Some(info) => (info.magic1, info.magic2, info.base_size),
            None => (0, 0, msg_len),
        };
        let ck = if config.payload.has_length && base_size < msg_len {
            let overhead_in_crc = crc_len - msg_len;
            let base_end = crc_start + overhead_in_crc + base_size;
            fletcher_checksum_ext(
                &buffer[crc_start..base_end],
                &buffer[base_end..crc_start + crc_len],
                magic1,
                magic2,
            )
        } else {
            fletcher_checksum(&buffer[crc_start..crc_start + crc_len], magic1, magic2)
        };
        if ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1] {
            return FrameMsgInfo { status: FrameMsgStatus::CrcFailure, ..FrameMsgInfo::invalid() };
        }
    }

    // Extract payload bytes
    let msg_data = buffer[header_size..header_size + msg_len].to_vec();

    FrameMsgInfo {
        valid: true,
        msg_id,
        msg_len,
        frame_size: total_size,
        package_id: pkg_id,
        sequence: seq,
        system_id: sys_id,
        component_id: comp_id,
        msg_data,
        ..Default::default()
    }
}

/// Parse a minimal frame (no length, no CRC) from a buffer.
/// Sets status to WaitingForStart or Collecting on failure.
pub fn parse_minimal(
    config: &ProfileConfig,
    buffer: &[u8],
    get_message_info: &dyn Fn(u16) -> Option<MessageInfo>,
) -> FrameMsgInfo {
    let header_size = config.header_size();

    if buffer.len() < header_size {
        return FrameMsgInfo { status: FrameMsgStatus::Collecting, ..FrameMsgInfo::invalid() };
    }

    let mut idx = 0;

    // Verify start bytes
    if config.header.num_start_bytes >= 1 {
        if buffer[idx] != config.computed_start_byte1() {
            return FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() };
        }
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        if buffer[idx] != config.computed_start_byte2() {
            return FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() };
        }
        idx += 1;
    }

    // Read message ID
    let msg_id = buffer[idx] as u16;

    // Get message length from callback
    let info = match get_message_info(msg_id) {
        Some(info) => info,
        None => return FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() },
    };
    let msg_len = info.size;
    let total_size = header_size + msg_len;

    if buffer.len() < total_size {
        return FrameMsgInfo { status: FrameMsgStatus::Collecting, ..FrameMsgInfo::invalid() };
    }

    // Extract payload bytes
    let msg_data = buffer[header_size..header_size + msg_len].to_vec();

    FrameMsgInfo {
        valid: true,
        msg_id,
        msg_len,
        frame_size: total_size,
        msg_data,
        ..Default::default()
    }
}

// =============================================================================
// encode_message_crc / encode_message_minimal — C1: zero-allocation encode
// =============================================================================

/// High-level: encode any StructFrameMessage with CRC using a profile config.
/// Uses variable-length pack() for variable messages (for profiles with length field).
/// C1: packs directly into the output buffer — no intermediate Vec allocation.
pub fn encode_message_crc<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
    pkg_id: u8,
) -> usize {
    // A2: reject msg_id > 255 on profiles that have no pkg_id field
    if !config.payload.has_pkg_id && M::MSG_ID > 255 {
        return 0;
    }

    let actual_pkg_id = if config.payload.has_pkg_id {
        (M::MSG_ID >> 8) as u8
    } else {
        pkg_id
    };
    let msg_id_byte = (M::MSG_ID & 0xFF) as u8;

    // Compute header/footer to find where the payload window starts
    let header_size = config.header_size();
    let footer_size = config.footer_size();
    // We need at least header + MAX_SIZE + footer to guarantee enough room for pack()
    let min_needed = header_size + M::MAX_SIZE + footer_size;
    if buffer.len() < min_needed {
        return 0;
    }

    // Pack directly into the payload window of the output buffer
    let payload_window = &mut buffer[header_size..header_size + M::MAX_SIZE];
    let payload_len = msg.pack(payload_window);

    // A2: payload_len must fit in the length field
    if config.payload.has_length {
        let max_len = max_payload_for_length_bytes(config.payload.length_bytes);
        if payload_len > max_len {
            return 0;
        }
    }

    // Now write header before the payload and CRC after it using the low-level helper.
    // We call encode_with_crc_ext on the full buffer, but the payload was already
    // written into place — copy it to a stack-temp so we can hand the whole buffer to
    // encode_with_crc_ext which expects an empty destination.
    // Rather than a temp copy, we rebuild directly (mirrors encode_with_crc_ext logic):
    let total_size = header_size + payload_len + footer_size;
    let mut idx = 0usize;

    if config.header.num_start_bytes >= 1 {
        buffer[idx] = config.computed_start_byte1();
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        buffer[idx] = config.computed_start_byte2();
        idx += 1;
    }

    let crc_start = idx;

    if config.payload.has_seq { buffer[idx] = 0; idx += 1; }
    if config.payload.has_sys_id { buffer[idx] = 0; idx += 1; }
    if config.payload.has_comp_id { buffer[idx] = 0; idx += 1; }

    if config.payload.has_length {
        if config.payload.length_bytes == 1 {
            buffer[idx] = payload_len as u8; idx += 1;
        } else {
            buffer[idx] = (payload_len & 0xFF) as u8;
            buffer[idx + 1] = ((payload_len >> 8) & 0xFF) as u8;
            idx += 2;
        }
    }

    if config.payload.has_pkg_id { buffer[idx] = actual_pkg_id; idx += 1; }
    buffer[idx] = msg_id_byte; idx += 1;

    // Payload already in place at buffer[header_size..header_size+payload_len]
    debug_assert_eq!(idx, header_size);
    idx += payload_len;

    if config.payload.has_crc {
        let ck = if config.payload.has_length && M::BASE_SIZE < payload_len {
            let overhead_in_crc = idx - crc_start - payload_len;
            let base_end = crc_start + overhead_in_crc + M::BASE_SIZE;
            fletcher_checksum_ext(
                &buffer[crc_start..base_end],
                &buffer[base_end..idx],
                M::MAGIC1,
                M::MAGIC2,
            )
        } else {
            fletcher_checksum(&buffer[crc_start..idx], M::MAGIC1, M::MAGIC2)
        };
        buffer[idx] = ck.byte1;
        buffer[idx + 1] = ck.byte2;
        idx += 2;
    }

    debug_assert_eq!(idx, total_size);
    idx
}

/// High-level: encode any StructFrameMessage minimal (no CRC) using a profile config.
/// Uses fixed-size pack_max_size() so the receiver can determine size without a length field.
/// C1: packs directly into the output buffer — no intermediate Vec allocation.
pub fn encode_message_minimal<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
) -> usize {
    // A2: reject msg_id > 255 when no pkg_id field
    if !config.payload.has_pkg_id && M::MSG_ID > 255 {
        return 0;
    }

    let header_size = config.header_size();
    let total_size = header_size + M::MAX_SIZE;
    if buffer.len() < total_size {
        return 0;
    }

    // Pack directly into the payload window, then write start bytes + msg_id
    let payload_len = msg.pack_max_size(&mut buffer[header_size..header_size + M::MAX_SIZE]);

    let mut idx = 0usize;
    if config.header.num_start_bytes >= 1 {
        buffer[idx] = config.computed_start_byte1();
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        buffer[idx] = config.computed_start_byte2();
        idx += 1;
    }
    buffer[idx] = (M::MSG_ID & 0xFF) as u8;
    idx += 1;

    debug_assert_eq!(idx, header_size);
    idx + payload_len
}

// =============================================================================
// encode_message / parse_frame — config-dispatched entry points
// Matches the Python/TS/C# single-function API: one call, profile decides path.
// =============================================================================

/// Encode any StructFrameMessage using the profile config.
/// Dispatches to encode_message_crc or encode_message_minimal based on config.has_crc.
/// Returns the number of bytes written, or 0 on error.
pub fn encode_message<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
    pkg_id: u8,
) -> usize {
    if config.payload.has_crc {
        encode_message_crc(config, buffer, msg, pkg_id)
    } else {
        encode_message_minimal(config, buffer, msg)
    }
}

/// Parse one frame from a buffer using the profile config.
/// Dispatches to parse_with_crc or parse_minimal based on config.has_crc.
pub fn parse_frame(
    config: &ProfileConfig,
    buffer: &[u8],
    get_message_info: &dyn Fn(u16) -> Option<MessageInfo>,
) -> FrameMsgInfo {
    if config.payload.has_crc {
        parse_with_crc(config, buffer, get_message_info)
    } else {
        parse_minimal(config, buffer, get_message_info)
    }
}

// =============================================================================
// BufferWriter - Encode multiple frames with automatic offset tracking
// =============================================================================

/// Writer for encoding multiple frames into a buffer
pub struct BufferWriter {
    config: ProfileConfig,
    data: Vec<u8>,
    offset: usize,
}

impl BufferWriter {
    pub fn new(config: ProfileConfig, capacity: usize) -> Self {
        BufferWriter {
            config,
            data: vec![0u8; capacity],
            offset: 0,
        }
    }

    /// Write a message (with CRC) to the buffer
    pub fn write_crc<M: StructFrameMessage>(&mut self, msg: &M, pkg_id: u8) -> usize {
        let buf = &mut self.data[self.offset..];
        let written = encode_message_crc(&self.config, buf, msg, pkg_id);
        self.offset += written;
        written
    }

    /// Write a minimal message (no CRC) to the buffer
    pub fn write_minimal<M: StructFrameMessage>(&mut self, msg: &M) -> usize {
        let buf = &mut self.data[self.offset..];
        let written = encode_message_minimal(&self.config, buf, msg);
        self.offset += written;
        written
    }

    /// Get the encoded data
    pub fn data(&self) -> &[u8] {
        &self.data[..self.offset]
    }

    /// Get the number of bytes written
    pub fn size(&self) -> usize {
        self.offset
    }
}

// =============================================================================
// BufferReader - Parse multiple frames from a buffer (B1: advance past bad frames)
// =============================================================================

/// Reader for parsing multiple frames from a buffer
pub struct BufferReader {
    config: ProfileConfig,
    data: Vec<u8>,
    offset: usize,
}

impl BufferReader {
    pub fn new(config: ProfileConfig, data: Vec<u8>) -> Self {
        BufferReader { config, data, offset: 0 }
    }

    /// Get the next frame from the buffer.
    ///
    /// B1: on CRC failure or bad start bytes, advances the internal offset to the next
    /// candidate start-byte position and returns None, so the *next* call can attempt
    /// the following frame.  Only stalls (returns None without advancing) when the
    /// buffer has too little data to make a decision (Collecting status).
    pub fn next(&mut self, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> Option<FrameMsgInfo> {
        if self.offset >= self.data.len() {
            return None;
        }
        let remaining = &self.data[self.offset..];
        let result = if self.config.payload.has_crc {
            parse_with_crc(&self.config, remaining, get_message_info)
        } else {
            parse_minimal(&self.config, remaining, get_message_info)
        };

        if result.valid {
            self.offset += result.frame_size;
            return Some(result);
        }

        // B1: advance past the bad position so the next call starts from the next candidate.
        if result.status != FrameMsgStatus::Collecting {
            let advance = self.find_next_start_byte_offset(remaining).max(1);
            self.offset += advance;
        }
        None
    }

    /// Find the offset of the next possible start-byte sequence within `buf` starting at index 1.
    fn find_next_start_byte_offset(&self, buf: &[u8]) -> usize {
        match self.config.header.header_type {
            HeaderType::None => 1,
            HeaderType::Tiny => {
                let sb = self.config.computed_start_byte1();
                buf[1..].iter().position(|&b| b == sb).map(|p| p + 1).unwrap_or(buf.len())
            }
            HeaderType::Basic => {
                let sb2 = self.config.computed_start_byte2();
                for i in 1..buf.len().saturating_sub(1) {
                    if buf[i] == BASIC_START_BYTE && buf[i + 1] == sb2 {
                        return i;
                    }
                }
                if buf.last() == Some(&BASIC_START_BYTE) {
                    buf.len().saturating_sub(1)
                } else {
                    buf.len()
                }
            }
        }
    }
}

// =============================================================================
// AccumulatingReader - Parse from streaming data
// C2: head-pointer drain (no memmove per frame; compact only at threshold)
// A6: IPC/None-header resync
// A7: buffer overflow cap + early-reject on corrupted length
// =============================================================================

/// Accumulating reader that handles partial messages across buffer boundaries.
pub struct AccumulatingReader {
    config: ProfileConfig,
    buffer: Vec<u8>,
    /// Logical start of unconsumed data.
    head: usize,
    /// Maximum bytes to hold before enforcing overflow policy.
    capacity: usize,
    /// Diagnostic counters (stream mode)
    diagnostics: ParserDiagnostics,
    /// Last seen sequence number for gap detection
    last_seq: Option<u8>,
}

impl AccumulatingReader {
    pub fn new(config: ProfileConfig, capacity: usize) -> Self {
        AccumulatingReader {
            config,
            buffer: Vec::with_capacity(capacity),
            head: 0,
            capacity,
            diagnostics: ParserDiagnostics::default(),
            last_seq: None,
        }
    }

    /// Get a snapshot of the current diagnostic counters.
    pub fn diagnostics(&self) -> ParserDiagnostics {
        self.diagnostics
    }

    /// Reset all diagnostic counters to zero.
    pub fn reset_diagnostics(&mut self) {
        self.diagnostics = ParserDiagnostics::default();
    }

    /// Add data to the internal buffer.
    /// A7: when adding would exceed capacity, compact first; if still full, drop with diagnostic.
    pub fn add_data(&mut self, data: &[u8]) {
        // Compact first to reclaim drained space
        if self.head > 0 {
            self.buffer.drain(..self.head);
            self.head = 0;
        }
        let available = self.capacity.saturating_sub(self.buffer.len());
        if data.len() <= available {
            self.buffer.extend_from_slice(data);
        } else {
            // Partial fill to capacity, drop the rest
            self.buffer.extend_from_slice(&data[..available]);
            let dropped = data.len() - available;
            self.diagnostics.cnt_failed_bytes += dropped as u32;
            self.diagnostics.cnt_sync_recoveries += 1;
        }
    }

    fn buf(&self) -> &[u8] {
        &self.buffer[self.head..]
    }

    /// Compact the buffer if head is past half capacity, to avoid growing indefinitely.
    fn maybe_compact(&mut self) {
        if self.head >= self.capacity / 2 {
            self.buffer.drain(..self.head);
            self.head = 0;
        }
    }

    /// Drain `n` bytes from the logical front of the buffer.
    fn drain_head(&mut self, n: usize) {
        self.head = (self.head + n).min(self.buffer.len());
        self.maybe_compact();
    }

    /// Returns true if the buffer front starts with the expected start-byte sequence
    fn starts_with_possible_frame(&self) -> bool {
        let buf = self.buf();
        if buf.is_empty() {
            return false;
        }
        match self.config.header.header_type {
            HeaderType::None => true,
            HeaderType::Tiny => {
                buf[0] == get_tiny_start_byte(self.config.payload.payload_type as u8)
            }
            HeaderType::Basic => {
                buf.len() >= 2
                    && buf[0] == BASIC_START_BYTE
                    && buf[1] == get_basic_second_start_byte(self.config.payload.payload_type as u8)
            }
        }
    }

    /// Returns the number of bytes to drain to re-align the buffer to the next
    /// possible start-byte position (0 means "wait for more data").
    fn bytes_to_drain_for_resync(&self, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> usize {
        let buf = self.buf();
        if buf.is_empty() {
            return 0;
        }
        match self.config.header.header_type {
            // A6: for None-header profiles, drain 1 on unknown msg_id instead of stalling
            HeaderType::None => {
                if buf.is_empty() {
                    return 0;
                }
                // The msg_id byte is the first byte
                let msg_id = buf[0] as u16;
                match get_message_info(msg_id) {
                    Some(info) => {
                        // Known msg_id — wait until full frame is present
                        let total = 1 + info.size; // header_size=1 (msg_id) for None+Minimal
                        if buf.len() < total { 0 } else { 1 } // resync past this bad frame
                    }
                    None => 1, // Unknown msg_id: drain to search for valid next frame
                }
            }
            HeaderType::Tiny => {
                let start_byte =
                    get_tiny_start_byte(self.config.payload.payload_type as u8);
                if self.starts_with_possible_frame() {
                    if self.config.payload.has_length {
                        let header_size = 1 + self.config.payload.header_size();
                        let footer_size = self.config.footer_size();
                        if buf.len() < header_size {
                            return 0; // Wait for more data
                        }
                        // A7: validate length against get_message_info before waiting
                        let len_offset = 1usize;
                        let msg_len = if self.config.payload.length_bytes == 1 {
                            buf[len_offset] as usize
                        } else {
                            (buf[len_offset] as usize) | ((buf[len_offset + 1] as usize) << 8)
                        };
                        // Peek at msg_id to validate length early
                        if buf.len() >= header_size {
                            let id_offset = 1 + self.config.payload.length_bytes as usize
                                + if self.config.payload.has_pkg_id { 1 } else { 0 };
                            if buf.len() > id_offset {
                                let mut full_id: u16 = 0;
                                let mut off = 1 + self.config.payload.length_bytes as usize;
                                if self.config.payload.has_pkg_id && buf.len() > off {
                                    full_id = (buf[off] as u16) << 8;
                                    off += 1;
                                }
                                if buf.len() > off {
                                    full_id |= buf[off] as u16;
                                    if let Some(info) = get_message_info(full_id) {
                                        // A7: corrupted length → resync immediately
                                        if msg_len > info.size || msg_len < info.min_size {
                                            let search_from = 1;
                                            return buf[search_from..].iter()
                                                .position(|&b| b == start_byte)
                                                .map(|p| search_from + p)
                                                .unwrap_or(buf.len());
                                        }
                                    }
                                }
                            }
                        }
                        if buf.len() < header_size + msg_len + footer_size {
                            return 0; // Wait for more data
                        }
                    } else {
                        // No length field: use get_message_info
                        let header_size = 1 + self.config.payload.header_size();
                        if buf.len() < header_size {
                            return 0;
                        }
                        let msg_id = buf[header_size - 1] as u16;
                        if let Some(info) = get_message_info(msg_id) {
                            let total = header_size + info.size + self.config.footer_size();
                            if buf.len() < total {
                                return 0;
                            }
                            // Full frame present but parse failed — fall through to drain
                        } else {
                            return 1; // Unknown msg_id
                        }
                    }
                }
                let search_from = if self.starts_with_possible_frame() { 1 } else { 0 };
                // D3: removed the dead `self.buffer.last() == Some(&start_byte)` arm;
                // position() already handles the last-byte case correctly.
                buf[search_from..].iter()
                    .position(|&b| b == start_byte)
                    .map(|p| search_from + p)
                    .unwrap_or(buf.len())
            }
            HeaderType::Basic => {
                let second_start =
                    get_basic_second_start_byte(self.config.payload.payload_type as u8);
                if self.starts_with_possible_frame() {
                    if self.config.payload.has_length {
                        let header_size = 2 + self.config.payload.header_size();
                        let footer_size = self.config.footer_size();
                        if buf.len() < header_size {
                            return 0;
                        }
                        let len_offset = 2usize;
                        let msg_len = if self.config.payload.length_bytes == 1 {
                            buf[len_offset] as usize
                        } else {
                            (buf[len_offset] as usize) | ((buf[len_offset + 1] as usize) << 8)
                        };
                        // A7: validate length against get_message_info
                        if buf.len() >= header_size {
                            let mut off = 2 + self.config.payload.length_bytes as usize;
                            if self.config.payload.has_pkg_id && buf.len() > off {
                                let pkg = (buf[off] as u16) << 8;
                                off += 1;
                                if buf.len() > off {
                                    let full_id = pkg | buf[off] as u16;
                                    if let Some(info) = get_message_info(full_id) {
                                        if msg_len > info.size || msg_len < info.min_size {
                                            return Self::scan_for_basic_start(&buf[1..], second_start)
                                                .map(|p| p + 1)
                                                .unwrap_or(buf.len());
                                        }
                                    }
                                }
                            } else if buf.len() > off {
                                let full_id = buf[off] as u16;
                                if let Some(info) = get_message_info(full_id) {
                                    if msg_len > info.size || msg_len < info.min_size {
                                        return Self::scan_for_basic_start(&buf[1..], second_start)
                                            .map(|p| p + 1)
                                            .unwrap_or(buf.len());
                                    }
                                }
                            }
                        }
                        if buf.len() < header_size + msg_len + footer_size {
                            return 0;
                        }
                    } else {
                        // D2: no-length Basic header — mirror Tiny logic with get_message_info
                        let header_size = 2 + self.config.payload.header_size();
                        if buf.len() < header_size {
                            return 0;
                        }
                        let msg_id = buf[header_size - 1] as u16;
                        if let Some(info) = get_message_info(msg_id) {
                            let total = header_size + info.size + self.config.footer_size();
                            if buf.len() < total {
                                return 0;
                            }
                            // Full frame present but parse failed — fall through to scan
                        } else {
                            // Unknown msg_id: scan for next start pair
                            return Self::scan_for_basic_start(&buf[1..], second_start)
                                .map(|p| p + 1)
                                .unwrap_or(buf.len());
                        }
                    }
                }
                let search_from = if self.starts_with_possible_frame() { 1 } else { 0 };
                Self::scan_for_basic_start(&buf[search_from..], second_start)
                    .map(|p| search_from + p)
                    .unwrap_or(buf.len())
            }
        }
    }

    fn scan_for_basic_start(buf: &[u8], second_start: u8) -> Option<usize> {
        for i in 0..buf.len().saturating_sub(1) {
            if buf[i] == BASIC_START_BYTE && buf[i + 1] == second_start {
                return Some(i);
            }
        }
        if buf.last() == Some(&BASIC_START_BYTE) {
            Some(buf.len().saturating_sub(1))
        } else {
            None
        }
    }

    /// Push a single byte and attempt to extract a complete frame.
    /// Returns `Some(FrameMsgInfo)` as soon as a frame is available.
    pub fn push_byte(&mut self, byte: u8, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> Option<FrameMsgInfo> {
        self.add_data(&[byte]);
        self.next(get_message_info)
    }

    /// Get the next complete frame, or None if not enough data yet.
    /// Automatically re-synchronizes past noise or partial frames.
    pub fn next(&mut self, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> Option<FrameMsgInfo> {
        loop {
            if self.buf().is_empty() {
                return None;
            }

            let result = if self.config.payload.has_crc {
                parse_with_crc(&self.config, self.buf(), get_message_info)
            } else {
                parse_minimal(&self.config, self.buf(), get_message_info)
            };

            if result.valid {
                let frame_size = result.frame_size;

                // Check for sequence gap on profiles that carry a sequence number
                if self.config.payload.has_seq {
                    let seq = self.buf()[self.config.header.num_start_bytes as usize];
                    if let Some(last) = self.last_seq {
                        if seq != last.wrapping_add(1) {
                            self.diagnostics.cnt_seq_gaps += 1;
                        }
                    }
                    self.last_seq = Some(seq);
                }

                self.drain_head(frame_size);
                return Some(result);
            }

            let bytes_to_drain = self.bytes_to_drain_for_resync(get_message_info);
            if bytes_to_drain == 0 {
                return None;
            }

            // Record diagnostics before draining
            if self.starts_with_possible_frame() {
                // A8: only fire cnt_len_errors when the length is genuinely wrong
                if self.config.payload.has_length {
                    let buf = self.buf();
                    let header_size = self.config.header_size();
                    if buf.len() >= header_size {
                        let mut len_offset = self.config.header.num_start_bytes as usize;
                        if self.config.payload.has_seq { len_offset += 1; }
                        if self.config.payload.has_sys_id { len_offset += 1; }
                        if self.config.payload.has_comp_id { len_offset += 1; }
                        let msg_len = if self.config.payload.length_bytes == 1 {
                            buf[len_offset] as usize
                        } else {
                            (buf[len_offset] as usize) | ((buf[len_offset + 1] as usize) << 8)
                        };
                        let mut id_offset = len_offset + self.config.payload.length_bytes as usize;
                        let mut full_msg_id: u16 = 0;
                        if self.config.payload.has_pkg_id && buf.len() > id_offset {
                            full_msg_id = (buf[id_offset] as u16) << 8;
                            id_offset += 1;
                        }
                        if buf.len() > id_offset {
                            full_msg_id |= buf[id_offset] as u16;
                            if let Some(info) = get_message_info(full_msg_id) {
                                // A8: mirrors C++ / TS fix — only error on out-of-range
                                if msg_len > info.size || msg_len < info.min_size {
                                    self.diagnostics.cnt_len_errors += 1;
                                }
                            }
                        }
                    }
                }

                if result.status == FrameMsgStatus::CrcFailure {
                    self.diagnostics.cnt_crc_failures += 1;
                }
            }

            self.diagnostics.cnt_failed_bytes += bytes_to_drain as u32;
            self.diagnostics.cnt_sync_recoveries += 1;
            self.drain_head(bytes_to_drain);
        }
    }
}

// =============================================================================
// Profile-specific type aliases
// =============================================================================

/// Create a standard profile writer
pub fn new_standard_writer(capacity: usize) -> BufferWriter {
    BufferWriter::new(PROFILE_STANDARD_CONFIG, capacity)
}

/// Create a sensor profile writer
pub fn new_sensor_writer(capacity: usize) -> BufferWriter {
    BufferWriter::new(PROFILE_SENSOR_CONFIG, capacity)
}

/// Create an IPC profile writer
pub fn new_ipc_writer(capacity: usize) -> BufferWriter {
    BufferWriter::new(PROFILE_IPC_CONFIG, capacity)
}

/// Create a bulk profile writer
pub fn new_bulk_writer(capacity: usize) -> BufferWriter {
    BufferWriter::new(PROFILE_BULK_CONFIG, capacity)
}

/// Create a network profile writer
pub fn new_network_writer(capacity: usize) -> BufferWriter {
    BufferWriter::new(PROFILE_NETWORK_CONFIG, capacity)
}

/// Create a standard profile accumulating reader
pub fn new_standard_reader(capacity: usize) -> AccumulatingReader {
    AccumulatingReader::new(PROFILE_STANDARD_CONFIG, capacity)
}

/// Create a sensor profile accumulating reader
pub fn new_sensor_reader(capacity: usize) -> AccumulatingReader {
    AccumulatingReader::new(PROFILE_SENSOR_CONFIG, capacity)
}

/// Create an IPC profile accumulating reader
pub fn new_ipc_reader(capacity: usize) -> AccumulatingReader {
    AccumulatingReader::new(PROFILE_IPC_CONFIG, capacity)
}

/// Create a bulk profile accumulating reader
pub fn new_bulk_reader(capacity: usize) -> AccumulatingReader {
    AccumulatingReader::new(PROFILE_BULK_CONFIG, capacity)
}

/// Create a network profile accumulating reader
pub fn new_network_reader(capacity: usize) -> AccumulatingReader {
    AccumulatingReader::new(PROFILE_NETWORK_CONFIG, capacity)
}
