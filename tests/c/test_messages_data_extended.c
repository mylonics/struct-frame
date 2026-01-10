/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 */

#include "test_messages_data_extended.h"
#include <stdio.h>
#include <string.h>

#define EXTENDED_TEST_MESSAGE_COUNT 12

size_t get_extended_test_message_count(void) {
  return EXTENDED_TEST_MESSAGE_COUNT;
}

bool get_extended_test_message(size_t index, extended_mixed_message_t* out_message) {
  if (index >= EXTENDED_TEST_MESSAGE_COUNT || !out_message) {
    return false;
  }

  memset(out_message, 0, sizeof(extended_mixed_message_t));

  switch (index) {
    case 0: { // ExtendedIdMessage1
      out_message->type = EXT_MSG_TYPE_ID1;
      out_message->data.ext_id_1.sequence_number = 12345678;
      strncpy(out_message->data.ext_id_1.label, "Test Label Extended 1", 31);
      out_message->data.ext_id_1.label[31] = '\0';
      out_message->data.ext_id_1.value = 3.14159f;
      out_message->data.ext_id_1.enabled = true;
      break;
    }

    case 1: { // ExtendedIdMessage2
      out_message->type = EXT_MSG_TYPE_ID2;
      out_message->data.ext_id_2.sensor_id = -42;
      out_message->data.ext_id_2.reading = 2.718281828;
      out_message->data.ext_id_2.status_code = 50000;
      strncpy(out_message->data.ext_id_2.description.data, "Extended ID test message 2", 63);
      out_message->data.ext_id_2.description.data[63] = '\0';
      out_message->data.ext_id_2.description.length = strlen(out_message->data.ext_id_2.description.data);
      break;
    }

    case 2: { // ExtendedIdMessage3
      out_message->type = EXT_MSG_TYPE_ID3;
      out_message->data.ext_id_3.timestamp = 1704067200000000ULL;
      out_message->data.ext_id_3.temperature = -40;
      out_message->data.ext_id_3.humidity = 85;
      strncpy(out_message->data.ext_id_3.location, "Sensor Room A", 15);
      out_message->data.ext_id_3.location[15] = '\0';
      break;
    }

    case 3: { // ExtendedIdMessage4
      out_message->type = EXT_MSG_TYPE_ID4;
      out_message->data.ext_id_4.event_id = 999999;
      out_message->data.ext_id_4.event_type = 42;
      out_message->data.ext_id_4.event_time = 1704067200000LL;
      strncpy(out_message->data.ext_id_4.event_data.data, "Event payload with extended message ID", 127);
      out_message->data.ext_id_4.event_data.data[127] = '\0';
      out_message->data.ext_id_4.event_data.length = strlen(out_message->data.ext_id_4.event_data.data);
      break;
    }

    case 4: { // ExtendedIdMessage5
      out_message->type = EXT_MSG_TYPE_ID5;
      out_message->data.ext_id_5.x_position = 100.5f;
      out_message->data.ext_id_5.y_position = -200.25f;
      out_message->data.ext_id_5.z_position = 50.125f;
      out_message->data.ext_id_5.frame_number = 1000000;
      break;
    }

    case 5: { // ExtendedIdMessage6
      out_message->type = EXT_MSG_TYPE_ID6;
      out_message->data.ext_id_6.command_id = -12345;
      out_message->data.ext_id_6.parameter1 = 1000;
      out_message->data.ext_id_6.parameter2 = 2000;
      out_message->data.ext_id_6.acknowledged = false;
      strncpy(out_message->data.ext_id_6.command_name, "CALIBRATE_SENSOR", 23);
      out_message->data.ext_id_6.command_name[23] = '\0';
      break;
    }

    case 6: { // ExtendedIdMessage7
      out_message->type = EXT_MSG_TYPE_ID7;
      out_message->data.ext_id_7.counter = 4294967295U;
      out_message->data.ext_id_7.average = 123.456789;
      out_message->data.ext_id_7.minimum = -999.99f;
      out_message->data.ext_id_7.maximum = 999.99f;
      break;
    }

    case 7: { // ExtendedIdMessage8
      out_message->type = EXT_MSG_TYPE_ID8;
      out_message->data.ext_id_8.level = 255;
      out_message->data.ext_id_8.offset = -32768;
      out_message->data.ext_id_8.duration = 86400000;
      strncpy(out_message->data.ext_id_8.tag, "TEST123", 7);
      out_message->data.ext_id_8.tag[7] = '\0';
      break;
    }

    case 8: { // ExtendedIdMessage9
      out_message->type = EXT_MSG_TYPE_ID9;
      out_message->data.ext_id_9.big_number = -9223372036854775807LL;
      out_message->data.ext_id_9.big_unsigned = 18446744073709551615ULL;
      out_message->data.ext_id_9.precision_value = 1.7976931348623157e+308;
      break;
    }

    case 9: { // ExtendedIdMessage10
      out_message->type = EXT_MSG_TYPE_ID10;
      out_message->data.ext_id_10.small_value = 256;
      strncpy(out_message->data.ext_id_10.short_text, "Boundary Test", 15);
      out_message->data.ext_id_10.short_text[15] = '\0';
      out_message->data.ext_id_10.flag = true;
      break;
    }

    case 10: { // LargePayloadMessage1
      out_message->type = EXT_MSG_TYPE_LARGE1;
      // Fill sensor_readings with sequential values 1.0 to 64.0
      for (int i = 0; i < 64; i++) {
        out_message->data.large_1.sensor_readings[i] = (float)(i + 1);
      }
      out_message->data.large_1.reading_count = 64;
      out_message->data.large_1.timestamp = 1704067200000000LL;
      strncpy(out_message->data.large_1.device_name, "Large Sensor Array Device", 31);
      out_message->data.large_1.device_name[31] = '\0';
      break;
    }

    case 11: { // LargePayloadMessage2
      out_message->type = EXT_MSG_TYPE_LARGE2;
      // Fill large_data with sequential values 0-255, then 0-23
      for (int i = 0; i < 256; i++) {
        out_message->data.large_2.large_data[i] = (uint8_t)i;
      }
      for (int i = 256; i < 280; i++) {
        out_message->data.large_2.large_data[i] = (uint8_t)(i - 256);
      }
      break;
    }

    default:
      return false;
  }

  return true;
}

