/**
 * Test codec - Extended message ID and payload tests (C).
 */

#include "test_codec_extended.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "frame_parsers.h"
#include "extended_test.sf.h"

/* Extended message types */
typedef enum extended_message_type {
  EXT_MSG_TYPE_ID1 = 0,
  EXT_MSG_TYPE_ID2,
  EXT_MSG_TYPE_ID3,
  EXT_MSG_TYPE_ID4,
  EXT_MSG_TYPE_ID5,
  EXT_MSG_TYPE_ID6,
  EXT_MSG_TYPE_ID7,
  EXT_MSG_TYPE_ID8,
  EXT_MSG_TYPE_ID9,
  EXT_MSG_TYPE_ID10,
  EXT_MSG_TYPE_LARGE1,
  EXT_MSG_TYPE_LARGE2
} extended_message_type_t;

/* Mixed message union for extended tests */
typedef struct extended_mixed_message {
  extended_message_type_t type;
  union {
    ExtendedTestExtendedIdMessage1 ext_id_1;
    ExtendedTestExtendedIdMessage2 ext_id_2;
    ExtendedTestExtendedIdMessage3 ext_id_3;
    ExtendedTestExtendedIdMessage4 ext_id_4;
    ExtendedTestExtendedIdMessage5 ext_id_5;
    ExtendedTestExtendedIdMessage6 ext_id_6;
    ExtendedTestExtendedIdMessage7 ext_id_7;
    ExtendedTestExtendedIdMessage8 ext_id_8;
    ExtendedTestExtendedIdMessage9 ext_id_9;
    ExtendedTestExtendedIdMessage10 ext_id_10;
    ExtendedTestLargePayloadMessage1 large_1;
    ExtendedTestLargePayloadMessage2 large_2;
  } data;
} extended_mixed_message_t;

#define MAX_EXTENDED_MESSAGES 20

/* Helper functions */
static int64_t parse_int64(cJSON* field) {
  if (cJSON_IsString(field)) {
    return (int64_t)strtoll(cJSON_GetStringValue(field), NULL, 10);
  }
  return (int64_t)cJSON_GetNumberValue(field);
}

static uint64_t parse_uint64(cJSON* field) {
  if (cJSON_IsString(field)) {
    return (uint64_t)strtoull(cJSON_GetStringValue(field), NULL, 10);
  }
  return (uint64_t)cJSON_GetNumberValue(field);
}

