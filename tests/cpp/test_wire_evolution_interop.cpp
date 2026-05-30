/**
 * Cross-version wire-evolution *interop* tests for the generated C++ bindings.
 *
 * Unlike the single-schema round-trip test, this runner uses two SEPARATELY
 * generated schema versions of the same messages:
 *
 *   - wire_evolution_v1  -- base fields only (older, extension-unaware)
 *   - wire_evolution_v2  -- base fields + `extensions_start` extension fields
 *
 * Each side has its own message structs, magic constants and
 * `get_message_info` lookup, exactly as two independently-built code-bases
 * would.  The tests exercise genuine newer<->older interop over the
 * length-bearing Standard/Bulk/Network profiles plus negative coverage.
 *
 * Scenarios (mirrors the project's wire-evolution interop plan, 1-10):
 *   1. Newer sender -> older receiver (v2 encodes extensions, v1 decodes base)
 *   2. Older sender -> newer receiver (v1 base-only, v2 zero-fills extensions)
 *   3. Same-version sanity (v2 -> v2 with extension variant)
 *   4. Newer ext oneof variant -> older receiver degrades gracefully
 *   5. Older base oneof variant -> newer receiver decodes correctly
 *   6. Multi-oneof: base oneof unaffected while ext oneof exercises 4/5
 *   7. Corrupted extension bytes invalidate the full CRC
 *   8. Truncated payload (fewer bytes than length field claims) is rejected
 *   9. Length-less profile guard (IPC): both sides must agree on full size
 *  10. Variable base array + trailing extension field, both interop directions
 *
 * Build:
 *   g++ -std=c++20 -I../../generated/cpp test_wire_evolution_interop.cpp \
 *       -o test_wire_evolution_interop
 */

#include <cstdio>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <array>

#include "../generated/cpp/wire_evolution_v1.structframe.hpp"
#include "../generated/cpp/wire_evolution_v2.structframe.hpp"
#include "../generated/cpp/frame_profiles.hpp"

using namespace structframe;
namespace v1 = structframe::wire_evolution_v1;
namespace v2 = structframe::wire_evolution_v2;

static int g_pass = 0;
static int g_fail = 0;

static void check(bool cond, const char* msg) {
    if (cond) { printf("  [PASS] %s\n", msg); ++g_pass; }
    else      { printf("  [FAIL] %s\n", msg); ++g_fail; }
}

// Copy a (possibly shorter, base-only) payload into a MAX_SIZE zero buffer so a
// newer receiver can zero-fill the missing extension bytes before decoding.
template <typename Msg>
static void decode_zerofill(Msg& out, const uint8_t* data, size_t len) {
    uint8_t padded[Msg::MAX_SIZE];
    std::memset(padded, 0, sizeof(padded));
    if (len > Msg::MAX_SIZE) len = Msg::MAX_SIZE;
    std::memcpy(padded, data, len);
    out.deserialize(padded, sizeof(padded));
}

// ---------------------------------------------------------------------------
// Scenario 1: newer sender -> older receiver over length-bearing profiles
// ---------------------------------------------------------------------------
template <typename Config>
static void scenario_1_profile(const char* name) {
    v2::BaseExtensionMessage m{};
    m.header = 0xBEEF; m.seq = 42; m.crc_seed = 0xDEADC0DE;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<Config>::encode(buffer, sizeof(buffer), m);

    char label[128];
    auto result = BufferParserWithCrc<Config>::parse(buffer, encoded, v1::get_message_info);
    snprintf(label, sizeof(label), "[S1/%s] v2->v1 frame validates CRC (magic from base)", name);
    check(result.valid, label);

    if (result.valid && result.msg_data) {
        v1::BaseExtensionMessage d{};
        d.deserialize(result.msg_data, result.msg_len);
        snprintf(label, sizeof(label), "[S1/%s] v1 decodes base; trailing ext bytes ignored", name);
        check(d.header == 0xBEEF && d.seq == 42, label);
    }
}

static void scenario_1() {
    scenario_1_profile<ProfileStandardConfig>("standard");
    scenario_1_profile<ProfileBulkConfig>("bulk");
    scenario_1_profile<ProfileNetworkConfig>("network");
}

// ---------------------------------------------------------------------------
// Scenario 2: older sender -> newer receiver (zero-fill extensions)
// ---------------------------------------------------------------------------
static void scenario_2() {
    v1::BaseExtensionMessage m{};
    m.header = 0x1234; m.seq = 7;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v2::get_message_info);
    check(result.valid, "[S2] v1->v2 base-only frame validates CRC");

    if (result.valid && result.msg_data) {
        v2::BaseExtensionMessage d{};
        decode_zerofill(d, result.msg_data, result.msg_len);
        check(d.header == 0x1234 && d.seq == 7, "[S2] v2 decodes base fields correctly");
        check(d.crc_seed == 0, "[S2] v2 extension field zero-filled to default");
    }
}

