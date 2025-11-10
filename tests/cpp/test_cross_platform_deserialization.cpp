#include "serialization_test.sf.hpp"
#include <iostream>
#include <fstream>
#include <cstring>
#include <cmath>

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
                  << msg->test_array.count << ")\n";
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

bool read_and_validate_test_data(const char* filename, const char* language) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cout << "  Skipping " << language << " - file not found: " << filename << "\n";
        return true;  // Skip if file not available
    }

    uint8_t buffer[512];
    file.read(reinterpret_cast<char*>(buffer), sizeof(buffer));
    size_t size = file.gcount();
    file.close();

    if (size == 0) {
        print_failure_details("Empty file");
        return false;
    }

    size_t msg_size = 0;
    if (!StructFrame::get_message_length(SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, &msg_size)) {
        print_failure_details("Failed to get message length");
        return false;
    }

    StructFrame::BasicPacket format;
    StructFrame::FrameParser parser;
    parser.register_format(0x90, &format);
    parser.register_msg_definition(SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, msg_size);

    SerializationTestSerializationTestMessage* decoded_msg = nullptr;
    for (size_t i = 0; i < size; i++) {
        auto result = parser.parse_char(buffer[i]);
        if (result.msg_id == SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID) {
            decoded_msg = reinterpret_cast<SerializationTestSerializationTestMessage*>(result.data);
            break;
        }
    }

    if (!decoded_msg) {
        std::cout << "  Failed to decode " << language << " data\n";
        return false;
    }

    if (!validate_message(decoded_msg)) {
        std::cout << "  Validation failed for " << language << " data\n";
        return false;
    }

    std::cout << "  ✓ " << language << " data validated successfully\n";
    return true;
}

int main() {
    std::cout << "\n[TEST START] C++ Cross-Platform Deserialization\n";
    
    bool success = true;
    success = success && read_and_validate_test_data("python_test_data.bin", "Python");
    success = success && read_and_validate_test_data("c_test_data.bin", "C");
    success = success && read_and_validate_test_data("cpp_test_data.bin", "C++");
    success = success && read_and_validate_test_data("typescript_test_data.bin", "TypeScript");
    
    std::cout << "[TEST END] C++ Cross-Platform Deserialization: " 
              << (success ? "PASS" : "FAIL") << "\n\n";
    
    return success ? 0 : 1;
}
