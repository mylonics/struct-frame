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

    // -------------------------------------------------------------------------
    // Scenario 8: truncated payload is rejected
    // -------------------------------------------------------------------------
    private static void Scenario8()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo);

        var orig = new V1.BaseExtensionMessage { Header = 1, Seq = 2 };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        // Drop the last byte — fewer bytes than the length field claims.
        var info = parser.Parse(buffer, 0, encoded - 1);
        Check(!info.Valid, "[S8] truncated payload (fewer bytes than length claims) is rejected");
    }

    // -------------------------------------------------------------------------
    // Scenario 9: length-less profile guard (IPC)
    //
    // On a length-less (IPC) profile both sides must agree on the full fixed
    // size.  An older (base-only, shorter) frame is NOT silently accepted by a
    // newer receiver because the frame size does not match the expected MaxSize.
    // -------------------------------------------------------------------------
    private static void Scenario9()
    {
        // Positive: same-version v2 over IPC validates.
        var ipcEncoder = new ProfileIPCEncoder();
        var ipcParserV2 = new ProfileIPCParser(V2.MessageDefinitions.GetMessageInfo);

        var same = new V2.BaseExtensionMessage { Header = 0xAA, Seq = 5, CrcSeed = 0x99 };
        byte[] buffer = new byte[256];
        int encoded = ipcEncoder.Encode(buffer, 0, same);
        var info = ipcParserV2.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S9] IPC same-version v2 frame validates");

        // Negative: base-only v1 frame (shorter) rejected by newer v2 receiver.
        var older = new V1.BaseExtensionMessage { Header = 0xAA, Seq = 5 };
        byte[] buffer2 = new byte[256];
        int encoded2 = ipcEncoder.Encode(buffer2, 0, older);
        var info2 = ipcParserV2.Parse(buffer2, 0, encoded2);
        Check(!info2.Valid,
              "[S9] IPC base-only older frame is rejected by newer receiver "
              + "(both sides must agree on size)");
    }

    // -------------------------------------------------------------------------
    // Scenario 10: variable base array + trailing extension, both directions
    // -------------------------------------------------------------------------
    private static void Scenario10()
    {
        var encoder = new ProfileStandardEncoder();

        // Newer -> older: v1 locates variable base, ignores trailing ext bytes.
        var parserV1 = new ProfileStandardParser(V1.MessageDefinitions.GetMessageInfo);

        var orig = new V2.VariableExtensionMessage
        {
            NodeId = 7,
            ReadingsCount = 3,
            ReadingsData = new ushort[] { 10, 20, 30 },
            ExtTimestamp = 0x12345678,
        };
        byte[] buffer = new byte[256];
        int encoded = encoder.Encode(buffer, 0, orig);
        var info = parserV1.Parse(buffer, 0, encoded);
        Check(info.Valid, "[S10] v2 variable+ext -> v1 validates CRC");
        if (info.Valid && info.MsgData != null)
        {
            var d = V1.VariableExtensionMessage.Deserialize(info);
            Check(d.NodeId == 7
                  && d.ReadingsCount == 3
                  && d.ReadingsData != null
                  && d.ReadingsData[0] == 10
                  && d.ReadingsData[1] == 20
                  && d.ReadingsData[2] == 30,
                  "[S10] v1 locates/decodes variable base; trailing ext bytes ignored");
        }

        // Older -> newer: v2 zero-fills the trailing extension field.
        var parserV2 = new ProfileStandardParser(V2.MessageDefinitions.GetMessageInfo);

        var orig2 = new V1.VariableExtensionMessage
        {
            NodeId = 9,
            ReadingsCount = 2,
            ReadingsData = new ushort[] { 1, 2 },
        };
        byte[] buffer2 = new byte[256];
        int encoded2 = encoder.Encode(buffer2, 0, orig2);
        var info2 = parserV2.Parse(buffer2, 0, encoded2);
        Check(info2.Valid, "[S10] v1 variable (base-only) -> v2 validates CRC");
        if (info2.Valid && info2.MsgData != null)
        {
            var d2 = V2.VariableExtensionMessage.Deserialize(
                PadPayload(info2, V2.VariableExtensionMessage.MaxSize));
            Check(d2.NodeId == 9
                  && d2.ReadingsCount == 2
                  && d2.ReadingsData != null
                  && d2.ReadingsData[0] == 1
                  && d2.ReadingsData[1] == 2,
                  "[S10] v2 locates variable base after cross-version decode");
            Check(d2.ExtTimestamp == 0, "[S10] v2 zero-fills the trailing extension field");
        }
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
        Console.WriteLine("\nScenario 8: truncated payload rejected");
        Scenario8();
        Console.WriteLine("\nScenario 9: length-less profile guard (IPC)");
        Scenario9();
        Console.WriteLine("\nScenario 10: variable base + trailing extension (both directions)");
        Scenario10();

        Console.WriteLine($"\nResults: {_passed} passed, {_failed} failed");
        return _failed == 0 ? 0 : 1;
    }
}
