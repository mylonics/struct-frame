/* Frame Profiles - Pre-defined Header + Payload combinations */
/* 
 * This file provides ready-to-use encode/parse functions for the 5 standard profiles:
 * - ProfileStandard: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 */

#pragma once

#include "frame_base.hpp"

namespace FrameParsers {
namespace Profiles {

/*===========================================================================
 * ProfileStandard: Basic + Default
 * Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 6 bytes. Max payload: 255 bytes.
 *===========================================================================*/

namespace Standard {
    constexpr uint8_t START_BYTE1 = 0x90;
    constexpr uint8_t START_BYTE2 = 0x71;
    constexpr size_t HEADER_SIZE = 4;  /* start1 + start2 + len + msg_id */
    constexpr size_t FOOTER_SIZE = 2;  /* CRC */
    constexpr size_t OVERHEAD = HEADER_SIZE + FOOTER_SIZE;
    
    /**
     * Encode a message using ProfileStandard (Basic + Default) format.
     * 
     * @param buffer Output buffer to write the encoded frame
     * @param buffer_size Size of the output buffer
     * @param msg_id Message ID
     * @param payload Pointer to payload data
     * @param payload_size Size of payload in bytes (max 255)
     * @return Number of bytes written, or 0 on failure
     */
    inline size_t encode(uint8_t* buffer, size_t buffer_size,
                         uint8_t msg_id,
                         const uint8_t* payload, size_t payload_size) {
        size_t total_size = OVERHEAD + payload_size;
        
        if (buffer_size < total_size || payload_size > 255) {
            return 0;
        }
        
        buffer[0] = START_BYTE1;
        buffer[1] = START_BYTE2;
        buffer[2] = static_cast<uint8_t>(payload_size);
        buffer[3] = msg_id;
        
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + HEADER_SIZE, payload, payload_size);
        }
        
        /* CRC covers: [LEN] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, payload_size + 2);
        buffer[total_size - 2] = ck.byte1;
        buffer[total_size - 1] = ck.byte2;
        
        return total_size;
    }
    
    /**
     * Parse/validate a complete ProfileStandard frame from a buffer.
     * 
     * @param buffer Input buffer containing the frame
     * @param length Length of data in buffer
     * @return FrameMsgInfo with valid=true if frame is valid
     */
    inline FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t length) {
        if (length < OVERHEAD) {
            return FrameMsgInfo();
        }
        
        if (buffer[0] != START_BYTE1 || buffer[1] != START_BYTE2) {
            return FrameMsgInfo();
        }
        
        size_t msg_len = buffer[2];
        size_t total_size = OVERHEAD + msg_len;
        
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 2);
        if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, buffer[3], msg_len,
                          const_cast<uint8_t*>(buffer + HEADER_SIZE));
    }
}  // namespace Standard


/*===========================================================================
 * ProfileSensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * Overhead: 2 bytes. No length field or CRC. Requires known message sizes.
 *===========================================================================*/

namespace Sensor {
    constexpr uint8_t START_BYTE = 0x70;
    constexpr size_t HEADER_SIZE = 2;  /* start + msg_id */
    constexpr size_t FOOTER_SIZE = 0;
    constexpr size_t OVERHEAD = HEADER_SIZE + FOOTER_SIZE;
    
    /**
     * Encode a message using ProfileSensor (Tiny + Minimal) format.
     * 
     * @param buffer Output buffer to write the encoded frame
     * @param buffer_size Size of the output buffer
     * @param msg_id Message ID
     * @param payload Pointer to payload data
     * @param payload_size Size of payload in bytes
     * @return Number of bytes written, or 0 on failure
     */
    inline size_t encode(uint8_t* buffer, size_t buffer_size,
                         uint8_t msg_id,
                         const uint8_t* payload, size_t payload_size) {
        size_t total_size = OVERHEAD + payload_size;
        
        if (buffer_size < total_size) {
            return 0;
        }
        
        buffer[0] = START_BYTE;
        buffer[1] = msg_id;
        
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + HEADER_SIZE, payload, payload_size);
        }
        
        return total_size;
    }
    
    /**
     * Parse/validate a ProfileSensor frame from a buffer.
     * Requires a callback to get the expected message size.
     * 
     * @param buffer Input buffer containing the frame
     * @param length Length of data in buffer
     * @param get_msg_length Callback to get expected message length from msg_id
     * @return FrameMsgInfo with valid=true if frame is valid
     */
    inline FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t length,
                                     std::function<bool(uint8_t, size_t*)> get_msg_length) {
        if (length < OVERHEAD) {
            return FrameMsgInfo();
        }
        
        if (buffer[0] != START_BYTE) {
            return FrameMsgInfo();
        }
        
        uint8_t msg_id = buffer[1];
        size_t msg_len = 0;
        
        if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
            return FrameMsgInfo();
        }
        
        size_t total_size = OVERHEAD + msg_len;
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, msg_id, msg_len,
                          const_cast<uint8_t*>(buffer + HEADER_SIZE));
    }
}  // namespace Sensor


/*===========================================================================
 * ProfileIPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * Overhead: 1 byte. No start bytes, no CRC. Relies on external synchronization.
 *===========================================================================*/

