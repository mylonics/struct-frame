#include "basic_types.sf.hpp"
#include "basic_frame.hpp"
#include <iostream>
#include <fstream>
#include <cstring>

void print_failure_details(const char* label) {
    std::cout << "\n============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n\n";
}

int main() {
    std::cout << "\n[TEST START] C++ Cross-Platform Basic Types Serialization\n";
    
    try {
        BasicTypesBasicTypesMessage msg{};
        // Use values from expected_values.json
        msg.small_int = -42;
        msg.medium_int = -1000;
        msg.regular_int = -100000;
        msg.large_int = -1000000000LL;
        msg.small_uint = 255;
        msg.medium_uint = 65535;
        msg.regular_uint = 4294967295U;
        msg.large_uint = 18446744073709551615ULL;
        msg.single_precision = 3.14159f;
        msg.double_precision = 2.718281828459045;
        msg.flag = true;
        std::strncpy(msg.device_id, "TEST_DEVICE_12345678901234567890", 32);
        msg.description.length = 33;
        std::strncpy(msg.description.data, "Test description for basic types", sizeof(msg.description.data));
        
        uint8_t buffer[512];
        StructFrame::BasicFrameEncodeBuffer encoder(buffer, sizeof(buffer));
        
        if (!encoder.encode(BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID, &msg, 
                            BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE)) {
            print_failure_details("Failed to encode message");
            std::cout << "[TEST END] C++ Cross-Platform Basic Types Serialization: FAIL\n\n";
            return 1;
        }
        
        std::ofstream file("cpp_basic_types_test_data.bin", std::ios::binary);
        if (!file) {
            print_failure_details("Failed to create test data file");
            std::cout << "[TEST END] C++ Cross-Platform Basic Types Serialization: FAIL\n\n";
            return 1;
        }
        file.write(reinterpret_cast<const char*>(buffer), encoder.size());
        file.close();
        
        std::cout << "[TEST END] C++ Cross-Platform Basic Types Serialization: PASS\n\n";
        return 0;
        
    } catch (const std::exception& e) {
        print_failure_details(e.what());
        std::cout << "[TEST END] C++ Cross-Platform Basic Types Serialization: FAIL\n\n";
        return 1;
    }
}
