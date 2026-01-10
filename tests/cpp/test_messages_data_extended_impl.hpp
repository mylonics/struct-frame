/**
 * Template implementation for writing extended test messages.
 * Included by test_messages_data_extended.hpp.
 */

#ifndef TEST_MESSAGES_DATA_EXTENDED_IMPL_HPP
#define TEST_MESSAGES_DATA_EXTENDED_IMPL_HPP

#include <iostream>

namespace ExtendedTestMessages {

// Template implementation - works with any BufferWriter type
template<typename WriterType>
bool write_extended_test_messages(WriterType& writer, size_t& encoded_size) {
  extern const std::array<MixedMessage, 12>& get_messages_array();
  const auto& messages = get_messages_array();

  for (const auto& msg : messages) {
    size_t written = 0;
    
    switch (msg.type) {
      case MessageType::EXT_ID_1:
        written = writer.write(msg.data.ext_id_1);
        break;
      case MessageType::EXT_ID_2:
        written = writer.write(msg.data.ext_id_2);
        break;
      case MessageType::EXT_ID_3:
        written = writer.write(msg.data.ext_id_3);
        break;
      case MessageType::EXT_ID_4:
        written = writer.write(msg.data.ext_id_4);
        break;
      case MessageType::EXT_ID_5:
        written = writer.write(msg.data.ext_id_5);
        break;
      case MessageType::EXT_ID_6:
        written = writer.write(msg.data.ext_id_6);
        break;
      case MessageType::EXT_ID_7:
        written = writer.write(msg.data.ext_id_7);
        break;
      case MessageType::EXT_ID_8:
        written = writer.write(msg.data.ext_id_8);
        break;
      case MessageType::EXT_ID_9:
        written = writer.write(msg.data.ext_id_9);
        break;
      case MessageType::EXT_ID_10:
        written = writer.write(msg.data.ext_id_10);
        break;
      case MessageType::LARGE_1:
        written = writer.write(msg.data.large_1);
        break;
      case MessageType::LARGE_2:
        written = writer.write(msg.data.large_2);
        break;
      default:
        std::cerr << "  Unknown extended message type\n";
        return false;
    }
    
    if (written == 0) {
      std::cerr << "  Encoding failed for extended message\n";
      return false;
    }
  }
  
  encoded_size = writer.size();
  return true;
}

} // namespace ExtendedTestMessages

#endif // TEST_MESSAGES_DATA_EXTENDED_IMPL_HPP
