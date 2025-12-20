/* Base definitions for payload types (C++) */
/* Payload types define message structure (length fields, CRC, extra fields) */

#pragma once

#include <cstdint>
#include <string>

namespace FrameParsers {
namespace PayloadTypes {

/* Payload type enumeration */
enum class PayloadType {
    MINIMAL = 0,                      /* [MSG_ID] [PACKET] */
    DEFAULT = 1,                      /* [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    EXTENDED_MSG_IDS = 2,             /* [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    EXTENDED_LENGTH = 3,              /* [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    EXTENDED = 4,                     /* [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    SYS_COMP = 5,                     /* [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    SEQ = 6,                          /* [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    MULTI_SYSTEM_STREAM = 7,          /* [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    EXTENDED_MULTI_SYSTEM_STREAM = 8  /* [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
};

/* Maximum payload type value (for range checking) */
constexpr uint8_t MAX_PAYLOAD_TYPE_VALUE = 8;

/* Configuration for a payload type */
struct PayloadConfig {
    PayloadType payload_type;
    std::string name;
    bool has_crc;
    uint8_t crc_bytes;
    bool has_length;
    uint8_t length_bytes;  /* 1 or 2 */
    bool has_sequence;
    bool has_system_id;
    bool has_component_id;
    bool has_package_id;
    std::string description;
    
    /* Helper function to calculate header size */
    uint8_t header_size() const {
        uint8_t size = 1;  /* msg_id */
        if (has_length) {
            size += length_bytes;
        }
        if (has_sequence) {
            size += 1;
        }
        if (has_system_id) {
            size += 1;
        }
        if (has_component_id) {
            size += 1;
        }
        if (has_package_id) {
            size += 1;
        }
        return size;
    }
    
    /* Helper function to calculate footer size */
    uint8_t footer_size() const {
        return crc_bytes;
    }
    
    /* Helper function to calculate overhead */
    uint8_t overhead() const {
        return header_size() + footer_size();
    }
};

} // namespace PayloadTypes
} // namespace FrameParsers
