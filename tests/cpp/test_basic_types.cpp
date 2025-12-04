#include "basic_types.sf.hpp"
#include "frame_parsers.hpp"
#include <iostream>
#include <cstring>

void print_failure_details(const char* label, const uint8_t* raw_data = nullptr, size_t raw_data_size = 0) {
    std::cout << "\n";
    std::cout << "============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n";
    
    if (raw_data && raw_data_size > 0) {
        std::cout << "\nRaw Data (" << raw_data_size << " bytes):\n  Hex: ";
        for (size_t i = 0; i < raw_data_size && i < 64; i++) {
            printf("%02x", raw_data[i]);
        }
        if (raw_data_size > 64) std::cout << "...";
        std::cout << "\n";
    }
    
    std::cout << "============================================================\n\n";
}

int main() {
    std::cout << "\n[TEST START] C++ Basic Types\n";
    
    try {
        BasicTypesBasicTypesMessage msg{};
        
        msg.small_int = -42;
        msg.medium_int = -1234;
        msg.regular_int = -123456;
        msg.large_int = -123456789;
        msg.small_uint = 200;
        msg.medium_uint = 50000;
        msg.regular_uint = 3000000000U;
        msg.large_uint = 9000000000000000000ULL;
        msg.single_precision = 3.14159f;
        msg.double_precision = 2.718281828;
        msg.flag = true;
        std::strncpy(msg.device_id, "TEST_DEVICE_001", sizeof(msg.device_id));
        msg.description.length = 12;
        std::strncpy(msg.description.data, "Test message", sizeof(msg.description.data));
        
        // Encode message into BasicDefault format
        uint8_t buffer[512];
        FrameParsers::BasicDefaultEncodeBuffer encoder(buffer, sizeof(buffer));
        
        if (!encoder.encode(BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID, &msg, 
                            BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE)) {
            print_failure_details("Failed to encode message", buffer, encoder.size());
            std::cout << "[TEST END] C++ Basic Types: FAIL\n\n";
            return 1;
        }
        
        // Verify encoding produced data
        if (encoder.size() == 0) {
            print_failure_details("Encoded data is empty", buffer, encoder.size());
            std::cout << "[TEST END] C++ Basic Types: FAIL\n\n";
            return 1;
        }
        
        // Verify minimum packet structure (start bytes + msg_id + data + checksums)
        if (encoder.size() < 5) {
            print_failure_details("Encoded data too small", buffer, encoder.size());
            std::cout << "[TEST END] C++ Basic Types: FAIL\n\n";
            return 1;
        }
        
        std::cout << "[TEST END] C++ Basic Types: PASS\n\n";
        return 0;
        
    } catch (const std::exception& e) {
        print_failure_details(e.what());
        std::cout << "[TEST END] C++ Basic Types: FAIL\n\n";
        return 1;
    }
}
