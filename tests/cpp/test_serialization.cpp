// Cross-language serialization test for C++
#include "serialization_test.sf.hpp"
#include <iostream>
#include <fstream>
#include <cstring>

int main() {
    // Create test message
    SerializationTestSerializationTestMessage msg{};
    msg.magic_number = 0xDEADBEEF;
    msg.test_string.length = 11;
    std::strncpy(msg.test_string.data, "Hello World", sizeof(msg.test_string.data));
    msg.test_float = 3.14159f;
    msg.test_bool = true;
    msg.test_array.count = 3;
    msg.test_array.data[0] = 100;
    msg.test_array.data[1] = 200;
    msg.test_array.data[2] = 300;
    
    // Serialize to binary file
    size_t msg_size = 0;
    if (!StructFrame::get_message_length(SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, &msg_size)) {
        std::cerr << "Failed to get message length" << std::endl;
        return 1;
    }
    
    uint8_t buffer[512];
    StructFrame::BasicPacket format;
    StructFrame::EncodeBuffer encoder(buffer, sizeof(buffer));
    
    if (!encoder.encode(&format, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, 
                        reinterpret_cast<uint8_t*>(&msg), static_cast<uint8_t>(msg_size))) {
        std::cerr << "Failed to encode message" << std::endl;
        return 1;
    }
    
    // Write to file for cross-language testing
    std::ofstream outfile("cpp_test_data.bin", std::ios::binary);
    if (!outfile) {
        std::cerr << "Failed to open output file" << std::endl;
        return 1;
    }
    outfile.write(reinterpret_cast<const char*>(buffer), encoder.size());
    outfile.close();
    
    std::cout << "Wrote " << encoder.size() << " bytes to cpp_test_data.bin" << std::endl;
    
    // Test deserialization
    StructFrame::FrameParser parser(&format, [](size_t msg_id, size_t* size) {
        return StructFrame::get_message_length(msg_id, size);
    });
    
    for (size_t i = 0; i < encoder.size(); i++) {
        StructFrame::MessageInfo info = parser.parse_byte(buffer[i]);
        if (info.valid) {
            auto* decoded = reinterpret_cast<SerializationTestSerializationTestMessage*>(info.msg_location);
            
            // Verify decoded data
            if (decoded->magic_number != msg.magic_number ||
                decoded->test_float != msg.test_float ||
                decoded->test_bool != msg.test_bool ||
                decoded->test_array.count != msg.test_array.count) {
                std::cerr << "Decoded data mismatch" << std::endl;
                return 1;
            }
            
            std::cout << "C++ serialization test passed!" << std::endl;
            return 0;
        }
    }
    
    std::cerr << "Failed to parse message" << std::endl;
    return 1;
}
