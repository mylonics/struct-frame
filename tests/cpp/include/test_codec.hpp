/**
 * Test codec (header-only) - Template-based encode/decode and test runner infrastructure.
 *
 * This file provides:
 * 1. Template encode/decode functions that work with any message data struct
 * 2. Test runner utilities (file I/O, hex dump, CLI parsing)
 * 3. A unified run_test_main() function for entry points
 *
 * Usage:
 * Each test entry point (.cpp file) must provide a TestConfig struct with:
 * - MESSAGE_COUNT: number of messages
 * - BUFFER_SIZE: buffer size for encode/decode
 * - FORMATS_HELP: help text for supported formats
 * - TEST_NAME: name for logging
 * - get_msg_id_order(): array of msg_ids in encode/decode order
 * - Encoder: struct with write_message(writer, msg_id) method
 * - Validator: struct with get_expected(msg_id, data, size) method
 * - get_message_info(): function for minimal profiles (optional)
 * - supports_format(): function to check if format is supported
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "frame_parsers.hpp"

namespace TestCodec {

// ============================================================================
// Utility functions
// ============================================================================

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
 * Print usage help.
 */
inline void print_usage(const char* program_name, const char* formats_help) {
  std::cout << "Usage:\n";
  std::cout << "  " << program_name << " encode <frame_format> <output_file>\n";
  std::cout << "  " << program_name << " decode <frame_format> <input_file>\n";
  std::cout << "\nFrame formats: " << formats_help << "\n";
}

// ============================================================================
// Template encode function
// ============================================================================

template <typename Config>
bool encode_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  using namespace FrameParsers;

  if (!Config::supports_format(format)) {
    std::cout << "  Unsupported format: " << format << "\n";
    return false;
  }

  const auto& msg_order = Config::get_msg_id_order();
  encoded_size = 0;

  auto encode_all = [&](auto& writer) -> bool {
    typename Config::Encoder encoder;

    for (size_t i = 0; i < Config::MESSAGE_COUNT; i++) {
      uint16_t msg_id = msg_order[i];
      size_t written = encoder.write_message(writer, msg_id);

      if (written == 0) {
        std::cout << "  Encoding failed for message " << i << " (ID " << msg_id << ")\n";
        return false;
      }
    }
    encoded_size = writer.size();
    if (std::string(Config::TEST_NAME).find("Variable Flag") != std::string::npos) {
      std::cout << "Total: " << encoded_size << " bytes\n";
    }
    return true;
  };

  if (format == "profile_standard") {
    ProfileStandardWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_sensor") {
    ProfileSensorWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_ipc") {
    ProfileIPCWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_bulk") {
    ProfileBulkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_network") {
    ProfileNetworkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  }

  std::cout << "  Unknown frame format: " << format << "\n";
  return false;
}

// ============================================================================
// Template decode function
// ============================================================================

