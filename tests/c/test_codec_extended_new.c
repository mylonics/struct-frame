/**
 * Test codec - Extended message ID and payload tests (C).
 * Refactored to use streaming interface with hardcoded message data.
 */

#include "test_codec_extended.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "frame_parsers.h"
#include "extended_test.sf.h"
#include "test_messages_data_extended.h"

#define MAX_EXTENDED_MESSAGES 20

/* Extended encoding wrapper for profile_bulk */
static size_t encode_profile_bulk_wrapper(uint8_t* buffer, size_t buffer_size,
                                          uint16_t msg_id, const uint8_t* msg_ptr,
                                          size_t msg_size) {
  return encode_profile_bulk(buffer, buffer_size, msg_id, msg_ptr, msg_size);
}

/* Extended encoding wrapper for profile_network */
static size_t encode_profile_network_wrapper(uint8_t* buffer, size_t buffer_size,
                                             uint16_t msg_id, const uint8_t* msg_ptr,
                                             size_t msg_size) {
  return encode_profile_network(buffer, buffer_size, 0, 0, 0, msg_id, msg_ptr, msg_size);
}

bool encode_extended_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  // Select the appropriate encoder based on format
  encode_extended_message_fn encoder = NULL;
  
  if (strcmp(format, "profile_bulk") == 0) {
    encoder = encode_profile_bulk_wrapper;
  } else if (strcmp(format, "profile_network") == 0) {
    encoder = encode_profile_network_wrapper;
  } else {
    printf("  Unknown or unsupported frame format for extended tests: %s\n", format);
    return false;
  }

  // Use the streaming interface to write messages directly
  return write_extended_test_messages(buffer, buffer_size, encoder, encoded_size);
}

bool decode_extended_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count) {
  *message_count = 0;
  size_t offset = 0;
  
  while (offset < buffer_size) {
    frame_msg_info_t frame_info;
    size_t msg_length = 0;
    
    if (strcmp(format, "profile_bulk") == 0) {
      msg_length = decode_profile_bulk(buffer + offset, buffer_size - offset, &frame_info);
    } else if (strcmp(format, "profile_network") == 0) {
      msg_length = decode_profile_network(buffer + offset, buffer_size - offset, &frame_info);
    } else {
      printf("  Unknown or unsupported frame format for extended tests: %s\n", format);
      return false;
    }
    
    if (msg_length == 0) {
      break; // No more messages or error
    }
    
    (*message_count)++;
    offset += msg_length;
  }
  
  return *message_count > 0;
}
