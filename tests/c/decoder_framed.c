#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "serialization_test.sf.h"
#include "struct_frame_default_frame.h"

// Decoder for cross-platform testing with framing
// Reads framed SerializationTestMessage from stdin and decodes it
int main() {
  // Read binary data from stdin
  uint8_t buffer[512];
  size_t size = fread(buffer, 1, sizeof(buffer), stdin);

  if (size == 0) {
    fprintf(stderr, "ERROR: No data received from stdin\n");
    return 1;
  }

  // Decode the message
  packet_format_t* format = &default_frame_format;
  msg_info_t decode_result = format->validate_packet(buffer, size);

  if (!decode_result.valid) {
    fprintf(stderr, "ERROR: Failed to decode message\n");
    return 1;
  }

  SerializationTestSerializationTestMessage msg =
      serialization_test_serialization_test_message_get(decode_result);

  // Print decoded values in a consistent format
  printf("magic_number=0x%08X\n", msg.magic_number);
  printf("test_string=%.*s\n", msg.test_string.length, msg.test_string.data);
  printf("test_float=%.5f\n", msg.test_float);
  printf("test_bool=%s\n", msg.test_bool ? "True" : "False");
  printf("test_array=");
  for (int i = 0; i < msg.test_array.count; i++) {
    printf("%d", msg.test_array.data[i]);
    if (i < msg.test_array.count - 1) printf(",");
  }
  printf("\n");

  return 0;
}
