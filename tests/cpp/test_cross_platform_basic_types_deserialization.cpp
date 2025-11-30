#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>

#include "basic_types.sf.hpp"
#include "basic_frame.hpp"

void print_failure_details(const char* label) {
  std::cout << "\n============================================================\n";
  std::cout << "FAILURE DETAILS: " << label << "\n";
  std::cout << "============================================================\n\n";
}

bool validate_message(const BasicTypesBasicTypesMessage* msg) {
  // Expected values from expected_values.json
  if (msg->small_int != -42) {
    std::cout << "  Value mismatch: small_int (expected -42, got " << (int)msg->small_int << ")\n";
    return false;
  }

  if (msg->medium_int != -1000) {
    std::cout << "  Value mismatch: medium_int (expected -1000, got " << msg->medium_int << ")\n";
    return false;
  }

  if (msg->regular_int != -100000) {
    std::cout << "  Value mismatch: regular_int (expected -100000, got " << msg->regular_int << ")\n";
    return false;
  }

  if (msg->large_int != -1000000000LL) {
    std::cout << "  Value mismatch: large_int (expected -1000000000, got " << msg->large_int << ")\n";
    return false;
  }

  if (msg->small_uint != 255) {
    std::cout << "  Value mismatch: small_uint (expected 255, got " << (int)msg->small_uint << ")\n";
    return false;
  }

  if (msg->medium_uint != 65535) {
    std::cout << "  Value mismatch: medium_uint (expected 65535, got " << msg->medium_uint << ")\n";
    return false;
  }

  if (std::fabs(msg->single_precision - 3.14159f) > 0.0001f) {
    std::cout << "  Value mismatch: single_precision (expected 3.14159, got " << msg->single_precision << ")\n";
    return false;
  }

  if (msg->flag != true) {
    std::cout << "  Value mismatch: flag (expected true, got false)\n";
    return false;
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
    print_failure_details("Empty file");
    return false;
  }

  StructFrame::BasicFrameMsgInfo decode_result = StructFrame::basic_frame_validate_packet(buffer, size);

  if (!decode_result.valid) {
    print_failure_details("Failed to decode data");
    return false;
  }

  const BasicTypesBasicTypesMessage* decoded_msg =
      reinterpret_cast<const BasicTypesBasicTypesMessage*>(decode_result.msg_data);

  if (!validate_message(decoded_msg)) {
    std::cout << "  Validation failed\n";
    return false;
  }

  return true;
}

int main(int argc, char* argv[]) {
  std::cout << "\n[TEST START] C++ Cross-Platform Basic Types Deserialization\n";

  if (argc != 2) {
    std::cout << "  Usage: " << argv[0] << " <binary_file>\n";
    std::cout << "[TEST END] C++ Cross-Platform Basic Types Deserialization: FAIL\n\n";
    return 1;
  }

  bool success = read_and_validate_test_data(argv[1]);

  std::cout << "[TEST END] C++ Cross-Platform Basic Types Deserialization: " << (success ? "PASS" : "FAIL") << "\n\n";

  return success ? 0 : 1;
}
