// Frame Profiles - Pre-defined Header + Payload combinations (Rust)
// Mirrors frame_profiles.h from C boilerplate

use crate::frame_base::{fletcher_checksum, fletcher_checksum_ext, FrameChecksum, FrameMsgInfo, MessageInfo, StructFrameMessage};
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

/// Encode a message with CRC into a buffer.
///
/// Returns the number of bytes written, or 0 on error.
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

    // Calculate and write CRC (extension-aware; base_size defaults to full payload)
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

/// Parse a frame with CRC from a buffer.
///
/// Returns FrameMsgInfo with valid=true if parsing succeeded.
pub fn parse_with_crc(
    config: &ProfileConfig,
    buffer: &[u8],
    get_message_info: &dyn Fn(u16) -> Option<MessageInfo>,
) -> FrameMsgInfo {
    let header_size = config.header_size();
    let footer_size = config.footer_size();
    let overhead = header_size + footer_size;

    if buffer.len() < overhead {
        return FrameMsgInfo::invalid();
    }

    let mut idx = 0;

    // Verify start bytes
    if config.header.num_start_bytes >= 1 {
        if buffer[idx] != config.computed_start_byte1() {
            return FrameMsgInfo::invalid();
        }
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        if buffer[idx] != config.computed_start_byte2() {
            return FrameMsgInfo::invalid();
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

    // Read message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id)
    let mut msg_id: u16 = 0;
    let mut pkg_id: u8 = 0;
    if config.payload.has_pkg_id {
        pkg_id = buffer[idx];
        msg_id = (buffer[idx] as u16) << 8;
        idx += 1;
    }
    msg_id |= buffer[idx] as u16;
    let _ = idx;  // idx no longer needed after reading msg_id

    // Verify total size
    let total_size = overhead + msg_len;
    if buffer.len() < total_size {
        return FrameMsgInfo::invalid();
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
            return FrameMsgInfo::invalid();
        }
    }

    // Extract payload bytes
    let payload = buffer[header_size..header_size + msg_len].to_vec();

    FrameMsgInfo {
        valid: true,
        msg_id,
        msg_len,
        frame_size: total_size,
        package_id: pkg_id,
        sequence: seq,
        system_id: sys_id,
        component_id: comp_id,
        payload,
    }
}

/// Parse a minimal frame (no length, no CRC) from a buffer.
pub fn parse_minimal(
    config: &ProfileConfig,
    buffer: &[u8],
    get_message_info: &dyn Fn(u16) -> Option<MessageInfo>,
) -> FrameMsgInfo {
    let header_size = config.header_size();

    if buffer.len() < header_size {
        return FrameMsgInfo::invalid();
    }

    let mut idx = 0;

    // Verify start bytes
    if config.header.num_start_bytes >= 1 {
        if buffer[idx] != config.computed_start_byte1() {
            return FrameMsgInfo::invalid();
        }
        idx += 1;
    }
    if config.header.num_start_bytes >= 2 {
        if buffer[idx] != config.computed_start_byte2() {
            return FrameMsgInfo::invalid();
        }
        idx += 1;
    }

    // Read message ID
    let msg_id = buffer[idx] as u16;

    // Get message length from callback
    let info = match get_message_info(msg_id) {
        Some(info) => info,
        None => return FrameMsgInfo::invalid(),
    };
    let msg_len = info.size;
    let total_size = header_size + msg_len;

    if buffer.len() < total_size {
        return FrameMsgInfo::invalid();
    }

    // Extract payload bytes
    let payload = buffer[header_size..header_size + msg_len].to_vec();

    FrameMsgInfo {
        valid: true,
        msg_id,
        msg_len,
        frame_size: total_size,
        payload,
        ..Default::default()
    }
}

/// High-level: encode any StructFrameMessage with CRC using a profile config.
/// Uses variable-length pack() for variable messages (for profiles with length field).
pub fn encode_message_crc<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
    pkg_id: u8,
) -> usize {
    let mut payload = vec![0u8; M::MAX_SIZE];
    // Variable messages use pack() (variable-length); profiles with has_length support this.
    // Fixed messages: pack() == pack_max_size().
    let payload_len = msg.pack(&mut payload);
    // When the profile encodes a pkg_id field, derive it from the high byte of MSG_ID,
    // mirroring C++: buffer[idx++] = (T::MSG_ID >> 8) & 0xFF.
    // The caller-supplied pkg_id is only used for profiles without a pkg_id field.
    let actual_pkg_id = if config.payload.has_pkg_id {
        (M::MSG_ID >> 8) as u8
    } else {
        pkg_id
    };
    encode_with_crc_ext(
        config,
        buffer,
        0,
        0,
        0,
        actual_pkg_id,
        (M::MSG_ID & 0xFF) as u8,
        &payload[..payload_len],
        M::MAGIC1,
        M::MAGIC2,
        M::BASE_SIZE,
    )
}

