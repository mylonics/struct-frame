/**
 * Cross-version wire-evolution *interop* tests for the generated C bindings.
 *
 * Unlike a single-schema round-trip test, this runner uses two SEPARATELY
 * generated schema versions of the same messages:
 *
 *   - wire_evolution_v1  -- base fields only (older, extension-unaware)
 *   - wire_evolution_v2  -- base fields + `extensions_start` extension fields
 *
 * Each side has its own message structs, magic constants and
 * `*_get_message_info` lookup, exactly as two independently-built code-bases
 * would.  The tests exercise genuine newer<->older interop over the
 * length-bearing Standard/Bulk/Network profiles plus negative coverage.
 *
 * Scenarios (mirrors the project's wire-evolution interop plan, 1-7):
 *   1. Newer sender -> older receiver (v2 encodes extensions, v1 decodes base)
 *   2. Older sender -> newer receiver (v1 base-only, v2 zero-fills extensions)
 *   3. Same-version sanity (v2 -> v2 with extension variant)
 *   4. Newer ext oneof variant -> older receiver degrades gracefully
 *   5. Older base oneof variant -> newer receiver decodes correctly
 *   6. Multi-oneof: base oneof unaffected while ext oneof exercises 4/5
 *   7. Corrupted extension bytes invalidate the full CRC
 *
 * Build:
 *   gcc -I../../generated/c test_wire_evolution_interop.c -o test_wire_evolution_interop -lm
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <stdbool.h>

#include "wire_evolution_v1.structframe.h"
#include "wire_evolution_v2.structframe.h"
#include "frame_profiles.h"

static int g_pass = 0;
static int g_fail = 0;

static void check(bool cond, const char* msg) {
    if (cond) { printf("  [PASS] %s\n", msg); ++g_pass; }
    else      { printf("  [FAIL] %s\n", msg); ++g_fail; }
}

/* Encode a payload into a frame with extension-aware CRC over a profile. */
static size_t encode_ext(const profile_config_t* config, uint8_t* buffer, size_t cap,
                         uint8_t msg_id, const uint8_t* payload, size_t payload_size,
                         size_t base_size, uint8_t magic1, uint8_t magic2) {
    buffer_writer_t writer;
    buffer_writer_init(&writer, config, buffer, cap);
    return buffer_writer_write_ext(&writer, msg_id, payload, payload_size,
                                   0, 0, 0, 0, base_size, magic1, magic2);
}

static frame_msg_info_t parse_with(const profile_config_t* config, uint8_t* buffer,
                                   size_t frame_size, bool (*gmi)(uint16_t, message_info_t*)) {
    buffer_reader_t reader;
    buffer_reader_init(&reader, config, buffer, frame_size, gmi);
    return buffer_reader_next(&reader);
}

/* -------------------------------------------------------------------------
 * Scenario 1: newer sender -> older receiver over length-bearing profiles
 * ------------------------------------------------------------------------- */
static void scenario_1(void) {
    const profile_config_t* configs[3] = {
        &PROFILE_STANDARD_CONFIG, &PROFILE_BULK_CONFIG, &PROFILE_NETWORK_CONFIG };
    const char* names[3] = { "standard", "bulk", "network" };

    for (int i = 0; i < 3; ++i) {
        WireEvolutionV2BaseExtensionMessage m = {0};
        m.header = 0xBEEF; m.seq = 42; m.crc_seed = 0xDEADC0DE;
        uint8_t payload[64];
        size_t plen = WireEvolutionV2BaseExtensionMessage_serialize(&m, payload);

        uint8_t buffer[128];
        size_t fs = encode_ext(configs[i], buffer, sizeof(buffer),
                               WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MSG_ID,
                               payload, plen,
                               WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_BASE_SIZE,
                               WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MAGIC1,
                               WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MAGIC2);
        char label[96];
        snprintf(label, sizeof(label), "[S1/%s] v2->v1 frame validates CRC (magic from base)", names[i]);

        frame_msg_info_t r = parse_with(configs[i], buffer, fs, wire_evolution_v1_get_message_info);
        check(r.valid, label);

        if (r.valid && r.msg_data) {
            WireEvolutionV1BaseExtensionMessage d = {0};
            WireEvolutionV1BaseExtensionMessage_deserialize(r.msg_data, r.msg_len, &d);
            snprintf(label, sizeof(label), "[S1/%s] v1 decodes base; trailing ext bytes ignored", names[i]);
            check(d.header == 0xBEEF && d.seq == 42, label);
        }
    }
}

