// System frames: struct-frame's own messages (heartbeat, ping, link tests, RPC).
//
// A system frame uses the header of the profile it travels with (Basic or Tiny; profiles
// without start bytes cannot carry system frames) followed by a fixed payload layout:
//
//     [start bytes][SEQ][SYS][COMP][LEN lo][LEN hi][SYS_MSG_ID] payload [CRC1][CRC2]
//
// The second start byte (Basic) or the start byte (Tiny) is 0x79: payload type 9. System
// message ids are a separate id space (see `sf_system`), so they never collide with
// application messages. The CRC is the usual Fletcher-16 with the system message's magic
// bytes mixed in after the data. Some system messages carry a raw tail after their fixed
// fields (ping padding, link-test data, RPC payloads); its length is the frame length minus
// the message's fixed size.

use crate::frame_base::{fletcher_checksum, FrameMsgInfo, FrameMsgStatus, MessageInfo, StructFrameMessage};
use crate::frame_headers::{BASIC_START_BYTE, PAYLOAD_TYPE_BASE};
use crate::frame_profiles::{parse_with_crc, ProfileConfig};
use crate::payload_types::PAYLOAD_SYSTEM_CONFIG;
use crate::sf_system;

/// Payload type of system frames.
pub const PAYLOAD_TYPE_VALUE: u8 = 9;
/// Start byte of system frames (after a Basic header's 0x90, or alone for a Tiny header).
pub const START_BYTE: u8 = PAYLOAD_TYPE_BASE + PAYLOAD_TYPE_VALUE;
/// Largest tail accepted after a system message's fixed fields.
pub const MAX_TAIL: usize = sf_system::MAX_TAIL as usize;

/// System message ids that may carry a tail.
pub const TAIL_MESSAGES: [u16; 5] = [
    <sf_system::Ping as StructFrameMessage>::MSG_ID,
    <sf_system::Pong as StructFrameMessage>::MSG_ID,
    <sf_system::LinkTestData as StructFrameMessage>::MSG_ID,
    <sf_system::RpcRequest as StructFrameMessage>::MSG_ID,
    <sf_system::RpcResponse as StructFrameMessage>::MSG_ID,
];

/// True when frames of `config` can be told apart from system frames: the header carries
/// the payload type in a start byte (Basic and Tiny headers).
#[inline]
pub fn supports(config: &ProfileConfig) -> bool {
    config.header.encodes_payload_type && config.header.num_start_bytes >= 1
}

/// The system-frame profile for the header of `config`, or None when it cannot carry
/// system frames.
#[inline]
pub fn config_for(config: &ProfileConfig) -> Option<ProfileConfig> {
    if supports(config) {
        Some(ProfileConfig::new(config.header, PAYLOAD_SYSTEM_CONFIG))
    } else {
        None
    }
}

/// Size limits and magic bytes of a system message, for the frame readers. `min_size` is the
/// fixed size; `size` also allows a tail for the messages that take one; `base_size == size`
/// so the CRC is never extension-split.
pub fn message_info(msg_id: u16) -> Option<MessageInfo> {
    let info = sf_system::get_message_info(msg_id)?;
    let fixed = info.size;
    let largest = fixed + if TAIL_MESSAGES.contains(&msg_id) { MAX_TAIL } else { 0 };
    Some(MessageInfo::new_variable(largest, info.magic1, info.magic2, largest, fixed))
}

/// Encode a system message (and its tail) as a system frame for the header of `config`.
/// Returns the frame size, or 0 when the profile cannot carry system frames, `M` is not a
/// system message, the message takes no tail but one was given, the tail is too long or
/// the buffer too small.
pub fn encode<M: StructFrameMessage>(
    config: &ProfileConfig,
    buffer: &mut [u8],
    msg: &M,
    tail: &[u8],
    seq: u8,
    sys_id: u8,
    comp_id: u8,
) -> usize {
    let sys = match config_for(config) {
        Some(sys) => sys,
        None => return 0,
    };
    let info = match message_info(M::MSG_ID) {
        Some(info) if info.min_size == M::MAX_SIZE && info.magic1 == M::MAGIC1 && info.magic2 == M::MAGIC2 => info,
        _ => return 0,
    };
    if tail.len() > info.size - info.min_size {
        return 0;
    }
    let header_size = sys.header_size();
    let payload_len = M::MAX_SIZE + tail.len();
    let total = sys.overhead() + payload_len;
    if buffer.len() < total {
        return 0;
    }
    let mut idx = 0;
    buffer[idx] = sys.computed_start_byte1();
    idx += 1;
    if sys.header.num_start_bytes >= 2 {
        buffer[idx] = sys.computed_start_byte2();
        idx += 1;
    }
    let crc_start = idx;
    buffer[idx] = seq;
    buffer[idx + 1] = sys_id;
    buffer[idx + 2] = comp_id;
    buffer[idx + 3] = (payload_len & 0xFF) as u8;
    buffer[idx + 4] = ((payload_len >> 8) & 0xFF) as u8;
    buffer[idx + 5] = M::MSG_ID as u8;
    idx = header_size;
    let written = msg.pack_max_size(&mut buffer[idx..idx + M::MAX_SIZE]);
    if written != M::MAX_SIZE {
        return 0;
    }
    idx += M::MAX_SIZE;
    buffer[idx..idx + tail.len()].copy_from_slice(tail);
    idx += tail.len();
    let ck = fletcher_checksum(&buffer[crc_start..idx], M::MAGIC1, M::MAGIC2);
    buffer[idx] = ck.byte1;
    buffer[idx + 1] = ck.byte2;
    idx + 2
}