// ---------------------------------------------------------------------------
// Scenario 3: same-version sanity (v2 -> v2 with extension variant)
// ---------------------------------------------------------------------------
static void scenario_3() {
    v2::OneOfExtensionMessage m{};
    m.device_id = 2;
    m.command_discriminator = v2::OneOfExtensionMessage::CommandField::CMD_C;
    m.command.cmd_c.value_c = 3.14f;
    m.command.cmd_c.mode_c = 2;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v2::get_message_info);
    check(result.valid, "[S3] v2->v2 (ext variant) frame validates CRC");

    if (result.valid && result.msg_data) {
        v2::OneOfExtensionMessage d{};
        d.deserialize(result.msg_data, result.msg_len);
        check(d.command_discriminator == v2::OneOfExtensionMessage::CommandField::CMD_C
              && std::fabs(d.command.cmd_c.value_c - 3.14f) < 1e-4f,
              "[S3] v2 round-trips the extension variant");
    }
}

// ---------------------------------------------------------------------------
// Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
// ---------------------------------------------------------------------------
static void scenario_4() {
    v2::OneOfExtensionMessage m{};
    m.device_id = 9;
    m.command_discriminator = v2::OneOfExtensionMessage::CommandField::CMD_D;
    m.command.cmd_d.value_d = 2.718281828;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v1::get_message_info);
    check(result.valid, "[S4] v2 ext-variant -> v1 frame validates CRC");

    if (result.valid && result.msg_data) {
        v1::OneOfExtensionMessage d{};
        d.deserialize(result.msg_data, result.msg_len);
        check(d.device_id == 9, "[S4] v1 still decodes the base header field");
        // v1 knows nothing about discriminator 4; it must preserve the raw value
        // without corrupting the base field.
        check(static_cast<int>(d.command_discriminator) == 4,
              "[S4] v1 preserves unknown ext discriminator without corruption");
    }
}

// ---------------------------------------------------------------------------
// Scenario 5: older base oneof variant -> newer receiver decodes correctly
// ---------------------------------------------------------------------------
static void scenario_5() {
    v1::OneOfExtensionMessage m{};
    m.device_id = 5;
    m.command_discriminator = v1::OneOfExtensionMessage::CommandField::CMD_B;
    m.command.cmd_b.value_b = -1234;
    m.command.cmd_b.active_b = true;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v2::get_message_info);
    check(result.valid, "[S5] v1 base-variant -> v2 frame validates CRC");

    if (result.valid && result.msg_data) {
        v2::OneOfExtensionMessage d{};
        decode_zerofill(d, result.msg_data, result.msg_len);
        check(d.command_discriminator == v2::OneOfExtensionMessage::CommandField::CMD_B
              && d.command.cmd_b.value_b == -1234,
              "[S5] v2 decodes the older base oneof variant correctly");
    }
}

// ---------------------------------------------------------------------------
// Scenario 6: multi-oneof, ext only in the second union
// ---------------------------------------------------------------------------
static void scenario_6() {
    v2::MultiOneOfExtensionMessage m{};
    m.priority = 3;
    m.base_union_discriminator = v2::MultiOneOfExtensionMessage::BaseUnionField::FIRST_A;
    m.base_union.first_a.value_a = 100;
    m.base_union.first_a.flags_a = 5;
    m.ext_union_discriminator = v2::MultiOneOfExtensionMessage::ExtUnionField::SECOND_EXT;
    m.ext_union.second_ext.value_c = 2.71f;
    m.ext_union.second_ext.mode_c = 1;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v1::get_message_info);
    check(result.valid, "[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC");

    if (result.valid && result.msg_data) {
        v1::MultiOneOfExtensionMessage d{};
        d.deserialize(result.msg_data, result.msg_len);
        check(d.priority == 3
              && d.base_union_discriminator == v1::MultiOneOfExtensionMessage::BaseUnionField::FIRST_A
              && d.base_union.first_a.value_a == 100,
              "[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second");
    }
}

// ---------------------------------------------------------------------------
// Scenario 7: corrupted extension bytes invalidate the full CRC
// ---------------------------------------------------------------------------
static void scenario_7() {
    v2::BaseExtensionMessage m{};
    m.header = 0xBEEF; m.seq = 42; m.crc_seed = 0xDEADC0DE;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    // Payload data starts at header_size; extension region begins BASE_SIZE in.
    size_t ext_offset = ProfileStandardConfig::header_size
                      + v2::BaseExtensionMessage::BASE_SIZE;
    buffer[ext_offset] ^= 0xFF;

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v1::get_message_info);
    check(!result.valid, "[S7] corrupted extension byte invalidates full CRC");
}

// ---------------------------------------------------------------------------
// Scenario 8: truncated payload is rejected
// ---------------------------------------------------------------------------
static void scenario_8() {
    v1::BaseExtensionMessage m{};
    m.header = 1; m.seq = 2;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    // Drop the last byte — fewer bytes than the length field claims.
    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded - 1, v1::get_message_info);
    check(!result.valid, "[S8] truncated payload (fewer bytes than length claims) is rejected");
}

