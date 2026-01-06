#include "test_codec.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "frame_parsers.h"
#include "serialization_test.sf.h"

/* Minimal frame format helper functions (replacing frame_compat) */

/* Basic + Default */
static inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                          size_t msg_size) {
  const size_t header_size = 4; /* [0x90] [0x71] [LEN] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
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

  if (length < 6 || buffer[0] != BASIC_START_BYTE || !is_basic_second_start_byte(buffer[1])) {
    return result;
  }

  /* Extract length from the frame */
  const size_t msg_len = buffer[2];
  const size_t total_size = 4 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 2);
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
static inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  const size_t header_size = 2; /* [0x70] [MSG_ID] */
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
static inline size_t none_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  const size_t header_size = 1; /* [MSG_ID] */
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
static inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                           size_t msg_size) {
  const size_t header_size = 6; /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 65535) {
    return 0;
  }

  buffer[0] = BASIC_START_BYTE;
  buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_CONFIG.payload_type);
  buffer[2] = (uint8_t)(msg_size & 0xFF);
  buffer[3] = (uint8_t)((msg_size >> 8) & 0xFF);
  buffer[4] = 0; /* PKG_ID = 0 */
  buffer[5] = msg_id;
  memcpy(buffer + header_size, msg, msg_size);

  frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 4);
  buffer[total_size - 2] = ck.byte1;
  buffer[total_size - 1] = ck.byte2;

  return total_size;
}

static inline frame_msg_info_t basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
  frame_msg_info_t result = {false, 0, 0, NULL};

  if (length < 8 || buffer[0] != BASIC_START_BYTE || !is_basic_second_start_byte(buffer[1])) {
    return result;
  }

  /* Extract length from the frame */
  const size_t msg_len = buffer[2] | (buffer[3] << 8);
  const size_t total_size = 6 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 4);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[5]; /* MSG_ID at position 5 */
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 6); /* Payload starts after header */

  return result;
}

/* Basic + Extended Multi System Stream */
static inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id,
                                                               const uint8_t* msg, size_t msg_size) {
  const size_t header_size = 9; /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 65535) {
    return 0;
  }

  buffer[0] = BASIC_START_BYTE;
  buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type);
  buffer[2] = 0; /* SEQ = 0 */
  buffer[3] = 0; /* SYS_ID = 0 */
  buffer[4] = 0; /* COMP_ID = 0 */
  buffer[5] = (uint8_t)(msg_size & 0xFF);
  buffer[6] = (uint8_t)((msg_size >> 8) & 0xFF);
  buffer[7] = 0; /* PKG_ID = 0 */
  buffer[8] = msg_id;
  memcpy(buffer + header_size, msg, msg_size);

  frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 7);
  buffer[total_size - 2] = ck.byte1;
  buffer[total_size - 1] = ck.byte2;

  return total_size;
}

static inline frame_msg_info_t basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer,
                                                                                  size_t length) {
  frame_msg_info_t result = {false, 0, 0, NULL};

  if (length < 11 || buffer[0] != BASIC_START_BYTE || !is_basic_second_start_byte(buffer[1])) {
    return result;
  }

  /* Extract length from the frame */
  const size_t msg_len = buffer[5] | (buffer[6] << 8);
  const size_t total_size = 9 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 7);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[8]; /* MSG_ID at position 8 */
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 9); /* Payload starts after header */

  return result;
}