/* -------------------------------------------------------------------------
 * Scenario 2: older sender -> newer receiver (zero-fill extensions)
 * ------------------------------------------------------------------------- */
static void scenario_2(void) {
    WireEvolutionV1BaseExtensionMessage m = {0};
    m.header = 0x1234; m.seq = 7;
    uint8_t payload[64];
    size_t plen = WireEvolutionV1BaseExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V1_BASE_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V1_BASE_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V1_BASE_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V1_BASE_EXTENSION_MESSAGE_MAGIC2);

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v2_get_message_info);
    check(r.valid, "[S2] v1->v2 base-only frame validates CRC");

    if (r.valid && r.msg_data) {
        /* Newer receiver zero-fills the missing extension bytes before decoding. */
        uint8_t padded[WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MAX_SIZE] = {0};
        size_t copy_len = r.msg_len < sizeof(padded) ? r.msg_len : sizeof(padded);
        memcpy(padded, r.msg_data, copy_len);
        WireEvolutionV2BaseExtensionMessage d = {0};
        WireEvolutionV2BaseExtensionMessage_deserialize(padded, sizeof(padded), &d);
        check(d.header == 0x1234 && d.seq == 7, "[S2] v2 decodes base fields correctly");
        check(d.crc_seed == 0, "[S2] v2 extension field zero-filled to default");
    }
}

/* -------------------------------------------------------------------------
 * Scenario 3: same-version sanity (v2 -> v2 with extension variant)
 * ------------------------------------------------------------------------- */
static void scenario_3(void) {
    WireEvolutionV2OneOfExtensionMessage m = {0};
    m.device_id = 2;
    m.command_discriminator = WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_COMMAND_FIELD_CMD_C;
    m.command.cmd_c.value_c = 3.14f;
    m.command.cmd_c.mode_c = 2;
    uint8_t payload[64];
    size_t plen = WireEvolutionV2OneOfExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MAGIC2);

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v2_get_message_info);
    check(r.valid, "[S3] v2->v2 (ext variant) frame validates CRC");
    if (r.valid && r.msg_data) {
        WireEvolutionV2OneOfExtensionMessage d = {0};
        WireEvolutionV2OneOfExtensionMessage_deserialize(r.msg_data, r.msg_len, &d);
        check(d.command_discriminator == WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_COMMAND_FIELD_CMD_C
              && fabsf(d.command.cmd_c.value_c - 3.14f) < 1e-4f,
              "[S3] v2 round-trips the extension variant");
    }
}

/* -------------------------------------------------------------------------
 * Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
 * ------------------------------------------------------------------------- */
static void scenario_4(void) {
    WireEvolutionV2OneOfExtensionMessage m = {0};
    m.device_id = 9;
    m.command_discriminator = WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_COMMAND_FIELD_CMD_D;
    m.command.cmd_d.value_d = 2.718281828;
    uint8_t payload[64];
    size_t plen = WireEvolutionV2OneOfExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MAGIC2);

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v1_get_message_info);
    check(r.valid, "[S4] v2 ext-variant -> v1 frame validates CRC");
    if (r.valid && r.msg_data) {
        WireEvolutionV1OneOfExtensionMessage d = {0};
        WireEvolutionV1OneOfExtensionMessage_deserialize(r.msg_data, r.msg_len, &d);
        check(d.device_id == 9, "[S4] v1 still decodes the base header field");
        /* v1 knows nothing about discriminator 4; it must preserve the raw value
         * without corrupting the base field. */
        check((int)d.command_discriminator == 4,
              "[S4] v1 preserves unknown ext discriminator without corruption");
    }
}

/* -------------------------------------------------------------------------
 * Scenario 5: older base oneof variant -> newer receiver decodes correctly
 * ------------------------------------------------------------------------- */
