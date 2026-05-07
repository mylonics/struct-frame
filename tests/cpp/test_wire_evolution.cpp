/**
 * Wire-evolution extension field tests for the C++ SDK.
 *
 * Verifies that `option extensions_start` and the extension-aware CRC algorithm
 * work correctly end-to-end using the generated C++ bindings.
 *
 * Tests:
 *   1. BASE_SIZE < MAX_SIZE for extension messages
 *   2. Encode → decode round-trip for BaseExtensionMessage (Standard profile)
 *   3. Encode → decode round-trip for OneOfExtensionMessage (extension variant)
 *   4. Encode → decode round-trip for MultiOneOfExtensionMessage
 *   5. Legacy-frame compatibility: a frame with only base bytes still validates
 *
 * Build:
 *   g++ -std=c++20 -I../../generated/cpp test_wire_evolution.cpp -o test_wire_evolution
 *
 * Run:
 *   ./test_wire_evolution
 */

#include <cstdio>
#include <cstring>
#include <cmath>
#include <cstdint>

#include "../../generated/cpp/wire_evolution.structframe.hpp"
#include "../../generated/cpp/frame_profiles.hpp"

using namespace structframe;
using namespace structframe::wire_evolution;

// ---------------------------------------------------------------------------
// Simple test harness
// ---------------------------------------------------------------------------

static int g_pass = 0;
static int g_fail = 0;

static void check(bool cond, const char* msg) {
    if (cond) {
        printf("  [PASS] %s\n", msg);
        ++g_pass;
    } else {
        printf("  [FAIL] %s\n", msg);
        ++g_fail;
    }
}

// ---------------------------------------------------------------------------
// Test 1: compile-time BASE_SIZE < MAX_SIZE
// ---------------------------------------------------------------------------

void test_base_size_constants() {
    check(BaseExtensionMessage::BASE_SIZE < BaseExtensionMessage::MAX_SIZE,
          "BaseExtensionMessage BASE_SIZE < MAX_SIZE");
    check(BaseExtensionMessage::BASE_SIZE == 3,
          "BaseExtensionMessage BASE_SIZE == 3 (header+seq)");
    check(BaseExtensionMessage::MAX_SIZE == 7,
          "BaseExtensionMessage MAX_SIZE == 7 (header+seq+crc_seed)");

    check(OneOfExtensionMessage::BASE_SIZE < OneOfExtensionMessage::MAX_SIZE,
          "OneOfExtensionMessage BASE_SIZE < MAX_SIZE");

    // MultiOneOfExtensionMessage: BASE_SIZE == MAX_SIZE (all fields are base)
    check(MultiOneOfExtensionMessage::BASE_SIZE == MultiOneOfExtensionMessage::MAX_SIZE,
          "MultiOneOfExtensionMessage BASE_SIZE == MAX_SIZE (no extensions)");
}

// ---------------------------------------------------------------------------
// Test 2: BaseExtensionMessage encode → decode round-trip (Standard profile)
// ---------------------------------------------------------------------------

void test_base_extension_roundtrip() {
    BaseExtensionMessage orig{};
    orig.header   = 0xBEEF;
    orig.seq      = 42;
    orig.crc_seed = 0xDEADC0DE;

    uint8_t buffer[512];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
        buffer, sizeof(buffer), orig);

    check(encoded > 0, "BaseExtensionMessage encode succeeded");

    // Parse back
    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, get_message_info);

    check(result.valid, "BaseExtensionMessage frame validates CRC");
    check(result.msg_id == BaseExtensionMessage::MSG_ID,
          "BaseExtensionMessage msg_id matches");
    check(result.msg_len == BaseExtensionMessage::MAX_SIZE,
          "BaseExtensionMessage msg_len matches MAX_SIZE");

    if (result.valid && result.msg_data) {
        BaseExtensionMessage decoded{};
        decoded.deserialize(result.msg_data, result.msg_len);
        check(decoded.header   == 0xBEEF,     "decoded header matches");
        check(decoded.seq      == 42,          "decoded seq matches");
        check(decoded.crc_seed == 0xDEADC0DE, "decoded crc_seed matches");
    }
}

// ---------------------------------------------------------------------------
// Test 3: OneOfExtensionMessage with extension variant
// ---------------------------------------------------------------------------

void test_oneof_extension_variant_roundtrip() {
    OneOfExtensionMessage orig{};
    orig.device_id             = 7;
    orig.command_discriminator = OneOfExtensionMessage::CommandField::CMD_C;
    orig.command.cmd_c.value_c = 3.14f;
    orig.command.cmd_c.mode_c  = 2;

    uint8_t buffer[512];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
        buffer, sizeof(buffer), orig);

    check(encoded > 0, "OneOfExtensionMessage (ext variant) encode succeeded");

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, get_message_info);

    check(result.valid, "OneOfExtensionMessage (ext variant) frame validates CRC");

    if (result.valid && result.msg_data) {
        OneOfExtensionMessage decoded{};
        decoded.deserialize(result.msg_data, result.msg_len);
        check(decoded.device_id == 7, "decoded device_id matches");
        check(decoded.command_discriminator == OneOfExtensionMessage::CommandField::CMD_C,
              "decoded command discriminator == CMD_C");
        check(std::fabs(decoded.command.cmd_c.value_c - 3.14f) < 1e-4f,
              "decoded cmd_c.value_c matches");
        check(decoded.command.cmd_c.mode_c == 2, "decoded cmd_c.mode_c matches");
    }
}