/* Basic + Minimal */
static inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                          size_t msg_size) {
  const size_t header_size = 3; /* [0x90] [0x70] [MSG_ID] */
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

  if (length < 3 || buffer[0] != BASIC_START_BYTE || !is_basic_second_start_byte(buffer[1])) {
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
static inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  const size_t header_size = 3; /* [0x71] [LEN] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
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

  /* Extract length from the frame */
  const size_t msg_len = buffer[1];
  const size_t total_size = 3 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + 1, msg_len + 2);
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
size_t load_test_messages(test_message_t* messages, size_t max_count) {
  const char* possible_paths[] = {
    "../test_messages.json",
    "../../test_messages.json",
    "test_messages.json",
    "../../../tests/test_messages.json"
  };
  
  for (size_t i = 0; i < sizeof(possible_paths) / sizeof(possible_paths[0]); i++) {
    FILE* file = fopen(possible_paths[i], "r");
    if (file) {
      fseek(file, 0, SEEK_END);
      long file_size = ftell(file);
      fseek(file, 0, SEEK_SET);
      
      char* json_str = (char*)malloc(file_size + 1);
      if (!json_str) {
        fclose(file);
        continue;
      }
      
      size_t read_size = fread(json_str, 1, file_size, file);
      json_str[read_size] = '\0';
      fclose(file);
      
      cJSON* root = cJSON_Parse(json_str);
      free(json_str);
      
      if (!root) {
        continue;
      }
      
      // Try to read from SerializationTestMessage key, fall back to messages key
      cJSON* message_array = cJSON_GetObjectItem(root, "SerializationTestMessage");
      if (!message_array) {
        message_array = cJSON_GetObjectItem(root, "messages");
      }
      
      if (!message_array || !cJSON_IsArray(message_array)) {
        cJSON_Delete(root);
        continue;
      }
      
      size_t count = 0;
      cJSON* msg_item = NULL;
      cJSON_ArrayForEach(msg_item, message_array) {
        if (count >= max_count) break;
        
        cJSON* magic_number = cJSON_GetObjectItem(msg_item, "magic_number");
        cJSON* test_string = cJSON_GetObjectItem(msg_item, "test_string");
        cJSON* test_float = cJSON_GetObjectItem(msg_item, "test_float");
        cJSON* test_bool = cJSON_GetObjectItem(msg_item, "test_bool");
        cJSON* test_array = cJSON_GetObjectItem(msg_item, "test_array");
        
        if (magic_number && test_string && test_float && test_bool) {
          messages[count].magic_number = (uint32_t)cJSON_GetNumberValue(magic_number);
          
          strncpy(messages[count].test_string, cJSON_GetStringValue(test_string), MAX_STRING_LENGTH - 1);
          messages[count].test_string[MAX_STRING_LENGTH - 1] = '\0';
          
          messages[count].test_float = (float)cJSON_GetNumberValue(test_float);
          messages[count].test_bool = cJSON_IsTrue(test_bool);
          
          messages[count].test_array_count = 0;
          if (test_array && cJSON_IsArray(test_array)) {
            size_t array_idx = 0;
            cJSON* array_item = NULL;
            cJSON_ArrayForEach(array_item, test_array) {
              if (array_idx >= MAX_ARRAY_LENGTH) break;
              messages[count].test_array[array_idx++] = (int32_t)cJSON_GetNumberValue(array_item);
            }
            messages[count].test_array_count = array_idx;
          }
          
          count++;
        }
      }
      
      cJSON_Delete(root);
      if (count > 0) {
        return count;
      }
    }
  }
  
  /* If we couldn't load from JSON, return 0 to indicate failure */
  fprintf(stderr, "Error: Could not load test_messages.json\n");
  return 0;
}

void create_message_from_data(const test_message_t* test_msg, SerializationTestSerializationTestMessage* msg) {
  memset(msg, 0, sizeof(*msg));

  msg->magic_number = test_msg->magic_number;
  msg->test_string.length = strlen(test_msg->test_string);
  strncpy(msg->test_string.data, test_msg->test_string, sizeof(msg->test_string.data) - 1);
  msg->test_string.data[sizeof(msg->test_string.data) - 1] = '\0';
  msg->test_float = test_msg->test_float;
  msg->test_bool = test_msg->test_bool;
  msg->test_array.count = test_msg->test_array_count;
  for (size_t i = 0;
       i < test_msg->test_array_count && i < sizeof(msg->test_array.data) / sizeof(msg->test_array.data[0]); i++) {
    msg->test_array.data[i] = test_msg->test_array[i];
  }
}

bool validate_message(const SerializationTestSerializationTestMessage* msg, const test_message_t* test_msg) {
  if (msg->magic_number != test_msg->magic_number) {
    printf("  Value mismatch: magic_number (expected %u, got %u)\n", test_msg->magic_number, msg->magic_number);
    return false;
  }

  char decoded_str[MAX_STRING_LENGTH];
  strncpy(decoded_str, msg->test_string.data, msg->test_string.length);
  decoded_str[msg->test_string.length] = '\0';

  if (strcmp(decoded_str, test_msg->test_string) != 0) {
    printf("  Value mismatch: test_string (expected '%s', got '%s')\n", test_msg->test_string, decoded_str);
    return false;
  }

  if (fabs(msg->test_float - test_msg->test_float) > 0.01f) {
    printf("  Value mismatch: test_float (expected %f, got %f)\n", test_msg->test_float, msg->test_float);
    return false;
  }

  if (msg->test_bool != test_msg->test_bool) {
    printf("  Value mismatch: test_bool (expected %d, got %d)\n", test_msg->test_bool, msg->test_bool);
    return false;
  }

  if (msg->test_array.count != test_msg->test_array_count) {
    printf("  Value mismatch: test_array.count (expected %zu, got %u)\n", test_msg->test_array_count,
           msg->test_array.count);
    return false;
  }

  for (size_t i = 0; i < test_msg->test_array_count; i++) {
    if (msg->test_array.data[i] != test_msg->test_array[i]) {
      printf("  Value mismatch: test_array[%zu] (expected %d, got %d)\n", i, test_msg->test_array[i],
             msg->test_array.data[i]);
      return false;
    }
  }

  return true;
}

bool encode_test_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  test_message_t test_messages[MAX_TEST_MESSAGES];
  size_t msg_count = load_test_messages(test_messages, MAX_TEST_MESSAGES);

  if (msg_count == 0) {
    printf("  Failed to load test messages\n");
    return false;
  }

  *encoded_size = 0;
  size_t offset = 0;

  for (size_t i = 0; i < msg_count; i++) {
    SerializationTestSerializationTestMessage msg;
    create_message_from_data(&test_messages[i], &msg);

    size_t msg_encoded_size = 0;

    if (strcmp(format, "profile_standard") == 0) {
      msg_encoded_size = basic_default_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (strcmp(format, "profile_sensor") == 0) {
      msg_encoded_size = tiny_minimal_encode(buffer + offset, buffer_size - offset,
                                             SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, (const uint8_t*)&msg,
                                             SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (strcmp(format, "profile_ipc") == 0) {
      msg_encoded_size = none_minimal_encode(buffer + offset, buffer_size - offset,
                                             SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, (const uint8_t*)&msg,
                                             SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (strcmp(format, "profile_bulk") == 0) {
      msg_encoded_size = basic_extended_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else if (strcmp(format, "profile_network") == 0) {
      msg_encoded_size = basic_extended_multi_system_stream_encode(
          buffer + offset, buffer_size - offset, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
          (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
    } else {
      printf("  Unknown frame format: %s\n", format);
      return false;
    }

    if (msg_encoded_size == 0) {
      printf("  Encoding failed for message %zu\n", i);
      return false;
    }

    offset += msg_encoded_size;
    *encoded_size = offset;
  }

  return *encoded_size > 0;
}

bool decode_test_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count) {
  test_message_t test_messages[MAX_TEST_MESSAGES];
  size_t msg_count = load_test_messages(test_messages, MAX_TEST_MESSAGES);

  if (msg_count == 0) {
    printf("  Failed to load test messages\n");
    *message_count = 0;
    return false;
  }

  size_t offset = 0;
  *message_count = 0;

  while (offset < buffer_size && *message_count < msg_count) {
    frame_msg_info_t decode_result;

    if (strcmp(format, "profile_standard") == 0) {
      decode_result = basic_default_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_sensor") == 0) {
      decode_result = tiny_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_ipc") == 0) {
      decode_result = none_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_bulk") == 0) {
      decode_result = basic_extended_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_network") == 0) {
      decode_result = basic_extended_multi_system_stream_validate_packet(buffer + offset, buffer_size - offset);
    } else {
      printf("  Unknown frame format: %s\n", format);
      return false;
    }

    if (!decode_result.valid) {
      printf("  Decoding failed for message %zu at offset %zu\n", *message_count, offset);
      if (buffer_size - offset >= 6) {
        printf("  Buffer first bytes: %02x %02x %02x %02x %02x %02x\n",
               buffer[offset], buffer[offset+1], buffer[offset+2], 
               buffer[offset+3], buffer[offset+4], buffer[offset+5]);
      }
      return false;
    }

    SerializationTestSerializationTestMessage msg;
    memcpy(&msg, decode_result.msg_data, sizeof(msg));

    if (!validate_message(&msg, &test_messages[*message_count])) {
      printf("  Validation failed for message %zu\n", *message_count);
      return false;
    }

    /* Calculate the size of this encoded message */
    size_t msg_size = 0;
    if (strcmp(format, "profile_standard") == 0) {
      msg_size = 4 + decode_result.msg_len + 2; /* header + payload + crc */
    } else if (strcmp(format, "profile_sensor") == 0) {
      msg_size = 2 + decode_result.msg_len; /* header + payload */
    } else if (strcmp(format, "profile_ipc") == 0) {
      msg_size = 1 + decode_result.msg_len; /* header + payload */
    } else if (strcmp(format, "profile_bulk") == 0) {
      msg_size = 6 + decode_result.msg_len + 2; /* header + payload + crc */
    } else if (strcmp(format, "profile_network") == 0) {
      msg_size = 9 + decode_result.msg_len + 2; /* header + payload + crc */
    }

    offset += msg_size;
    (*message_count)++;
  }

  if (*message_count != msg_count) {
    printf("  Expected %zu messages, but decoded %zu\n", msg_count, *message_count);
    return false;
  }

  if (offset != buffer_size) {
    printf("  Extra data after messages: expected %zu bytes, got %zu bytes\n", offset, buffer_size);
    return false;
  }

  return true;
}

/* Expected test values (from test_messages.json) - for backwards compatibility */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage* msg) {
  test_message_t test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  strncpy(test_msg.test_string, EXPECTED_TEST_STRING, MAX_STRING_LENGTH - 1);
  test_msg.test_string[MAX_STRING_LENGTH - 1] = '\0';
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array_count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    test_msg.test_array[i] = EXPECTED_TEST_ARRAY[i];
  }

  create_message_from_data(&test_msg, msg);
}

bool validate_test_message(const SerializationTestSerializationTestMessage* msg) {
  test_message_t test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  strncpy(test_msg.test_string, EXPECTED_TEST_STRING, MAX_STRING_LENGTH - 1);
  test_msg.test_string[MAX_STRING_LENGTH - 1] = '\0';
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array_count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    test_msg.test_array[i] = EXPECTED_TEST_ARRAY[i];
  }

  return validate_message(msg, &test_msg);
}

bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  return encode_test_messages(format, buffer, buffer_size, encoded_size);
}

bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg) {
  size_t message_count = 0;
  return decode_test_messages(format, buffer, buffer_size, &message_count);
}