template <typename Config>
bool decode_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size, size_t& message_count) {
  using namespace FrameParsers;

  if (!Config::supports_format(format)) {
    std::cout << "  Unsupported format: " << format << "\n";
    return false;
  }

  const auto& msg_order = Config::get_msg_id_order();
  message_count = 0;

  // Split buffer into 3 chunks to test partial message handling
  size_t chunk1_size = buffer_size / 3;
  size_t chunk2_size = buffer_size / 3;
  size_t chunk3_size = buffer_size - chunk1_size - chunk2_size;

  const uint8_t* chunk1 = buffer;
  const uint8_t* chunk2 = buffer + chunk1_size;
  const uint8_t* chunk3 = buffer + chunk1_size + chunk2_size;

  typename Config::Validator validator;

  auto validate = [&](const FrameMsgInfo& result) -> bool {
    // Note: result is already valid here due to while(auto result = reader.next()) implicit bool check

    if (message_count >= Config::MESSAGE_COUNT) {
      std::cout << "  Too many messages decoded: " << message_count << "\n";
      return false;
    }

    uint16_t expected_msg_id = msg_order[message_count];
    if (result.msg_id != expected_msg_id) {
      std::cout << "  Message " << message_count << " ID mismatch: expected " << expected_msg_id << ", got "
                << result.msg_id << "\n";
      return false;
    }

    // Use operator== for validation via validate_with_equals
    if (!validator.validate_with_equals(result)) {
      std::cout << "  Message " << message_count << " content mismatch (equality check failed)\n";
      return false;
    }

    return true;
  };

  auto decode_all = [&](auto& reader) -> bool {
    const uint8_t* chunks[] = {chunk1, chunk2, chunk3};
    size_t sizes[] = {chunk1_size, chunk2_size, chunk3_size};

    for (int c = 0; c < 3; c++) {
      reader.add_data(chunks[c], sizes[c]);
      while (auto result = reader.next()) {
        if (!validate(result)) return false;
        message_count++;
      }
    }

    if (message_count != Config::MESSAGE_COUNT) {
      std::cout << "  Expected " << Config::MESSAGE_COUNT << " messages, decoded " << message_count << "\n";
      return false;
    }

    if (reader.has_partial()) {
      std::cout << "  Incomplete partial message: " << reader.partial_size() << " bytes\n";
      return false;
    }

    return true;
  };

  if (format == "profile_standard") {
    auto reader = make_accumulating_reader<ProfileStandardConfig, 4096>(Config::get_message_info);
    return decode_all(reader);
  } else if (format == "profile_sensor") {
    auto reader = make_accumulating_reader<ProfileSensorConfig, 4096>(Config::get_message_info);
    return decode_all(reader);
  } else if (format == "profile_ipc") {
    auto reader = make_accumulating_reader<ProfileIPCConfig, 4096>(Config::get_message_info);
    return decode_all(reader);
  } else if (format == "profile_bulk") {
    auto reader = make_accumulating_reader<ProfileBulkConfig, 4096>(Config::get_message_info);
    return decode_all(reader);
  } else if (format == "profile_network") {
    auto reader = make_accumulating_reader<ProfileNetworkConfig, 4096>(Config::get_message_info);
    return decode_all(reader);
  }

  std::cout << "  Unknown frame format: " << format << "\n";
  return false;
}

// ============================================================================
// Test runner functions
// ============================================================================

template <typename Config>
int run_encode(const std::string& format, const std::string& output_file) {
  std::vector<uint8_t> buffer(Config::BUFFER_SIZE);
  size_t encoded_size = 0;

  std::cout << "[ENCODE] Format: " << format << "\n";

  if (!encode_messages<Config>(format, buffer.data(), buffer.size(), encoded_size)) {
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

template <typename Config>
int run_decode(const std::string& format, const std::string& input_file) {
  std::vector<uint8_t> buffer(Config::BUFFER_SIZE);

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
  if (!decode_messages<Config>(format, buffer.data(), size, message_count)) {
    std::cout << "[DECODE] FAILED: " << message_count << " messages validated before error\n";
    print_hex(buffer.data(), size);
    return 1;
  }

  std::cout << "[DECODE] SUCCESS: " << message_count << " messages validated correctly\n";
  return 0;
}

// ============================================================================
// Main entry point template
// ============================================================================

template <typename Config>
int run_test_main(int argc, char* argv[]) {
  if (argc != 4) {
    print_usage(argv[0], Config::FORMATS_HELP);
    return 1;
  }

  std::string mode = argv[1];
  std::string format = argv[2];
  std::string file = argv[3];

  std::cout << "\n[TEST START] " << Config::TEST_NAME << " " << format << " " << mode << "\n";

  int result;
  if (mode == "encode") {
    result = run_encode<Config>(format, file);
  } else if (mode == "decode") {
    result = run_decode<Config>(format, file);
  } else {
    std::cout << "Unknown mode: " << mode << "\n";
    result = 1;
  }

  std::cout << "[TEST END] " << Config::TEST_NAME << " " << format << " " << mode << ": "
            << (result == 0 ? "PASS" : "FAIL") << "\n\n";
  return result;
}

}  // namespace TestCodec