namespace IPC {
    constexpr size_t HEADER_SIZE = 1;  /* msg_id only */
    constexpr size_t FOOTER_SIZE = 0;
    constexpr size_t OVERHEAD = HEADER_SIZE + FOOTER_SIZE;
    
    /**
     * Encode a message using ProfileIPC (None + Minimal) format.
     * 
     * @param buffer Output buffer to write the encoded frame
     * @param buffer_size Size of the output buffer
     * @param msg_id Message ID
     * @param payload Pointer to payload data
     * @param payload_size Size of payload in bytes
     * @return Number of bytes written, or 0 on failure
     */
    inline size_t encode(uint8_t* buffer, size_t buffer_size,
                         uint8_t msg_id,
                         const uint8_t* payload, size_t payload_size) {
        size_t total_size = OVERHEAD + payload_size;
        
        if (buffer_size < total_size) {
            return 0;
        }
        
        buffer[0] = msg_id;
        
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + HEADER_SIZE, payload, payload_size);
        }
        
        return total_size;
    }
    
    /**
     * Parse/validate a ProfileIPC frame from a buffer.
     * Requires a callback to get the expected message size.
     * 
     * @param buffer Input buffer containing the frame
     * @param length Length of data in buffer
     * @param get_msg_length Callback to get expected message length from msg_id
     * @return FrameMsgInfo with valid=true if frame is valid
     */
    inline FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t length,
                                     std::function<bool(uint8_t, size_t*)> get_msg_length) {
        if (length < OVERHEAD) {
            return FrameMsgInfo();
        }
        
        uint8_t msg_id = buffer[0];
        size_t msg_len = 0;
        
        if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
            return FrameMsgInfo();
        }
        
        size_t total_size = OVERHEAD + msg_len;
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, msg_id, msg_len,
                          const_cast<uint8_t*>(buffer + HEADER_SIZE));
    }
}  // namespace IPC


/*===========================================================================
 * ProfileBulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 8 bytes. Max payload: 64KB. Supports package namespaces.
 *===========================================================================*/

namespace Bulk {
    constexpr uint8_t START_BYTE1 = 0x90;
    constexpr uint8_t START_BYTE2 = 0x74;
    constexpr size_t HEADER_SIZE = 6;  /* start1 + start2 + len16 + pkg_id + msg_id */
    constexpr size_t FOOTER_SIZE = 2;  /* CRC */
    constexpr size_t OVERHEAD = HEADER_SIZE + FOOTER_SIZE;
    
