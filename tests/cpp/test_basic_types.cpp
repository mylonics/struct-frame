// Basic types serialization test for C++
#include "basic_types.sf.hpp"
#include <iostream>
#include <cstring>

int main() {
    // Create and populate a basic types message
    BasicTypesBasicTypesMessage msg{};
    
    // Integer types
    msg.small_int = -42;
    msg.medium_int = -1234;
    msg.regular_int = -123456;
    msg.large_int = -123456789;
    
    // Unsigned integer types
    msg.small_uint = 200;
    msg.medium_uint = 50000;
    msg.regular_uint = 3000000000U;
    msg.large_uint = 9000000000000000000ULL;
    
    // Floating point types
    msg.single_precision = 3.14159f;
    msg.double_precision = 2.718281828;
    
    // Boolean type
    msg.flag = true;
    
    // Fixed string
    std::strncpy(msg.device_id, "TEST_DEVICE_001", sizeof(msg.device_id));
    
    // Variable string
    msg.description.length = 12;
    std::strncpy(msg.description.data, "Test message", sizeof(msg.description.data));
    
    // Verify message size
    size_t msg_size = 0;
    if (!StructFrame::get_message_length(BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID, &msg_size)) {
        std::cerr << "Failed to get message length" << std::endl;
        return 1;
    }
    
    if (msg_size != BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE) {
        std::cerr << "Message size mismatch: expected " << BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE 
                  << ", got " << msg_size << std::endl;
        return 1;
    }
    
    // Test serialization with encoder
    uint8_t buffer[512];
    StructFrame::BasicPacket format;
    StructFrame::EncodeBuffer encoder(buffer, sizeof(buffer));
    
    if (!encoder.encode(&format, BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID, &msg, msg_size)) {
        std::cerr << "Failed to encode message" << std::endl;
        return 1;
    }
    
    std::cout << "Encoded " << encoder.size() << " bytes" << std::endl;
    
    // Test parsing
    StructFrame::FrameParser parser(&format, [](size_t msg_id, size_t* size) {
        return StructFrame::get_message_length(msg_id, size);
    });
    
    for (size_t i = 0; i < encoder.size(); i++) {
        StructFrame::MessageInfo info = parser.parse_byte(buffer[i]);
        if (info.valid) {
            auto* decoded = reinterpret_cast<BasicTypesBasicTypesMessage*>(info.msg_location);
            
            // Verify decoded data
            if (decoded->small_int != msg.small_int ||
                decoded->small_uint != msg.small_uint ||
                decoded->flag != msg.flag) {
                std::cerr << "Decoded data mismatch" << std::endl;
                return 1;
            }
            
            std::cout << "C++ basic types test passed!" << std::endl;
            return 0;
        }
    }
    
    std::cerr << "Failed to parse message" << std::endl;
    return 1;
}
