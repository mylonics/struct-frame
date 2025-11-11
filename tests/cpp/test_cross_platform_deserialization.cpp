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

bool validate_basic_frame(const uint8_t* buffer, size_t size, const char* language, uint32_t expected_magic) {
    // Very basic frame validation
    if (size < 4) {
        std::cout << "  " << language << " data too short\n";
        return false;
    }

    // Check start byte (BasicPacket uses 0x90)
    if (buffer[0] != 0x90) {
        std::cout << "  " << language << " invalid start byte\n";
        return false;
    }

    // Check message ID (SerializationTestMessage is 204)
    if (buffer[1] != 204) {
        std::cout << "  " << language << " invalid message ID\n";
        return false;
    }

    // Extract magic number from payload (starts at byte 2, little-endian)
    if (size < 6) {
        std::cout << "  " << language << " data too short for magic number\n";
        return false;
    }
    
    uint32_t magic_number = buffer[2] | (buffer[3] << 8) | (buffer[4] << 16) | (buffer[5] << 24);
    if (magic_number != expected_magic) {
        std::cout << "  " << language << " magic number mismatch (expected " << expected_magic 
                  << ", got " << magic_number << ")\n";
        return false;
    }

    std::cout << "  ✓ " << language << " data validated successfully\n";
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

    // Expected values from expected_values.json
    uint32_t expected_magic = 3735928559;  // 0xDEADBEEF

    if (!validate_basic_frame(buffer, size, language, expected_magic)) {
        std::cout << "  Validation failed for " << language << " data\n";
        return false;
    }

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
