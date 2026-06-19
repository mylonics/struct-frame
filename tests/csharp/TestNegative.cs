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
using StructFrame.Framing;
using StructFrame.Profiles;
using StructFrame.SerializationTest;
using StructFrame.PkgTestMessages;
using StructFrame.PkgTestA;
using SerializationTestMD = StructFrame.SerializationTest.MessageDefinitions;
using PkgTestMessagesMD = StructFrame.PkgTestMessages.MessageDefinitions;
using StructFrame.CommonTypes;
using CommonTypesStatus = StructFrame.CommonTypes.Status;

public class TestNegative
{
    private static int testsRun = 0;
    private static int testsPassed = 0;
    private static int testsFailed = 0;

    private static BasicTypesMessage CreateTestMessage()
        {
            var msg = new BasicTypesMessage
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
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
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
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 10) return false;
            
            // Truncate the frame
            var truncatedSize = bytesWritten - 5;
            
            // Try to parse - should fail
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
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
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 2) return false;
            
            // Corrupt start bytes
            buffer[0] = 0xDE;
            buffer[1] = 0xAD;
            
            // Try to parse - should fail
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
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
            
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
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
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt length field (byte 2)
            buffer[2] = 0xFF;
            
            // Try to parse - should fail
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
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
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt CRC
            buffer[bytesWritten - 1] ^= 0xFF;
            
            // Try streaming parse
            var reader = new AccumulatingReader<StandardProfile>(1024, SerializationTestMD.GetMessageInfo);
            
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
            var reader = new AccumulatingReader<StandardProfile>(1024, SerializationTestMD.GetMessageInfo);
            
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
         * Test: Stream mode recovers after a garbage prefix.
         * Mirrors the C/C++/TS/JS/Rust "Stream mode: recovers after garbage prefix"
         * scenario. Junk bytes are fed into the byte-at-a-time accumulating reader,
         * then a real frame; the reader must resync and surface the valid frame.
         */
        private static bool TestStreamRecoversAfterGarbage()
        {
            var reader = new AccumulatingReader<StandardProfile>(1024, SerializationTestMD.GetMessageInfo);

            // Junk prefix that does not begin a valid frame.
            byte[] garbage = { 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56 };
            foreach (var b in garbage)
            {
                reader.PushByte(b);
            }

            // Encode a real frame.
            var msg = CreateTestMessage();
            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            // Feed the frame byte by byte; the reader should resync and yield a valid frame.
            for (int i = 0; i < frameSize; i++)
            {
                var r = reader.PushByte(buffer[i]);
                if (r.Valid)
                {
                    return true;
                }
            }
            return false;
        }

        /**
         * Test: Bulk profile with corrupted CRC
         */
        private static bool TestBulkProfileCorruptedCrc()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<BulkProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var bytesWritten = writer.Size;
            
            if (bytesWritten < 4) return false;
            
            // Corrupt the CRC (last 2 bytes)
            buffer[bytesWritten - 1] ^= 0xFF;
            buffer[bytesWritten - 2] ^= 0xFF;
            
            // Try to parse - should fail
            var reader = new BufferReader<BulkProfile>(SerializationTestMD.GetMessageInfo);
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
            var writer = new BufferWriter<StandardProfile>();
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
            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, totalBytes);
            
            var result1 = reader.Next();
            if (!result1.Valid) return false;  // First should be valid
            
            var result2 = reader.Next();
            return !result2.Valid;  // Second should be invalid
        }

        /**
         * Test: AccumulatingReader handles a frame fed in two separate AddData chunks
         */
        private static bool TestPartialFrameBoundary()
        {
            var msg = CreateTestMessage();
            
            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;
            
            if (frameSize < 10) return false;
            
            int mid = frameSize / 2;
            
            var reader = new AccumulatingReader<StandardProfile>(1024, SerializationTestMD.GetMessageInfo);
            
            // Feed first half via AddData, then call Next() to save partial data to internal buffer
            byte[] firstHalf = new byte[mid];
            Array.Copy(buffer, 0, firstHalf, 0, mid);
            reader.AddData(firstHalf);
            reader.Next();  // Should return invalid but save partial data internally
            
            // Feed second half - adds to internal buffer completing the frame
            byte[] secondHalf = new byte[frameSize - mid];
            Array.Copy(buffer, mid, secondHalf, 0, frameSize - mid);
            reader.AddData(secondHalf);
            
            // Call Next() once all data is present - should successfully decode the frame
            var result = reader.Next();
            return result.Valid;  // Expect success after accumulating both halves
        }

        /**
         * Test: BufferReader advances past a CRC-failed frame and returns the next valid frame.
         * Mirrors the C++ "Buffer reader: skips CRC-failed frame" test.
         */
        private static bool TestBufferReaderSkipsCrcFailed()
        {
            var msg = CreateTestMessage();

            byte[] buffer = new byte[4096];
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            int frame1End = writer.Size;

            msg.SmallInt = 99;
            writer.Write(msg);
            int totalBytes = writer.Size;

            // Corrupt the CRC of the first frame.
            buffer[frame1End - 1] ^= 0xFF;

            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, totalBytes);

            var result1 = reader.Next();
            if (result1.Valid) return false;  // First frame must be CRC-failed

            var result2 = reader.Next();
            if (!result2.Valid) return false;  // Second frame must be valid

            var decoded = BasicTypesMessage.Deserialize(result2);
            return decoded.SmallInt == 99;
        }

        /**
         * Test: AccumulatingReader in buffer mode recovers after a CRC-failed frame
         * and successfully decodes the subsequent valid frame.
         * Mirrors the C++ "Buffer mode: recovers after CRC failure" test.
         */
        private static bool TestBufferModeRecoverAfterCrcFailure()
        {
            var msg = CreateTestMessage();

            byte[] buffer = new byte[4096];
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            int frame1End = writer.Size;

            msg.SmallInt = 55;
            writer.Write(msg);
            int totalBytes = writer.Size;

            // Corrupt the CRC of the first frame.
            buffer[frame1End - 1] ^= 0xFF;

            var reader = new AccumulatingReader<StandardProfile>(4096, SerializationTestMD.GetMessageInfo);
            reader.AddData(buffer, 0, totalBytes);

            var result1 = reader.Next();
            if (result1.Valid) return false;  // First frame must be CRC-failed

            var result2 = reader.Next();
            if (!result2.Valid) return false;  // Second frame must be valid

            var decoded = BasicTypesMessage.Deserialize(result2);
            return decoded.SmallInt == 55;
        }

        private static bool TestInvalidMsgId()
        {
            var msg = CreateTestMessage();

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<StandardProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            if (frameSize < 5) return false;

            // Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
            // 0xFF is not a known message ID → GetMessageInfo returns null magic → CRC fails
            buffer[3] = 0xFF;

            var reader = new BufferReader<StandardProfile>(SerializationTestMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, frameSize);
            var result = reader.Next();
            return !result.Valid;  // Expect failure: CRC mismatch due to wrong magic values
        }

        private static bool TestMinimalProfileTruncatedFrame()
        {
            var msg = CreateTestMessage();

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<SensorProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            if (frameSize <= 5) return false;

            // Provide fewer bytes than the full frame to trigger truncation error
            int truncatedSize = frameSize - 5;

            var reader = new BufferReader<SensorProfile>(SerializationTestMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, truncatedSize);
            var result = reader.Next();
            return !result.Valid;  // Expect failure: buffer too small for expected payload
        }

        private static bool TestNetworkSysIdCompId()
        {
            var msg = CreateTestMessage();

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<NetworkProfile>();
            writer.SetBuffer(buffer);
            // Encode with seq=1, sysId=5, compId=10
            writer.Write(msg, seq: 1, sysId: 5, compId: 10);
            var frameSize = writer.Size;

            if (frameSize < 10) return false;

            // Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
            // sys_id is inside the CRC-protected region so CRC will fail
            buffer[3] ^= 0xFF;

            var reader = new BufferReader<NetworkProfile>(SerializationTestMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, frameSize);
            var result = reader.Next();
            return !result.Valid;  // Expect failure: corrupted sys_id invalidates CRC
        }

        /**
         * Test: Bulk profile rejects frame with corrupted pkg_id byte.
         * The pkg_id byte is inside the CRC-protected region, so corruption
         * must cause CRC failure.
         */
        private static bool TestBulkCorruptedPkgId()
        {
            var msg = new PackageTestMessage
            {
                CreatedAt = new Timestamp { Seconds = 1704067200, Nanoseconds = 123456789 },
                CurrentStatus = CommonTypesStatus.ACTIVE,
                Name = new byte[32]
            };
            var nameBytes = System.Text.Encoding.UTF8.GetBytes("test_device");
            Array.Copy(nameBytes, msg.Name, Math.Min(nameBytes.Length, 32));

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<BulkProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            if (frameSize < 10) return false;

            // Bulk frame layout: [start1][start2][len_lo][len_hi][pkg_id][msg_id][payload...][crc1][crc2]
            // pkg_id is at byte 4
            buffer[4] ^= 0xFF;

            var reader = new BufferReader<BulkProfile>(PkgTestMessagesMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, frameSize);
            var result = reader.Next();
            return !result.Valid;  // Expect failure: CRC mismatch due to corrupted pkg_id
        }

        /**
         * Test: Network profile rejects frame with corrupted pkg_id byte.
         * The pkg_id byte is inside the CRC-protected region.
         */
        private static bool TestNetworkCorruptedPkgId()
        {
            var msg = new PackageTestMessage
            {
                CreatedAt = new Timestamp { Seconds = 1704067200, Nanoseconds = 123456789 },
                CurrentStatus = CommonTypesStatus.ACTIVE,
                Name = new byte[32]
            };
            var nameBytes = System.Text.Encoding.UTF8.GetBytes("test_device");
            Array.Copy(nameBytes, msg.Name, Math.Min(nameBytes.Length, 32));

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<NetworkProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg, seq: 1, sysId: 5, compId: 10);
            var frameSize = writer.Size;

            if (frameSize < 12) return false;

            // Network frame layout: [start1][start2][seq][sys_id][comp_id][len_lo][len_hi][pkg_id][msg_id][payload...][crc1][crc2]
            // pkg_id is at byte 7
            buffer[7] ^= 0xFF;

            var reader = new BufferReader<NetworkProfile>(PkgTestMessagesMD.GetMessageInfo);
            reader.SetBuffer(buffer, 0, frameSize);
            var result = reader.Next();
            return !result.Valid;  // Expect failure: CRC mismatch due to corrupted pkg_id
        }

        /**
         * Test: Cross-package rejection — a frame with pkg_id=2 is rejected
         * by a pkg_id=1 message handler (GetMessageInfo returns null).
         * We encode a valid PackageTestMessage (pkgid=1, msgid=257) then
         * change the pkg_id byte to 2 so the combined msgid becomes 513 (0x201).
         * The PkgTestMessages handler should reject this because pkgid != 1.
         */
        private static bool TestCrossPackageRejection()
        {
            var msg = new PackageTestMessage
            {
                CreatedAt = new Timestamp { Seconds = 1704067200, Nanoseconds = 0 },
                CurrentStatus = CommonTypesStatus.IDLE,
                Name = new byte[32]
            };

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<BulkProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            if (frameSize < 10) return false;

            // Bulk frame: [start1][start2][len_lo][len_hi][pkg_id][msg_id][payload...][crc1][crc2]
            // pkg_id is at byte 4. Original value is 1 (for pkgid=1).
            // Change to 2 so combined msgid = (2 << 8) | 1 = 513.
            buffer[4] = 2;

            // Parse with PkgTestMessages handler — should reject because pkgid=2 != PackageInfo.PackageId=1
            var reader = new AccumulatingReader<BulkProfile>(2024, (id) => PkgTestMessagesMD.GetMessageInfo(id));
            reader.AddData(buffer, 0, frameSize);
            var result = reader.Next();

            // The parser should either reject (CRC fail due to pkgid change) or
            // GetMessageInfo returns null for the wrong pkgid, causing the frame to be skipped.
            // Either way, we should NOT get a valid frame with msgid 257.
            if (result.Valid && result.MsgId == PackageTestMessage.MsgId)
                return false;  // Should NOT have decoded as PackageTestMessage

            return true;  // Correctly rejected
        }

        /**
         * Test: Bulk profile with corrupted msg_id low byte.
         * Changes the local msg_id so GetMessageInfo returns null.
         */
        private static bool TestBulkCorruptedMsgIdLowByte()
        {
            var msg = new PackageTestMessage
            {
                CreatedAt = new Timestamp { Seconds = 1704067200, Nanoseconds = 0 },
                CurrentStatus = CommonTypesStatus.IDLE,
                Name = new byte[32]
            };

            byte[] buffer = new byte[1024];
            var writer = new BufferWriter<BulkProfile>();
            writer.SetBuffer(buffer);
            writer.Write(msg);
            var frameSize = writer.Size;

            if (frameSize < 10) return false;

            // Bulk frame: [start1][start2][len_lo][len_hi][pkg_id][msg_id_lo][payload...][crc1][crc2]
            // msg_id low byte is at byte 5. Original value is 1 (msgid=257, low byte = 1).
            // Change to 0xFF so combined msgid = (1 << 8) | 0xFF = 511.
            buffer[5] = 0xFF;

            var reader = new AccumulatingReader<BulkProfile>(2024, (id) => PkgTestMessagesMD.GetMessageInfo(id));
            reader.AddData(buffer, 0, frameSize);
            var result = reader.Next();

            // CRC will fail because we corrupted a byte in the CRC-protected region.
            return !result.Valid;
        }

        public static int Main(string[] args)
        {
            Console.WriteLine("\n========================================");
            Console.WriteLine("NEGATIVE TESTS - C# Parser");
            Console.WriteLine("========================================\n");

            // Define test matrix
            var tests = new (string name, Func<bool> func)[]
            {
                ("Buffer mode: recovers after CRC failure", TestBufferModeRecoverAfterCrcFailure),
                ("Buffer reader: skips CRC-failed frame", TestBufferReaderSkipsCrcFailed),
                ("Bulk profile: Corrupted CRC", TestBulkProfileCorruptedCrc),
                ("Bulk profile: Corrupted pkg_id byte", TestBulkCorruptedPkgId),
                ("Bulk profile: Corrupted msg_id low byte", TestBulkCorruptedMsgIdLowByte),
                ("Corrupted CRC detection", TestCorruptedCrc),
                ("Corrupted length field detection", TestCorruptedLength),
                ("Cross-package rejection (pkgid mismatch)", TestCrossPackageRejection),
                ("Invalid message ID rejection", TestInvalidMsgId),
                ("Invalid start bytes detection", TestInvalidStartBytes),
                ("Minimal profile: Truncated frame", TestMinimalProfileTruncatedFrame),
                ("Multiple frames: Corrupted middle frame", TestMultipleCorruptedFrames),
                ("Network profile: Corrupted pkg_id byte", TestNetworkCorruptedPkgId),
                ("Network profile: SysId/CompId corruption", TestNetworkSysIdCompId),
                ("Partial frame across buffer boundary", TestPartialFrameBoundary),
                ("Stream mode: recovers after garbage prefix", TestStreamRecoversAfterGarbage),
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
