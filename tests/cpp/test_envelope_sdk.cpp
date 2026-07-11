/**
 * Test for envelope SDK interface: msgid-discriminator (CommandEnvelope) and
 * field_order-discriminator (RawDataEnvelope) round-trips.
 *
 * Mirrors tests/rust/src/main.rs::run_envelope_sdk_tests().
 */

#include <cstdio>
#include <cstring>
#include <cmath>
#include <vector>

#include "frame_profiles.hpp"
#include "envelope_test.structframe.hpp"

using namespace structframe;
using namespace structframe::envelope_test;

static int g_passed = 0;
static int g_failed = 0;

static void expect(bool condition, const char* name) {
  if (condition) {
    printf("  PASS  %s\n", name);
    g_passed++;
  } else {
    printf("  FAIL  %s\n", name);
    g_failed++;
  }
}

int main() {
  printf("=== C++ EnvelopeSdk tests ===\n");

  // --- CommandEnvelope with msgid discriminator ---
  ADCCommand adc{};
  adc.channel = 2;
  adc.sample_rate = 1000;
  adc.enable = true;
  CommandEnvelope env = CommandEnvelope::wrap(42, 5, true, adc);

  expect(env.command_discriminator == ADCCommand::MSG_ID,
         "CommandEnvelope: discriminator == ADCCommand::MSG_ID");

  // Encode with ProfileStandard (MSG_ID=200 fits in u8)
  std::vector<uint8_t> buffer(2048);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  size_t written = writer.write(env);
  expect(written > 0, "CommandEnvelope: write returned > 0");

  AccumulatingReader<ProfileStandardConfig, 4096, decltype(&get_message_info)> reader(get_message_info);
  reader.add_data(buffer.data(), written);
  auto frame = reader.next();
  expect(frame.valid, "CommandEnvelope: frame valid");
  if (frame.valid) {
    expect(frame.msg_id == CommandEnvelope::MSG_ID, "CommandEnvelope: msg_id matches");
    CommandEnvelope decoded;
    size_t n = decoded.deserialize(frame);
    expect(n > 0, "CommandEnvelope: deserialize succeeded");
    expect(decoded.sequence_number == 42, "CommandEnvelope: sequence_number round-trips");
    expect(decoded.priority == 5, "CommandEnvelope: priority round-trips");
    expect(decoded.run_immediately, "CommandEnvelope: run_immediately round-trips");
    expect(decoded.command_discriminator == ADCCommand::MSG_ID,
           "CommandEnvelope: discriminator round-trips");
    expect(decoded.command.adc.channel == 2, "CommandEnvelope: adc.channel round-trips");
    expect(decoded.command.adc.sample_rate == 1000, "CommandEnvelope: adc.sample_rate round-trips");
    expect(decoded.command.adc.enable, "CommandEnvelope: adc.enable round-trips");
  }

  // --- RawDataEnvelope with field_order discriminator ---
  RawSamplePayload sample{};
  sample.channel = 7;
  sample.value = 2.718f;
  sample.flags = 0xBE;
  RawDataEnvelope raw_env = RawDataEnvelope::wrap(3, 999000, sample);

  // field_order discriminator: sample is 1st field -> discriminator == 1
  expect(static_cast<uint8_t>(raw_env.payload_discriminator) == 1,
         "RawDataEnvelope: field_order discriminator == 1 for first variant");

  std::vector<uint8_t> raw_buffer(2048);
  BufferWriter<ProfileBulkConfig> raw_writer(raw_buffer.data(), raw_buffer.size());
  size_t raw_written = raw_writer.write(raw_env);
  expect(raw_written > 0, "RawDataEnvelope: write returned > 0");

  AccumulatingReader<ProfileBulkConfig, 4096, decltype(&get_message_info)> raw_reader(get_message_info);
  raw_reader.add_data(raw_buffer.data(), raw_written);
  auto raw_frame = raw_reader.next();
  expect(raw_frame.valid, "RawDataEnvelope: frame valid");
  if (raw_frame.valid) {
    RawDataEnvelope raw_decoded;
    size_t n = raw_decoded.deserialize(raw_frame);
    expect(n > 0, "RawDataEnvelope: deserialize succeeded");
    expect(raw_decoded.priority == 3, "RawDataEnvelope: priority round-trips");
    expect(raw_decoded.timestamp_us == 999000, "RawDataEnvelope: timestamp_us round-trips");
    expect(static_cast<uint8_t>(raw_decoded.payload_discriminator) == 1,
           "RawDataEnvelope: discriminator round-trips == 1");
    expect(raw_decoded.payload.sample.channel == 7, "RawDataEnvelope: sample.channel round-trips");
    expect(std::abs(raw_decoded.payload.sample.value - 2.718f) < 1e-4f,
           "RawDataEnvelope: sample.value round-trips");
    expect(raw_decoded.payload.sample.flags == 0xBE, "RawDataEnvelope: sample.flags round-trips");
  }

  printf("\nSummary: %d passed, %d failed\n", g_passed, g_failed);
  return g_failed > 0 ? 1 : 0;
}
