/**
 * Test for oneof special cases: discriminator=none and multi-oneof messages,
 * plus the rule that the discriminator alone selects the serialized payload.
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
 *
 * The second half is a regression guard specific to C#: union members are
 * separate nullable properties here (unlike the C/C++/Rust union or the
 * TypeScript raw payload buffer), and more than one of them can be non-null
 * at once -- a variant whose type carries schema defaults is constructed
 * eagerly, and a reused message object keeps whatever was assigned before.
 * Every serialization path must therefore switch on the discriminator rather
 * than write the first non-null property.
 */

using System;
using System.Buffers.Binary;
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

    // --- DefaultedOneofEnvelope: the discriminator selects the payload ---
    // DefaultedVariantA carries schema defaults, so CommandA is constructed
    // eagerly and stays non-null while CommandB is the active variant. Writing
    // "the first non-null union member" would put CommandA's default bytes on
    // the wire underneath CommandB's discriminator.
    var envB = DefaultedOneofEnvelope.Wrap(new DefaultedVariantB { Payload = 0xDEADBEEF }, 0x5A);
    Expect(envB.CommandA != null, "Defaulted: CommandA is eagerly constructed (non-null)");

    byte[] raw3 = envB.Serialize();
    byte[] payloadB = new byte[] { 0xEF, 0xBE, 0xAD, 0xDE };
    Expect(raw3.Length == DefaultedOneofEnvelope.MaxSize, "Defaulted: serializes to MaxSize");
    Expect(raw3[0] == 0x5A, "Defaulted: header byte written");
    Expect(raw3[1] == (byte)DefaultedOneofEnvelopeCommandField.CommandB,
           "Defaulted: discriminator byte is CommandB");
    Expect(raw3.AsSpan(2, 4).SequenceEqual(payloadB),
           "Defaulted: payload bytes are CommandB's, not CommandA's defaults");

    var dec3 = DefaultedOneofEnvelope.Deserialize(raw3);
    Expect(dec3.Header == 0x5A, "Defaulted: header round-trips");
    Expect(dec3.CommandDiscriminator == DefaultedOneofEnvelopeCommandField.CommandB,
           "Defaulted: discriminator round-trips");
    Expect(dec3.CommandB != null && dec3.CommandB.Payload == 0xDEADBEEF,
           "Defaulted: CommandB payload round-trips");

    // SerializeTo writes into a caller-owned buffer: the previous variant's
    // bytes must not survive underneath the new discriminator.
    byte[] reused = new byte[DefaultedOneofEnvelope.MaxSize];
    DefaultedOneofEnvelope.Wrap(new DefaultedVariantA { Code = 0x11, Value = 0x2233 }, 0x01)
                          .SerializeTo(reused, 0);
    envB.SerializeTo(reused, 0);
    Expect(reused.AsSpan(2, 4).SequenceEqual(payloadB),
           "Defaulted: SerializeTo into a reused buffer writes only CommandB");

    // --- Same rule with a msgid discriminator and a stale union member ---
    var multi = new MultiOneofMessage
    {
      Selector = 3,
      FirstPayloadDiscriminator = SerializationTestMessage.MsgId,
      Basic = new BasicTypesMessage { SmallInt = -7 },  // stale: declared first, not active
      TestMsg = new SerializationTestMessage { MagicNumber = 0xCAFEBABE },
    };
    var dec4 = MultiOneofMessage.Deserialize(multi.Serialize());
    Expect(dec4.TestMsg != null && dec4.TestMsg.MagicNumber == 0xCAFEBABE,
           "MultiOneof: msgid discriminator selects TestMsg over the stale Basic");

    // --- Variable message, fixed (trimmed) union: same rule ---
    var varEnv = new VariableEnvelopeMessage
    {
      Priority = 5,
      PayloadDiscriminator = VariableEnvelopeMessagePayloadField.PayloadB,
      PayloadA = new VarEnvPayloadA { Code = 0x99, Value = 0x8877 },  // stale
      PayloadB = new VarEnvPayloadB { Flags = 0x01020304, Ratio = 0.5f },
    };
    byte[] raw5 = varEnv.Serialize();
    Expect(raw5[1] == (byte)VariableEnvelopeMessagePayloadField.PayloadB,
           "VariableEnvelope: discriminator byte is PayloadB");
    Expect(BinaryPrimitives.ReadUInt32LittleEndian(raw5.AsSpan(2, 4)) == 0x01020304,
           "VariableEnvelope: trimmed union holds PayloadB, not the stale PayloadA");
    var dec5 = VariableEnvelopeMessage.Deserialize(raw5);
    Expect(dec5.PayloadB != null && dec5.PayloadB.Flags == 0x01020304,
           "VariableEnvelope: PayloadB round-trips");

    // --- Variable-length union (length-prefixed): same rule ---
    var varOneof = new VariableOneofMessage
    {
      Header = 0x42,
      DataDiscriminator = VariableOneofMessageDataField.LargePayload,
      SmallPayload = new VarEnvPayloadA { Code = 0x99, Value = 0x8877 },  // stale
      LargePayload = new VarEnvPayloadB { Flags = 0x0A0B0C0D, Ratio = 1.5f },
    };
    byte[] raw6 = varOneof.Serialize();
    Expect(raw6[1] == (byte)VariableOneofMessageDataField.LargePayload,
           "VariableOneof: discriminator byte is LargePayload");
    Expect(BinaryPrimitives.ReadUInt16LittleEndian(raw6.AsSpan(2, 2)) == VarEnvPayloadB.MaxSize,
           "VariableOneof: length prefix is LargePayload's size");
    Expect(BinaryPrimitives.ReadUInt32LittleEndian(raw6.AsSpan(4, 4)) == 0x0A0B0C0D,
           "VariableOneof: payload bytes are LargePayload's, not the stale SmallPayload's");

    // A LargePayload frame is exactly MaxSize bytes long (MaxSize counts the
    // 2-byte union length prefix). Deserialize() must not mistake it for the
    // MAX_SIZE layout, which has no prefix: a message carrying a variable
    // oneof is always read with the variable decoder, as in C/C++/Rust.
    Expect(raw6.Length == VariableOneofMessage.MaxSize,
           "VariableOneof: large variant frame is exactly MaxSize bytes");
    var dec6 = VariableOneofMessage.Deserialize(raw6);
    Expect(dec6.LargePayload != null && dec6.LargePayload.Flags == 0x0A0B0C0D,
           "VariableOneof: LargePayload round-trips at the ambiguous length");

    var varOneofSmall = new VariableOneofMessage
    {
      Header = 0x43,
      DataDiscriminator = VariableOneofMessageDataField.SmallPayload,
      SmallPayload = new VarEnvPayloadA { Code = 0x12, Value = 0x3456 },
      LargePayload = new VarEnvPayloadB { Flags = 0xFFFFFFFF, Ratio = 9.5f },  // stale
    };
    byte[] raw7 = varOneofSmall.Serialize();
    Expect(raw7.Length == 7, "VariableOneof: small variant writes only its own bytes");
    var dec7 = VariableOneofMessage.Deserialize(raw7);
    Expect(dec7.SmallPayload != null && dec7.SmallPayload.Code == 0x12
           && dec7.SmallPayload.Value == 0x3456,
           "VariableOneof: SmallPayload round-trips");

    Console.WriteLine();
    Console.WriteLine($"Summary: {_passed} passed, {_failed} failed");

    return _failed > 0 ? 1 : 0;
  }
}