/* Load extended messages from JSON */
static size_t load_extended_messages(extended_mixed_message_t* messages, size_t max_count) {
  const char* possible_paths[] = {
    "../extended_messages.json",
    "../../extended_messages.json",
    "extended_messages.json",
    "../../../tests/extended_messages.json"
  };
  
  for (size_t i = 0; i < sizeof(possible_paths) / sizeof(possible_paths[0]); i++) {
    FILE* file = fopen(possible_paths[i], "r");
    if (!file) continue;
    
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
    
    if (!root) continue;
    
    cJSON* mixed_array = cJSON_GetObjectItem(root, "MixedMessages");
    if (!mixed_array || !cJSON_IsArray(mixed_array)) {
      cJSON_Delete(root);
      continue;
    }
    
    /* Get message data arrays */
    cJSON* ext_id_1_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage1");
    cJSON* ext_id_2_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage2");
    cJSON* ext_id_3_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage3");
    cJSON* ext_id_4_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage4");
    cJSON* ext_id_5_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage5");
    cJSON* ext_id_6_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage6");
    cJSON* ext_id_7_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage7");
    cJSON* ext_id_8_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage8");
    cJSON* ext_id_9_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage9");
    cJSON* ext_id_10_arr = cJSON_GetObjectItem(root, "ExtendedIdMessage10");
    cJSON* large_1_arr = cJSON_GetObjectItem(root, "LargePayloadMessage1");
    cJSON* large_2_arr = cJSON_GetObjectItem(root, "LargePayloadMessage2");
    
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
      
      /* Determine message type and find data */
      cJSON* msg_array = NULL;
      extended_message_type_t msg_type;
      
      if (strcmp(type_str, "ExtendedIdMessage1") == 0) {
        msg_type = EXT_MSG_TYPE_ID1;
        msg_array = ext_id_1_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage2") == 0) {
        msg_type = EXT_MSG_TYPE_ID2;
        msg_array = ext_id_2_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage3") == 0) {
        msg_type = EXT_MSG_TYPE_ID3;
        msg_array = ext_id_3_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage4") == 0) {
        msg_type = EXT_MSG_TYPE_ID4;
        msg_array = ext_id_4_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage5") == 0) {
        msg_type = EXT_MSG_TYPE_ID5;
        msg_array = ext_id_5_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage6") == 0) {
        msg_type = EXT_MSG_TYPE_ID6;
        msg_array = ext_id_6_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage7") == 0) {
        msg_type = EXT_MSG_TYPE_ID7;
        msg_array = ext_id_7_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage8") == 0) {
        msg_type = EXT_MSG_TYPE_ID8;
        msg_array = ext_id_8_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage9") == 0) {
        msg_type = EXT_MSG_TYPE_ID9;
        msg_array = ext_id_9_arr;
      } else if (strcmp(type_str, "ExtendedIdMessage10") == 0) {
        msg_type = EXT_MSG_TYPE_ID10;
        msg_array = ext_id_10_arr;
      } else if (strcmp(type_str, "LargePayloadMessage1") == 0) {
        msg_type = EXT_MSG_TYPE_LARGE1;
        msg_array = large_1_arr;
      } else if (strcmp(type_str, "LargePayloadMessage2") == 0) {
        msg_type = EXT_MSG_TYPE_LARGE2;
        msg_array = large_2_arr;
      } else {
        continue;
      }
      
      if (!msg_array) continue;
      
      /* Find message data by name */
      cJSON* msg_data = NULL;
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
      
      /* Parse message data based on type */
      switch (msg_type) {
        case EXT_MSG_TYPE_ID1: {
          ExtendedTestExtendedIdMessage1* msg = &messages[count].data.ext_id_1;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "sequence_number")))
            msg->sequence_number = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "label"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->label, str, sizeof(msg->label) - 1);
          }
          if ((field = cJSON_GetObjectItem(msg_data, "value")))
            msg->value = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "enabled")))
            msg->enabled = cJSON_IsTrue(field);
          break;
        }
        case EXT_MSG_TYPE_ID2: {
          ExtendedTestExtendedIdMessage2* msg = &messages[count].data.ext_id_2;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "sensor_id")))
            msg->sensor_id = (int32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "reading")))
            msg->reading = cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "status_code")))
            msg->status_code = (uint16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "description"))) {
            const char* str = cJSON_GetStringValue(field);
            msg->description.length = strlen(str);
            if (msg->description.length > sizeof(msg->description.data) - 1)
              msg->description.length = sizeof(msg->description.data) - 1;
            strncpy(msg->description.data, str, msg->description.length);
          }
          break;
        }
        case EXT_MSG_TYPE_ID3: {
          ExtendedTestExtendedIdMessage3* msg = &messages[count].data.ext_id_3;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "timestamp")))
            msg->timestamp = parse_uint64(field);
          if ((field = cJSON_GetObjectItem(msg_data, "temperature")))
            msg->temperature = (int16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "humidity")))
            msg->humidity = (uint8_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "location"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->location, str, sizeof(msg->location) - 1);
          }
          break;
        }
        case EXT_MSG_TYPE_ID4: {
          ExtendedTestExtendedIdMessage4* msg = &messages[count].data.ext_id_4;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "event_id")))
            msg->event_id = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "event_type")))
            msg->event_type = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "event_time")))
            msg->event_time = parse_int64(field);
          if ((field = cJSON_GetObjectItem(msg_data, "event_data"))) {
            const char* str = cJSON_GetStringValue(field);
            msg->event_data.length = strlen(str);
            if (msg->event_data.length > sizeof(msg->event_data.data) - 1)
              msg->event_data.length = sizeof(msg->event_data.data) - 1;
            strncpy(msg->event_data.data, str, msg->event_data.length);
          }
          break;
        }
        case EXT_MSG_TYPE_ID5: {
          ExtendedTestExtendedIdMessage5* msg = &messages[count].data.ext_id_5;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "x_position")))
            msg->x_position = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "y_position")))
            msg->y_position = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "z_position")))
            msg->z_position = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "frame_number")))
            msg->frame_number = (uint32_t)cJSON_GetNumberValue(field);
          break;
        }
        case EXT_MSG_TYPE_ID6: {
          ExtendedTestExtendedIdMessage6* msg = &messages[count].data.ext_id_6;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "command_id")))
            msg->command_id = (int32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "parameter1")))
            msg->parameter1 = (uint16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "parameter2")))
            msg->parameter2 = (uint16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "acknowledged")))
            msg->acknowledged = cJSON_IsTrue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "command_name"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->command_name, str, sizeof(msg->command_name) - 1);
          }
          break;
        }
        case EXT_MSG_TYPE_ID7: {
          ExtendedTestExtendedIdMessage7* msg = &messages[count].data.ext_id_7;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "counter")))
            msg->counter = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "average")))
            msg->average = cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "minimum")))
            msg->minimum = (float)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "maximum")))
            msg->maximum = (float)cJSON_GetNumberValue(field);
          break;
        }
        case EXT_MSG_TYPE_ID8: {
          ExtendedTestExtendedIdMessage8* msg = &messages[count].data.ext_id_8;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "level")))
            msg->level = (uint8_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "offset")))
            msg->offset = (int16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "duration")))
            msg->duration = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "tag"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->tag, str, sizeof(msg->tag) - 1);
          }
          break;
        }
        case EXT_MSG_TYPE_ID9: {
          ExtendedTestExtendedIdMessage9* msg = &messages[count].data.ext_id_9;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "big_number")))
            msg->big_number = parse_int64(field);
          if ((field = cJSON_GetObjectItem(msg_data, "big_unsigned")))
            msg->big_unsigned = parse_uint64(field);
          if ((field = cJSON_GetObjectItem(msg_data, "precision_value")))
            msg->precision_value = cJSON_GetNumberValue(field);
          break;
        }
        case EXT_MSG_TYPE_ID10: {
          ExtendedTestExtendedIdMessage10* msg = &messages[count].data.ext_id_10;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "small_value")))
            msg->small_value = (uint16_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "short_text"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->short_text, str, sizeof(msg->short_text) - 1);
          }
          if ((field = cJSON_GetObjectItem(msg_data, "flag")))
            msg->flag = cJSON_IsTrue(field);
          break;
        }
        case EXT_MSG_TYPE_LARGE1: {
          ExtendedTestLargePayloadMessage1* msg = &messages[count].data.large_1;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "sensor_readings")) && cJSON_IsArray(field)) {
            size_t idx = 0;
            cJSON* arr_item = NULL;
            cJSON_ArrayForEach(arr_item, field) {
              if (idx >= 64) break;
              msg->sensor_readings[idx++] = (float)cJSON_GetNumberValue(arr_item);
            }
          }
          if ((field = cJSON_GetObjectItem(msg_data, "reading_count")))
            msg->reading_count = (uint32_t)cJSON_GetNumberValue(field);
          if ((field = cJSON_GetObjectItem(msg_data, "timestamp")))
            msg->timestamp = parse_int64(field);
          if ((field = cJSON_GetObjectItem(msg_data, "device_name"))) {
            const char* str = cJSON_GetStringValue(field);
            strncpy(msg->device_name, str, sizeof(msg->device_name) - 1);
          }
          break;
        }
        case EXT_MSG_TYPE_LARGE2: {
          ExtendedTestLargePayloadMessage2* msg = &messages[count].data.large_2;
          memset(msg, 0, sizeof(*msg));
          cJSON* field;
          if ((field = cJSON_GetObjectItem(msg_data, "large_data")) && cJSON_IsArray(field)) {
            size_t idx = 0;
            cJSON* arr_item = NULL;
            cJSON_ArrayForEach(arr_item, field) {
              if (idx >= 280) break;
              msg->large_data[idx++] = (uint8_t)cJSON_GetNumberValue(arr_item);
            }
          }
          break;
        }
      }
      
      count++;
    }
    
    cJSON_Delete(root);
    if (count > 0) {
      return count;
    }
  }
  
  fprintf(stderr, "Error: Could not load extended_messages.json\n");
  return 0;
}