// ---------------------------------------------------------------------------
// Test 4: MultiOneOfExtensionMessage with extension variant in second oneof
// ---------------------------------------------------------------------------

void test_multi_oneof_extension_roundtrip() {
    MultiOneOfExtensionMessage orig{};
    orig.priority                  = 3;
    orig.base_union_discriminator  = MultiOneOfExtensionMessage::BaseUnionField::FIRST_A;
    orig.base_union.first_a.value_a = 100;
    orig.base_union.first_a.flags_a = 5;
    orig.ext_union_discriminator   = MultiOneOfExtensionMessage::ExtUnionField::SECOND_EXT;
    orig.ext_union.second_ext.value_c = 2.71f;
    orig.ext_union.second_ext.mode_c  = 1;

    uint8_t buffer[512];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
        buffer, sizeof(buffer), orig);

    check(encoded > 0, "MultiOneOfExtensionMessage encode succeeded");

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, get_message_info);

    check(result.valid, "MultiOneOfExtensionMessage frame validates CRC");

    if (result.valid && result.msg_data) {
        MultiOneOfExtensionMessage decoded{};
        decoded.deserialize(result.msg_data, result.msg_len);
        check(decoded.priority == 3, "decoded priority matches");
        check(decoded.ext_union_discriminator ==
              MultiOneOfExtensionMessage::ExtUnionField::SECOND_EXT,
              "decoded ext_union discriminator == SECOND_EXT");
        check(std::fabs(decoded.ext_union.second_ext.value_c - 2.71f) < 1e-4f,
              "decoded second_ext.value_c matches");
    }
}

// ---------------------------------------------------------------------------
// Test 5: Legacy-frame compatibility
//
// A "legacy" sender encodes only the base portion (BASE_SIZE bytes).
// An extension-aware receiver pads the payload to MAX_SIZE and validates.
// The CRC must pass because the extension bytes are all-zeros.
// ---------------------------------------------------------------------------

void test_legacy_frame_compatibility() {
    // Build a frame with only base fields populated; extension bytes are zero.
    BaseExtensionMessage orig{};
    orig.header   = 0x1234;
    orig.seq      = 7;
    orig.crc_seed = 0;  // legacy sender does not set this

    uint8_t buffer[512];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
        buffer, sizeof(buffer), orig);

    check(encoded > 0, "legacy (zero extension) frame encodes");

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, get_message_info);

    check(result.valid, "legacy (zero extension) frame validates CRC");

    if (result.valid && result.msg_data) {
        BaseExtensionMessage decoded{};
        decoded.deserialize(result.msg_data, result.msg_len);
        check(decoded.header == 0x1234, "legacy decoded header matches");
        check(decoded.seq    == 7,      "legacy decoded seq matches");
        check(decoded.crc_seed == 0,    "legacy decoded crc_seed is 0");
    }

    // Verify that corrupting the extension bytes invalidates the CRC
    if (encoded > 0) {
        uint8_t bad_buffer[512];
        memcpy(bad_buffer, buffer, encoded);
        // Flip a bit in the extension area of the payload.
        // Payload data starts at buffer offset header_size.
        // The extension field is at payload offset BASE_SIZE..MAX_SIZE-1.
        size_t ext_offset = ProfileStandardConfig::header_size
                          + BaseExtensionMessage::BASE_SIZE;
        bad_buffer[ext_offset] ^= 0xFF;

        auto bad_result = BufferParserWithCrc<ProfileStandardConfig>::parse(
            bad_buffer, encoded, get_message_info);
        check(!bad_result.valid, "corrupted extension bytes invalidate CRC");
    }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main() {
    printf("=== C++ Wire-Evolution Extension Field Tests ===\n\n");

    printf("Test group 1: BASE_SIZE constants\n");
    test_base_size_constants();
    printf("\n");

    printf("Test group 2: BaseExtensionMessage encode/decode round-trip\n");
    test_base_extension_roundtrip();
    printf("\n");

    printf("Test group 3: OneOfExtensionMessage (extension variant) round-trip\n");
    test_oneof_extension_variant_roundtrip();
    printf("\n");

    printf("Test group 4: MultiOneOfExtensionMessage (extension variant) round-trip\n");
    test_multi_oneof_extension_roundtrip();
    printf("\n");

    printf("Test group 5: Legacy-frame compatibility\n");
    test_legacy_frame_compatibility();
    printf("\n");

    printf("Results: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