/// High-level: encode any StructFrameMessage minimal (no CRC) using a profile config.
/// Uses fixed-size pack_max_size() so the receiver can determine size without a length field.
pub fn encode_message_minimal<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
) -> usize {
    let mut payload = vec![0u8; M::MAX_SIZE];
    // Minimal profiles have no length field: receiver uses MAX_SIZE, so must send fixed-size payload.
    let payload_len = msg.pack_max_size(&mut payload);
    encode_minimal(config, buffer, (M::MSG_ID & 0xFF) as u8, &payload[..payload_len])
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
// BufferReader - Parse multiple frames from a buffer
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

    /// Get the next frame from the buffer
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
            Some(result)
        } else {
            None
        }
    }
}

// =============================================================================
// AccumulatingReader - Parse from streaming data
// =============================================================================

/// Accumulating reader that handles partial messages across buffer boundaries
pub struct AccumulatingReader {
    config: ProfileConfig,
    buffer: Vec<u8>,
}

impl AccumulatingReader {
    pub fn new(config: ProfileConfig, capacity: usize) -> Self {
        AccumulatingReader {
            config,
            buffer: Vec::with_capacity(capacity),
        }
    }

    /// Add data to the internal buffer
    pub fn add_data(&mut self, data: &[u8]) {
        self.buffer.extend_from_slice(data);
    }

    /// Returns true if the buffer starts with the expected start-byte sequence
    fn starts_with_possible_frame(&self) -> bool {
        if self.buffer.is_empty() {
            return false;
        }
        match self.config.header.header_type {
            HeaderType::None => true,
            HeaderType::Tiny => {
                self.buffer[0] == get_tiny_start_byte(self.config.payload.payload_type as u8)
            }
            HeaderType::Basic => {
                self.buffer.len() >= 2
                    && self.buffer[0] == BASIC_START_BYTE
                    && self.buffer[1]
                        == get_basic_second_start_byte(self.config.payload.payload_type as u8)
            }
        }
    }

