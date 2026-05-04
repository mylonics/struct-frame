/**
 * Test for envelope SDK interface with field_order discriminator.
 *
 * Regression test for the enum naming bug in SdkInterface.cs where the
 * discriminator enum was referenced without the package prefix (e.g.
 * "RawDataEnvelopePayloadField") instead of the correct full name
 * (e.g. "RawDataEnvelopePayloadField"), causing CS0266
 * implicit conversion errors when building the SDK interface.
 *
 * This test verifies:
 * 1. The discriminator enum is accessible with the correct package-prefixed name.
 * 2. Enum values follow the field_order (1-based) convention.
 * 3. RawDataEnvelope can be round-trip serialized with each payload variant.
 * 4. The discriminator field is correctly set/read after deserialization.
 */

using System;
using StructFrame.EnvelopeTest;

public class TestEnvelopeSdk
{
  private static int _passed = 0;
  private static int _failed = 0;

  private static void Expect(bool condition, string testName)
  {
    if (condition)
    {
      Console.WriteLine($"  PASS  {testName}");
      _passed++;
    }
    else
    {
      Console.Error.WriteLine($"  FAIL  {testName}");
      _failed++;
    }
  }

  /**
   * Verify discriminator enum values follow field_order (1-based).
   * Before the fix this file would not compile due to the wrong enum type name
   * being referenced in SdkInterface.cs.
   */
  private static void TestDiscriminatorEnumValues()
  {
    // RawDataEnvelopePayloadField is the correct full name.
    // If SdkInterface.cs used the wrong name, the generated library would
    // fail to build and this test file would never reach execution.
    Expect((byte)RawDataEnvelopePayloadField.None == 0,
           "Discriminator None == 0");
    Expect((byte)RawDataEnvelopePayloadField.Sample == 1,
           "Discriminator Sample == 1 (first field in oneof)");
    Expect((byte)RawDataEnvelopePayloadField.Config == 2,
           "Discriminator Config == 2 (second field in oneof)");
  }

  /**
   * Round-trip test: serialize a RawDataEnvelope with a RawSamplePayload,
   * deserialize it, and confirm the discriminator and payload fields survive.
   */
  private static void TestRoundTripSamplePayload()
  {
    var sample = new RawSamplePayload
    {
      Channel = 3,
      Value = 1.23f,
      Flags = 0xAB
    };

    var envelope = new RawDataEnvelope
    {
      Priority = 5,
      TimestampUs = 1000000,
      PayloadDiscriminator = RawDataEnvelopePayloadField.Sample,
      Sample = sample
    };

    byte[] bytes = envelope.Serialize();
    var decoded = RawDataEnvelope.Deserialize(bytes);

    Expect(decoded.Priority == 5, "RoundTrip Sample: Priority");
    Expect(decoded.TimestampUs == 1000000, "RoundTrip Sample: TimestampUs");
    Expect(decoded.PayloadDiscriminator == RawDataEnvelopePayloadField.Sample,
           "RoundTrip Sample: Discriminator == Sample");
    Expect(decoded.Sample != null, "RoundTrip Sample: Sample field not null");
    if (decoded.Sample != null)
    {
      Expect(decoded.Sample.Channel == 3, "RoundTrip Sample: Channel");
      Expect(Math.Abs(decoded.Sample.Value - 1.23f) < 1e-5f, "RoundTrip Sample: Value");
      Expect(decoded.Sample.Flags == 0xAB, "RoundTrip Sample: Flags");
    }
  }

  /**
   * Round-trip test: serialize a RawDataEnvelope with a RawConfigPayload.
   */
  private static void TestRoundTripConfigPayload()
  {
    var config = new RawConfigPayload
    {
      SettingId = 7,
      SettingValue = 4096
    };

    var envelope = new RawDataEnvelope
    {
      Priority = 1,
      TimestampUs = 500,
      PayloadDiscriminator = RawDataEnvelopePayloadField.Config,
      Config = config
    };

    byte[] bytes = envelope.Serialize();
    var decoded = RawDataEnvelope.Deserialize(bytes);

    Expect(decoded.Priority == 1, "RoundTrip Config: Priority");
    Expect(decoded.TimestampUs == 500, "RoundTrip Config: TimestampUs");
    Expect(decoded.PayloadDiscriminator == RawDataEnvelopePayloadField.Config,
           "RoundTrip Config: Discriminator == Config");
    Expect(decoded.Config != null, "RoundTrip Config: Config field not null");
    if (decoded.Config != null)
    {
      Expect(decoded.Config.SettingId == 7, "RoundTrip Config: SettingId");
      Expect(decoded.Config.SettingValue == 4096, "RoundTrip Config: SettingValue");
    }
  }

  public static int Main(string[] args)
  {
    Console.WriteLine("=== EnvelopeSdk field_order discriminator tests ===");

    TestDiscriminatorEnumValues();
    TestRoundTripSamplePayload();
    TestRoundTripConfigPayload();

    Console.WriteLine();
    Console.WriteLine($"Summary: {_passed} passed, {_failed} failed");

    return _failed > 0 ? 1 : 0;
  }
}
