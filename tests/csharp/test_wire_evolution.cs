/**
 * Wire-evolution extension field tests for the C# SDK.
 *
 * Verifies that `option extensions_start` and the extension-aware CRC algorithm
 * work correctly end-to-end using the generated C# bindings.
 *
 * Tests:
 *   1. BaseSize < MaxSize for extension messages
 *   2. Encode → decode round-trip for BaseExtensionMessage (Standard profile)
 *   3. Encode → decode round-trip for OneOfExtensionMessage (extension variant)
 *   4. Encode → decode round-trip for MultiOneOfExtensionMessage
 *   5. Legacy-frame compatibility: zero-extension frame still validates CRC
 *   6. Corrupted extension bytes invalidate CRC
 */

using System;
using StructFrame;
using StructFrame.Profiles;
using StructFrame.WireEvolution;
using StructFrame.Framing;

public class TestWireEvolution
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

    // ---------------------------------------------------------------------------
    // Test 1: BaseSize constants
    // ---------------------------------------------------------------------------

    private static void TestBaseSizeConstants()
    {
        Check(BaseExtensionMessage.BaseSize < BaseExtensionMessage.MaxSize,
              "BaseExtensionMessage BaseSize < MaxSize");
        Check(BaseExtensionMessage.BaseSize == 3,
              "BaseExtensionMessage BaseSize == 3 (header+seq)");
        Check(BaseExtensionMessage.MaxSize == 7,
              "BaseExtensionMessage MaxSize == 7 (header+seq+crc_seed)");

        Check(OneOfExtensionMessage.BaseSize < OneOfExtensionMessage.MaxSize,
              "OneOfExtensionMessage BaseSize < MaxSize");

        Check(MultiOneOfExtensionMessage.BaseSize == MultiOneOfExtensionMessage.MaxSize,
              "MultiOneOfExtensionMessage BaseSize == MaxSize (no extensions)");
    }

    // ---------------------------------------------------------------------------
    // Test 2: BaseExtensionMessage encode → decode round-trip (Standard profile)
    // ---------------------------------------------------------------------------

    private static void TestBaseExtensionRoundtrip()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(MessageDefinitions.GetMessageInfo);

        var orig = new BaseExtensionMessage
        {
            Header = 0xBEEF,
            Seq = 42,
            CrcSeed = 0xDEADC0DE,
        };

        byte[] buffer = new byte[512];
        int encoded = encoder.Encode(buffer, 0, orig);
        Check(encoded > 0, "BaseExtensionMessage encode succeeded");

        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "BaseExtensionMessage frame validates CRC");
        Check(info.MsgId == BaseExtensionMessage.MsgId, "BaseExtensionMessage msg_id matches");
        Check(info.MsgLen == BaseExtensionMessage.MaxSize, "BaseExtensionMessage msg_len matches MaxSize");

        if (info.Valid && info.MsgData != null)
        {
            var decoded = BaseExtensionMessage.Deserialize(info);
            Check(decoded.Header == 0xBEEF,       "decoded Header matches");
            Check(decoded.Seq == 42,               "decoded Seq matches");
            Check(decoded.CrcSeed == 0xDEADC0DE,  "decoded CrcSeed matches");
        }
    }

    // ---------------------------------------------------------------------------
    // Test 3: OneOfExtensionMessage with extension variant (CMD_C)
    // ---------------------------------------------------------------------------

    private static void TestOneOfExtensionVariantRoundtrip()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(MessageDefinitions.GetMessageInfo);

        var cmdC = new ExtCommandC
        {
            ValueC = 3.14f,
            ModeC = 2,
        };

        var orig = new OneOfExtensionMessage
        {
            DeviceId = 7,
            CommandDiscriminator = OneOfExtensionMessageCommandField.CmdC,
            CmdC = cmdC,
        };

        byte[] buffer = new byte[512];
        int encoded = encoder.Encode(buffer, 0, orig);
        Check(encoded > 0, "OneOfExtensionMessage (ext variant) encode succeeded");

        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "OneOfExtensionMessage (ext variant) frame validates CRC");

        if (info.Valid && info.MsgData != null)
        {
            var decoded = OneOfExtensionMessage.Deserialize(info);
            Check(decoded.DeviceId == 7, "decoded DeviceId matches");
            Check(decoded.CommandDiscriminator == OneOfExtensionMessageCommandField.CmdC,
                  "decoded command discriminator == CMD_C");
            Check(decoded.CmdC != null, "decoded CmdC is not null");
            if (decoded.CmdC != null)
            {
                Check(Math.Abs(decoded.CmdC.ValueC - 3.14f) < 0.001f, "decoded cmd_c.ValueC matches");
                Check(decoded.CmdC.ModeC == 2, "decoded cmd_c.ModeC matches");
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Test 4: MultiOneOfExtensionMessage with extension variant in second oneof
    // ---------------------------------------------------------------------------

    private static void TestMultiOneOfExtensionRoundtrip()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(MessageDefinitions.GetMessageInfo);

        var extVariant = new ExtCommandC
        {
            ValueC = 2.71f,
            ModeC = 1,
        };

        var orig = new MultiOneOfExtensionMessage
        {
            Priority = 3,
            BaseUnionDiscriminator = MultiOneOfExtensionMessageBaseUnionField.FirstA,
            FirstA = new BaseCommandA { ValueA = 1, FlagsA = 100 },
            ExtUnionDiscriminator = MultiOneOfExtensionMessageExtUnionField.SecondExt,
            SecondExt = extVariant,
        };

        byte[] buffer = new byte[512];
        int encoded = encoder.Encode(buffer, 0, orig);
        Check(encoded > 0, "MultiOneOfExtensionMessage encode succeeded");

        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "MultiOneOfExtensionMessage frame validates CRC");

        if (info.Valid && info.MsgData != null)
        {
            var decoded = MultiOneOfExtensionMessage.Deserialize(info);
            Check(decoded.Priority == 3, "decoded Priority matches");
            Check(decoded.ExtUnionDiscriminator == MultiOneOfExtensionMessageExtUnionField.SecondExt,
                  "decoded ext_union discriminator == SECOND_EXT");
            Check(decoded.SecondExt != null, "decoded SecondExt is not null");
            if (decoded.SecondExt != null)
            {
                Check(Math.Abs(decoded.SecondExt.ValueC - 2.71f) < 0.001f, "decoded second_ext.ValueC matches");
                Check(decoded.SecondExt.ModeC == 1, "decoded second_ext.ModeC matches");
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Test 5: Legacy-frame compatibility (zero extension bytes)
    // ---------------------------------------------------------------------------

    private static void TestLegacyFrameCompatibility()
    {
        var encoder = new ProfileStandardEncoder();
        var parser = new ProfileStandardParser(MessageDefinitions.GetMessageInfo);

        var orig = new BaseExtensionMessage
        {
            Header = 0x1234,
            Seq = 7,
            CrcSeed = 0,
        };

        byte[] buffer = new byte[512];
        int encoded = encoder.Encode(buffer, 0, orig);
        Check(encoded > 0, "legacy (zero extension) frame encodes");

        var info = parser.Parse(buffer, 0, encoded);
        Check(info.Valid, "legacy (zero extension) frame validates CRC");

        if (info.Valid && info.MsgData != null)
        {
            var decoded = BaseExtensionMessage.Deserialize(info);
            Check(decoded.Header == 0x1234, "legacy decoded Header matches");
            Check(decoded.Seq == 7,          "legacy decoded Seq matches");
            Check(decoded.CrcSeed == 0,      "legacy decoded CrcSeed is 0");
        }

        // Verify that corrupting the extension bytes invalidates the CRC
        // Standard profile: header_size = 2 (start) + 2 (length) + 2 (msgid) = 6
        int headerSize = 2 + 2 + 2;
        int extOffset = headerSize + BaseExtensionMessage.BaseSize;
        var corruptedBuffer = new byte[encoded];
        Array.Copy(buffer, corruptedBuffer, encoded);
        corruptedBuffer[extOffset] ^= 0xFF;
        var badInfo = parser.Parse(corruptedBuffer, 0, encoded);
        Check(!badInfo.Valid, "corrupted extension bytes invalidate CRC");
    }

    // ---------------------------------------------------------------------------
    // Entry point
    // ---------------------------------------------------------------------------

    public static int Main(string[] args)
    {
        Console.WriteLine("=== C# Wire-Evolution Extension Field Tests ===\n");

        Console.WriteLine("Test group 1: BaseSize constants");
        TestBaseSizeConstants();
        Console.WriteLine();

        Console.WriteLine("Test group 2: BaseExtensionMessage encode/decode round-trip");
        TestBaseExtensionRoundtrip();
        Console.WriteLine();

        Console.WriteLine("Test group 3: OneOfExtensionMessage (extension variant) round-trip");
        TestOneOfExtensionVariantRoundtrip();
        Console.WriteLine();

        Console.WriteLine("Test group 4: MultiOneOfExtensionMessage round-trip");
        TestMultiOneOfExtensionRoundtrip();
        Console.WriteLine();

        Console.WriteLine("Test group 5: Legacy-frame compatibility");
        TestLegacyFrameCompatibility();
        Console.WriteLine();

        Console.WriteLine($"Results: {_passed} passed, {_failed} failed");
        return _failed == 0 ? 0 : 1;
    }
}