bool write_extended_test_messages(uint8_t* buffer, size_t buffer_size, 
                                  encode_extended_message_fn encoder, size_t* encoded_size) {
  if (!buffer || !encoder || !encoded_size) {
    return false;
  }

  *encoded_size = 0;
  size_t offset = 0;
  size_t total_count = get_extended_test_message_count();

  for (size_t i = 0; i < total_count; i++) {
    extended_mixed_message_t msg;
    if (!get_extended_test_message(i, &msg)) {
      fprintf(stderr, "Error: Failed to get extended test message %zu\n", i);
      return false;
    }

    // Determine message ID, pointer, and size based on type
    uint16_t msg_id;
    const uint8_t* msg_ptr;
    size_t msg_size;

    switch (msg.type) {
      case EXT_MSG_TYPE_ID1:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_1;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID2:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_2;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID3:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_3;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID4:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_4;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID5:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_5;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID6:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_6;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID7:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_7;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID8:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_8;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID9:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_9;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_ID10:
        msg_id = EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.ext_id_10;
        msg_size = EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_LARGE1:
        msg_id = EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.large_1;
        msg_size = EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAX_SIZE;
        break;
      case EXT_MSG_TYPE_LARGE2:
        msg_id = EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID;
        msg_ptr = (const uint8_t*)&msg.data.large_2;
        msg_size = EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAX_SIZE;
        break;
      default:
        fprintf(stderr, "Error: Unknown extended message type for message %zu\n", i);
        return false;
    }

    // Encode the message using the callback
    size_t msg_encoded_size = encoder(buffer + offset, buffer_size - offset, 
                                      msg_id, msg_ptr, msg_size);

    if (msg_encoded_size == 0) {
      fprintf(stderr, "Error: Encoding failed for extended message %zu\n", i);
      return false;
    }

    offset += msg_encoded_size;
    *encoded_size = offset;
  }

  return true;
}
