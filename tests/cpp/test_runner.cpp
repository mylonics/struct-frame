/**
 * Test runner entry point for C++.
 *
 * Usage:
 *   test_runner encode <frame_format> <output_file>
 *   test_runner decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "test_codec.hpp"

static const size_t MAX_BUFFER_SIZE = 4096;  // Increased for multiple messages

static void print_usage(const char* program_name) {
  std::cout << "Usage:\n";
  std::cout << "  " << program_name << " encode <frame_format> <output_file>\n";
  std::cout << "  " << program_name << " decode <frame_format> <input_file>\n";
  std::cout << "\nFrame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network\n";
}

static void print_hex(const uint8_t* data, size_t size) {
  std::cout << "  Hex (" << size << " bytes): ";
  for (size_t i = 0; i < size && i < 64; i++) {
    printf("%02x", data[i]);
  }
  if (size > 64) std::cout << "...";
  std::cout << "\n";
}

static int run_encode(const std::string& format, const std::string& output_file) {
  uint8_t buffer[MAX_BUFFER_SIZE];
  size_t encoded_size = 0;

  std::cout << "[ENCODE] Format: " << format << "\n";

  if (!encode_test_messages(format, buffer, sizeof(buffer), encoded_size)) {
    std::cout << "[ENCODE] FAILED: Encoding error\n";
    return 1;
  }

  std::ofstream file(output_file, std::ios::binary);
  if (!file) {
    std::cout << "[ENCODE] FAILED: Cannot create output file: " << output_file << "\n";
    return 1;
  }

  file.write(reinterpret_cast<const char*>(buffer), encoded_size);
  file.close();

  std::cout << "[ENCODE] SUCCESS: Wrote " << encoded_size << " bytes to " << output_file << "\n";
  return 0;
}

static int run_decode(const std::string& format, const std::string& input_file) {
  std::vector<uint8_t> buffer(MAX_BUFFER_SIZE);

  std::cout << "[DECODE] Format: " << format << ", File: " << input_file << "\n";

  std::ifstream file(input_file, std::ios::binary);
  if (!file) {
    std::cout << "[DECODE] FAILED: Cannot open input file: " << input_file << "\n";
    return 1;
  }

  file.read(reinterpret_cast<char*>(buffer.data()), buffer.size());
  size_t size = file.gcount();
  file.close();

  if (size == 0) {
    std::cout << "[DECODE] FAILED: Empty file\n";
    return 1;
  }

  size_t message_count = 0;
  if (!decode_test_messages(format, buffer.data(), size, message_count)) {
    std::cout << "[DECODE] FAILED: Decoding error\n";
    print_hex(buffer.data(), size);
    return 1;
  }

  std::cout << "[DECODE] SUCCESS: " << message_count << " messages validated correctly\n";
  return 0;
}

int main(int argc, char* argv[]) {
  if (argc != 4) {
    print_usage(argv[0]);
    return 1;
  }

  std::string mode = argv[1];
  std::string format = argv[2];
  std::string file = argv[3];

  std::cout << "\n[TEST START] C++ " << format << " " << mode << "\n";

  int result;
  if (mode == "encode") {
    result = run_encode(format, file);
  } else if (mode == "decode") {
    result = run_decode(format, file);
  } else {
    std::cout << "Unknown mode: " << mode << "\n";
    print_usage(argv[0]);
    result = 1;
  }

  std::cout << "[TEST END] C++ " << format << " " << mode << ": " << (result == 0 ? "PASS" : "FAIL") << "\n\n";
  return result;
}
