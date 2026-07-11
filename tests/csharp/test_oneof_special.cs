/**
 * Test for oneof special cases: discriminator=none and multi-oneof messages.
 *
 * Mirrors tests/rust/src/main.rs::run_oneof_special_tests(). C# does not
 * auto-decode a discriminator=none oneof on Deserialize() (the app must
 * already know the active variant), so the payload is recovered by slicing
 * the known union byte range out of the serialized envelope and decoding it
 * directly. This works for NoneDiscriminatorMessage and
 * MultiOneofMessage.FirstPayload (both fixed-size union members);
 * MultiOneofMessage.SecondPayload pairs discriminator=none with
 * variable-length payload types (Message/VariableSingleArray) and is not
 * covered here.
 */

using System;
using StructFrame.SerializationTest;

public class TestOneofSpecial
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

  public static int Main(string[] args)
  {
    Console.WriteLine("=== C# oneof special tests ===");

    // --- NoneDiscriminatorMessage: no discriminator field, data bytes preserved ---
    var basic = new BasicTypesMessage { SmallInt = -42, MediumUint = 5000 };
    var msg1 = new NoneDiscriminatorMessage { Header = 0xAB, Basic = basic };

    byte[] raw1 = msg1.Serialize();
    var dec1 = NoneDiscriminatorMessage.Deserialize(raw1);
    Expect(dec1.Header == 0xAB, "NoneDiscriminator: header round-trips");
    // Without a discriminator the receiver must know which variant to use --
    // slice the known union byte range and decode it directly.
    var basic1 = BasicTypesMessage.Deserialize(raw1.AsSpan(1, BasicTypesMessage.MaxSize));
    Expect(basic1.SmallInt == -42, "NoneDiscriminator: basic.SmallInt round-trips");
    Expect(basic1.MediumUint == 5000, "NoneDiscriminator: basic.MediumUint round-trips");

    // --- MultiOneofMessage: msgid-discriminated FirstPayload round-trips normally ---
    var basic2 = new BasicTypesMessage { SmallInt = 99 };
    var msg2 = new MultiOneofMessage
    {
      Selector = 7,
      FirstPayloadDiscriminator = BasicTypesMessage.MsgId,
      Basic = basic2,
    };

    byte[] raw2 = msg2.Serialize();
    var dec2 = MultiOneofMessage.Deserialize(raw2);
    Expect(dec2.Selector == 7, "MultiOneof: selector round-trips");
    Expect(dec2.FirstPayloadDiscriminator == BasicTypesMessage.MsgId,
           "MultiOneof: FirstPayload discriminator is BasicTypesMessage MsgId");
    Expect(dec2.Basic != null, "MultiOneof: FirstPayload auto-decoded");
    if (dec2.Basic != null)
    {
      Expect(dec2.Basic.SmallInt == 99, "MultiOneof: basic.SmallInt round-trips");
    }

    Console.WriteLine();
    Console.WriteLine($"Summary: {_passed} passed, {_failed} failed");

    return _failed > 0 ? 1 : 0;
  }
}
