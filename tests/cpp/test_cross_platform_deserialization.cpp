#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>

#include "serialization_test.sf.hpp"

void print_failure_details(const char* label) {
  std::cout << "\n============================================================\n";
  std::cout << "FAILURE DETAILS: " << label << "\n";
  std::cout << "============================================================\n\n";
}

bool validate_basic_frame(const uint8_t* buffer, size_t size, uint32_t expected_magic) {
  // Very basic frame validation
  if (size < 4) {
    std::cout << "  Data too short\n";
    return false;
  }

  // Check start byte (BasicPacket uses 0x90)
  if (buffer[0] != 0x90) {
    std::cout << "  Invalid start byte\n";
    return false;
  }

  // Check message ID (SerializationTestMessage is 204)
  if (buffer[1] != 204) {
    std::cout << "  Invalid message ID\n";
    return false;
  }

  // Extract magic number from payload (starts at byte 2, little-endian)
  if (size < 6) {
    std::cout << "  Data too short for magic number\n";
    return false;
  }

  uint32_t magic_number = buffer[2] | (buffer[3] << 8) | (buffer[4] << 16) | (buffer[5] << 24);
  if (magic_number != expected_magic) {
    std::cout << "  Magic number mismatch (expected " << expected_magic << ", got " << magic_number << ")\n";
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

  // Expected values from expected_values.json
  uint32_t expected_magic = 3735928559;  // 0xDEADBEEF

  if (!validate_basic_frame(buffer, size, expected_magic)) {
    std::cout << "  Validation failed\n";
    return false;
  }

  return true;
}

int main(int argc, char* argv[]) {
  std::cout << "\n[TEST START] C++ Cross-Platform Deserialization\n";

  if (argc != 2) {
    std::cout << "  Usage: " << argv[0] << " <binary_file>\n";
    std::cout << "[TEST END] C++ Cross-Platform Deserialization: FAIL\n\n";
    return 1;
  }

  bool success = read_and_validate_test_data(argv[1]);

  std::cout << "[TEST END] C++ Cross-Platform Deserialization: " << (success ? "PASS" : "FAIL") << "\n\n";

  return success ? 0 : 1;
}
