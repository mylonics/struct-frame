#include "test_codec.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "frame_parsers.h"
#include "serialization_test.sf.h"

/* 
 * Frame format helper functions - Use generated profile functions from frame_profiles.h
 * The manual implementations have been replaced with calls to the generated functions.
 */

/* Basic + Default -> Profile Standard */
static inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                          size_t msg_size) {
  return encode_profile_standard(buffer, buffer_size, msg_id, msg, msg_size);
}

static inline frame_msg_info_t basic_default_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_standard_buffer(buffer, length);
}

/* Tiny + Minimal -> Profile Sensor */
static inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  return encode_profile_sensor(buffer, buffer_size, msg_id, msg, msg_size);
}

static inline frame_msg_info_t tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_sensor_buffer(buffer, length, get_message_length);
}

/* None + Minimal -> Profile IPC */
static inline size_t none_minimal_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  return encode_profile_ipc(buffer, buffer_size, msg_id, msg, msg_size);
}

static inline frame_msg_info_t none_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_ipc_buffer(buffer, length, get_message_length);
}

/* Basic + Extended -> Profile Bulk */
static inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                           size_t msg_size) {
  return encode_profile_bulk(buffer, buffer_size, 0, msg_id, msg, msg_size);  /* pkg_id = 0 */
}

static inline frame_msg_info_t basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_bulk_buffer(buffer, length);
}

/* Basic + Extended Multi System Stream -> Profile Network */
static inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id,
                                                               const uint8_t* msg, size_t msg_size) {
  return encode_profile_network(buffer, buffer_size, 0, 0, 0, 0, msg_id, msg, msg_size);  /* seq=0, sys=0, comp=0, pkg=0 */
}

static inline frame_msg_info_t basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer,
                                                                                  size_t length) {
  return parse_profile_network_buffer(buffer, length);
}

/* Basic + Minimal - This combination is not a standard profile but is used in tests */
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

/* Tiny + Default - This combination is not a standard profile but is used in tests */
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

