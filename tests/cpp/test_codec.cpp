/**
 * Test codec - Encode/decode functions for all frame formats (C++).
 */

#include "test_codec.hpp"

#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>

#include "frame_parsers.hpp"
#include "json.hpp"
#include "serialization_test.sf.hpp"

using json = nlohmann::json;
using namespace FrameParsers;

/* Minimal frame format helper functions (replacing frame_compat) */

/* Basic + Default */
inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                   size_t msg_size) {
  const size_t header_size = 4; /* [0x90] [0x71] [LEN] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 255) {
    return 0;
  }

  buffer[0] = FrameHeaders::BASIC_START_BYTE;
  buffer[1] = FrameHeaders::get_basic_second_start_byte(
      static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
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

  /* Extract length from the frame */
  const size_t msg_len = buffer[2];
  const size_t total_size = 4 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
  FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 2);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[3]; /* MSG_ID at position 3 */
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 4); /* Payload starts after header */

  return result;
}

/* Tiny + Minimal */
inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                  size_t msg_size) {
  const size_t header_size = 2; /* [0x70] [MSG_ID] */
  const size_t total_size = header_size + msg_size;

  if (buffer_size < total_size) {
    return 0;
  }

  buffer[0] =
      FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
  buffer[1] = msg_id;
  std::memcpy(buffer + header_size, msg, msg_size);

  return total_size;
}

inline FrameMsgInfo tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  FrameMsgInfo result = {false, 0, 0, nullptr};

  if (length < 2 || !FrameHeaders::is_tiny_start_byte(buffer[0])) {
    return result;
  }

  /* For minimal payloads, we need to know the message size */
  const uint8_t msg_id = buffer[1];
  size_t msg_len = 0;
  if (!get_message_length(msg_id, &msg_len)) {
    return result; /* Unknown message ID */
  }

  const size_t total_size = 2 + msg_len; /* header + payload */
  if (length < total_size) {
    return result;
  }

  result.valid = true;
  result.msg_id = msg_id;
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 2);

  return result;
}

/* None + Minimal */
inline size_t none_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                  size_t msg_size) {
  const size_t header_size = 1; /* [MSG_ID] */
  const size_t total_size = header_size + msg_size;

  if (buffer_size < total_size) {
    return 0;
  }

  buffer[0] = msg_id;
  std::memcpy(buffer + header_size, msg, msg_size);

  return total_size;
}

inline FrameMsgInfo none_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  FrameMsgInfo result = {false, 0, 0, nullptr};

  if (length < 1) {
    return result;
  }

  /* For minimal payloads, we need to know the message size */
  const uint8_t msg_id = buffer[0];
  size_t msg_len = 0;
  if (!get_message_length(msg_id, &msg_len)) {
    return result; /* Unknown message ID */
  }

  const size_t total_size = 1 + msg_len; /* header + payload */
  if (length < total_size) {
    return result;
  }

  result.valid = true;
  result.msg_id = msg_id;
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 1);

  return result;
}

/* Basic + Extended */
inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                    size_t msg_size) {
  const size_t header_size = 6; /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 65535) {
    return 0;
  }

  buffer[0] = FrameHeaders::BASIC_START_BYTE;
  buffer[1] = FrameHeaders::get_basic_second_start_byte(
      static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_CONFIG.payload_type));
  buffer[2] = static_cast<uint8_t>(msg_size & 0xFF);
  buffer[3] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
  buffer[4] = 0; /* PKG_ID = 0 */
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

  /* Extract length from the frame */
  const size_t msg_len = buffer[2] | (buffer[3] << 8);
  const size_t total_size = 6 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
  FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 4);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[5]; /* MSG_ID at position 5 */
  result.msg_len = msg_len;
  result.msg_data = const_cast<uint8_t*>(buffer + 6); /* Payload starts after header */

  return result;
}

/* Basic + Extended Multi System Stream */
inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id,
                                                        const uint8_t* msg, size_t msg_size) {
  const size_t header_size = 9; /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 65535) {
    return 0;
  }

  buffer[0] = FrameHeaders::BASIC_START_BYTE;
  buffer[1] = FrameHeaders::get_basic_second_start_byte(
      static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type));
  buffer[2] = 0; /* SEQ = 0 */
  buffer[3] = 0; /* SYS_ID = 0 */
  buffer[4] = 0; /* COMP_ID = 0 */
  buffer[5] = static_cast<uint8_t>(msg_size & 0xFF);
  buffer[6] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
  buffer[7] = 0; /* PKG_ID = 0 */
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

  /* Extract length from the frame */
  const size_t msg_len = buffer[5] | (buffer[6] << 8);
  const size_t total_size = 9 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
  FrameChecksum ck = fletcher_checksum(buffer + 2, msg_len + 7);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[8]; /* MSG_ID at position 8 */
  result.msg_len = msg_len;
  result.msg_data = const_cast<uint8_t*>(buffer + 9); /* Payload starts after header */

  return result;
}

