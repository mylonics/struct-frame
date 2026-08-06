/**
 * Regression tests for generated-codec robustness (C#).
 *
 * Each test here pins a defect found while auditing the generated C# output
 * for messages whose max_size exceeds 255, plus the SDK's handling of faults
 * raised during dispatch:
 *
 *   R1. The generated Send<Msg>(fields...) convenience method must not
 *       truncate a >255 count to a byte (300 elements became 44, 4096 became 0).
 *   R2. Serializing with a caller-supplied backing array longer than max_size
 *       must copy at most max_size bytes, not max_size + 1.
 *   R3. A variable payload truncated mid-string must fail with the same typed
 *       InvalidDataException the array path already raised, not an
 *       ArgumentOutOfRangeException escaping from Span.Slice.
 *   R4. Serializing an object whose Length disagrees with its backing array
 *       must produce a short/padded message rather than throwing.
 *   R5. A subscriber that throws must reach ErrorOccurred even with Debug off,
 *       and must not stop the remaining subscribers.
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Sdk;
using StructFrame.ExtendedTest;
using StructFrame.SerializationTest;
using ExtendedClient = StructFrame.ExtendedTest.Sdk.Client;

static class TestCodecRobustness
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static void Assert(string name, bool condition)
    {
        bool ok = condition;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")} {name}");
        if (ok) _passed++; else _failed++;
    }

    // -------------------------------------------------------------------------
    // R1. Counts above 255 survive the generated convenience setter.
    //
    // BigTelemetryCount/BigLabelLength are ushort (max_size=300). The SDK
    // interface used to cast the clamped length to byte, so 300 wrapped to 44
    // and a 4096-byte payload wrapped to 0 — a silently truncated send.
    // -------------------------------------------------------------------------
    static async Task TestLargeCountNotTruncated()
    {
        byte[] payload = new byte[300];
        for (int i = 0; i < payload.Length; i++) payload[i] = (byte)(i & 0xFF);

        var transport = new MockTransport();
        // ExtendedTest carries msgids above 255, so it needs a pkg_id-bearing profile.
        using var sdk = new StructFrameSdk(new StructFrameSdkConfig(
            transport,
            StructFrame.ExtendedTest.MessageDefinitions.GetMessageInfo,
            StructFrame.Profiles.Profiles.Bulk));
        var client = new ExtendedClient(sdk);

        // Exercise the generated convenience overload, which is where the
        // clamped length was cast to byte.
        await client.SendExtendedVariableLargeArray(7u, payload, payload, (ushort)9);

        Assert("R1: convenience send emitted a frame", transport.SentData.Count == 1);
        if (transport.SentData.Count != 1) return;

        var parser = new BufferParser(StructFrame.Profiles.Profiles.Bulk,
                                      StructFrame.ExtendedTest.MessageDefinitions.GetMessageInfo);
        var frame = parser.Parse(transport.SentData[0], 0, transport.SentData[0].Length);
        Assert("R1: emitted frame parses as valid", frame.Valid);

        var decoded = ExtendedVariableLargeArray.Deserialize(frame);
        Assert("R1: 300-element count is not truncated to a byte", decoded.BigTelemetryCount == 300);
        Assert("R1: 300-char length is not truncated to a byte", decoded.BigLabelLength == 300);
        Assert("R1: payload round-trips byte-for-byte",
               decoded.BigTelemetryData.AsSpan(0, 300).SequenceEqual(payload));
    }

    // -------------------------------------------------------------------------
    // R2. An oversized backing array must not push one byte past the field.
    //
    // The copy cap was computed as size - 1 (one count byte) even where the
    // count prefix is two bytes, so a caller-supplied array longer than
    // max_size copied max_size + 1 bytes. ExtendedTrailingLargeArray ends with
    // the bounded array on purpose: anywhere else the stray byte lands on the
    // next field and is immediately overwritten by that field's own write,
    // which hides the defect.
    // -------------------------------------------------------------------------
    static void TestOversizedBackingArrayDoesNotOverrun()
    {
        var msg = new ExtendedTrailingLargeArray
        {
            Id = 0x11223344,
            PayloadCount = 300,
            // Deliberately longer than max_size: the SDK convenience method
            // assigns the caller's array as-is, so this is reachable in practice.
            PayloadData = Enumerable.Repeat((byte)0xAB, 512).ToArray(),
        };

        byte[] wire;
        try
        {
            wire = msg.Serialize();
        }
        catch (Exception ex)
        {
            Assert($"R2: Serialize does not overrun on oversized backing array (threw {ex.GetType().Name})", false);
            return;
        }

        Assert("R2: emitted frame is exactly MaxSize", wire.Length == ExtendedTrailingLargeArray.MaxSize);

        var decoded = ExtendedTrailingLargeArray.Deserialize(wire);
        Assert("R2: leading field is intact", decoded.Id == 0x11223344);
        Assert("R2: count is intact", decoded.PayloadCount == 300);
        Assert("R2: payload is copied at max_size, not max_size + 1",
               decoded.PayloadData.AsSpan(0, 300).ToArray().All(b => b == 0xAB));

        // Same copy path, but writing into a caller-owned buffer at an offset:
        // a one-byte overrun here corrupts whatever the caller placed next.
        byte[] host = new byte[ExtendedTrailingLargeArray.MaxSize + 4];
        const byte sentinel = 0x5A;
        for (int i = 0; i < host.Length; i++) host[i] = sentinel;
        msg.SerializeTo(host, 0);
        Assert("R2: byte after the message is untouched in a caller buffer",
               host[ExtendedTrailingLargeArray.MaxSize] == sentinel);
    }

    // -------------------------------------------------------------------------
    // R3. Truncated variable payloads fail with the typed error.
    //
    // The array branch already bounds-checked; the variable-string and
    // fixed-field branches did not, so Span.Slice threw
    // ArgumentOutOfRangeException straight through the SDK's catch.
    // -------------------------------------------------------------------------
    static void TestTruncatedVariablePayloadIsRejected()
    {
        var msg = new ExtendedVariableLargeArray
        {
            Id = 1,
            BigTelemetryCount = 8,
            BigTelemetryData = new byte[300],
            BigLabelLength = 200,
            BigLabelData = new byte[300],
            Trailer = 0x1234,
        };
        byte[] full = msg.Serialize();

        // Cut inside big_label's payload, and again inside the trailing uint16.
        foreach (var (cut, label) in new[]
                 {
                     (full.Length - 150, "mid-string"),
                     (full.Length - 1, "mid-fixed-field"),
                 })
        {
            byte[] truncated = full.Take(cut).ToArray();
            // Length must differ from MaxSize or Deserialize takes the fixed path.
            if (truncated.Length == ExtendedVariableLargeArray.MaxSize) continue;

            string outcome;
            try
            {
                ExtendedVariableLargeArray.Deserialize(truncated);
                outcome = "no exception";
            }
            catch (System.IO.InvalidDataException)
            {
                outcome = "InvalidDataException";
            }
            catch (Exception ex)
            {
                outcome = ex.GetType().Name;
            }

            Assert($"R3: truncated {label} payload raises InvalidDataException (got {outcome})",
                   outcome == "InvalidDataException");
        }
    }

    // -------------------------------------------------------------------------
    // R4. Inconsistent Length/Data serializes short instead of throwing.
    // -------------------------------------------------------------------------
    static void TestInconsistentLengthDoesNotThrow()
    {
        var msg = new ExtendedVariableLargeArray
        {
            Id = 2,
            BigTelemetryCount = 4,
            BigTelemetryData = new byte[] { 1, 2, 3, 4 },
            // Claims 32 bytes but only carries 2.
            BigLabelLength = 32,
            BigLabelData = new byte[] { (byte)'h', (byte)'i' },
            Trailer = 77,
        };

        try
        {
            byte[] wire = msg.Serialize();
            var decoded = ExtendedVariableLargeArray.Deserialize(wire);
            Assert("R4: inconsistent length serializes without throwing", true);
            Assert("R4: declared length is preserved on the wire", decoded.BigLabelLength == 32);
            Assert("R4: supplied bytes survive, remainder is zero-filled",
                   decoded.BigLabelData[0] == (byte)'h' && decoded.BigLabelData[1] == (byte)'i'
                   && decoded.BigLabelData[2] == 0);
            Assert("R4: following field is intact", decoded.Trailer == 77);
        }
        catch (Exception ex)
        {
            Assert($"R4: inconsistent length serializes without throwing (threw {ex.GetType().Name})", false);
        }
    }

    // -------------------------------------------------------------------------
    // R5. Handler faults reach ErrorOccurred with Debug off.
    // -------------------------------------------------------------------------
    static void TestHandlerExceptionSurfaces()
    {
        var transport = new MockTransport();
        // Debug defaults to false — the whole point is that this must not be
        // the only way to learn that a handler failed.
        using var sdk = new StructFrameSdk(new StructFrameSdkConfig(
            transport,
            StructFrame.SerializationTest.MessageDefinitions.GetMessageInfo,
            StructFrame.Profiles.Profiles.Standard));

        var errors = new List<Exception>();
        sdk.ErrorOccurred += (_, ex) => errors.Add(ex);

        bool secondHandlerRan = false;
        sdk.Subscribe<BasicTypesMessage>(_ => throw new InvalidOperationException("boom"));
        sdk.Subscribe<BasicTypesMessage>(_ => secondHandlerRan = true);

        var encoder = new FrameEncoder(StructFrame.Profiles.Profiles.Standard);
        byte[] buf = new byte[512];
        int len = encoder.Encode(buf, 0, new BasicTypesMessage { RegularInt = 5, Flag = true });
        transport.InjectData(buf.Take(len).ToArray());

        Assert("R5: handler exception reaches ErrorOccurred with Debug off", errors.Count == 1);
        Assert("R5: reported error names the message ID",
               errors.Count == 1 && errors[0].Message.Contains(BasicTypesMessage.MsgId.ToString()));
        Assert("R5: original exception is preserved as InnerException",
               errors.Count == 1 && errors[0].InnerException is InvalidOperationException);
        Assert("R5: a throwing handler does not starve the next subscriber", secondHandlerRan);
    }

    // -------------------------------------------------------------------------
    // Entry point
    // -------------------------------------------------------------------------
    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("CODEC ROBUSTNESS TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestLargeCountNotTruncated().GetAwaiter().GetResult();
        TestOversizedBackingArrayDoesNotOverrun();
        TestTruncatedVariablePayloadIsRejected();
        TestInconsistentLengthDoesNotThrow();
        TestHandlerExceptionSurfaces();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}