/* Get message ID for extended message type */
static uint16_t get_extended_msg_id(extended_message_type_t type) {
  switch (type) {
    case EXT_MSG_TYPE_ID1: return EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MSG_ID;
    case EXT_MSG_TYPE_ID2: return EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID;
    case EXT_MSG_TYPE_ID3: return EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MSG_ID;
    case EXT_MSG_TYPE_ID4: return EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MSG_ID;
    case EXT_MSG_TYPE_ID5: return EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MSG_ID;
    case EXT_MSG_TYPE_ID6: return EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MSG_ID;
    case EXT_MSG_TYPE_ID7: return EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MSG_ID;
    case EXT_MSG_TYPE_ID8: return EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MSG_ID;
    case EXT_MSG_TYPE_ID9: return EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID;
    case EXT_MSG_TYPE_ID10: return EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID;
    case EXT_MSG_TYPE_LARGE1: return EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID;
    case EXT_MSG_TYPE_LARGE2: return EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID;
    default: return 0;
  }
}

/* Get message size for extended message type */
static size_t get_extended_msg_size(extended_message_type_t type) {
  switch (type) {
    case EXT_MSG_TYPE_ID1: return EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MAX_SIZE;
    case EXT_MSG_TYPE_ID2: return EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAX_SIZE;
    case EXT_MSG_TYPE_ID3: return EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MAX_SIZE;
    case EXT_MSG_TYPE_ID4: return EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MAX_SIZE;
    case EXT_MSG_TYPE_ID5: return EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MAX_SIZE;
    case EXT_MSG_TYPE_ID6: return EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MAX_SIZE;
    case EXT_MSG_TYPE_ID7: return EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MAX_SIZE;
    case EXT_MSG_TYPE_ID8: return EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MAX_SIZE;
    case EXT_MSG_TYPE_ID9: return EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAX_SIZE;
    case EXT_MSG_TYPE_ID10: return EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAX_SIZE;
    case EXT_MSG_TYPE_LARGE1: return EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAX_SIZE;
    case EXT_MSG_TYPE_LARGE2: return EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAX_SIZE;
    default: return 0;
  }
}

