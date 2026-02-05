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
using StructFrame;
using StructFrame.SerializationTest;

public class TestNegative
{
    private static int testsRun = 0;
    private static int testsPassed = 0;
    private static int testsFailed = 0;

    private static SerializationTestBasicTypesMessage CreateTestMessage()
        {
            var msg = new SerializationTestBasicTypesMessage
            {
                SmallInt = 42,
                MediumInt = 1000,
                RegularInt = 100000,
                LargeInt = 1000000000L,
                SmallUint = 200,
                MediumUint = 50000,
                RegularUint = 3000000000U,
                LargeUint = 9000000000000000000UL,
                SinglePrecision = 3.14159f,
                DoublePrecision = 2.71828,
                Flag = true
            };
            
            // Set DeviceId (fixed string, 32 bytes)
            var deviceIdBytes = System.Text.Encoding.UTF8.GetBytes("DEVICE123");
            msg.DeviceId = new byte[32];
            Array.Copy(deviceIdBytes, msg.DeviceId, Math.Min(deviceIdBytes.Length, 32));
            
            // Set Description (variable string, up to 128 bytes)
            var descBytes = System.Text.Encoding.UTF8.GetBytes("Test device");
            msg.DescriptionLength = (byte)Math.Min(descBytes.Length, 128);
            msg.DescriptionData = new byte[128];
            Array.Copy(descBytes, msg.DescriptionData, msg.DescriptionLength);
            
            return msg;
        }

        /**
         * Test: Parser rejects frame with corrupted CRC
         */
        private static bool TestCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, bytesWritten);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Parser rejects truncated frame
         */
        private static bool TestTruncatedFrame()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 10) return false;
            
            // Truncate the frame
            var truncatedSize = bytesWritten - 5;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, truncatedSize);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Parser rejects frame with invalid start bytes
         */
        private static bool TestInvalidStartBytes()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 2) return false;
            
            // Corrupt start bytes
            buffer[0] = 0xDE;
            buffer[1] = 0xAD;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, bytesWritten);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Parser handles zero-length buffer
         */
        private static bool TestZeroLengthBuffer()
        {
            var buffer = new byte[0];
            
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Parser handles corrupted length field
         */
        private static bool TestCorruptedLength()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt length field (byte 2)
            buffer[2] = 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, bytesWritten);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Streaming parser rejects corrupted CRC
         */
        private static bool TestStreamingCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt CRC
            buffer[bytesWritten - 1] ^= 0xFF;
            
            // Try streaming parse
            var reader = new ProfileStandardAccumulatingReader(1024, MessageDefinitions.GetMessageInfo);
            
            // Feed byte by byte
            for (int i = 0; i < bytesWritten; i++)
            {
                reader.PushByte(buffer[i]);
            }
            
            var result = reader.Next();
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Streaming parser handles garbage data
         */
        private static bool TestStreamingGarbage()
        {
            var reader = new ProfileStandardAccumulatingReader(1024, MessageDefinitions.GetMessageInfo);
            
            // Feed garbage bytes
            byte[] garbage = { 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A };
            
            foreach (var b in garbage)
            {
                reader.PushByte(b);
            }
            
            var result = reader.Next();
            return !result.Valid;  // Expect no valid frame
        }

        /**
         * Test: Bulk profile with corrupted CRC
         */
        private static bool TestBulkProfileCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new ProfileBulkWriter();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new ProfileBulkReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, bytesWritten);
            var result = reader.Next();
            
            return !result.Valid;  // Expect failure
        }

        /**
         * Test: Multiple frames with corrupted middle frame
         */
        private static bool TestMultipleCorruptedFrames()
        {
            // Create buffer with 3 messages
            byte[] buffer = new byte[4096];
            var writer = new ProfileStandardWriter();
            writer.SetBuffer(buffer);
            
            var msg1 = CreateTestMessage();
            msg1.SmallInt = 1;
            writer.Write(msg1);
            var bytes1End = writer.Size;
            
            var msg2 = CreateTestMessage();
            msg2.SmallInt = 2;
            writer.Write(msg2);
            var bytes2End = writer.Size;
            
            var msg3 = CreateTestMessage();
            msg3.SmallInt = 3;
            writer.Write(msg3);
            
            var totalBytes = writer.Size;
            
            // Corrupt second frame's CRC (last byte before third frame)
            buffer[bytes2End - 1] ^= 0xFF;
            
            // Parse all frames
            var reader = new ProfileStandardReader(MessageDefinitions.GetMessageInfo);
            reader.SetBuffer(buffer, 0, totalBytes);
            
            var result1 = reader.Next();
            if (!result1.Valid) return false;  // First should be valid
            
            var result2 = reader.Next();
            return !result2.Valid;  // Second should be invalid
        }

        public static int Main(string[] args)
        {
            Console.WriteLine("\n========================================");
            Console.WriteLine("NEGATIVE TESTS - C# Parser");
            Console.WriteLine("========================================\n");
            
            // Define test matrix
            var tests = new (string name, Func<bool> func)[]
            {
                ("Bulk profile: Corrupted CRC", TestBulkProfileCorruptedCrc),
                ("Corrupted CRC detection", TestCorruptedCrc),
                ("Corrupted length field detection", TestCorruptedLength),
                ("Invalid start bytes detection", TestInvalidStartBytes),
                ("Multiple frames: Corrupted middle frame", TestMultipleCorruptedFrames),
                ("Streaming: Corrupted CRC detection", TestStreamingCorruptedCrc),
                ("Streaming: Garbage data handling", TestStreamingGarbage),
                ("Truncated frame detection", TestTruncatedFrame),
                ("Zero-length buffer handling", TestZeroLengthBuffer),
            };
            
            Console.WriteLine("Test Results Matrix:\n");
            Console.WriteLine($"{"Test Name",-50} {"Result",6}");
            Console.WriteLine($"{new string('=', 50)} {new string('=', 6)}");
            
            // Run all tests from the matrix
            foreach (var test in tests)
            {
                testsRun++;
                bool passed = test.func();
                
                string result = passed ? "PASS" : "FAIL";
                Console.WriteLine($"{test.name,-50} {result,6}");
                
                if (passed)
                {
                    testsPassed++;
                }
                else
                {
                    testsFailed++;
                }
            }
            
            Console.WriteLine("\n========================================");
            Console.WriteLine($"Summary: {testsPassed}/{testsRun} tests passed");
            Console.WriteLine("========================================\n");
            
            return testsFailed > 0 ? 1 : 0;
        }
    }
