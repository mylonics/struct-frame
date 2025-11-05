#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "serialization_test.sf.h"
#include "struct_frame_default_frame.h"

// Encoder for cross-platform testing with framing
// Encodes a SerializationTestMessage with framing and writes to stdout
int main() {
  SerializationTestSerializationTestMessage msg = {0};

  // Set test data
  msg.magic_number = 0xDEADBEEF;
  msg.test_string.length = strlen("Hello from C!");
  strncpy(msg.test_string.data, "Hello from C!", msg.test_string.length);
  msg.test_float = 3.14159f;
  msg.test_bool = true;
  msg.test_array.count = 3;
  msg.test_array.data[0] = 100;
  msg.test_array.data[1] = 200;
  msg.test_array.data[2] = 300;

  // Create encoding buffer
  uint8_t encode_buffer[512];
  msg_encode_buffer buffer = {0};
  buffer.data = encode_buffer;

  // Encode the message with framing
  packet_format_t* format = &default_frame_format;
  bool encoded = serialization_test_serialization_test_message_encode(&buffer, format, &msg);

  if (!encoded) {
    fprintf(stderr, "ERROR: Failed to encode message\n");
    return 1;
  }

  // Write binary data to stdout
  fwrite(encode_buffer, 1, buffer.size, stdout);
  fflush(stdout);

  return 0;
}
