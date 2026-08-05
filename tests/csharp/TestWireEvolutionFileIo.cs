/**
 * Cross-language x cross-version wire-evolution file I/O (C#).
 * See tests/cpp/test_wire_evolution_file_io.cpp for the full rationale.
 *
 * Usage (via TestRunner.cs --runner dispatch):
 *   dotnet StructFrameTests.dll --runner test_wire_evolution_file_io encode v1 <file>
 *   dotnet StructFrameTests.dll --runner test_wire_evolution_file_io encode v2 <file>
 *   dotnet StructFrameTests.dll --runner test_wire_evolution_file_io decode v1 <file>
 *   dotnet StructFrameTests.dll --runner test_wire_evolution_file_io decode v2 <file>
 *
 * Canonical values must match every other language's file_io helper:
 * Header=0x1234, Seq=42, CrcSeed=0xDEADBEEF.
 */
using System;
using System.IO;
using V1 = StructFrame.WireEvolutionV1;
using V2 = StructFrame.WireEvolutionV2;

class TestWireEvolutionFileIo
{
    private const ushort Header = 0x1234;
    private const byte Seq = 42;
    private const uint CrcSeed = 0xDEADBEEF;

    public static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine("Usage: <encode|decode> <v1|v2> <file>");
            return 2;
        }
        string mode = args[0];
        string version = args[1];
        string path = args[2];

        if (mode == "encode") return DoEncode(version, path);
        if (mode == "decode") return DoDecode(version, path);
        Console.Error.WriteLine($"Unknown mode: {mode}");
        return 2;
    }

    private static int DoEncode(string version, string path)
    {
        byte[] buf;
        if (version == "v1")
        {
            var msg = new V1.BaseExtensionMessage { Header = Header, Seq = Seq };
            buf = msg.Serialize();
        }
        else if (version == "v2")
        {
            var msg = new V2.BaseExtensionMessage { Header = Header, Seq = Seq, CrcSeed = CrcSeed };
            buf = msg.Serialize();
        }
        else
        {
            Console.Error.WriteLine($"[ENCODE] FAILED: unknown version '{version}'");
            return 1;
        }
        File.WriteAllBytes(path, buf);
        Console.WriteLine($"[ENCODE] SUCCESS: wrote {buf.Length} bytes ({version}) to {path}");
        return 0;
    }

    private static int DoDecode(string version, string path)
    {
        byte[] buf = File.ReadAllBytes(path);

        if (version == "v1")
        {
            var msg = V1.BaseExtensionMessage.Deserialize(buf);
            if (msg.Header != Header || msg.Seq != Seq)
            {
                Console.Error.WriteLine($"[DECODE] FAILED: header=0x{msg.Header:x4} (expected 0x{Header:x4}) " +
                                        $"seq={msg.Seq} (expected {Seq})");
                return 1;
            }
            Console.WriteLine($"[DECODE] SUCCESS: v1 header=0x{msg.Header:x4} seq={msg.Seq}");
            return 0;
        }
        else if (version == "v2")
        {
            var msg = V2.BaseExtensionMessage.Deserialize(buf);
            if (msg.Header != Header || msg.Seq != Seq)
            {
                Console.Error.WriteLine($"[DECODE] FAILED: header=0x{msg.Header:x4} (expected 0x{Header:x4}) " +
                                        $"seq={msg.Seq} (expected {Seq})");
                return 1;
            }
            // A legacy (v1-sized, 3-byte) frame decoded as v2 must fill the
            // extension with its schema default (4242, not zero); a genuine
            // v2-sized (7-byte) frame must preserve the transmitted value.
            uint expectedCrc = buf.Length >= V2.BaseExtensionMessage.BaseSize + 4 ? CrcSeed : 4242;
            if (msg.CrcSeed != expectedCrc)
            {
                Console.Error.WriteLine($"[DECODE] FAILED: crcSeed=0x{msg.CrcSeed:x8} (expected 0x{expectedCrc:x8} " +
                                        $"for {buf.Length}-byte input)");
                return 1;
            }
            Console.WriteLine($"[DECODE] SUCCESS: v2 header=0x{msg.Header:x4} seq={msg.Seq} " +
                              $"crcSeed=0x{msg.CrcSeed:x8} (from {buf.Length} bytes)");
            return 0;
        }
        Console.Error.WriteLine($"[DECODE] FAILED: unknown version '{version}'");
        return 1;
    }
}