    /// Returns the number of bytes to drain to re-align the buffer to the next
    /// possible start-byte position (0 means "wait for more data").
    fn bytes_to_drain_for_resync(&self, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> usize {
        if self.buffer.is_empty() {
            return 0;
        }
        match self.config.header.header_type {
            HeaderType::None => 0,
            HeaderType::Tiny => {
                let start_byte =
                    get_tiny_start_byte(self.config.payload.payload_type as u8);
                // If buffer starts with valid start byte, check if we might just
                // need more data before deciding to drain.
                if self.starts_with_possible_frame() {
                    if self.config.payload.has_length {
                        let header_size = 1 + self.config.payload.header_size();
                        let footer_size = self.config.footer_size();
                        if self.buffer.len() < header_size {
                            return 0; // Too early to determine frame size - wait for more data
                        }
                        let len_offset = 1usize; // after 1 start byte
                        let msg_len = if self.config.payload.length_bytes == 1 {
                            self.buffer[len_offset] as usize
                        } else {
                            (self.buffer[len_offset] as usize)
                                | ((self.buffer[len_offset + 1] as usize) << 8)
                        };
                        if self.buffer.len() < header_size + msg_len + footer_size {
                            return 0; // Not enough data for full frame - wait for more
                        }
                    } else {
                        // No length field: need get_message_info to determine payload size.
                        // The header is start_byte(s) + msg_id byte(s).
                        let header_size = 1 + self.config.payload.header_size(); // start + payload_header
                        if self.buffer.len() < header_size {
                            return 0; // Haven't received the msg_id byte yet – wait
                        }
                        // msg_id is the last byte of the header (after start byte(s))
                        let msg_id = self.buffer[header_size - 1] as u16;
                        if let Some(info) = get_message_info(msg_id) {
                            // Valid msg_id: we know total frame size; wait if incomplete
                            let total = header_size + info.size + self.config.footer_size();
                            if self.buffer.len() < total {
                                return 0; // Wait for payload (+ CRC if any) to arrive
                            }
                            // Full frame is present but parse still failed (e.g. bad CRC).
                            // Fall through to drain past this start byte.
                        } else {
                            // Unknown msg_id: this start byte is not the beginning of a
                            // valid frame.  Drain past it.
                            return 1;
                        }
                    }
                }
                // Search from index 1 if index 0 already is the start byte (that parse
                // failed, so skip past it), otherwise from index 0.
                let search_from = if self.starts_with_possible_frame() { 1 } else { 0 };
                if let Some(pos) = self.buffer[search_from..]
                    .iter()
                    .position(|&b| b == start_byte)
                {
                    search_from + pos
                } else if self.buffer.last() == Some(&start_byte) {
                    self.buffer.len().saturating_sub(1)
                } else {
                    self.buffer.len()
                }
            }
            HeaderType::Basic => {
                let second_start =
                    get_basic_second_start_byte(self.config.payload.payload_type as u8);
                // If buffer starts with valid start bytes, check if we might just
                // need more data before deciding to drain.
                if self.starts_with_possible_frame() && self.config.payload.has_length {
                    let header_size = 2 + self.config.payload.header_size();
                    let footer_size = self.config.footer_size();
                    if self.buffer.len() < header_size {
                        return 0; // Too early to determine frame size - wait for more data
                    }
                    let len_offset = 2usize; // after 2 start bytes
                    let msg_len = if self.config.payload.length_bytes == 1 {
                        self.buffer[len_offset] as usize
                    } else {
                        (self.buffer[len_offset] as usize)
                            | ((self.buffer[len_offset + 1] as usize) << 8)
                    };
                    if self.buffer.len() < header_size + msg_len + footer_size {
                        return 0; // Not enough data for full frame - wait for more
                    }
                }
                let search_from = if self.starts_with_possible_frame() { 1 } else { 0 };
                for idx in search_from..self.buffer.len().saturating_sub(1) {
                    if self.buffer[idx] == BASIC_START_BYTE
                        && self.buffer[idx + 1] == second_start
                    {
                        return idx;
                    }
                }
                if self.buffer.last() == Some(&BASIC_START_BYTE) {
                    self.buffer.len().saturating_sub(1)
                } else {
                    self.buffer.len()
                }
            }
        }
    }

    /// Push a single byte and attempt to extract a complete frame.
    /// Returns `Some(FrameMsgInfo)` as soon as a frame is available.
    /// Equivalent to calling `add_data(&[byte])` then `next(...)`.
    pub fn push_byte(&mut self, byte: u8, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> Option<FrameMsgInfo> {
        self.add_data(&[byte]);
        self.next(get_message_info)
    }

    /// Get the next complete frame, or None if not enough data yet.
    /// Automatically re-synchronizes past noise or partial frames.
    pub fn next(&mut self, get_message_info: &dyn Fn(u16) -> Option<MessageInfo>) -> Option<FrameMsgInfo> {
        loop {
            if self.buffer.is_empty() {
                return None;
            }

            let result = if self.config.payload.has_crc {
                parse_with_crc(&self.config, &self.buffer, get_message_info)
            } else {
                parse_minimal(&self.config, &self.buffer, get_message_info)
            };

            if result.valid {
                let frame_size = result.frame_size;
                self.buffer.drain(..frame_size);
                return Some(result);
            }

            let bytes_to_drain = self.bytes_to_drain_for_resync(get_message_info);
            if bytes_to_drain == 0 {
                return None;
            }
            self.buffer.drain(..bytes_to_drain);
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
