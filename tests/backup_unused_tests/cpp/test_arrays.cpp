#include "comprehensive_arrays.sf.hpp"
#include "frame_parsers.hpp"
#include <iostream>
#include <cstring>

void print_failure_details(const char* label) {
    std::cout << "\n============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n\n";
}

int main() {
    std::cout << "\n[TEST START] C++ Array Operations\n";
    
    try {
        ComprehensiveArraysComprehensiveArrayMessage msg{};
        
        msg.fixed_ints[0] = 1; msg.fixed_ints[1] = 2; msg.fixed_ints[2] = 3;
        msg.fixed_floats[0] = 1.1f; msg.fixed_floats[1] = 2.2f;
        msg.fixed_bools[0] = true; msg.fixed_bools[1] = false;
        msg.fixed_bools[2] = true; msg.fixed_bools[3] = false;
        
        msg.bounded_uints.count = 3;
        msg.bounded_uints.data[0] = 100;
        msg.bounded_uints.data[1] = 200;
        msg.bounded_uints.data[2] = 300;
        
        // Encode message into BasicDefault format
        uint8_t buffer[1024];
        FrameParsers::BasicDefaultEncodeBuffer encoder(buffer, sizeof(buffer));
        
        if (!encoder.encode(COMPREHENSIVE_ARRAYS_COMPREHENSIVE_ARRAY_MESSAGE_MSG_ID, &msg, 
                            COMPREHENSIVE_ARRAYS_COMPREHENSIVE_ARRAY_MESSAGE_MAX_SIZE)) {
            print_failure_details("Failed to encode message");
            std::cout << "[TEST END] C++ Array Operations: FAIL\n\n";
            return 1;
        }
        
        // Verify encoding produced data
        if (encoder.size() == 0) {
            print_failure_details("Encoded data is empty");
            std::cout << "[TEST END] C++ Array Operations: FAIL\n\n";
            return 1;
        }
        
        std::cout << "[TEST END] C++ Array Operations: PASS\n\n";
        return 0;
        
    } catch (const std::exception& e) {
        print_failure_details(e.what());
        std::cout << "[TEST END] C++ Array Operations: FAIL\n\n";
        return 1;
    }
}