    /**
     * Encode a message using ProfileBulk (Basic + Extended) format.
     * 
     * @param buffer Output buffer to write the encoded frame
     * @param buffer_size Size of the output buffer
     * @param pkg_id Package ID (0-255)
     * @param msg_id Message ID
     * @param payload Pointer to payload data
     * @param payload_size Size of payload in bytes (max 65535)
     * @return Number of bytes written, or 0 on failure
     */
    inline size_t encode(uint8_t* buffer, size_t buffer_size,
                         uint8_t pkg_id, uint8_t msg_id,
                         const uint8_t* payload, size_t payload_size) {
        size_t total_size = OVERHEAD + payload_size;
        
        if (buffer_size < total_size || payload_size > 65535) {
            return 0;
        }
        
        buffer[0] = START_BYTE1;
        buffer[1] = START_BYTE2;
        buffer[2] = static_cast<uint8_t>(payload_size & 0xFF);
        buffer[3] = static_cast<uint8_t>((payload_size >> 8) & 0xFF);
        buffer[4] = pkg_id;
        buffer[5] = msg_id;
        
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + HEADER_SIZE, payload, payload_size);
        }
        
        /* CRC covers: [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, payload_size + 4);
        buffer[total_size - 2] = ck.byte1;
        buffer[total_size - 1] = ck.byte2;
        
        return total_size;
    }
    
    /**
     * Parse/validate a complete ProfileBulk frame from a buffer.
     * 
     * @param buffer Input buffer containing the frame
     * @param length Length of data in buffer
     * @return FrameMsgInfo with valid=true if frame is valid
     */
    inline FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t length) {
        if (length < OVERHEAD) {
            return FrameMsgInfo();
        }
        
        if (buffer[0] != START_BYTE1 || buffer[1] != START_BYTE2) {
            return FrameMsgInfo();
        }
        
        size_t msg_len = buffer[2] | (static_cast<size_t>(buffer[3]) << 8);
        size_t total_size = OVERHEAD + msg_len;
        
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        /* Verify CRC: covers [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 4);
        if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, buffer[5], msg_len,
                          const_cast<uint8_t*>(buffer + HEADER_SIZE));
    }
}  // namespace Bulk


/*===========================================================================
 * ProfileNetwork: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 11 bytes. Max payload: 64KB. Full routing and sequencing support.
 *===========================================================================*/

namespace Network {
    constexpr uint8_t START_BYTE1 = 0x90;
    constexpr uint8_t START_BYTE2 = 0x78;
    constexpr size_t HEADER_SIZE = 9;  /* start1 + start2 + seq + sys + comp + len16 + pkg_id + msg_id */
    constexpr size_t FOOTER_SIZE = 2;  /* CRC */
    constexpr size_t OVERHEAD = HEADER_SIZE + FOOTER_SIZE;
    
    /**
     * Encode a message using ProfileNetwork (Basic + ExtendedMultiSystemStream) format.
     * 
     * @param buffer Output buffer to write the encoded frame
     * @param buffer_size Size of the output buffer
     * @param sequence Sequence number (0-255)
     * @param system_id System ID (0-255)
     * @param component_id Component ID (0-255)
     * @param pkg_id Package ID (0-255)
     * @param msg_id Message ID
     * @param payload Pointer to payload data
     * @param payload_size Size of payload in bytes (max 65535)
     * @return Number of bytes written, or 0 on failure
     */
    inline size_t encode(uint8_t* buffer, size_t buffer_size,
                         uint8_t sequence, uint8_t system_id,
                         uint8_t component_id, uint8_t pkg_id,
                         uint8_t msg_id,
                         const uint8_t* payload, size_t payload_size) {
        size_t total_size = OVERHEAD + payload_size;
        
        if (buffer_size < total_size || payload_size > 65535) {
            return 0;
        }
        
        buffer[0] = START_BYTE1;
        buffer[1] = START_BYTE2;
        buffer[2] = sequence;
        buffer[3] = system_id;
        buffer[4] = component_id;
        buffer[5] = static_cast<uint8_t>(payload_size & 0xFF);
        buffer[6] = static_cast<uint8_t>((payload_size >> 8) & 0xFF);
        buffer[7] = pkg_id;
        buffer[8] = msg_id;
        
        if (payload_size > 0 && payload != nullptr) {
            std::memcpy(buffer + HEADER_SIZE, payload, payload_size);
        }
        
        /* CRC covers: [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, payload_size + 7);
        buffer[total_size - 2] = ck.byte1;
        buffer[total_size - 1] = ck.byte2;
        
        return total_size;
    }
    
    /**
     * Parse/validate a complete ProfileNetwork frame from a buffer.
     * 
     * @param buffer Input buffer containing the frame
     * @param length Length of data in buffer
     * @return FrameMsgInfo with valid=true if frame is valid
     */
    inline FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t length) {
        if (length < OVERHEAD) {
            return FrameMsgInfo();
        }
        
        if (buffer[0] != START_BYTE1 || buffer[1] != START_BYTE2) {
            return FrameMsgInfo();
        }
        
        size_t msg_len = buffer[5] | (static_cast<size_t>(buffer[6]) << 8);
        size_t total_size = OVERHEAD + msg_len;
        
        if (length < total_size) {
            return FrameMsgInfo();
        }
        
        /* Verify CRC: covers [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
        FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 7);
        if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
            return FrameMsgInfo();
        }
        
        return FrameMsgInfo(true, buffer[8], msg_len,
                          const_cast<uint8_t*>(buffer + HEADER_SIZE));
    }
}  // namespace Network

}  // namespace Profiles

/*===========================================================================
 * Convenience aliases at FrameParsers namespace level
 *===========================================================================*/

// Standard profile (Basic + Default) - for general serial/UART communication
inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size,
                                      uint8_t msg_id,
                                      const uint8_t* payload, size_t payload_size) {
    return Profiles::Standard::encode(buffer, buffer_size, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
    return Profiles::Standard::parse_buffer(buffer, length);
}

// Sensor profile (Tiny + Minimal) - for low-bandwidth sensors
inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size,
                                    uint8_t msg_id,
                                    const uint8_t* payload, size_t payload_size) {
    return Profiles::Sensor::encode(buffer, buffer_size, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                std::function<bool(uint8_t, size_t*)> get_msg_length) {
    return Profiles::Sensor::parse_buffer(buffer, length, get_msg_length);
}

// IPC profile (None + Minimal) - for trusted inter-process communication
inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size,
                                 uint8_t msg_id,
                                 const uint8_t* payload, size_t payload_size) {
    return Profiles::IPC::encode(buffer, buffer_size, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                             std::function<bool(uint8_t, size_t*)> get_msg_length) {
    return Profiles::IPC::parse_buffer(buffer, length, get_msg_length);
}

// Bulk profile (Basic + Extended) - for large data transfers
inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                  uint8_t pkg_id, uint8_t msg_id,
                                  const uint8_t* payload, size_t payload_size) {
    return Profiles::Bulk::encode(buffer, buffer_size, pkg_id, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    return Profiles::Bulk::parse_buffer(buffer, length);
}

// Network profile (Basic + ExtendedMultiSystemStream) - for multi-system networked communication
inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                     uint8_t sequence, uint8_t system_id,
                                     uint8_t component_id, uint8_t pkg_id,
                                     uint8_t msg_id,
                                     const uint8_t* payload, size_t payload_size) {
    return Profiles::Network::encode(buffer, buffer_size, sequence, system_id, component_id,
                                     pkg_id, msg_id, payload, payload_size);
}

inline FrameMsgInfo parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    return Profiles::Network::parse_buffer(buffer, length);
}

}  // namespace FrameParsers