/* Load mixed test messages from test_messages.json */
size_t load_mixed_messages(mixed_message_t* messages, size_t max_count) {
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
      
      // Load MixedMessages array which specifies the sequence
      cJSON* mixed_array = cJSON_GetObjectItem(root, "MixedMessages");
      if (!mixed_array || !cJSON_IsArray(mixed_array)) {
        cJSON_Delete(root);
        continue;
      }
      
      // Load message data arrays
      cJSON* serial_msgs = cJSON_GetObjectItem(root, "SerializationTestMessage");
      cJSON* basic_msgs = cJSON_GetObjectItem(root, "BasicTypesMessage");
      cJSON* union_msgs = cJSON_GetObjectItem(root, "UnionTestMessage");
      
      if (!serial_msgs || !basic_msgs) {
        cJSON_Delete(root);
        continue;
      }
      
      size_t count = 0;
      cJSON* mix_item = NULL;
      cJSON_ArrayForEach(mix_item, mixed_array) {
        if (count >= max_count) break;
        
        cJSON* type_json = cJSON_GetObjectItem(mix_item, "type");
        cJSON* name_json = cJSON_GetObjectItem(mix_item, "name");
        
        if (!type_json || !name_json) continue;
        
        const char* type_str = cJSON_GetStringValue(type_json);
        const char* name_str = cJSON_GetStringValue(name_json);
        
        if (!type_str || !name_str) continue;
        
        // Find the message by name in the appropriate array
        cJSON* msg_data = NULL;
        cJSON* msg_array = NULL;
        message_type_t msg_type;
        
        if (strcmp(type_str, "SerializationTestMessage") == 0) {
          msg_type = MSG_TYPE_SERIALIZATION_TEST;
          msg_array = serial_msgs;
        } else if (strcmp(type_str, "BasicTypesMessage") == 0) {
          msg_type = MSG_TYPE_BASIC_TYPES;
          msg_array = basic_msgs;
        } else if (strcmp(type_str, "UnionTestMessage") == 0) {
          msg_type = MSG_TYPE_UNION_TEST;
          msg_array = union_msgs;
        } else {
          continue;
        }
        
        // Find message by name
        cJSON* item = NULL;
        cJSON_ArrayForEach(item, msg_array) {
          cJSON* item_name = cJSON_GetObjectItem(item, "name");
          if (item_name && strcmp(cJSON_GetStringValue(item_name), name_str) == 0) {
            msg_data = item;
            break;
          }
        }
        
        if (!msg_data) continue;
        
        messages[count].type = msg_type;
        
        if (msg_type == MSG_TYPE_SERIALIZATION_TEST) {
          // Parse SerializationTestMessage
          SerializationTestSerializationTestMessage* msg = &messages[count].data.serialization_test;
          memset(msg, 0, sizeof(*msg));
          
          cJSON* magic_number = cJSON_GetObjectItem(msg_data, "magic_number");
          cJSON* test_string = cJSON_GetObjectItem(msg_data, "test_string");
          cJSON* test_float = cJSON_GetObjectItem(msg_data, "test_float");
          cJSON* test_bool = cJSON_GetObjectItem(msg_data, "test_bool");
          cJSON* test_array = cJSON_GetObjectItem(msg_data, "test_array");
          
          if (magic_number) msg->magic_number = (uint32_t)cJSON_GetNumberValue(magic_number);
          if (test_string) {
            const char* str = cJSON_GetStringValue(test_string);
            msg->test_string.length = strlen(str);
            if (msg->test_string.length > 64) msg->test_string.length = 64;
            strncpy(msg->test_string.data, str, msg->test_string.length);
          }
          if (test_float) msg->test_float = (float)cJSON_GetNumberValue(test_float);
          if (test_bool) msg->test_bool = cJSON_IsTrue(test_bool);
          if (test_array && cJSON_IsArray(test_array)) {
            size_t idx = 0;
            cJSON* arr_item = NULL;
            cJSON_ArrayForEach(arr_item, test_array) {
              if (idx >= 5) break;
              msg->test_array.data[idx++] = (int32_t)cJSON_GetNumberValue(arr_item);
            }
            msg->test_array.count = idx;
          }
        } else if (msg_type == MSG_TYPE_BASIC_TYPES) {
          // Parse BasicTypesMessage
          SerializationTestBasicTypesMessage* msg = &messages[count].data.basic_types;
          memset(msg, 0, sizeof(*msg));
          
          cJSON* field = NULL;
          if ((field = cJSON_GetObjectItem(msg_data, "small_int"))) msg->small_int = (int8_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "medium_int"))) msg->medium_int = (int16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "regular_int"))) msg->regular_int = (int32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "large_int"))) {
            // large_int is stored as string in JSON to preserve precision
            const char* str = cJSON_GetStringValue(field);
            if (str) {
              msg->large_int = (int64_t)strtoll(str, NULL, 10);
            } else {
              msg->large_int = (int64_t)cJSON_GetNumberValue(field);
            }
          }
          if ((field = cJSON_GetObjectItem(msg_data, "small_uint"))) msg->small_uint = (uint8_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "medium_uint"))) msg->medium_uint = (uint16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "regular_uint"))) msg->regular_uint = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "large_uint"))) {
            // large_uint is stored as string in JSON to preserve precision
            const char* str = cJSON_GetStringValue(field);
            if (str) {
              msg->large_uint = (uint64_t)strtoull(str, NULL, 10);
            } else {
              msg->large_uint = (uint64_t)cJSON_GetNumberValue(field);
            }
          }
          if ((field = cJSON_GetObjectItem(msg_data, "single_precision"))) msg->single_precision = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "double_precision"))) msg->double_precision = cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "flag"))) msg->flag = cJSON_IsTrue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "device_id"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->device_id, str, 32);
            msg->device_id[31] = '\0';
          }
          if ((field = cJSON_GetObjectItem(msg_data, "description"))) {
            const char* str = cJSON_GetStringValue(field);
            msg->description.length = strlen(str);
            if (msg->description.length > 128) msg->description.length = 128;
            strncpy(msg->description.data, str, msg->description.length);
          }
        } else if (msg_type == MSG_TYPE_UNION_TEST) {
          // Parse UnionTestMessage
          SerializationTestUnionTestMessage* msg = &messages[count].data.union_test;
          memset(msg, 0, sizeof(*msg));
          
          // Parse array_payload if present
          cJSON* array_payload = cJSON_GetObjectItem(msg_data, "array_payload");
          if (array_payload && !cJSON_IsNull(array_payload)) {
            // Set discriminator to ComprehensiveArrayMessage ID
            msg->payload_discriminator = SERIALIZATION_TEST_COMPREHENSIVE_ARRAY_MESSAGE_MSG_ID;
            cJSON* field = NULL;
            
            // fixed_ints
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_ints")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 3) break;
                msg->payload.array_payload.fixed_ints[idx++] = (int32_t)cJSON_GetNumberValue(item);
              }
            }
            
            // fixed_floats
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_floats")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                msg->payload.array_payload.fixed_floats[idx++] = (float)cJSON_GetNumberValue(item);
              }
            }
            
            // fixed_bools
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_bools")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 4) break;
                msg->payload.array_payload.fixed_bools[idx++] = cJSON_IsTrue(item);
              }
            }
            
            // bounded_uints
            if ((field = cJSON_GetObjectItem(array_payload, "bounded_uints")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 3) break;
                msg->payload.array_payload.bounded_uints.data[idx++] = (uint16_t)cJSON_GetNumberValue(item);
              }
              msg->payload.array_payload.bounded_uints.count = idx;
            }
            
            // bounded_doubles
            if ((field = cJSON_GetObjectItem(array_payload, "bounded_doubles")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                msg->payload.array_payload.bounded_doubles.data[idx++] = cJSON_GetNumberValue(item);
              }
              msg->payload.array_payload.bounded_doubles.count = idx;
            }
            
            // fixed_strings
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_strings")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                const char* str = cJSON_GetStringValue(item);
                if (str) {
                  strncpy(msg->payload.array_payload.fixed_strings[idx], str, 8);
                  msg->payload.array_payload.fixed_strings[idx][7] = '\0';
                }
                idx++;
              }
            }
            
            // bounded_strings
            if ((field = cJSON_GetObjectItem(array_payload, "bounded_strings")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                const char* str = cJSON_GetStringValue(item);
                if (str) {
                  strncpy(msg->payload.array_payload.bounded_strings.data[idx], str, 12);
                  msg->payload.array_payload.bounded_strings.data[idx][11] = '\0';
                }
                idx++;
              }
              msg->payload.array_payload.bounded_strings.count = idx;
            }
            
            // fixed_statuses
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_statuses")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                msg->payload.array_payload.fixed_statuses[idx++] = (uint8_t)cJSON_GetNumberValue(item);
              }
            }
            
            // bounded_statuses
            if ((field = cJSON_GetObjectItem(array_payload, "bounded_statuses")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 2) break;
                msg->payload.array_payload.bounded_statuses.data[idx++] = (uint8_t)cJSON_GetNumberValue(item);
              }
              msg->payload.array_payload.bounded_statuses.count = idx;
            }
            
            // fixed_sensors
            if ((field = cJSON_GetObjectItem(array_payload, "fixed_sensors")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 1) break;
                cJSON* sensor_id = cJSON_GetObjectItem(item, "id");
                cJSON* sensor_value = cJSON_GetObjectItem(item, "value");
                cJSON* sensor_status = cJSON_GetObjectItem(item, "status");
                cJSON* sensor_name = cJSON_GetObjectItem(item, "name");
                if (sensor_id) msg->payload.array_payload.fixed_sensors[idx].id = (uint8_t)cJSON_GetNumberValue(sensor_id);
                if (sensor_value) msg->payload.array_payload.fixed_sensors[idx].value = (float)cJSON_GetNumberValue(sensor_value);
                if (sensor_status) msg->payload.array_payload.fixed_sensors[idx].status = (uint8_t)cJSON_GetNumberValue(sensor_status);
                if (sensor_name) {
                  const char* str = cJSON_GetStringValue(sensor_name);
                  if (str) strncpy(msg->payload.array_payload.fixed_sensors[idx].name, str, 16);
                }
                idx++;
              }
            }
            
            // bounded_sensors
            if ((field = cJSON_GetObjectItem(array_payload, "bounded_sensors")) && cJSON_IsArray(field)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, field) {
                if (idx >= 1) break;
                cJSON* sensor_id = cJSON_GetObjectItem(item, "id");
                cJSON* sensor_value = cJSON_GetObjectItem(item, "value");
                cJSON* sensor_status = cJSON_GetObjectItem(item, "status");
                cJSON* sensor_name = cJSON_GetObjectItem(item, "name");
                if (sensor_id) msg->payload.array_payload.bounded_sensors.data[idx].id = (uint8_t)cJSON_GetNumberValue(sensor_id);
                if (sensor_value) msg->payload.array_payload.bounded_sensors.data[idx].value = (float)cJSON_GetNumberValue(sensor_value);
                if (sensor_status) msg->payload.array_payload.bounded_sensors.data[idx].status = (uint8_t)cJSON_GetNumberValue(sensor_status);
                if (sensor_name) {
                  const char* str = cJSON_GetStringValue(sensor_name);
                  if (str) strncpy(msg->payload.array_payload.bounded_sensors.data[idx].name, str, 16);
                }
                idx++;
              }
              msg->payload.array_payload.bounded_sensors.count = idx;
            }
          }
          
          // Parse test_payload if present
          cJSON* test_payload = cJSON_GetObjectItem(msg_data, "test_payload");
          if (test_payload && !cJSON_IsNull(test_payload)) {
            // Set discriminator to SerializationTestMessage ID
            msg->payload_discriminator = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
            cJSON* magic = cJSON_GetObjectItem(test_payload, "magic_number");
            cJSON* tstr = cJSON_GetObjectItem(test_payload, "test_string");
            cJSON* tflt = cJSON_GetObjectItem(test_payload, "test_float");
            cJSON* tbool = cJSON_GetObjectItem(test_payload, "test_bool");
            cJSON* tarr = cJSON_GetObjectItem(test_payload, "test_array");
            
            if (magic) msg->payload.test_payload.magic_number = (uint32_t)cJSON_GetNumberValue(magic);
            if (tstr) {
              const char* str = cJSON_GetStringValue(tstr);
              msg->payload.test_payload.test_string.length = strlen(str);
              if (msg->payload.test_payload.test_string.length > 64) msg->payload.test_payload.test_string.length = 64;
              strncpy(msg->payload.test_payload.test_string.data, str, msg->payload.test_payload.test_string.length);
            }
            if (tflt) msg->payload.test_payload.test_float = (float)cJSON_GetNumberValue(tflt);
            if (tbool) msg->payload.test_payload.test_bool = cJSON_IsTrue(tbool);
            if (tarr && cJSON_IsArray(tarr)) {
              size_t idx = 0;
              cJSON* item = NULL;
              cJSON_ArrayForEach(item, tarr) {
                if (idx >= 5) break;
                msg->payload.test_payload.test_array.data[idx++] = (int32_t)cJSON_GetNumberValue(item);
              }
              msg->payload.test_payload.test_array.count = idx;
            }
          }
        }
        
        count++;
      }
      
      cJSON_Delete(root);
      if (count > 0) {
        return count;
      }
    }
  }
  
  fprintf(stderr, "Error: Could not load mixed messages from test_messages.json\n");
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
  mixed_message_t mixed_messages[MAX_TEST_MESSAGES];
  size_t msg_count = load_mixed_messages(mixed_messages, MAX_TEST_MESSAGES);

  if (msg_count == 0) {
    printf("  Failed to load mixed test messages\n");
    return false;
  }

  *encoded_size = 0;
  size_t offset = 0;

  for (size_t i = 0; i < msg_count; i++) {
    size_t msg_encoded_size = 0;
    uint8_t msg_id;
    const uint8_t* msg_ptr;
    size_t msg_size;
    
    if (mixed_messages[i].type == MSG_TYPE_SERIALIZATION_TEST) {
      msg_id = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&mixed_messages[i].data.serialization_test;
      msg_size = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE;
    } else if (mixed_messages[i].type == MSG_TYPE_BASIC_TYPES) {
      msg_id = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&mixed_messages[i].data.basic_types;
      msg_size = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAX_SIZE;
    } else if (mixed_messages[i].type == MSG_TYPE_UNION_TEST) {
      msg_id = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&mixed_messages[i].data.union_test;
      msg_size = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MAX_SIZE;
    } else {
      printf("  Unknown message type for message %zu\n", i);
      return false;
    }

    if (strcmp(format, "profile_standard") == 0) {
      msg_encoded_size = basic_default_encode(
          buffer + offset, buffer_size - offset, msg_id, msg_ptr, msg_size);
    } else if (strcmp(format, "profile_sensor") == 0) {
      msg_encoded_size = tiny_minimal_encode(buffer + offset, buffer_size - offset,
                                             msg_id, msg_ptr, msg_size);
    } else if (strcmp(format, "profile_ipc") == 0) {
      msg_encoded_size = none_minimal_encode(buffer + offset, buffer_size - offset,
                                             msg_id, msg_ptr, msg_size);
    } else if (strcmp(format, "profile_bulk") == 0) {
      msg_encoded_size = basic_extended_encode(
          buffer + offset, buffer_size - offset, msg_id, msg_ptr, msg_size);
    } else if (strcmp(format, "profile_network") == 0) {
      msg_encoded_size = basic_extended_multi_system_stream_encode(
          buffer + offset, buffer_size - offset, msg_id, msg_ptr, msg_size);
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
  mixed_message_t mixed_messages[MAX_TEST_MESSAGES];
  size_t msg_count = load_mixed_messages(mixed_messages, MAX_TEST_MESSAGES);

  if (msg_count == 0) {
    printf("  Failed to load mixed test messages\n");
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

    // Validate msg_id matches expected type
    uint8_t expected_msg_id;
    if (mixed_messages[*message_count].type == MSG_TYPE_SERIALIZATION_TEST) {
      expected_msg_id = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
    } else if (mixed_messages[*message_count].type == MSG_TYPE_BASIC_TYPES) {
      expected_msg_id = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID;
    } else if (mixed_messages[*message_count].type == MSG_TYPE_UNION_TEST) {
      expected_msg_id = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID;
    } else {
      printf("  Unknown message type for message %zu\n", *message_count);
      return false;
    }

    if (decode_result.msg_id != expected_msg_id) {
      printf("  Message ID mismatch for message %zu: expected %u, got %u\n", 
             *message_count, expected_msg_id, decode_result.msg_id);
      return false;
    }

    // Verify the decoded message matches expected data
    // For now, we just check that it decoded correctly
    // Full validation would require comparing all fields for both message types

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
