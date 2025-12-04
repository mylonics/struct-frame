/**
 * Frame format serialization test for C++.
 * 
 * This test serializes data using different frame formats and saves to binary files.
 * Usage: test_frame_format_serialization <frame_format>
 */

#include "serialization_test.sf.hpp"
#include "frame_parsers.hpp"
#include <iostream>
#include <fstream>
#include <cstring>
#include <map>
#include <functional>

void print_failure_details(const char* label) {
    std::cout << "\n============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n\n";
}

void init_test_message(SerializationTestSerializationTestMessage& msg) {
    memset(&msg, 0, sizeof(msg));
    
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
}

struct FrameFormatEntry {
    std::string name;
    std::function<bool(uint8_t*, size_t, size_t&)> encode;
    std::function<FrameParsers::FrameMsgInfo(const uint8_t*, size_t)> validate;
};

std::map<std::string, FrameFormatEntry> get_frame_formats() {
    std::map<std::string, FrameFormatEntry> formats;
    
    // Note: We can only use BasicDefault in C++ as it's the main supported format
    // Other formats would need additional boilerplate support
    formats["basic_default"] = {
        "basic_default",
        [](uint8_t* buffer, size_t buffer_size, size_t& encoded_size) -> bool {
            SerializationTestSerializationTestMessage msg{};
            init_test_message(msg);
            FrameParsers::BasicDefaultEncodeBuffer encoder(buffer, buffer_size);
            if (!encoder.encode(SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, &msg, 
                                SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE)) {
                return false;
            }
            encoded_size = encoder.size();
            return true;
        },
        FrameParsers::basic_default_validate_packet
    };
    
    return formats;
}

bool create_test_data(const std::string& frame_format) {
    auto formats = get_frame_formats();
    
    auto it = formats.find(frame_format);
    if (it == formats.end()) {
        std::cout << "  Frame format not supported in C++: " << frame_format << "\n";
        std::cout << "  C++ only supports: basic_default\n";
        return false;
    }
    
    try {
        uint8_t buffer[512];
        size_t encoded_size = 0;
        
        if (!it->second.encode(buffer, sizeof(buffer), encoded_size)) {
            print_failure_details("Failed to encode message");
            return false;
        }
        
        std::string filename = "cpp_" + frame_format + "_test_data.bin";
        std::ofstream file(filename, std::ios::binary);
        if (!file) {
            print_failure_details("Failed to create test data file");
            return false;
        }
        file.write(reinterpret_cast<const char*>(buffer), encoded_size);
        file.close();
        
        // Self-validate
        auto result = it->second.validate(buffer, encoded_size);
        if (!result.valid) {
            print_failure_details("Self-validation failed");
            return false;
        }
        
        std::cout << "  [OK] Encoded with " << frame_format << " format (" 
                  << encoded_size << " bytes) -> " << filename << "\n";
        return true;
        
    } catch (const std::exception& e) {
        print_failure_details(e.what());
        return false;
    }
}

int main(int argc, char* argv[]) {
    std::cout << "\n[TEST START] C++ Frame Format Serialization\n";
    
    if (argc != 2) {
        std::cout << "  Usage: " << argv[0] << " <frame_format>\n";
        std::cout << "  Supported formats in C++:\n";
        std::cout << "    basic_default\n";
        std::cout << "[TEST END] C++ Frame Format Serialization: FAIL\n\n";
        return 1;
    }
    
    bool success = create_test_data(argv[1]);
    
    std::cout << "[TEST END] C++ Frame Format Serialization: " << (success ? "PASS" : "FAIL") << "\n\n";
    return success ? 0 : 1;
}
