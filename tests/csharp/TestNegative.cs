/**
 * Negative tests for struct-frame C# parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 */

using System;
using StructFrame.Generated;

namespace StructFrameTests
{
    public class TestNegative
    {
        private static int testsRun = 0;
        private static int testsPassed = 0;
        private static int testsFailed = 0;

        private static void TestResult(string name, bool passed)
        {
            testsRun++;
            if (passed)
            {
                Console.WriteLine($"  [TEST] {name}... PASS");
                testsPassed++;
            }
            else
            {
                Console.WriteLine($"  [TEST] {name}... FAIL");
                testsFailed++;
            }
        }

        private static SerializationTestBasicTypesMessage CreateTestMessage()
        {
            var msg = new SerializationTestBasicTypesMessage
            {
                small_int = 42,
                medium_int = 1000,
                regular_int = 100000,
                large_int = 1000000000L,
                small_uint = 200,
                medium_uint = 50000,
                regular_uint = 3000000000U,
                large_uint = 9000000000000000000UL,
                single_precision = 3.14159f,
                double_precision = 2.71828,
                flag = true,
                device_id = "DEVICE123",
                description = "Test device"
            };
            return msg;
        }

        /**
         * Test: Parser rejects frame with corrupted CRC
         */
        private static bool TestCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileStandardWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, bytesWritten);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Parser rejects truncated frame
         */
        private static bool TestTruncatedFrame()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileStandardWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 10) return false;
            
            // Truncate the frame
            var truncatedSize = bytesWritten - 5;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, truncatedSize);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Parser rejects frame with invalid start bytes
         */
        private static bool TestInvalidStartBytes()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileStandardWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 2) return false;
            
            // Corrupt start bytes
            buffer[0] = 0xDE;
            buffer[1] = 0xAD;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, bytesWritten);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Parser handles zero-length buffer
         */
        private static bool TestZeroLengthBuffer()
        {
            var buffer = new byte[0];
            
            var reader = new ProfileStandardReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, 0);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Parser handles corrupted length field
         */
        private static bool TestCorruptedLength()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileStandardWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 4) return false;
            
            // Corrupt length field (byte 2)
            buffer[2] = 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, bytesWritten);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Streaming parser rejects corrupted CRC
         */
        private static bool TestStreamingCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileStandardWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 4) return false;
            
            // Corrupt CRC
            buffer[bytesWritten - 1] ^= 0xFF;
            
            // Try streaming parse
            var reader = new ProfileStandardAccumulatingReader(1024, SerializationTestMessages.GetMessageInfo);
            
            // Feed byte by byte
            for (int i = 0; i < bytesWritten; i++)
            {
                reader.PushByte(buffer[i]);
            }
            
            var result = reader.Next();
            return !result.valid;  // Expect failure
        }

        /**
         * Test: Streaming parser handles garbage data
         */
        private static bool TestStreamingGarbage()
        {
            var reader = new ProfileStandardAccumulatingReader(1024, SerializationTestMessages.GetMessageInfo);
            
            // Feed garbage bytes
            byte[] garbage = { 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A };
            
            foreach (var b in garbage)
            {
                reader.PushByte(b);
            }
            
            var result = reader.Next();
            return !result.valid;  // Expect no valid frame
        }

        /**
         * Test: Bulk profile with corrupted CRC
         */
        private static bool TestBulkProfileCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            var writer = new ProfileBulkWriter();
            writer.Write(msg);
            var buffer = writer.Data();
            var bytesWritten = writer.Size();
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileBulkReader(SerializationTestMessages.GetMessageInfo);
            reader.SetBuffer(buffer, bytesWritten);
            var result = reader.Next();
            
            return !result.valid;  // Expect failure
        }

        public static int Main(string[] args)
        {
            Console.WriteLine("\n========================================");
            Console.WriteLine("NEGATIVE TESTS - C# Parser");
            Console.WriteLine("========================================\n");
            
            Console.WriteLine("Testing error handling for invalid frames:\n");
            
            TestResult("Corrupted CRC detection", TestCorruptedCrc());
            TestResult("Truncated frame detection", TestTruncatedFrame());
            TestResult("Invalid start bytes detection", TestInvalidStartBytes());
            TestResult("Zero-length buffer handling", TestZeroLengthBuffer());
            TestResult("Corrupted length field detection", TestCorruptedLength());
            TestResult("Streaming: Corrupted CRC detection", TestStreamingCorruptedCrc());
            TestResult("Streaming: Garbage data handling", TestStreamingGarbage());
            TestResult("Bulk profile: Corrupted CRC", TestBulkProfileCorruptedCrc());
            
            Console.WriteLine("\n========================================");
            Console.WriteLine("RESULTS");
            Console.WriteLine("========================================");
            Console.WriteLine($"Tests run:    {testsRun}");
            Console.WriteLine($"Tests passed: {testsPassed}");
            Console.WriteLine($"Tests failed: {testsFailed}");
            Console.WriteLine("========================================\n");
            
            return testsFailed > 0 ? 1 : 0;
        }
    }
}
