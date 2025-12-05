/**
 * Tiny Minimal frame format deserialization test for C++.
 */

#include <cmath>
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

bool validate_message(const SerializationTestSerializationTestMessage* msg) {
  // Expected values from expected_values.json
  uint32_t expected_magic = 3735928559;  // 0xDEADBEEF
  const char* expected_string = "Cross-platform test!";
  float expected_float = 3.14159f;
  bool expected_bool = true;
  int expected_array[3] = {100, 200, 300};

  if (msg->magic_number != expected_magic) {
    std::cout << "  Value mismatch: magic_number (expected " << expected_magic << ", got " << msg->magic_number
              << ")\n";
    return false;
  }

  if (std::strncmp(msg->test_string.data, expected_string, msg->test_string.length) != 0) {
    std::cout << "  Value mismatch: test_string\n";
    return false;
  }

  if (std::fabs(msg->test_float - expected_float) > 0.0001f) {
    std::cout << "  Value mismatch: test_float (expected " << expected_float << ", got " << msg->test_float << ")\n";
    return false;
  }

  if (msg->test_bool != expected_bool) {
    std::cout << "  Value mismatch: test_bool\n";
    return false;
  }

  if (msg->test_array.count != 3) {
    std::cout << "  Value mismatch: test_array.count (expected 3, got " << static_cast<int>(msg->test_array.count)
              << ")\n";
    return false;
  }

  for (int i = 0; i < 3; i++) {
    if (msg->test_array.data[i] != expected_array[i]) {
      std::cout << "  Value mismatch: test_array[" << i << "] (expected " << expected_array[i] << ", got "
                << msg->test_array.data[i] << ")\n";
      return false;
    }
  }

  std::cout << "  [OK] Data validated successfully\n";
  return true;
}

bool read_and_validate_test_data(const char* filename) {
  std::ifstream file(filename, std::ios::binary);
  if (!file) {
    std::cout << "  Error: file not found: " << filename << "\n";
    return false;
  }

  uint8_t buffer[512];
  file.read(reinterpret_cast<char*>(buffer), sizeof(buffer));
  size_t size = file.gcount();
  file.close();

  if (size == 0) {
    print_failure_details("Empty file", buffer, size);
    return false;
  }

  FrameMsgInfo decode_result = tiny_minimal_validate_packet(buffer, size);

  if (!decode_result.valid) {
    print_failure_details("Failed to decode data", buffer, size);
    return false;
  }

  const SerializationTestSerializationTestMessage* decoded_msg =
      reinterpret_cast<const SerializationTestSerializationTestMessage*>(decode_result.msg_data);

  if (!validate_message(decoded_msg)) {
    std::cout << "  Validation failed\n";
    return false;
  }

  return true;
}

int main(int argc, char* argv[]) {
  std::cout << "\n[TEST START] C++ Tiny Minimal Deserialization\n";

  if (argc != 2) {
    std::cout << "  Usage: " << argv[0] << " <binary_file>\n";
    std::cout << "[TEST END] C++ Tiny Minimal Deserialization: FAIL\n\n";
    return 1;
  }

  bool success = read_and_validate_test_data(argv[1]);

  const char* status = success ? "PASS" : "FAIL";
  std::cout << "[TEST END] C++ Tiny Minimal Deserialization: " << status << "\n\n";

  return success ? 0 : 1;
}
