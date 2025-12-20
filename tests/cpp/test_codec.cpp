/**
 * Test codec - Encode/decode functions for all frame formats (C++).
 */

#include "test_codec.hpp"

#include <cmath>
#include <cstring>
#include <iostream>

#include "frame_parsers.hpp"
#include "serialization_test.sf.hpp"

using namespace FrameParsers;

/* Minimal frame format helper functions (replacing frame_compat) */

/* Basic + Default */
inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size,
                                   uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 4;  /* [0x90] [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
    buffer[2] = static_cast<uint8_t>(msg_size);
    buffer[3] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_default_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 6 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 4, 1, 2);
}

/* Tiny + Minimal */
inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                  uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 2;  /* [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
    buffer[1] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

inline FrameMsgInfo tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 2 || !FrameHeaders::is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return validate_payload_minimal(buffer, length, 2);
}

/* Basic + Extended */
inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size,
                                    uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 6;  /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_CONFIG.payload_type));
    buffer[2] = static_cast<uint8_t>(msg_size & 0xFF);
    buffer[3] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
    buffer[4] = 0;  /* PKG_ID = 0 */
    buffer[5] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 4);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 8 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 6, 2, 2);
}

/* Basic + Extended Multi System Stream */
inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size,
                                                         uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 9;  /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type));
    buffer[2] = 0;  /* SEQ = 0 */
    buffer[3] = 0;  /* SYS_ID = 0 */
    buffer[4] = 0;  /* COMP_ID = 0 */
    buffer[5] = static_cast<uint8_t>(msg_size & 0xFF);
    buffer[6] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
    buffer[7] = 0;  /* PKG_ID = 0 */
    buffer[8] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 7);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 11 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 9, 2, 2);
}

/* Basic + Minimal */
inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                   uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x90] [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
    buffer[2] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

inline FrameMsgInfo basic_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 3 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_minimal(buffer, length, 3);
}

/* Tiny + Default */
inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size,
                                  uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
    buffer[1] = static_cast<uint8_t>(msg_size);
    buffer[2] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 1, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo tiny_default_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 5 || !FrameHeaders::is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 3, 1, 1);
}

/* Expected test values (from expected_values.json) */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage& msg) {
  std::memset(&msg, 0, sizeof(msg));

  msg.magic_number = EXPECTED_MAGIC_NUMBER;
  msg.test_string.length = std::strlen(EXPECTED_TEST_STRING);
  std::strncpy(msg.test_string.data, EXPECTED_TEST_STRING, sizeof(msg.test_string.data));
  msg.test_float = EXPECTED_TEST_FLOAT;
  msg.test_bool = EXPECTED_TEST_BOOL;
  msg.test_array.count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    msg.test_array.data[i] = EXPECTED_TEST_ARRAY[i];
  }
}

bool validate_test_message(const SerializationTestSerializationTestMessage& msg) {
  if (msg.magic_number != EXPECTED_MAGIC_NUMBER) {
    std::cout << "  Value mismatch: magic_number (expected " << EXPECTED_MAGIC_NUMBER << ", got " << msg.magic_number
              << ")\n";
    return false;
  }

  if (std::strncmp(msg.test_string.data, EXPECTED_TEST_STRING, msg.test_string.length) != 0) {
    std::cout << "  Value mismatch: test_string\n";
    return false;
  }

  if (std::fabs(msg.test_float - EXPECTED_TEST_FLOAT) > 0.0001f) {
    std::cout << "  Value mismatch: test_float (expected " << EXPECTED_TEST_FLOAT << ", got " << msg.test_float
              << ")\n";
    return false;
  }

  if (msg.test_bool != EXPECTED_TEST_BOOL) {
    std::cout << "  Value mismatch: test_bool\n";
    return false;
  }

  if (msg.test_array.count != EXPECTED_TEST_ARRAY_COUNT) {
    std::cout << "  Value mismatch: test_array.count (expected " << EXPECTED_TEST_ARRAY_COUNT << ", got "
              << msg.test_array.count << ")\n";
    return false;
  }

  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    if (msg.test_array.data[i] != EXPECTED_TEST_ARRAY[i]) {
      std::cout << "  Value mismatch: test_array[" << i << "] (expected " << EXPECTED_TEST_ARRAY[i] << ", got "
                << msg.test_array.data[i] << ")\n";
      return false;
    }
  }

  return true;
}

bool encode_test_message(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  SerializationTestSerializationTestMessage msg;
  create_test_message(msg);

  encoded_size = 0;

  // Support profile names (preferred) and legacy direct format names
  if (format == "profile_standard" || format == "basic_default") {
    encoded_size = basic_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        reinterpret_cast<const uint8_t*>(&msg),
                                        SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (format == "profile_sensor" || format == "tiny_minimal") {
    encoded_size = tiny_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                       reinterpret_cast<const uint8_t*>(&msg),
                                       SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (format == "profile_bulk" || format == "basic_extended") {
    encoded_size = basic_extended_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                         reinterpret_cast<const uint8_t*>(&msg),
                                         SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (format == "profile_network" || format == "basic_extended_multi_system_stream") {
    encoded_size = basic_extended_multi_system_stream_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                                             reinterpret_cast<const uint8_t*>(&msg),
                                                             SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (format == "basic_minimal") {
    encoded_size = basic_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        reinterpret_cast<const uint8_t*>(&msg),
                                        SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (format == "tiny_default") {
    encoded_size = tiny_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                       reinterpret_cast<const uint8_t*>(&msg),
                                       SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else {
    std::cout << "  Unknown frame format: " << format << "\n";
    return false;
  }

  return encoded_size > 0;
}

bool decode_test_message(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage& msg) {
  FrameMsgInfo decode_result;

  // Support profile names (preferred) and legacy direct format names
  if (format == "profile_standard" || format == "basic_default") {
    decode_result = basic_default_validate_packet(buffer, buffer_size);
  } else if (format == "profile_sensor" || format == "tiny_minimal") {
    decode_result = tiny_minimal_validate_packet(buffer, buffer_size);
  } else if (format == "profile_bulk" || format == "basic_extended") {
    decode_result = basic_extended_validate_packet(buffer, buffer_size);
  } else if (format == "profile_network" || format == "basic_extended_multi_system_stream") {
    decode_result = basic_extended_multi_system_stream_validate_packet(buffer, buffer_size);
  } else if (format == "basic_minimal") {
    decode_result = basic_minimal_validate_packet(buffer, buffer_size);
  } else if (format == "tiny_default") {
    decode_result = tiny_default_validate_packet(buffer, buffer_size);
  } else {
    std::cout << "  Unknown frame format: " << format << "\n";
    return false;
  }

  if (!decode_result.valid) {
    return false;
  }

  std::memcpy(&msg, decode_result.msg_data, sizeof(msg));
  return true;
}
