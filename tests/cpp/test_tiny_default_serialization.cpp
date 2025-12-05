/**
 * Tiny Default frame format serialization test for C++.
 */

#include <cstring>
#include <fstream>
#include <iostream>

#include "frame_parsers.hpp"
#include "serialization_test.sf.hpp"

using namespace FrameParsers;

void print_failure_details(const char* label, const uint8_t* raw_data = nullptr, size_t raw_data_size = 0) {
  std::cout << "\n";
  std::cout << "============================================================\n";
  std::cout << "FAILURE DETAILS: " << label << "\n";
  std::cout << "============================================================\n";

  if (raw_data && raw_data_size > 0) {
    std::cout << "\nRaw Data (" << raw_data_size << " bytes):\n  Hex: ";
    for (size_t i = 0; i < raw_data_size && i < 64; i++) {
      printf("%02x", raw_data[i]);
    }
    if (raw_data_size > 64) std::cout << "...";
    std::cout << "\n";
  }

  std::cout << "============================================================\n\n";
}

bool create_test_data() {
  SerializationTestSerializationTestMessage msg{};

  // Use values from expected_values.json
  msg.magic_number = 3735928559;  // 0xDEADBEEF
  msg.test_string.length = 20;
  std::strncpy(msg.test_string.data, "Cross-platform test!", sizeof(msg.test_string.data));
  msg.test_float = 3.14159f;
  msg.test_bool = true;
  msg.test_array.count = 3;
  msg.test_array.data[0] = 100;
  msg.test_array.data[1] = 200;
  msg.test_array.data[2] = 300;

  uint8_t encode_buffer[512];
  size_t encoded_size = tiny_default_encode(
      encode_buffer, sizeof(encode_buffer), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
      reinterpret_cast<const uint8_t*>(&msg), SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);

  if (encoded_size == 0) {
    print_failure_details("Encoding failed");
    return false;
  }

  std::ofstream file("cpp_tiny_default_test_data.bin", std::ios::binary);
  if (!file) {
    print_failure_details("File creation failed");
    return false;
  }

  file.write(reinterpret_cast<const char*>(encode_buffer), encoded_size);
  file.close();

  // Self-validate
  FrameMsgInfo decode_result = tiny_default_validate_packet(encode_buffer, encoded_size);
  if (!decode_result.valid) {
    print_failure_details("Self-validation failed", encode_buffer, encoded_size);
    return false;
  }

  const SerializationTestSerializationTestMessage* decoded_msg =
      reinterpret_cast<const SerializationTestSerializationTestMessage*>(decode_result.msg_data);

  if (decoded_msg->magic_number != 3735928559 || decoded_msg->test_array.count != 3) {
    print_failure_details("Self-verification failed", encode_buffer, encoded_size);
    return false;
  }

  return true;
}

int main() {
  std::cout << "\n[TEST START] C++ Tiny Default Serialization\n";

  bool success = create_test_data();

  const char* status = success ? "PASS" : "FAIL";
  std::cout << "[TEST END] C++ Tiny Default Serialization: " << status << "\n\n";

  return success ? 0 : 1;
}
