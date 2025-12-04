/**
 * Frame format deserialization test for C++.
 * 
 * This test reads binary files and deserializes using different frame formats.
 * Usage: test_frame_format_deserialization <frame_format> <binary_file>
 */

#include <cmath>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <functional>

#include "serialization_test.sf.hpp"
#include "frame_parsers.hpp"

void print_failure_details(const char* label) {
    std::cout << "\n============================================================\n";
    std::cout << "FAILURE DETAILS: " << label << "\n";
    std::cout << "============================================================\n\n";
}

bool validate_message(const SerializationTestSerializationTestMessage* msg) {
    // Expected values from expected_values.json
    uint32_t expected_magic = 3735928559;  // 0xDEADBEEF
    const char* expected_string = "Cross-platform test!";
    float expected_float = 3.14159f;
    bool expected_bool = true;
    int expected_array[3] = {100, 200, 300};

    if (msg->magic_number != expected_magic) {
        std::cout << "  Value mismatch: magic_number (expected " << expected_magic 
                  << ", got " << msg->magic_number << ")\n";
        return false;
    }

    if (std::strncmp(msg->test_string.data, expected_string, msg->test_string.length) != 0) {
        std::cout << "  Value mismatch: test_string\n";
        return false;
    }

    if (std::fabs(msg->test_float - expected_float) > 0.0001f) {
        std::cout << "  Value mismatch: test_float (expected " << expected_float 
                  << ", got " << msg->test_float << ")\n";
        return false;
    }

    if (msg->test_bool != expected_bool) {
        std::cout << "  Value mismatch: test_bool\n";
        return false;
    }

    if (msg->test_array.count != 3) {
        std::cout << "  Value mismatch: test_array.count (expected 3, got " 
                  << (int)msg->test_array.count << ")\n";
        return false;
    }

    for (int i = 0; i < 3; i++) {
        if (msg->test_array.data[i] != expected_array[i]) {
            std::cout << "  Value mismatch: test_array[" << i << "] (expected " 
                      << expected_array[i] << ", got " << msg->test_array.data[i] << ")\n";
            return false;
        }
    }

    return true;
}

std::map<std::string, std::function<FrameParsers::FrameMsgInfo(const uint8_t*, size_t)>> get_frame_formats() {
    std::map<std::string, std::function<FrameParsers::FrameMsgInfo(const uint8_t*, size_t)>> formats;
    
    // Note: We can only use BasicDefault in C++ as it's the main supported format
    formats["basic_default"] = FrameParsers::basic_default_validate_packet;
    
    return formats;
}

bool read_and_validate_test_data(const std::string& frame_format, const std::string& filename) {
    auto formats = get_frame_formats();
    
    auto it = formats.find(frame_format);
    if (it == formats.end()) {
        std::cout << "  Frame format not supported in C++: " << frame_format << "\n";
        std::cout << "  C++ only supports: basic_default\n";
        return false;
    }
    
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cout << "  Error: file not found: " << filename << "\n";
        return false;
    }

    uint8_t buffer[512];
    file.read(reinterpret_cast<char*>(buffer), sizeof(buffer));
    size_t size = file.gcount();
    file.close();

    if (size == 0) {
        print_failure_details("Empty file");
        return false;
    }

    auto decode_result = it->second(buffer, size);

    if (!decode_result.valid) {
        print_failure_details("Failed to decode data");
        return false;
    }

    const SerializationTestSerializationTestMessage* decoded_msg =
        reinterpret_cast<const SerializationTestSerializationTestMessage*>(decode_result.msg_data);

    if (!validate_message(decoded_msg)) {
        std::cout << "  Validation failed\n";
        return false;
    }

    std::cout << "  [OK] Data validated successfully with " << frame_format << " format\n";
    return true;
}

int main(int argc, char* argv[]) {
    std::cout << "\n[TEST START] C++ Frame Format Deserialization\n";

    if (argc != 3) {
        std::cout << "  Usage: " << argv[0] << " <frame_format> <binary_file>\n";
        std::cout << "  Supported formats in C++:\n";
        std::cout << "    basic_default\n";
        std::cout << "[TEST END] C++ Frame Format Deserialization: FAIL\n\n";
        return 1;
    }

    bool success = read_and_validate_test_data(argv[1], argv[2]);

    std::cout << "[TEST END] C++ Frame Format Deserialization: " << (success ? "PASS" : "FAIL") << "\n\n";

    return success ? 0 : 1;
}
