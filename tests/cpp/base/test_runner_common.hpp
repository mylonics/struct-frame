/**
 * Common utilities for test runners.
 * Shared code between test_runner.cpp and test_runner_extended.cpp.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace TestRunner {

/**
 * Print hex dump of data (up to 64 bytes).
 */
inline void print_hex(const uint8_t* data, size_t size) {
  std::cout << "  Hex (" << size << " bytes): ";
  for (size_t i = 0; i < size && i < 64; i++) {
    printf("%02x", data[i]);
  }
  if (size > 64) std::cout << "...";
  std::cout << "\n";
}

/**
 * Template for running encode operation.
 * @param format Frame format name
 * @param output_file Output file path
 * @param buffer_size Size of buffer to use
 * @param encode_fn Encode function to call
 */
template <typename EncodeFn>
int run_encode(const std::string& format, const std::string& output_file, size_t buffer_size, EncodeFn encode_fn) {
  std::vector<uint8_t> buffer(buffer_size);
  size_t encoded_size = 0;

  std::cout << "[ENCODE] Format: " << format << "\n";

  if (!encode_fn(format, buffer.data(), buffer.size(), encoded_size)) {
    std::cout << "[ENCODE] FAILED: Encoding error\n";
    return 1;
  }

  std::ofstream file(output_file, std::ios::binary);
  if (!file) {
    std::cout << "[ENCODE] FAILED: Cannot create output file: " << output_file << "\n";
    return 1;
  }

  file.write(reinterpret_cast<const char*>(buffer.data()), encoded_size);
  file.close();

  std::cout << "[ENCODE] SUCCESS: Wrote " << encoded_size << " bytes to " << output_file << "\n";
  return 0;
}

/**
 * Template for running decode operation.
 * @param format Frame format name
 * @param input_file Input file path
 * @param buffer_size Size of buffer to use
 * @param decode_fn Decode function to call
 */
template <typename DecodeFn>
int run_decode(const std::string& format, const std::string& input_file, size_t buffer_size, DecodeFn decode_fn) {
  std::vector<uint8_t> buffer(buffer_size);

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
  if (!decode_fn(format, buffer.data(), size, message_count)) {
    std::cout << "[DECODE] FAILED: Decoding error\n";
    print_hex(buffer.data(), size);
    return 1;
  }

  std::cout << "[DECODE] SUCCESS: " << message_count << " messages validated correctly\n";
  return 0;
}

/**
 * Run the test based on mode.
 * @param mode "encode" or "decode"
 * @param format Frame format name
 * @param file File path
 * @param test_name Name for logging (e.g., "C++" or "C++ Extended")
 * @param formats_help Help text for supported formats
 * @param buffer_size Size of buffer to use
 * @param encode_fn Encode function
 * @param decode_fn Decode function
 */
template <typename EncodeFn, typename DecodeFn>
int run_test(const std::string& mode, const std::string& format, const std::string& file, const std::string& test_name,
             size_t buffer_size, EncodeFn encode_fn, DecodeFn decode_fn) {
  std::cout << "\n[TEST START] " << test_name << " " << format << " " << mode << "\n";

  int result;
  if (mode == "encode") {
    result = run_encode(format, file, buffer_size, encode_fn);
  } else if (mode == "decode") {
    result = run_decode(format, file, buffer_size, decode_fn);
  } else {
    std::cout << "Unknown mode: " << mode << "\n";
    result = 1;
  }

  std::cout << "[TEST END] " << test_name << " " << format << " " << mode << ": " << (result == 0 ? "PASS" : "FAIL")
            << "\n\n";
  return result;
}

/**
 * Print usage help.
 */
inline void print_usage(const char* program_name, const char* formats_help) {
  std::cout << "Usage:\n";
  std::cout << "  " << program_name << " encode <frame_format> <output_file>\n";
  std::cout << "  " << program_name << " decode <frame_format> <input_file>\n";
  std::cout << "\nFrame formats: " << formats_help << "\n";
}

}  // namespace TestRunner