// ---------------------------------------------------------------------------
// Scenario 9: length-less profile guard (IPC)
//
// On a length-less (IPC) profile both sides must agree on the full fixed size.
// An older (base-only, shorter) frame is NOT silently accepted by a newer
// receiver because the frame size does not match the expected MAX_SIZE.
// ---------------------------------------------------------------------------
static void scenario_9() {
    // Positive: same-version v2 over IPC validates.
    v2::BaseExtensionMessage same{};
    same.header = 0xAA; same.seq = 5; same.crc_seed = 0x99;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderMinimal<ProfileIPCConfig>::encode(buffer, sizeof(buffer), same);
    auto result = BufferParserMinimal<ProfileIPCConfig>::parse(
        buffer, encoded, v2::get_message_info);
    check(result.valid, "[S9] IPC same-version v2 frame validates");

    // Negative: base-only v1 frame (shorter) rejected by newer v2 receiver.
    v1::BaseExtensionMessage older{};
    older.header = 0xAA; older.seq = 5;

    uint8_t buffer2[256];
    size_t encoded2 = FrameEncoderMinimal<ProfileIPCConfig>::encode(buffer2, sizeof(buffer2), older);
    auto result2 = BufferParserMinimal<ProfileIPCConfig>::parse(
        buffer2, encoded2, v2::get_message_info);
    check(!result2.valid,
          "[S9] IPC base-only older frame is rejected by newer receiver "
          "(both sides must agree on size)");
}

// ---------------------------------------------------------------------------
// Scenario 10: variable base array + trailing extension, both directions
// ---------------------------------------------------------------------------
static void scenario_10() {
    // Newer -> older: v1 locates variable base, ignores trailing ext bytes.
    v2::VariableExtensionMessage m{};
    m.node_id = 7;
    m.readings.count = 3;
    m.readings.data[0] = 10; m.readings.data[1] = 20; m.readings.data[2] = 30;
    m.ext_timestamp = 0x12345678;

    uint8_t buffer[256];
    size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer, sizeof(buffer), m);

    auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer, encoded, v1::get_message_info);
    check(result.valid, "[S10] v2 variable+ext -> v1 validates CRC");
    if (result.valid && result.msg_data) {
        v1::VariableExtensionMessage d{};
        d.deserialize(result.msg_data, result.msg_len);
        check(d.node_id == 7
              && d.readings.count == 3
              && d.readings.data[0] == 10
              && d.readings.data[1] == 20
              && d.readings.data[2] == 30,
              "[S10] v1 locates/decodes variable base; trailing ext bytes ignored");
    }

    // Older -> newer: v2 zero-fills the trailing extension field.
    v1::VariableExtensionMessage m1{};
    m1.node_id = 9;
    m1.readings.count = 2;
    m1.readings.data[0] = 1; m1.readings.data[1] = 2;

    uint8_t buffer2[256];
    size_t encoded2 = FrameEncoderWithCrc<ProfileStandardConfig>::encode(buffer2, sizeof(buffer2), m1);

    auto result2 = BufferParserWithCrc<ProfileStandardConfig>::parse(
        buffer2, encoded2, v2::get_message_info);
    check(result2.valid, "[S10] v1 variable (base-only) -> v2 validates CRC");
    if (result2.valid && result2.msg_data) {
        v2::VariableExtensionMessage d2{};
        decode_zerofill(d2, result2.msg_data, result2.msg_len);
        check(d2.node_id == 9
              && d2.readings.count == 2
              && d2.readings.data[0] == 1
              && d2.readings.data[1] == 2,
              "[S10] v2 locates variable base after cross-version decode");
        check(d2.ext_timestamp == 0, "[S10] v2 zero-fills the trailing extension field");
    }
}

int main() {
    printf("=== C++ Cross-Version Wire-Evolution Interop Tests ===\n\n");
    printf("Scenario 1: newer sender -> older receiver (length-bearing)\n");
    scenario_1();
    printf("\nScenario 2: older sender -> newer receiver (zero-fill)\n");
    scenario_2();
    printf("\nScenario 3: same-version sanity (v2 -> v2)\n");
    scenario_3();
    printf("\nScenario 4: newer ext oneof variant -> older receiver\n");
    scenario_4();
    printf("\nScenario 5: older base oneof variant -> newer receiver\n");
    scenario_5();
    printf("\nScenario 6: multi-oneof (ext only in 2nd union)\n");
    scenario_6();
    printf("\nScenario 7: corrupted extension bytes invalidate CRC\n");
    scenario_7();
    printf("\nScenario 8: truncated payload rejected\n");
    scenario_8();
    printf("\nScenario 9: length-less profile guard (IPC)\n");
    scenario_9();
    printf("\nScenario 10: variable base + trailing extension (both directions)\n");
    scenario_10();
    printf("\nResults: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
