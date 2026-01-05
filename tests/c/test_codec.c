#include "test_codec.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "frame_parsers.h"
#include "serialization_test.sf.h"

/* Minimal frame format helper functions (replacing frame_compat) */

/* Basic + Default */
static inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size,
                                          uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 4;  /* [0x90] [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_DEFAULT_CONFIG.payload_type);
    buffer[2] = (uint8_t)msg_size;
    buffer[3] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_default_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 6 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 4, 1, 2);
}

/* Tiny + Minimal */
static inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 2;  /* [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = get_tiny_start_byte(PAYLOAD_MINIMAL_CONFIG.payload_type);
    buffer[1] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

static inline frame_msg_info_t tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 2 || !is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return frame_validate_payload_minimal(buffer, length, 2);
}

/* None + Minimal */
static inline size_t none_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 1;  /* [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

static inline frame_msg_info_t none_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 1) {
        return result;
    }
    
    return frame_validate_payload_minimal(buffer, length, 1);
}

/* Basic + Extended */
static inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size,
                                           uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 6;  /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_CONFIG.payload_type);
    buffer[2] = (uint8_t)(msg_size & 0xFF);
    buffer[3] = (uint8_t)((msg_size >> 8) & 0xFF);
    buffer[4] = 0;  /* PKG_ID = 0 */
    buffer[5] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 4);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 8 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 6, 2, 2);
}

/* Basic + Extended Multi System Stream */
static inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size,
                                                                uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 9;  /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type);
    buffer[2] = 0;  /* SEQ = 0 */
    buffer[3] = 0;  /* SYS_ID = 0 */
    buffer[4] = 0;  /* COMP_ID = 0 */
    buffer[5] = (uint8_t)(msg_size & 0xFF);
    buffer[6] = (uint8_t)((msg_size >> 8) & 0xFF);
    buffer[7] = 0;  /* PKG_ID = 0 */
    buffer[8] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 7);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 11 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 9, 2, 2);
}

/* Basic + Minimal */
static inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                          uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x90] [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_MINIMAL_CONFIG.payload_type);
    buffer[2] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

static inline frame_msg_info_t basic_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 3 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_minimal(buffer, length, 3);
}

/* Tiny + Default */
static inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = get_tiny_start_byte(PAYLOAD_DEFAULT_CONFIG.payload_type);
    buffer[1] = (uint8_t)msg_size;
    buffer[2] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 1, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t tiny_default_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 5 || !is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 3, 1, 1);
}

/* Expected test values (from expected_values.json) */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage* msg) {
  memset(msg, 0, sizeof(*msg));

  msg->magic_number = EXPECTED_MAGIC_NUMBER;
  msg->test_string.length = strlen(EXPECTED_TEST_STRING);
  strncpy(msg->test_string.data, EXPECTED_TEST_STRING, msg->test_string.length);
  msg->test_float = EXPECTED_TEST_FLOAT;
  msg->test_bool = EXPECTED_TEST_BOOL;
  msg->test_array.count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    msg->test_array.data[i] = EXPECTED_TEST_ARRAY[i];
  }
}

bool validate_test_message(const SerializationTestSerializationTestMessage* msg) {
  if (msg->magic_number != EXPECTED_MAGIC_NUMBER) {
    printf("  Value mismatch: magic_number (expected %u, got %u)\n", EXPECTED_MAGIC_NUMBER, msg->magic_number);
    return false;
  }

  if (strncmp(msg->test_string.data, EXPECTED_TEST_STRING, msg->test_string.length) != 0) {
    printf("  Value mismatch: test_string (expected '%s', got '%.*s')\n", EXPECTED_TEST_STRING,
           (int)msg->test_string.length, msg->test_string.data);
    return false;
  }

  if (fabs(msg->test_float - EXPECTED_TEST_FLOAT) > 0.0001f) {
    printf("  Value mismatch: test_float (expected %f, got %f)\n", EXPECTED_TEST_FLOAT, msg->test_float);
    return false;
  }

  if (msg->test_bool != EXPECTED_TEST_BOOL) {
    printf("  Value mismatch: test_bool (expected %d, got %d)\n", EXPECTED_TEST_BOOL, msg->test_bool);
    return false;
  }

  if (msg->test_array.count != EXPECTED_TEST_ARRAY_COUNT) {
    printf("  Value mismatch: test_array.count (expected %zu, got %u)\n", EXPECTED_TEST_ARRAY_COUNT,
           msg->test_array.count);
    return false;
  }

  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    if (msg->test_array.data[i] != EXPECTED_TEST_ARRAY[i]) {
      printf("  Value mismatch: test_array[%zu] (expected %d, got %d)\n", i, EXPECTED_TEST_ARRAY[i],
             msg->test_array.data[i]);
      return false;
    }
  }

  return true;
}

bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  SerializationTestSerializationTestMessage msg;
  create_test_message(&msg);

  *encoded_size = 0;

  // Support profile names (preferred) and legacy direct format names
  if (strcmp(format, "profile_standard") == 0 || strcmp(format, "basic_default") == 0) {
    *encoded_size = basic_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                         (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_sensor") == 0 || strcmp(format, "tiny_minimal") == 0) {
    *encoded_size = tiny_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_ipc") == 0 || strcmp(format, "none_minimal") == 0) {
    *encoded_size = none_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_bulk") == 0 || strcmp(format, "basic_extended") == 0) {
    *encoded_size = basic_extended_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                          (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_network") == 0 || strcmp(format, "basic_extended_multi_system_stream") == 0) {
    *encoded_size = basic_extended_multi_system_stream_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                                               (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "basic_minimal") == 0) {
    *encoded_size = basic_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                         (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "tiny_default") == 0) {
    *encoded_size = tiny_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  return *encoded_size > 0;
}

bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg) {
  frame_msg_info_t decode_result;

  // Support profile names (preferred) and legacy direct format names
  if (strcmp(format, "profile_standard") == 0 || strcmp(format, "basic_default") == 0) {
    decode_result = basic_default_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_sensor") == 0 || strcmp(format, "tiny_minimal") == 0) {
    decode_result = tiny_minimal_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_ipc") == 0 || strcmp(format, "none_minimal") == 0) {
    decode_result = none_minimal_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_bulk") == 0 || strcmp(format, "basic_extended") == 0) {
    decode_result = basic_extended_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_network") == 0 || strcmp(format, "basic_extended_multi_system_stream") == 0) {
    decode_result = basic_extended_multi_system_stream_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "basic_minimal") == 0) {
    decode_result = basic_minimal_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "tiny_default") == 0) {
    decode_result = tiny_default_validate_packet(buffer, buffer_size);
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  if (!decode_result.valid) {
    return false;
  }

  memcpy(msg, decode_result.msg_data, sizeof(*msg));
  return true;
}