/* Basic + Minimal */
inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                   size_t msg_size) {
  const size_t header_size = 3; /* [0x90] [0x70] [MSG_ID] */
  const size_t total_size = header_size + msg_size;

  if (buffer_size < total_size) {
    return 0;
  }

  buffer[0] = FrameHeaders::BASIC_START_BYTE;
  buffer[1] = FrameHeaders::get_basic_second_start_byte(
      static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
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

  /* For minimal payloads, we need to know the message size */
  const uint8_t msg_id = buffer[2];
  size_t msg_len = 0;
  if (!get_message_length(msg_id, &msg_len)) {
    return result; /* Unknown message ID */
  }

  const size_t total_size = 3 + msg_len; /* header + payload */
  if (length < total_size) {
    return result;
  }

  result.valid = true;
  result.msg_id = msg_id;
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 3);

  return result;
}

/* Tiny + Default */
inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                  size_t msg_size) {
  const size_t header_size = 3; /* [0x71] [LEN] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 255) {
    return 0;
  }

  buffer[0] =
      FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
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

  /* Extract length from the frame */
  const size_t msg_len = buffer[1];
  const size_t total_size = 3 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
  FrameChecksum ck = fletcher_checksum(buffer + 1, msg_len + 2);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[2]; /* MSG_ID at position 2 */
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 3); /* Payload starts after header */

  return result;
}

/* Load test messages from test_messages.json */
std::vector<TestMessage> load_test_messages() {
  std::vector<std::string> possible_paths = {
    "../test_messages.json",
    "../../test_messages.json",
    "test_messages.json",
    "../../../tests/test_messages.json"
  };
  
  for (const auto& filepath : possible_paths) {
    std::ifstream file(filepath);
    if (file.is_open()) {
      try {
        json data;
        file >> data;
        
        std::vector<TestMessage> messages;
        
        // Try to read from SerializationTestMessage key, fall back to messages key
        json message_array;
        if (data.contains("SerializationTestMessage")) {
          message_array = data["SerializationTestMessage"];
        } else if (data.contains("messages")) {
          message_array = data["messages"];
        } else {
          continue;
        }
        
        for (const auto& msg : message_array) {
          TestMessage test_msg;
          test_msg.magic_number = msg["magic_number"];
          test_msg.test_string = msg["test_string"];
          test_msg.test_float = msg["test_float"];
          test_msg.test_bool = msg["test_bool"];
          
          if (msg.contains("test_array") && msg["test_array"].is_array()) {
            for (const auto& val : msg["test_array"]) {
              test_msg.test_array.push_back(val);
            }
          }
          
          messages.push_back(test_msg);
        }
        
        return messages;
      } catch (const std::exception& e) {
        // Try next path
        continue;
      }
    }
  }
  
  /* If we couldn't load from JSON, return empty vector to indicate failure */
  std::cerr << "Error: Could not load test_messages.json\n";
  return std::vector<TestMessage>();
}
void create_message_from_data(const TestMessage& test_msg, SerializationTestSerializationTestMessage& msg) {
  std::memset(&msg, 0, sizeof(msg));

  msg.magic_number = test_msg.magic_number;
  msg.test_string.length = test_msg.test_string.length();
  std::strncpy(msg.test_string.data, test_msg.test_string.c_str(), sizeof(msg.test_string.data) - 1);
  msg.test_string.data[sizeof(msg.test_string.data) - 1] = '\0';
  msg.test_float = test_msg.test_float;
  msg.test_bool = test_msg.test_bool;
  msg.test_array.count = test_msg.test_array.size();
  for (size_t i = 0; i < test_msg.test_array.size() && i < sizeof(msg.test_array.data) / sizeof(msg.test_array.data[0]);
       i++) {
    msg.test_array.data[i] = test_msg.test_array[i];
  }
}

bool validate_message(const SerializationTestSerializationTestMessage& msg, const TestMessage& test_msg) {
  if (msg.magic_number != test_msg.magic_number) {
    std::cout << "  Value mismatch: magic_number (expected " << test_msg.magic_number << ", got " << msg.magic_number
              << ")\n";
    return false;
  }

  std::string decoded_string(msg.test_string.data, msg.test_string.length);
  if (decoded_string != test_msg.test_string) {
    std::cout << "  Value mismatch: test_string (expected '" << test_msg.test_string << "', got '" << decoded_string
              << "')\n";
    return false;
  }

  if (std::fabs(msg.test_float - test_msg.test_float) > 0.0001f) {
    std::cout << "  Value mismatch: test_float (expected " << test_msg.test_float << ", got " << msg.test_float
              << ")\n";
    return false;
  }

  if (msg.test_bool != test_msg.test_bool) {
    std::cout << "  Value mismatch: test_bool (expected " << test_msg.test_bool << ", got " << msg.test_bool << ")\n";
    return false;
  }

  if (msg.test_array.count != test_msg.test_array.size()) {
    std::cout << "  Value mismatch: test_array.count (expected " << test_msg.test_array.size() << ", got "
              << msg.test_array.count << ")\n";
    return false;
  }

  for (size_t i = 0; i < test_msg.test_array.size(); i++) {
    if (msg.test_array.data[i] != test_msg.test_array[i]) {
      std::cout << "  Value mismatch: test_array[" << i << "] (expected " << test_msg.test_array[i] << ", got "
                << msg.test_array.data[i] << ")\n";
      return false;
    }
  }

  return true;
}