/* Get message pointer for extended message */
static const uint8_t* get_extended_msg_ptr(const extended_mixed_message_t* msg) {
  switch (msg->type) {
    case EXT_MSG_TYPE_ID1: return (const uint8_t*)&msg->data.ext_id_1;
    case EXT_MSG_TYPE_ID2: return (const uint8_t*)&msg->data.ext_id_2;
    case EXT_MSG_TYPE_ID3: return (const uint8_t*)&msg->data.ext_id_3;
    case EXT_MSG_TYPE_ID4: return (const uint8_t*)&msg->data.ext_id_4;
    case EXT_MSG_TYPE_ID5: return (const uint8_t*)&msg->data.ext_id_5;
    case EXT_MSG_TYPE_ID6: return (const uint8_t*)&msg->data.ext_id_6;
    case EXT_MSG_TYPE_ID7: return (const uint8_t*)&msg->data.ext_id_7;
    case EXT_MSG_TYPE_ID8: return (const uint8_t*)&msg->data.ext_id_8;
    case EXT_MSG_TYPE_ID9: return (const uint8_t*)&msg->data.ext_id_9;
    case EXT_MSG_TYPE_ID10: return (const uint8_t*)&msg->data.ext_id_10;
    case EXT_MSG_TYPE_LARGE1: return (const uint8_t*)&msg->data.large_1;
    case EXT_MSG_TYPE_LARGE2: return (const uint8_t*)&msg->data.large_2;
    default: return NULL;
  }
}

