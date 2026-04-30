// Payload Types - Payload format configurations (Rust)
// Mirrors payload_types.h from C boilerplate

/// Payload type identifier (encoded in the start byte)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum PayloadType {
    Minimal = 0,
    Default = 1,
    SysComp = 2,
    Seq = 3,
    MultiSystemStream = 4,
    Extended = 5,
    ExtendedMinimal = 6,
    ExtendedMultiSystemStream = 8,
}

/// Payload configuration
#[derive(Debug, Clone, Copy)]
pub struct PayloadConfig {
    pub payload_type: PayloadType,
    pub has_length: bool,
    pub length_bytes: u8,
    pub has_crc: bool,
    pub has_pkg_id: bool,
    pub has_seq: bool,
    pub has_sys_id: bool,
    pub has_comp_id: bool,
}

impl PayloadConfig {
    /// Size of header portion (length + optional fields + msg_id)
    pub fn header_size(&self) -> usize {
        let mut size = 0usize;
        if self.has_seq { size += 1; }
        if self.has_sys_id { size += 1; }
        if self.has_comp_id { size += 1; }
        if self.has_length { size += self.length_bytes as usize; }
        if self.has_pkg_id { size += 1; }
        size += 1; // msg_id (always 1 byte)
        size
    }

    /// Size of footer (CRC bytes)
    pub fn footer_size(&self) -> usize {
        if self.has_crc { 2 } else { 0 }
    }
}

// Pre-defined payload configurations

/// Minimal payload: [MSG_ID] [PAYLOAD] (no length, no CRC)
pub const PAYLOAD_MINIMAL_CONFIG: PayloadConfig = PayloadConfig {
    payload_type: PayloadType::Minimal,
    has_length: false,
    length_bytes: 0,
    has_crc: false,
    has_pkg_id: false,
    has_seq: false,
    has_sys_id: false,
    has_comp_id: false,
};

/// Default payload: [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
pub const PAYLOAD_DEFAULT_CONFIG: PayloadConfig = PayloadConfig {
    payload_type: PayloadType::Default,
    has_length: true,
    length_bytes: 1,
    has_crc: true,
    has_pkg_id: false,
    has_seq: false,
    has_sys_id: false,
    has_comp_id: false,
};

/// Extended payload: [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
pub const PAYLOAD_EXTENDED_CONFIG: PayloadConfig = PayloadConfig {
    payload_type: PayloadType::Extended,
    has_length: true,
    length_bytes: 2,
    has_crc: true,
    has_pkg_id: true,
    has_seq: false,
    has_sys_id: false,
    has_comp_id: false,
};

/// ExtendedMultiSystemStream: [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
pub const PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG: PayloadConfig = PayloadConfig {
    payload_type: PayloadType::ExtendedMultiSystemStream,
    has_length: true,
    length_bytes: 2,
    has_crc: true,
    has_pkg_id: true,
    has_seq: true,
    has_sys_id: true,
    has_comp_id: true,
};
