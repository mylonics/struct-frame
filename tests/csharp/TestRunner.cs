// Test runner entry point for C#
//
// Usage:
//     dotnet run -- encode <frame_format> <output_file>
//     dotnet run -- decode <frame_format> <input_file>
//
// Frame formats: basic_default, basic_minimal, tiny_default, tiny_minimal

using System;
using System.IO;

namespace StructFrameTests
{
    class TestRunner
    {
        static void PrintUsage()
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  dotnet run -- encode <frame_format> <output_file>");
            Console.WriteLine("  dotnet run -- decode <frame_format> <input_file>");
            Console.WriteLine();
            Console.WriteLine("Frame formats: basic_default, basic_minimal, tiny_default, tiny_minimal");
        }

        static void PrintHex(byte[] data)
        {
            int displayLen = Math.Min(data.Length, 64);
            string hex = BitConverter.ToString(data, 0, displayLen).Replace("-", "").ToLower();
            string suffix = data.Length > 64 ? "..." : "";
            Console.WriteLine($"  Hex ({data.Length} bytes): {hex}{suffix}");
        }

        static int RunEncode(string formatName, string outputFile)
        {
            Console.WriteLine($"[ENCODE] Format: {formatName}");

            byte[] encodedData;
            try
            {
                encodedData = TestCodec.EncodeTestMessage(formatName);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[ENCODE] FAILED: Encoding error - {e.Message}");
                return 1;
            }

            try
            {
                File.WriteAllBytes(outputFile, encodedData);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[ENCODE] FAILED: Cannot create output file: {outputFile} - {e.Message}");
                return 1;
            }

            Console.WriteLine($"[ENCODE] SUCCESS: Wrote {encodedData.Length} bytes to {outputFile}");
            return 0;
        }

        static int RunDecode(string formatName, string inputFile)
        {
            Console.WriteLine($"[DECODE] Format: {formatName}, File: {inputFile}");

            byte[] data;
            try
            {
                data = File.ReadAllBytes(inputFile);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[DECODE] FAILED: Cannot open input file: {inputFile} - {e.Message}");
                return 1;
            }

            if (data.Length == 0)
            {
                Console.WriteLine("[DECODE] FAILED: Empty file");
                return 1;
            }

            var msg = TestCodec.DecodeTestMessage(formatName, data);
            if (msg == null)
            {
                Console.WriteLine("[DECODE] FAILED: Frame validation failed");
                PrintHex(data);
                return 1;
            }

            if (!TestCodec.ValidateTestMessage(msg.Value))
            {
                Console.WriteLine("[DECODE] FAILED: Message validation failed");
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: Decoded and validated message ({data.Length} bytes)");
            return 0;
        }

        static int Main(string[] args)
        {
            if (args.Length < 3)
            {
                PrintUsage();
                return 1;
            }

            string mode = args[0].ToLower();
            string formatName = args[1];
            string filePath = args[2];

            switch (mode)
            {
                case "encode":
                    return RunEncode(formatName, filePath);
                case "decode":
                    return RunDecode(formatName, filePath);
                default:
                    Console.WriteLine($"Unknown mode: {mode}");
                    PrintUsage();
                    return 1;
            }
        }
    }
}
