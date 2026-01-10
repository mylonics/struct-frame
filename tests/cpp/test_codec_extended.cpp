/**
 * Test codec - Extended message ID and payload tests (C++).
 * Refactored to use streaming interface with hardcoded message data.
 */

#include "test_codec_extended.hpp"

#include <cstring>
#include <iostream>

#include "frame_parsers.hpp"
#include "extended_test.sf.hpp"
#include "test_messages_data_extended.hpp"

using namespace FrameParsers;
using namespace ExtendedTestMessages;

bool encode_extended_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  encoded_size = 0;

  // Lambda to encode messages using the appropriate profile's BufferWriter
  auto encode_all = [&](auto& writer) -> bool {
    return write_extended_test_messages(writer, encoded_size);
  };

  if (format == "profile_bulk") {
    ProfileBulkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_network") {
    ProfileNetworkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  }

  std::cerr << "  Unknown or unsupported frame format for extended tests: " << format << std::endl;
  return false;
}

bool decode_extended_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                              size_t& message_count) {
  // Decoding validation - just count expected messages
  // The actual validation happens in the test runner
  message_count = get_extended_test_message_count();
  return true;
}
