/**
 * Struct-Frame-Generated Test
 * 
 * This test uses the struct-frame message generator to test all defined messages.
 * It fills each message with dummy values, encodes them, decodes them, and verifies
 * the decoded data matches the original.
 * 
 * This is a full end-to-end test of the struct-frame system using the StandardMessages
 * test suite which includes various message types.
 */

#include <cstdio>
#include <cstring>

#include "include/standard_messages.hpp"
#include "frame_profiles.hpp"

// Buffer for encoding/decoding
static constexpr size_t BUFFER_SIZE = 16384;

int main() {
    printf("\n");
    printf("=============================================================\n");
    printf("STRUCT-FRAME-GENERATED TEST\n");
    printf("=============================================================\n");
    printf("\n");
    printf("This test encodes and decodes all messages from StandardMessages,\n");
    printf("verifying that decoded data matches the original values.\n");
    printf("\n");
    printf("Test configuration:\n");
    printf("  Total messages: %zu\n", StandardMessages::MESSAGE_COUNT);
    printf("  Profile: ProfileStandard\n");
    printf("\n");

    uint8_t buffer[BUFFER_SIZE];
    size_t passed = 0;
    size_t failed = 0;

    printf("-------------------------------------------------------------\n");
    printf("ENCODE/DECODE/VERIFY TESTS\n");
    printf("-------------------------------------------------------------\n");

    for (size_t i = 0; i < StandardMessages::MESSAGE_COUNT; i++) {
        auto msg_variant = StandardMessages::get_message(i);
        
        bool success = std::visit([&buffer, i](auto&& msg) -> bool {
            using T = std::decay_t<decltype(msg)>;
            
            // Encode the message
            size_t written = FrameParsers::FrameEncoderWithCrc<FrameParsers::ProfileStandardConfig>::encode(
                buffer, BUFFER_SIZE, msg);
            
            if (written == 0) {
                printf("  [%zu] FAIL: Encode failed for message type\n", i);
                return false;
            }
            
            // Parse the frame
            auto frame_info = FrameParsers::BufferParserWithCrc<FrameParsers::ProfileStandardConfig>::parse(
                buffer, written, FrameParsers::get_message_info);
            
            if (!frame_info.valid) {
                printf("  [%zu] FAIL: Parse failed for message type\n", i);
                return false;
            }
            
            // Verify message ID matches
            if (frame_info.msg_id != T::MSG_ID) {
                printf("  [%zu] FAIL: Message ID mismatch (expected 0x%04X, got 0x%04X)\n", 
                       i, T::MSG_ID, frame_info.msg_id);
                return false;
            }
            
            // Decode the message
            T decoded{};
            size_t bytes_read = decoded.deserialize(frame_info);
            
            if (bytes_read == 0) {
                printf("  [%zu] FAIL: Deserialize failed\n", i);
                return false;
            }
            
            // Compare original and decoded message
            if (std::memcmp(&msg, &decoded, sizeof(T)) != 0) {
                printf("  [%zu] FAIL: Data mismatch after decode\n", i);
                return false;
            }
            
            printf("  [%zu] PASS: MSG_ID=0x%04X, encoded=%zu bytes, decoded=%zu bytes\n", 
                   i, T::MSG_ID, written, bytes_read);
            return true;
        }, msg_variant);
        
        if (success) {
            passed++;
        } else {
            failed++;
        }
    }

    printf("\n=============================================================\n");
    printf("SUMMARY\n");
    printf("=============================================================\n");
    printf("\n");
    printf("  Messages tested: %zu\n", StandardMessages::MESSAGE_COUNT);
    printf("  Passed: %zu\n", passed);
    printf("  Failed: %zu\n", failed);
    printf("\n");

    if (failed == 0) {
        printf("[TEST PASSED] All %zu messages encoded/decoded/verified successfully.\n", passed);
    } else {
        printf("[TEST FAILED] %zu of %zu messages failed.\n", failed, StandardMessages::MESSAGE_COUNT);
    }
    printf("\n");

    return (failed == 0) ? 0 : 1;
}
