/**
 * Test harness (C#).
 * High-level test setup, CLI parsing, file I/O, and test execution.
 *
 * This file matches the C++ test_harness.hpp structure.
 */

using System;
using System.IO;

namespace StructFrameTests
{
    /// <summary>
    /// Test harness - High-level test setup, CLI parsing, file I/O, and test execution
    /// </summary>
    public static class TestHarness
    {
        private const int BUFFER_SIZE = 16384;

        private static void PrintUsage(string profileHelp)
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  dotnet run -- encode <profile> <output_file>");
            Console.WriteLine("  dotnet run -- decode <profile> <input_file>");
            Console.WriteLine("  dotnet run -- both <profile>");
            Console.WriteLine($"\nProfiles: {profileHelp}");
        }

        private static bool WriteFile(string path, byte[] data, int length)
        {
            try
            {
                using (var fs = new FileStream(path, FileMode.Create))
                {
                    fs.Write(data, 0, length);
                }
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static byte[] ReadFile(string path)
        {
            try
            {
                return File.ReadAllBytes(path);
            }
            catch
            {
                return null;
            }
        }

        private static int RunEncode(
            int messageCount,
            GetMessageFunc getMessage,
            string profile,
            string outputFile)
        {
            var buffer = new byte[BUFFER_SIZE];
            int bytesWritten = ProfileRunner.Encode(messageCount, getMessage, profile, buffer);

            if (bytesWritten == 0 || !WriteFile(outputFile, buffer, bytesWritten))
            {
                Console.WriteLine("[ENCODE] FAILED");
                return 1;
            }

            Console.WriteLine($"[ENCODE] SUCCESS: Wrote {bytesWritten} bytes to {outputFile}");
            return 0;
        }

        private static int RunDecode(
            int messageCount,
            GetMessageFunc getMessage,
            GetMessageInfoFunc getMessageInfo,
            string profile,
            string inputFile)
        {
            var buffer = ReadFile(inputFile);
            if (buffer == null || buffer.Length == 0)
            {
                Console.WriteLine("[DECODE] FAILED: Cannot read file");
                return 1;
            }

            int count = ProfileRunner.Parse(messageCount, getMessage, getMessageInfo, profile, buffer, buffer.Length);
            if (count != messageCount)
            {
                Console.WriteLine($"[DECODE] FAILED: {count} of {messageCount} messages validated");
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: {count} messages validated");
            return 0;
        }

        private static int RunBoth(
            int messageCount,
            GetMessageFunc getMessage,
            GetMessageInfoFunc getMessageInfo,
            string profile)
        {
            var buffer = new byte[BUFFER_SIZE];
            int bytesWritten = ProfileRunner.Encode(messageCount, getMessage, profile, buffer);

            if (bytesWritten == 0)
            {
                Console.WriteLine("[BOTH] FAILED: Encoding error");
                return 1;
            }

            Console.WriteLine($"[BOTH] Encoded {bytesWritten} bytes");

            int count = ProfileRunner.Parse(messageCount, getMessage, getMessageInfo, profile, buffer, bytesWritten);
            if (count != messageCount)
            {
                Console.WriteLine($"[BOTH] FAILED: {count} of {messageCount} messages validated");
                return 1;
            }

            Console.WriteLine($"[BOTH] SUCCESS: {count} messages round-trip validated");
            return 0;
        }

        /// <summary>
        /// Main entry point for test programs.
        /// </summary>
        public static int Run(
            string[] args,
            int messageCount,
            GetMessageFunc getMessage,
            GetMessageInfoFunc getMessageInfo,
            string testName,
            string profileHelp)
        {
            if (args.Length < 2)
            {
                PrintUsage(profileHelp);
                return 1;
            }

            string mode = args[0];
            string profile = args[1];
            string filePath = args.Length > 2 ? args[2] : "";

            if (mode != "encode" && mode != "decode" && mode != "both")
            {
                Console.WriteLine($"Unknown mode: {mode}");
                PrintUsage(profileHelp);
                return 1;
            }

            if ((mode == "encode" || mode == "decode") && string.IsNullOrEmpty(filePath))
            {
                Console.WriteLine($"Mode '{mode}' requires a file argument");
                PrintUsage(profileHelp);
                return 1;
            }

            Console.WriteLine($"\n[TEST START] {testName} {profile} {mode}");

            int result;
            if (mode == "encode")
            {
                result = RunEncode(messageCount, getMessage, profile, filePath);
            }
            else if (mode == "decode")
            {
                result = RunDecode(messageCount, getMessage, getMessageInfo, profile, filePath);
            }
            else // both
            {
                result = RunBoth(messageCount, getMessage, getMessageInfo, profile);
            }

            string status = result == 0 ? "PASS" : "FAIL";
            Console.WriteLine($"[TEST END] {testName} {profile} {mode}: {status}\n");

            return result;
        }
    }
}
