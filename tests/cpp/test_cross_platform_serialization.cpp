#include "serialization_test.sf.hpp"
#include <iostream>
#include <fstream>
#include <cstring>

void print_failure_details(const char* label) {
    std::cout << "\n============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n\n";
}

int main() {
    std::cout << "\n[TEST START] C++ Cross-Platform Serialization\n";
    
    try {
        SerializationTestSerializationTestMessage msg{};
        // Use values from expected_values.json
        msg.magic_number = 3735928559;  // 0xDEADBEEF
        msg.test_string.length = 20;
        std::strncpy(msg.test_string.data, "Cross-platform test!", sizeof(msg.test_string.data));
        msg.test_float = 3.14159f;
        msg.test_bool = true;
        msg.test_array.count = 3;
        msg.test_array.data[0] = 100;
        msg.test_array.data[1] = 200;
        msg.test_array.data[2] = 300;
        
        size_t msg_size = 0;
        if (!StructFrame::get_message_length(SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, &msg_size)) {
            print_failure_details("Failed to get message length");
            std::cout << "[TEST END] C++ Cross-Platform Serialization: FAIL\n\n";
            return 1;
        }
        
        uint8_t buffer[512];
        StructFrame::BasicPacket format;
        StructFrame::EncodeBuffer encoder(buffer, sizeof(buffer));
        
        if (!encoder.encode(&format, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, &msg, msg_size)) {
            print_failure_details("Failed to encode message");
            std::cout << "[TEST END] C++ Cross-Platform Serialization: FAIL\n\n";
            return 1;
        }
        
        std::ofstream file("cpp_test_data.bin", std::ios::binary);
        if (!file) {
            print_failure_details("Failed to create test data file");
            std::cout << "[TEST END] C++ Cross-Platform Serialization: FAIL\n\n";
            return 1;
        }
        file.write(reinterpret_cast<const char*>(buffer), encoder.size());
        file.close();
        
        std::cout << "[TEST END] C++ Cross-Platform Serialization: PASS\n\n";
        return 0;
        
    } catch (const std::exception& e) {
        print_failure_details(e.what());
        std::cout << "[TEST END] C++ Cross-Platform Serialization: FAIL\n\n";
        return 1;
    }
}
