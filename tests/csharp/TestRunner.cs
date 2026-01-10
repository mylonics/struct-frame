// Test runner entry point for C#
//
// Usage:
//     dotnet run -- encode <frame_format> <output_file> [--runner test_runner_extended]
//     dotnet run -- decode <frame_format> <input_file> [--runner test_runner_extended]
//
// Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network

using System;
using System.IO;

namespace StructFrameTests
{
    class TestRunner
    {
        static void PrintUsage()
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  dotnet run -- encode <frame_format> <output_file> [--runner test_runner_extended]");
            Console.WriteLine("  dotnet run -- decode <frame_format> <input_file> [--runner test_runner_extended]");
            Console.WriteLine();
            Console.WriteLine("Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network");
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
                encodedData = TestCodecHelpers.EncodeTestMessage(formatName);
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

            int messageCount = TestCodecHelpers.DecodeTestMessages(formatName, data);
            if (messageCount == 0)
            {
                Console.WriteLine("[DECODE] FAILED: No messages decoded");
                PrintHex(data);
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: {messageCount} messages validated correctly");
            return 0;
        }

        static int RunEncodeExtended(string formatName, string outputFile)
        {
            Console.WriteLine($"[ENCODE] Format: {formatName} (Extended)");

            byte[] encodedData;
            try
            {
                encodedData = ExtendedTestCodec.EncodeExtendedMessages(formatName);
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

        static int RunDecodeExtended(string formatName, string inputFile)
        {
            Console.WriteLine($"[DECODE] Format: {formatName}, File: {inputFile} (Extended)");

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

            int messageCount = ExtendedTestCodec.DecodeExtendedMessages(formatName, data);
            if (messageCount == 0)
            {
                Console.WriteLine("[DECODE] FAILED: No messages decoded");
                PrintHex(data);
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: {messageCount} messages validated correctly");
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

            // Check for --runner argument
            bool useExtended = false;
            for (int i = 3; i < args.Length - 1; i++)
            {
                if (args[i] == "--runner" && args[i + 1] == "test_runner_extended")
                {
                    useExtended = true;
                    break;
                }
            }

            if (useExtended)
            {
                switch (mode)
                {
                    case "encode":
                        return RunEncodeExtended(formatName, filePath);
                    case "decode":
                        return RunDecodeExtended(formatName, filePath);
                    default:
                        Console.WriteLine($"Unknown mode: {mode}");
                        PrintUsage();
                        return 1;
                }
            }
            else
            {
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
}