bool encode_extended_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  extended_mixed_message_t messages[MAX_EXTENDED_MESSAGES];
  size_t msg_count = load_extended_messages(messages, MAX_EXTENDED_MESSAGES);
  
  if (msg_count == 0) {
    printf("  Failed to load extended test messages\n");
    return false;
  }
  
  *encoded_size = 0;
  size_t offset = 0;
  
  for (size_t i = 0; i < msg_count; i++) {
    uint16_t msg_id = get_extended_msg_id(messages[i].type);
    size_t msg_size = get_extended_msg_size(messages[i].type);
    const uint8_t* msg_ptr = get_extended_msg_ptr(&messages[i]);
    
    if (!msg_ptr) {
      printf("  Unknown message type for message %zu\n", i);
      return false;
    }
    
    size_t msg_encoded_size = 0;
    
    if (strcmp(format, "profile_bulk") == 0) {
      msg_encoded_size = encode_profile_bulk(buffer + offset, buffer_size - offset, msg_id, msg_ptr, msg_size);
    } else if (strcmp(format, "profile_network") == 0) {
      msg_encoded_size = encode_profile_network(buffer + offset, buffer_size - offset, 0, 0, 0, msg_id, msg_ptr, msg_size);
    } else {
      printf("  Unknown or unsupported frame format for extended tests: %s\n", format);
      return false;
    }
    
    if (msg_encoded_size == 0) {
      printf("  Encoding failed for message %zu (msg_id=%u)\n", i, msg_id);
      return false;
    }
    
    offset += msg_encoded_size;
    *encoded_size = offset;
  }
  
  return *encoded_size > 0;
}

bool decode_extended_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count) {
  extended_mixed_message_t messages[MAX_EXTENDED_MESSAGES];
  size_t msg_count = load_extended_messages(messages, MAX_EXTENDED_MESSAGES);
  
  if (msg_count == 0) {
    printf("  Failed to load extended test messages\n");
    *message_count = 0;
    return false;
  }
  
  size_t offset = 0;
  *message_count = 0;
  
  while (offset < buffer_size && *message_count < msg_count) {
    frame_msg_info_t decode_result;
    
    if (strcmp(format, "profile_bulk") == 0) {
      decode_result = parse_profile_bulk_buffer(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_network") == 0) {
      decode_result = parse_profile_network_buffer(buffer + offset, buffer_size - offset);
    } else {
      printf("  Unknown or unsupported frame format for extended tests: %s\n", format);
      return false;
    }
    
    if (!decode_result.valid) {
      printf("  Decoding failed for message %zu at offset %zu\n", *message_count, offset);
      if (buffer_size - offset >= 8) {
        printf("  Buffer first bytes: %02x %02x %02x %02x %02x %02x %02x %02x\n",
               buffer[offset], buffer[offset+1], buffer[offset+2], buffer[offset+3],
               buffer[offset+4], buffer[offset+5], buffer[offset+6], buffer[offset+7]);
      }
      return false;
    }
    
    /* Validate msg_id matches expected type */
    uint16_t expected_msg_id = get_extended_msg_id(messages[*message_count].type);
    
    if (decode_result.msg_id != expected_msg_id) {
      printf("  Message ID mismatch for message %zu: expected %u, got %u\n",
             *message_count, expected_msg_id, decode_result.msg_id);
      return false;
    }
    
    /* Calculate the size of this encoded message */
    size_t msg_size = 0;
    if (strcmp(format, "profile_bulk") == 0) {
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
