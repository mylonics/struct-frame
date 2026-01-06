/* Frame Profiles - Pre-defined Header + Payload combinations */
/* 
 * This file provides ready-to-use encode/parse functions for frame format profiles.
 * It uses C++ templates for maximum code reuse with zero runtime overhead.
 *
 * Standard Profiles:
 * - ProfileStandard: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 */

#pragma once

#include "frame_base.hpp"
#include "frame_headers/base.hpp"
#include "frame_headers/header_basic.hpp"
#include "frame_headers/header_tiny.hpp"
#include "frame_headers/header_none.hpp"
#include "payload_types/base.hpp"
#include "payload_types/payload_default.hpp"
#include "payload_types/payload_minimal.hpp"
#include "payload_types/payload_extended.hpp"
#include "payload_types/payload_extended_multi_system_stream.hpp"

namespace FrameParsers {

/*===========================================================================
 * Frame Format Configuration Template
 *===========================================================================*/

/**
 * Frame format configuration - combines header type with payload type
 * Template parameters define the frame structure at compile time.
 */
template<
    uint8_t NumStartBytes,
    uint8_t StartByte1,
    uint8_t StartByte2,
    uint8_t HeaderSize,
    uint8_t FooterSize,
    bool HasLength,
    uint8_t LengthBytes,
    bool HasCrc,
    bool HasPkgId,
    bool HasSeq,
    bool HasSysId,
    bool HasCompId
>
struct FrameFormatConfig {
    static constexpr uint8_t num_start_bytes = NumStartBytes;
    static constexpr uint8_t start_byte1 = StartByte1;
    static constexpr uint8_t start_byte2 = StartByte2;
    static constexpr uint8_t header_size = HeaderSize;
    static constexpr uint8_t footer_size = FooterSize;
    static constexpr bool has_length = HasLength;
    static constexpr uint8_t length_bytes = LengthBytes;
    static constexpr bool has_crc = HasCrc;
    static constexpr bool has_pkg_id = HasPkgId;
    static constexpr bool has_seq = HasSeq;
    static constexpr bool has_sys_id = HasSysId;
    static constexpr bool has_comp_id = HasCompId;
    static constexpr size_t overhead = HeaderSize + FooterSize;
    static constexpr size_t max_payload = (LengthBytes == 1) ? 255 : 65535;
};

/*===========================================================================
 * Generic Frame Encoder/Parser Templates
 *===========================================================================*/

/**
 * Generic frame encoder for frames with CRC
 */
template<typename Config>
class FrameEncoderWithCrc {
public:
    static size_t encode(uint8_t* buffer, size_t buffer_size,
                        uint8_t seq, uint8_t sys_id, uint8_t comp_id,
                        uint8_t pkg_id, uint8_t msg_id,
                        const uint8_t* payload, size_t payload_size) {
        
        size_t total_size = Config::overhead + payload_size;
        
        if (buffer_size < total_size || payload_size > Config::max_payload) {
            return 0;
        }
        
        size_t idx = 0;
        
        // Write start bytes
        if constexpr (Config::num_start_bytes >= 1) {
            buffer[idx++] = Config::start_byte1;
        }
        if constexpr (Config::num_start_bytes >= 2) {
            buffer[idx++] = Config::start_byte2;
        }
        
        size_t crc_start = idx;
        
        // Write optional fields before length
        if constexpr (Config::has_seq) {
            buffer[idx++] = seq;
        }
        if constexpr (Config::has_sys_id) {
            buffer[idx++] = sys_id;
        }
        if constexpr (Config::has_comp_id) {
            buffer[idx++] = comp_id;
        }
        
        // Write length field
        if constexpr (Config::has_length) {
            if constexpr (Config::length_bytes == 1) {
                buffer[idx++] = static_cast<uint8_t>(payload_size & 0xFF);
            } else {
                buffer[idx++] = static_cast<uint8_t>(payload_size & 0xFF);
                buffer[idx++] = static_cast<uint8_t>((payload_size >> 8) & 0xFF);
            }
        }
        
        // Write package ID if present
        if constexpr (Config::has_pkg_id) {
            buffer[idx++] = pkg_id;
        }
        
        // Write message ID
        buffer[idx++] = msg_id;
        
        // Write payload
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + idx, payload, payload_size);
            idx += payload_size;
        }
        
        // Calculate and write CRC
        if constexpr (Config::has_crc) {
            size_t crc_len = idx - crc_start;
            FrameChecksum ck = fletcher_checksum(buffer + crc_start, crc_len);
            buffer[idx++] = ck.byte1;
            buffer[idx++] = ck.byte2;
        }
        
        return idx;
    }
};

/**
 * Generic frame encoder for minimal frames (no length, no CRC)
 */