/// The fixed fields and the tail of a valid system frame returned by a reader
/// (`frame.is_system`), or None when it is not one.
pub fn split(frame: &FrameMsgInfo) -> Option<(&[u8], &[u8])> {
    if !frame.valid || !frame.is_system {
        return None;
    }
    let info = message_info(frame.msg_id)?;
    if frame.msg_data.len() < info.min_size {
        return None;
    }
    Some(frame.msg_data.split_at(info.min_size))
}

/// Decode the system message `M` and the tail of a valid system frame.
pub fn decode<M: StructFrameMessage>(frame: &FrameMsgInfo) -> Option<(M, Vec<u8>)> {
    if frame.msg_id != M::MSG_ID {
        return None;
    }
    let (fixed, tail) = split(frame)?;
    Some((M::unpack(fixed)?, tail.to_vec()))
}

// ---------------------------------------------------------------------------------
// Helpers shared by the readers
// ---------------------------------------------------------------------------------

/// True when `data` starts with the start bytes of a system frame of `sys`.
#[inline]
pub(crate) fn is_system_start(sys: Option<&ProfileConfig>, data: &[u8]) -> bool {
    match sys {
        None => false,
        Some(sys) => {
            if data.is_empty() || data[0] != sys.computed_start_byte1() {
                return false;
            }
            if sys.header.num_start_bytes >= 2 {
                data.len() >= 2 && data[1] == sys.computed_start_byte2()
            } else {
                true
            }
        }
    }
}

/// Check the header of a candidate system frame: Some(true) when the system message id is
/// known and the length fits it, Some(false) when not, None while the header is incomplete.
pub(crate) fn header_ok(sys: &ProfileConfig, data: &[u8]) -> Option<bool> {
    let hs = sys.header_size();
    if data.len() < hs {
        return None;
    }
    let off = sys.header.num_start_bytes as usize + 3; // after SEQ, SYS, COMP
    let length = data[off] as usize | ((data[off + 1] as usize) << 8);
    Some(match message_info(data[hs - 1] as u16) {
        Some(info) => length >= info.min_size && length <= info.size,
        None => false,
    })
}

/// Parse a frame known to start with system start bytes.
pub(crate) fn parse(sys: &ProfileConfig, data: &[u8]) -> FrameMsgInfo {
    let mut result = if header_ok(sys, data) == Some(false) {
        FrameMsgInfo { status: FrameMsgStatus::WaitingForStart, ..FrameMsgInfo::invalid() }
    } else {
        parse_with_crc(sys, data, &message_info)
    };
    result.is_system = true;
    result
}

/// Offset (>= `from`) of the next byte in `buf` that can start a system frame of `sys`, or
/// None. A trailing 0x90 counts for a Basic header (its second byte has not arrived yet).
pub(crate) fn next_start(sys: Option<&ProfileConfig>, buf: &[u8], from: usize) -> Option<usize> {
    let sys = sys?;
    if from >= buf.len() {
        return None;
    }
    if sys.header.num_start_bytes >= 2 {
        let sb2 = sys.computed_start_byte2();
        let mut i = from;
        while i < buf.len() {
            if buf[i] == BASIC_START_BYTE && (i + 1 == buf.len() || buf[i + 1] == sb2) {
                return Some(i);
            }
            i += 1;
        }
        None
    } else {
        let sb1 = sys.computed_start_byte1();
        buf[from..].iter().position(|&b| b == sb1).map(|p| from + p)
    }
}