static void scenario_5(void) {
    WireEvolutionV1OneOfExtensionMessage m = {0};
    m.device_id = 5;
    m.command_discriminator = WIRE_EVOLUTION_V1_ONE_OF_EXTENSION_MESSAGE_COMMAND_FIELD_CMD_B;
    m.command.cmd_b.value_b = -1234;
    m.command.cmd_b.active_b = true;
    uint8_t payload[64];
    size_t plen = WireEvolutionV1OneOfExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V1_ONE_OF_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V1_ONE_OF_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V1_ONE_OF_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V1_ONE_OF_EXTENSION_MESSAGE_MAGIC2);

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v2_get_message_info);
    check(r.valid, "[S5] v1 base-variant -> v2 frame validates CRC");
    if (r.valid && r.msg_data) {
        uint8_t padded[WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_MAX_SIZE] = {0};
        size_t copy_len = r.msg_len < sizeof(padded) ? r.msg_len : sizeof(padded);
        memcpy(padded, r.msg_data, copy_len);
        WireEvolutionV2OneOfExtensionMessage d = {0};
        WireEvolutionV2OneOfExtensionMessage_deserialize(padded, sizeof(padded), &d);
        check(d.command_discriminator == WIRE_EVOLUTION_V2_ONE_OF_EXTENSION_MESSAGE_COMMAND_FIELD_CMD_B
              && d.command.cmd_b.value_b == -1234,
              "[S5] v2 decodes the older base oneof variant correctly");
    }
}

/* -------------------------------------------------------------------------
 * Scenario 6: multi-oneof, ext only in the second union
 * ------------------------------------------------------------------------- */
static void scenario_6(void) {
    /* Newer sender selects the ext variant in the second union only. */
    WireEvolutionV2MultiOneOfExtensionMessage m = {0};
    m.priority = 3;
    m.base_union_discriminator = WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_BASE_UNION_FIELD_FIRST_A;
    m.base_union.first_a.value_a = 100;
    m.base_union.first_a.flags_a = 5;
    m.ext_union_discriminator = WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_EXT_UNION_FIELD_SECOND_EXT;
    m.ext_union.second_ext.value_c = 2.71f;
    m.ext_union.second_ext.mode_c = 1;
    uint8_t payload[64];
    size_t plen = WireEvolutionV2MultiOneOfExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V2_MULTI_ONE_OF_EXTENSION_MESSAGE_MAGIC2);

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v1_get_message_info);
    check(r.valid, "[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC");
    if (r.valid && r.msg_data) {
        WireEvolutionV1MultiOneOfExtensionMessage d = {0};
        WireEvolutionV1MultiOneOfExtensionMessage_deserialize(r.msg_data, r.msg_len, &d);
        check(d.priority == 3
              && d.base_union_discriminator == WIRE_EVOLUTION_V1_MULTI_ONE_OF_EXTENSION_MESSAGE_BASE_UNION_FIELD_FIRST_A
              && d.base_union.first_a.value_a == 100,
              "[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second");
    }
}

/* -------------------------------------------------------------------------
 * Scenario 7: corrupted extension bytes invalidate the full CRC
 * ------------------------------------------------------------------------- */
static void scenario_7(void) {
    WireEvolutionV2BaseExtensionMessage m = {0};
    m.header = 0xBEEF; m.seq = 42; m.crc_seed = 0xDEADC0DE;
    uint8_t payload[64];
    size_t plen = WireEvolutionV2BaseExtensionMessage_serialize(&m, payload);

    uint8_t buffer[128];
    size_t fs = encode_ext(&PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer),
                           WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MSG_ID,
                           payload, plen,
                           WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_BASE_SIZE,
                           WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MAGIC1,
                           WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_MAGIC2);

    /* Footer is 2 bytes; the extension region starts BASE_SIZE bytes into the
     * payload, which itself starts (frame_size - footer - msg_len) bytes in. */
    frame_msg_info_t probe = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v1_get_message_info);
    size_t payload_off = fs - 2 - probe.msg_len;
    size_t ext_off = payload_off + WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_BASE_SIZE;
    buffer[ext_off] ^= 0xFF;

    frame_msg_info_t r = parse_with(&PROFILE_STANDARD_CONFIG, buffer, fs, wire_evolution_v1_get_message_info);
    check(!r.valid, "[S7] corrupted extension byte invalidates full CRC");
}

int main(void) {
    printf("=== C Cross-Version Wire-Evolution Interop Tests ===\n\n");
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
    printf("\nResults: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