template<typename Config>
class FrameEncoderMinimal {
public:
    static size_t encode(uint8_t* buffer, size_t buffer_size,
                        uint8_t msg_id,
                        const uint8_t* payload, size_t payload_size) {
        
        size_t total_size = Config::overhead + payload_size;
        
        if (buffer_size < total_size) {
            return 0;
        }
        
        size_t idx = 0;
        
        // Write start bytes
        if constexpr (Config::num_start_bytes >= 1) {
            buffer[idx++] = Config::start_byte1;
        }
        if constexpr (Config::num_start_bytes >= 2) {
            buffer[idx++] = Config::start_byte2;
        }
        
        // Write message ID
        buffer[idx++] = msg_id;
        
        // Write payload
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + idx, payload, payload_size);
            idx += payload_size;
        }
        
        return idx;
    }
};

/**
 * Generic frame parser for frames with CRC
 */
template<typename Config>
class FrameParserWithCrc {
public:
    static FrameMsgInfo parse(const uint8_t* buffer, size_t length) {
        if (length < Config::overhead) {
            return FrameMsgInfo();
        }
        
        size_t idx = 0;
        
        // Verify start bytes
        if constexpr (Config::num_start_bytes >= 1) {
            if (buffer[idx++] != Config::start_byte1) {
                return FrameMsgInfo();
            }
        }
        if constexpr (Config::num_start_bytes >= 2) {
            if (buffer[idx++] != Config::start_byte2) {
                return FrameMsgInfo();
            }
        }
        
        size_t crc_start = idx;
        
        // Skip optional fields before length
        if constexpr (Config::has_seq) idx++;
        if constexpr (Config::has_sys_id) idx++;
        if constexpr (Config::has_comp_id) idx++;
        
        // Read length field
        size_t msg_len = 0;
        if constexpr (Config::has_length) {
            if constexpr (Config::length_bytes == 1) {
                msg_len = buffer[idx++];
            } else {
                msg_len = buffer[idx] | (static_cast<size_t>(buffer[idx + 1]) << 8);
                idx += 2;
            }
        }
        
        // Skip package ID
        if constexpr (Config::has_pkg_id) idx++;
        
        // Read message ID
        uint8_t msg_id = buffer[idx++];
        
        // Verify total size
        size_t total_size = Config::overhead + msg_len;
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        // Verify CRC
        if constexpr (Config::has_crc) {
            size_t crc_len = total_size - crc_start - Config::footer_size;
            FrameChecksum ck = fletcher_checksum(buffer + crc_start, crc_len);
            if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
                return FrameMsgInfo();
            }
        }
        
        return FrameMsgInfo(true, msg_id, msg_len,
                          const_cast<uint8_t*>(buffer + Config::header_size));
    }
};

/**
 * Generic frame parser for minimal frames (requires get_msg_length callback)
 */
template<typename Config>
class FrameParserMinimal {
public:
    static FrameMsgInfo parse(const uint8_t* buffer, size_t length,
                             std::function<bool(uint8_t, size_t*)> get_msg_length) {
        if (length < Config::header_size) {
            return FrameMsgInfo();
        }
        
        size_t idx = 0;
        
        // Verify start bytes
        if constexpr (Config::num_start_bytes >= 1) {
            if (buffer[idx++] != Config::start_byte1) {
                return FrameMsgInfo();
            }
        }
        if constexpr (Config::num_start_bytes >= 2) {
            if (buffer[idx++] != Config::start_byte2) {
                return FrameMsgInfo();
            }
        }
        
        // Read message ID
        uint8_t msg_id = buffer[idx];
        
        // Get message length from callback
        size_t msg_len = 0;
        if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
            return FrameMsgInfo();
        }
        
        size_t total_size = Config::header_size + msg_len;
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, msg_id, msg_len,
                          const_cast<uint8_t*>(buffer + Config::header_size));
    }
};

/*===========================================================================
 * Profile Configuration Type Aliases
 *===========================================================================*/

// Profile Standard: Basic + Default
// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileStandardConfig = FrameFormatConfig<
    2,                                                              // num_start_bytes
    FrameHeaders::BASIC_START_BYTE,                                 // start_byte1
    FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(PayloadTypes::PayloadType::DEFAULT), // start_byte2
    4,                                                              // header_size
    2,                                                              // footer_size
    true,                                                           // has_length
    1,                                                              // length_bytes
    true,                                                           // has_crc
    false,                                                          // has_pkg_id
    false,                                                          // has_seq
    false,                                                          // has_sys_id
    false                                                           // has_comp_id
>;

// Profile Sensor: Tiny + Minimal
// Frame: [0x70] [MSG_ID] [PAYLOAD]
using ProfileSensorConfig = FrameFormatConfig<
    1,                                                              // num_start_bytes
    FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(PayloadTypes::PayloadType::MINIMAL), // start_byte1
    0,                                                              // start_byte2
    2,                                                              // header_size
    0,                                                              // footer_size
    false,                                                          // has_length
    0,                                                              // length_bytes
    false,                                                          // has_crc
    false,                                                          // has_pkg_id
    false,                                                          // has_seq
    false,                                                          // has_sys_id
    false                                                           // has_comp_id
>;