/* Expected test values (from test_messages.json) - kept for backwards compatibility */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage& msg) {
  TestMessage test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  test_msg.test_string = EXPECTED_TEST_STRING;
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array.assign(EXPECTED_TEST_ARRAY, EXPECTED_TEST_ARRAY + EXPECTED_TEST_ARRAY_COUNT);

  create_message_from_data(test_msg, msg);
}

bool validate_test_message(const SerializationTestSerializationTestMessage& msg) {
  TestMessage test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  test_msg.test_string = EXPECTED_TEST_STRING;
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array.assign(EXPECTED_TEST_ARRAY, EXPECTED_TEST_ARRAY + EXPECTED_TEST_ARRAY_COUNT);

  return validate_message(msg, test_msg);
}

bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  auto test_messages = load_test_messages();
  if (test_messages.empty()) {
    std::cout << "  Failed to load test messages\n";
    return false;
  }

  encoded_size = 0;
  size_t offset = 0;

  for (const auto& test_msg : test_messages) {
    SerializationTestSerializationTestMessage msg;
    create_message_from_data(test_msg, msg);

    size_t msg_encoded_size = 0;

    if (format == "profile_standard") {
      msg_encoded_size = basic_default_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (format == "profile_sensor") {
      msg_encoded_size = tiny_minimal_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (format == "profile_ipc") {
      msg_encoded_size = none_minimal_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (format == "profile_bulk") {
      msg_encoded_size = basic_extended_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (format == "profile_network") {
      msg_encoded_size = basic_extended_multi_system_stream_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else {
      std::cout << "  Unknown frame format: " << format << "\n";
      return false;
    }

    if (msg_encoded_size == 0) {
      std::cout << "  Encoding failed for message\n";
      return false;
    }

    offset += msg_encoded_size;
    encoded_size = offset;
  }

  return encoded_size > 0;
}

bool encode_test_message(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  return encode_test_messages(format, buffer, buffer_size, encoded_size);
}

bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size, size_t& message_count) {
  std::vector<TestMessage> test_messages = load_test_messages();
  if (test_messages.empty()) {
    std::cout << "  Failed to load test messages\n";
    message_count = 0;
    return false;
  }

  size_t offset = 0;
  message_count = 0;

  while (offset < buffer_size && message_count < test_messages.size()) {
    FrameMsgInfo decode_result;

    if (format == "profile_standard") {
      decode_result = basic_default_validate_packet(buffer + offset, buffer_size - offset);
    } else if (format == "profile_sensor") {
      decode_result = tiny_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (format == "profile_ipc") {
      decode_result = none_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (format == "profile_bulk") {
      decode_result = basic_extended_validate_packet(buffer + offset, buffer_size - offset);
    } else if (format == "profile_network") {
      decode_result = basic_extended_multi_system_stream_validate_packet(buffer + offset, buffer_size - offset);
    } else {
      std::cout << "  Unknown frame format: " << format << "\n";
      return false;
    }

    if (!decode_result.valid) {
      std::cout << "  Decoding failed for message " << message_count << "\n";
      return false;
    }

    SerializationTestSerializationTestMessage msg;
    std::memcpy(&msg, decode_result.msg_data, sizeof(msg));

    if (!validate_message(msg, test_messages[message_count])) {
      std::cout << "  Validation failed for message " << message_count << "\n";
      return false;
    }

    // Calculate the size of this encoded message
    size_t msg_size = 0;
    if (format == "profile_standard") {
      msg_size = 4 + decode_result.msg_len + 2;  // header + payload + crc
    } else if (format == "profile_sensor") {
      msg_size = 2 + decode_result.msg_len;  // header + payload
    } else if (format == "profile_ipc") {
      msg_size = 1 + decode_result.msg_len;  // header + payload
    } else if (format == "profile_bulk") {
      msg_size = 6 + decode_result.msg_len + 2;  // header + payload + crc
    } else if (format == "profile_network") {
      msg_size = 9 + decode_result.msg_len + 2;  // header + payload + crc
    }

    offset += msg_size;
    message_count++;
  }

  if (message_count != test_messages.size()) {
    std::cout << "  Expected " << test_messages.size() << " messages, but decoded " << message_count << "\n";
    return false;
  }

  if (offset != buffer_size) {
    std::cout << "  Extra data after messages: expected " << offset << " bytes, got " << buffer_size << " bytes\n";
    return false;
  }

  return true;
}

bool decode_test_message(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage& msg) {
  size_t message_count = 0;
  return decode_test_messages(format, buffer, buffer_size, message_count);
}
