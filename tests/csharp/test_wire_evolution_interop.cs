/**
 * Cross-version wire-evolution *interop* tests for the C# SDK.
 *
 * Unlike the single-schema round-trip test, this runner uses two SEPARATELY
 * generated schema versions of the same messages:
 *
 *   - StructFrame.WireEvolutionV1  -- base fields only (older, ext-unaware)
 *   - StructFrame.WireEvolutionV2  -- base fields + extension fields
 *
 * Each side has its own message classes, magic constants and
 * MessageDefinitions.GetMessageInfo lookup, exactly as two independently-built
 * code-bases would.  The tests exercise genuine newer<->older interop over the
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
 */

using System;
using StructFrame;
using StructFrame.Profiles;
using StructFrame.Framing;
using V1 = StructFrame.WireEvolutionV1;
using V2 = StructFrame.WireEvolutionV2;

public class TestWireEvolutionInterop
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static void Check(bool condition, string testName)
    {
        if (condition)
        {
            Console.WriteLine($"  [PASS] {testName}");
            _passed++;
        }
        else
        {
            Console.Error.WriteLine($"  [FAIL] {testName}");
            _failed++;
        }
    }

    // Copy a (possibly shorter, base-only) payload into a MaxSize zero buffer so
    // a newer receiver can zero-fill the missing extension bytes before decoding.
    private static byte[] PadPayload(FrameMsgInfo info, int maxSize)
    {
        var padded = new byte[maxSize];
        var span = info.GetPayloadSpan();
        int n = Math.Min(span.Length, maxSize);
        span.Slice(0, n).CopyTo(padded.AsSpan());
        return padded;
    }

    // -------------------------------------------------------------------------
    // Scenario 1: newer sender -> older receiver over length-bearing profiles
    // -------------------------------------------------------------------------
    private static void Scenario1()
    {
        var encoders = new (Func<byte[], int, V2.BaseExtensionMessage, int> Encode,
                            Func<byte[], int, int, FrameMsgInfo> Parse, string Name)[]
        {
            (((b, o, m) => new ProfileStandardEncoder().Encode(b, o, m)),
             ((b, o, n) => new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo).Parse(b, o, n)),
             "standard"),
            (((b, o, m) => new ProfileBulkEncoder().Encode(b, o, m)),
             ((b, o, n) => new ProfileBulkParser(V1.MessageDefinitions.GetMessageInfo).Parse(b, o, n)),
             "bulk"),
            (((b, o, m) => new ProfileNetworkEncoder().Encode(b, o, m)),
             ((b, o, n) => new ProfileNetworkParser(V1.MessageDefinitions.GetMessageInfo).Parse(b, o, n)),
             "network"),
        };

        foreach (var e in encoders)
        {
            var orig = new V2.BaseExtensionMessage { Header = 0xBEEF, Seq = 42, CrcSeed = 0xDEADC0DE };
            byte[] buffer = new byte[256];
            int encoded = e.Encode(buffer, 0, orig);
            var info = e.Parse(buffer, 0, encoded);
            Check(info.Valid, $"[S1/{e.Name}] v2->v1 frame validates CRC (magic from base)");
            if (info.Valid && info.MsgData != null)
            {
                var d = V1.BaseExtensionMessage.Deserialize(info);
                Check(d.Header == 0xBEEF && d.Seq == 42,
                      $"[S1/{e.Name}] v1 decodes base; trailing ext bytes ignored");
            }
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 2: older sender -> newer receiver (zero-fill extensions)
    // -------------------------------------------------------------------------
    private static void Scenario2()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V2.MessageDefinitions.GetMessageInfo);

        var orig = new V1.BaseExtensionMessage { Header = 0x1234, Seq = 7 };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S2] v1->v2 base-only frame validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V2.BaseExtensionMessage.Deserialize(PadPayload(info, V2.BaseExtensionMessage.MaxSize));
            Check(d.Header == 0x1234 && d.Seq == 7, "[S2] v2 decodes base fields correctly");
            Check(d.CrcSeed == 0, "[S2] v2 extension field zero-filled to default");
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 3: same-version sanity (v2 -> v2 with extension variant)
    // -------------------------------------------------------------------------
    private static void Scenario3()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V2.MessageDefinitions.GetMessageInfo);

        var orig = new V2.OneOfExtensionMessage
        {
            DeviceId = 2,
            CommandDiscriminator = V2.OneOfExtensionMessageCommandField.CmdC,
            CmdC = new V2.ExtCommandC { ValueC = 3.14f, ModeC = 2 },
        };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S3] v2->v2 (ext variant) frame validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V2.OneOfExtensionMessage.Deserialize(info);
            Check(d.CommandDiscriminator == V2.OneOfExtensionMessageCommandField.CmdC
                  && d.CmdC != null && Math.Abs(d.CmdC.ValueC - 3.14f) < 0.001f,
                  "[S3] v2 round-trips the extension variant");
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
    // -------------------------------------------------------------------------
    private static void Scenario4()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo);

        var orig = new V2.OneOfExtensionMessage
        {
            DeviceId = 9,
            CommandDiscriminator = V2.OneOfExtensionMessageCommandField.CmdD,
            CmdD = new V2.ExtCommandD { ValueD = 2.718281828 },
        };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S4] v2 ext-variant -> v1 frame validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V1.OneOfExtensionMessage.Deserialize(info);
            Check(d.DeviceId == 9, "[S4] v1 still decodes the base header field");
            // v1 knows nothing about discriminator 4; it must preserve the raw
            // value without corrupting the base field.
            Check((int)d.CommandDiscriminator == 4,
                  "[S4] v1 preserves unknown ext discriminator without corruption");
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 5: older base oneof variant -> newer receiver decodes correctly
    // -------------------------------------------------------------------------
    private static void Scenario5()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V2.MessageDefinitions.GetMessageInfo);

        var orig = new V1.OneOfExtensionMessage
        {
            DeviceId = 5,
            CommandDiscriminator = V1.OneOfExtensionMessageCommandField.CmdB,
            CmdB = new V1.BaseCommandB { ValueB = -1234, ActiveB = true },
        };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S5] v1 base-variant -> v2 frame validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V2.OneOfExtensionMessage.Deserialize(PadPayload(info, V2.OneOfExtensionMessage.MaxSize));
            Check(d.CommandDiscriminator == V2.OneOfExtensionMessageCommandField.CmdB
                  && d.CmdB != null && d.CmdB.ValueB == -1234,
                  "[S5] v2 decodes the older base oneof variant correctly");
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 6: multi-oneof, ext only in the second union
    // -------------------------------------------------------------------------
    private static void Scenario6()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo);

        var orig = new V2.MultiOneOfExtensionMessage
        {
            Priority = 3,
            BaseUnionDiscriminator = V2.MultiOneOfExtensionMessageBaseUnionField.FirstA,
            FirstA = new V2.BaseCommandA { ValueA = 100, FlagsA = 5 },
            ExtUnionDiscriminator = V2.MultiOneOfExtensionMessageExtUnionField.SecondExt,
            SecondExt = new V2.ExtCommandC { ValueC = 2.71f, ModeC = 1 },
        };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V1.MultiOneOfExtensionMessage.Deserialize(info);
            Check(d.Priority == 3
                  && d.BaseUnionDiscriminator == V1.MultiOneOfExtensionMessageBaseUnionField.FirstA
                  && d.FirstA != null && d.FirstA.ValueA == 100,
                  "[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second");
        }
    }

    // -------------------------------------------------------------------------
    // Scenario 7: corrupted extension bytes invalidate the full CRC
    // -------------------------------------------------------------------------
    private static void Scenario7()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo);

        var orig = new V2.BaseExtensionMessage { Header = 0xBEEF, Seq = 42, CrcSeed = 0xDEADC0DE };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);

        int headerSize = 2 + 2 + 2; // start bytes + length(2) + msgid(2)
        int extOffset = headerSize + V2.BaseExtensionMessage.BaseSize;
        buffer[extOffset] ^= 0xFF;

        var info = parser.Parse(buffer, 0, encoded);
        Check(!info.Valid, "[S7] corrupted extension byte invalidates full CRC");
    }

    public static int Main(string[] args)
    {
        Console.WriteLine("=== C# Cross-Version Wire-Evolution Interop Tests ===\n");

        Console.WriteLine("Scenario 1: newer sender -> older receiver (length-bearing)");
        Scenario1();
        Console.WriteLine("\nScenario 2: older sender -> newer receiver (zero-fill)");
        Scenario2();
        Console.WriteLine("\nScenario 3: same-version sanity (v2 -> v2)");
        Scenario3();
        Console.WriteLine("\nScenario 4: newer ext oneof variant -> older receiver");
        Scenario4();
        Console.WriteLine("\nScenario 5: older base oneof variant -> newer receiver");
        Scenario5();
        Console.WriteLine("\nScenario 6: multi-oneof (ext only in 2nd union)");
        Scenario6();
        Console.WriteLine("\nScenario 7: corrupted extension bytes invalidate CRC");
        Scenario7();

        Console.WriteLine($"\nResults: {_passed} passed, {_failed} failed");
        return _failed == 0 ? 0 : 1;
    }
}