// Profile IPC: None + Minimal
// Frame: [MSG_ID] [PAYLOAD]
using ProfileIPCConfig = FrameFormatConfig<
    0,                                                              // num_start_bytes
    0,                                                              // start_byte1
    0,                                                              // start_byte2
    1,                                                              // header_size
    0,                                                              // footer_size
    false,                                                          // has_length
    0,                                                              // length_bytes
    false,                                                          // has_crc
    false,                                                          // has_pkg_id
    false,                                                          // has_seq
    false,                                                          // has_sys_id
    false                                                           // has_comp_id
>;

// Profile Bulk: Basic + Extended
// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileBulkConfig = FrameFormatConfig<
    2,                                                              // num_start_bytes
    FrameHeaders::BASIC_START_BYTE,                                 // start_byte1
    FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(PayloadTypes::PayloadType::EXTENDED), // start_byte2
    6,                                                              // header_size
    2,                                                              // footer_size
    true,                                                           // has_length
    2,                                                              // length_bytes
    true,                                                           // has_crc
    true,                                                           // has_pkg_id
    false,                                                          // has_seq
    false,                                                          // has_sys_id
    false                                                           // has_comp_id
>;

// Profile Network: Basic + ExtendedMultiSystemStream
// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileNetworkConfig = FrameFormatConfig<
    2,                                                              // num_start_bytes
    FrameHeaders::BASIC_START_BYTE,                                 // start_byte1
    FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(PayloadTypes::PayloadType::EXTENDED_MULTI_SYSTEM_STREAM), // start_byte2
    9,                                                              // header_size
    2,                                                              // footer_size
    true,                                                           // has_length
    2,                                                              // length_bytes
    true,                                                           // has_crc
    true,                                                           // has_pkg_id
    true,                                                           // has_seq
    true,                                                           // has_sys_id
    true                                                            // has_comp_id
>;

/*===========================================================================
 * Profile-Specific Type Aliases for Encoders and Parsers
 *===========================================================================*/

// Profile Standard
using ProfileStandardEncoder = FrameEncoderWithCrc<ProfileStandardConfig>;
using ProfileStandardParser = FrameParserWithCrc<ProfileStandardConfig>;

// Profile Sensor
using ProfileSensorEncoder = FrameEncoderMinimal<ProfileSensorConfig>;
using ProfileSensorParser = FrameParserMinimal<ProfileSensorConfig>;

// Profile IPC
using ProfileIPCEncoder = FrameEncoderMinimal<ProfileIPCConfig>;
using ProfileIPCParser = FrameParserMinimal<ProfileIPCConfig>;

// Profile Bulk
using ProfileBulkEncoder = FrameEncoderWithCrc<ProfileBulkConfig>;
using ProfileBulkParser = FrameParserWithCrc<ProfileBulkConfig>;

// Profile Network
using ProfileNetworkEncoder = FrameEncoderWithCrc<ProfileNetworkConfig>;
using ProfileNetworkParser = FrameParserWithCrc<ProfileNetworkConfig>;

/*===========================================================================
 * Convenience Functions
 * These are simple wrapper functions for backward compatibility and ease of use.
 *===========================================================================*/

// Profile Standard (Basic + Default)
inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size,
                                      uint8_t msg_id,
                                      const uint8_t* payload, size_t payload_size) {
    return ProfileStandardEncoder::encode(buffer, buffer_size, 0, 0, 0, 0, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
    return ProfileStandardParser::parse(buffer, length);
}

// Profile Sensor (Tiny + Minimal)
inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size,
                                    uint8_t msg_id,
                                    const uint8_t* payload, size_t payload_size) {
    return ProfileSensorEncoder::encode(buffer, buffer_size, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                std::function<bool(uint8_t, size_t*)> get_msg_length) {
    return ProfileSensorParser::parse(buffer, length, get_msg_length);
}

// Profile IPC (None + Minimal)
inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size,
                                 uint8_t msg_id,
                                 const uint8_t* payload, size_t payload_size) {
    return ProfileIPCEncoder::encode(buffer, buffer_size, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                             std::function<bool(uint8_t, size_t*)> get_msg_length) {
    return ProfileIPCParser::parse(buffer, length, get_msg_length);
}

// Profile Bulk (Basic + Extended)
inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                  uint8_t pkg_id, uint8_t msg_id,
                                  const uint8_t* payload, size_t payload_size) {
    return ProfileBulkEncoder::encode(buffer, buffer_size, 0, 0, 0, pkg_id, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    return ProfileBulkParser::parse(buffer, length);
}

// Profile Network (Basic + ExtendedMultiSystemStream)
inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                     uint8_t sequence, uint8_t system_id,
                                     uint8_t component_id, uint8_t pkg_id,
                                     uint8_t msg_id,
                                     const uint8_t* payload, size_t payload_size) {
    return ProfileNetworkEncoder::encode(buffer, buffer_size, sequence, system_id, component_id,
                                         pkg_id, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    return ProfileNetworkParser::parse(buffer, length);
}

}  // namespace FrameParsers
