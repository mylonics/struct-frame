// Test codec - Encode/decode functions for all frame formats (C#)

using System;
using System.Text;
using System.Runtime.InteropServices;
using StructFrame;
using StructFrame.SerializationTest;
using StructFrame.FrameHeaders;

namespace StructFrameTests
{
    /// <summary>
    /// Expected test values (matching expected_values.json)
    /// </summary>
    public static class ExpectedValues
    {
        public const uint MagicNumber = 0xDEADBEEF;
        public const string TestString = "Cross-platform test!";
        public const float TestFloat = 3.14159f;
        public const bool TestBool = true;
        public static readonly int[] TestArray = { 100, 200, 300 };
    }

    /// <summary>
    /// Manual message serializer to avoid StructLayout alignment issues with managed arrays
    /// </summary>
    public static class MessageSerializer
    {
        public const int MessageSize = 95;

        /// <summary>
        /// Manually serialize the test message to bytes
        /// Layout: magic_number(4) + test_string_length(1) + test_string_data(64) + 
        ///         test_float(4) + test_bool(1) + test_array_count(1) + test_array_data(20)
        /// </summary>
        public static byte[] Serialize(uint magicNumber, byte stringLength, byte[] stringData,
                                       float testFloat, bool testBool, byte arrayCount, int[] arrayData)
        {
            byte[] buffer = new byte[MessageSize];
            int offset = 0;

            // magic_number (uint32, offset 0)
            BitConverter.GetBytes(magicNumber).CopyTo(buffer, offset);
            offset += 4;

            // test_string_length (uint8, offset 4)
            buffer[offset++] = stringLength;

            // test_string_data (64 bytes, offset 5)
            Array.Copy(stringData, 0, buffer, offset, Math.Min(stringData.Length, 64));
            offset += 64;

            // test_float (float32, offset 69)
            BitConverter.GetBytes(testFloat).CopyTo(buffer, offset);
            offset += 4;

            // test_bool (bool/uint8, offset 73)
            buffer[offset++] = testBool ? (byte)1 : (byte)0;

            // test_array_count (uint8, offset 74)
            buffer[offset++] = arrayCount;

            // test_array_data (5 x int32 = 20 bytes, offset 75)
            for (int i = 0; i < 5; i++)
            {
                int value = (i < arrayData.Length) ? arrayData[i] : 0;
                BitConverter.GetBytes(value).CopyTo(buffer, offset);
                offset += 4;
            }

            return buffer;
        }

        /// <summary>
        /// Manually deserialize bytes to message components
        /// </summary>
        public static (uint magicNumber, byte stringLength, byte[] stringData,
                       float testFloat, bool testBool, byte arrayCount, int[] arrayData)
            Deserialize(byte[] buffer)
        {
            int offset = 0;

            uint magicNumber = BitConverter.ToUInt32(buffer, offset);
            offset += 4;

            byte stringLength = buffer[offset++];

            byte[] stringData = new byte[64];
            Array.Copy(buffer, offset, stringData, 0, 64);
            offset += 64;

            float testFloat = BitConverter.ToSingle(buffer, offset);
            offset += 4;

            bool testBool = buffer[offset++] != 0;

            byte arrayCount = buffer[offset++];

            int[] arrayData = new int[5];
            for (int i = 0; i < 5; i++)
            {
                arrayData[i] = BitConverter.ToInt32(buffer, offset);
                offset += 4;
            }

            return (magicNumber, stringLength, stringData, testFloat, testBool, arrayCount, arrayData);
        }
    }

    /// <summary>
    /// Test codec for encoding/decoding test messages with various frame formats
    /// </summary>
    public static class TestCodec
    {
        /// <summary>
        /// Create serialized test message bytes with expected values
        /// </summary>
        public static byte[] CreateTestMessageBytes()
        {
            byte[] strBytes = Encoding.UTF8.GetBytes(ExpectedValues.TestString);
            byte[] stringData = new byte[64];
            Array.Copy(strBytes, stringData, Math.Min(strBytes.Length, 64));

            return MessageSerializer.Serialize(
                ExpectedValues.MagicNumber,
                (byte)strBytes.Length,
                stringData,
                ExpectedValues.TestFloat,
                ExpectedValues.TestBool,
                (byte)ExpectedValues.TestArray.Length,
                ExpectedValues.TestArray
            );
        }

        /// <summary>
        /// Validate that decoded message bytes match expected values
        /// </summary>
        public static bool ValidateMessageBytes(byte[] msgData)
        {
            var (magicNumber, stringLength, stringData, testFloat, testBool, arrayCount, arrayData) = 
                MessageSerializer.Deserialize(msgData);

            bool valid = true;

            if (magicNumber != ExpectedValues.MagicNumber)
            {
                Console.WriteLine($"  Value mismatch: magic_number: expected {ExpectedValues.MagicNumber}, got {magicNumber}");
                valid = false;
            }

            string testString = Encoding.UTF8.GetString(stringData, 0, stringLength);
            if (!testString.StartsWith(ExpectedValues.TestString))
            {
                Console.WriteLine($"  Value mismatch: test_string: expected '{ExpectedValues.TestString}', got '{testString}'");
                valid = false;
            }

            if (Math.Abs(testFloat - ExpectedValues.TestFloat) > 0.0001f)
            {
                Console.WriteLine($"  Value mismatch: test_float: expected {ExpectedValues.TestFloat}, got {testFloat}");
                valid = false;
            }

            if (testBool != ExpectedValues.TestBool)
            {
                Console.WriteLine($"  Value mismatch: test_bool: expected {ExpectedValues.TestBool}, got {testBool}");
                valid = false;
            }

            if (arrayCount != ExpectedValues.TestArray.Length)
            {
                Console.WriteLine($"  Value mismatch: test_array count: expected {ExpectedValues.TestArray.Length}, got {arrayCount}");
                valid = false;
            }
            else
            {
                for (int i = 0; i < arrayCount; i++)
                {
                    if (arrayData[i] != ExpectedValues.TestArray[i])
                    {
                        Console.WriteLine($"  Value mismatch: test_array[{i}]: expected {ExpectedValues.TestArray[i]}, got {arrayData[i]}");
                        valid = false;
                    }
                }
            }

            return valid;
        }

        /// <summary>
        /// Calculate Fletcher-16 checksum
        /// </summary>
        internal static (byte, byte) FletcherChecksum(byte[] buffer, int start, int length)
        {
            byte byte1 = 0;
            byte byte2 = 0;

            for (int i = start; i < start + length; i++)
            {
                byte1 = (byte)((byte1 + buffer[i]) % 256);
                byte2 = (byte)((byte2 + byte1) % 256);
            }

            return (byte1, byte2);
        }
    }

    /* Minimal frame format helper classes (replacing frame_compat) */

    /// <summary>
    /// Basic + Default frame format helper
    /// </summary>
    class BasicDefault : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 4;
            const int footerSize = 2;
            int totalSize = headerSize + msgData.Length + footerSize;
            
            if (msgData.Length > 255)
                return new byte[0];

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(1); // DEFAULT = 1
            buffer[2] = (byte)msgData.Length;
            buffer[3] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            var (ck1, ck2) = TestCodec.FletcherChecksum(buffer, 2, headerSize + msgData.Length - 2);
            buffer[totalSize - 2] = ck1;
            buffer[totalSize - 1] = ck2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 6 || data[0] != HeaderConstants.BASIC_START_BYTE || !HeaderBasic.IsSecondStartByte(data[1]))
                return result;

            int msgLen = data[2];
            int msgId = data[3];
            int totalSize = 4 + msgLen + 2;

            if (length < totalSize)
                return result;

            var (ck1, ck2) = TestCodec.FletcherChecksum(data, 2, 4 + msgLen - 2);
            if (ck1 == data[totalSize - 2] && ck2 == data[totalSize - 1])
            {
                result.Valid = true;
                result.MsgId = msgId;
                result.MsgSize = msgLen;
                result.MsgData = new byte[msgLen];
                Array.Copy(data, 4, result.MsgData, 0, msgLen);
            }

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Tiny + Minimal frame format helper
    /// </summary>
    class TinyMinimal : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 2;
            int totalSize = headerSize + msgData.Length;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderTiny.GetStartByte(0); // MINIMAL = 0
            buffer[1] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 2 || !HeaderTiny.IsStartByte(data[0]))
                return result;

            int msgId = data[1];
            int msgLen = length - 2;

            result.Valid = true;
            result.MsgId = msgId;
            result.MsgSize = msgLen;
            result.MsgData = new byte[msgLen];
            Array.Copy(data, 2, result.MsgData, 0, msgLen);

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Basic + Extended frame format helper
    /// </summary>
    class BasicExtended : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 6;
            const int footerSize = 2;
            int totalSize = headerSize + msgData.Length + footerSize;

            if (msgData.Length > 65535)
                return new byte[0];

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(4); // EXTENDED = 4
            buffer[2] = (byte)(msgData.Length & 0xFF);
            buffer[3] = (byte)((msgData.Length >> 8) & 0xFF);
            buffer[4] = 0; // PKG_ID
            buffer[5] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            var (ck1, ck2) = TestCodec.FletcherChecksum(buffer, 2, headerSize + msgData.Length - 2);
            buffer[totalSize - 2] = ck1;
            buffer[totalSize - 1] = ck2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 8 || data[0] != HeaderConstants.BASIC_START_BYTE || !HeaderBasic.IsSecondStartByte(data[1]))
                return result;

            int msgLen = data[2] | (data[3] << 8);
            int msgId = data[5];
            int totalSize = 6 + msgLen + 2;

            if (length < totalSize)
                return result;

            var (ck1, ck2) = TestCodec.FletcherChecksum(data, 2, 6 + msgLen - 2);
            if (ck1 == data[totalSize - 2] && ck2 == data[totalSize - 1])
            {
                result.Valid = true;
                result.MsgId = msgId;
                result.MsgSize = msgLen;
                result.MsgData = new byte[msgLen];
                Array.Copy(data, 6, result.MsgData, 0, msgLen);
            }

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Basic + Extended + Multi System Stream frame format helper
    /// </summary>
    class BasicExtendedMultiSystemStream : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 9;
            const int footerSize = 2;
            int totalSize = headerSize + msgData.Length + footerSize;

            if (msgData.Length > 65535)
                return new byte[0];

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(8); // EXTENDED_MULTI_SYSTEM_STREAM = 8
            buffer[2] = 0; // SEQ
            buffer[3] = 0; // SYS_ID
            buffer[4] = 0; // COMP_ID
            buffer[5] = (byte)(msgData.Length & 0xFF);
            buffer[6] = (byte)((msgData.Length >> 8) & 0xFF);
            buffer[7] = 0; // PKG_ID
            buffer[8] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            var (ck1, ck2) = TestCodec.FletcherChecksum(buffer, 2, headerSize + msgData.Length - 2);
            buffer[totalSize - 2] = ck1;
            buffer[totalSize - 1] = ck2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 11 || data[0] != HeaderConstants.BASIC_START_BYTE || !HeaderBasic.IsSecondStartByte(data[1]))
                return result;

            int msgLen = data[5] | (data[6] << 8);
            int msgId = data[8];
            int totalSize = 9 + msgLen + 2;

            if (length < totalSize)
                return result;

            var (ck1, ck2) = TestCodec.FletcherChecksum(data, 2, 9 + msgLen - 2);
            if (ck1 == data[totalSize - 2] && ck2 == data[totalSize - 1])
            {
                result.Valid = true;
                result.MsgId = msgId;
                result.MsgSize = msgLen;
                result.MsgData = new byte[msgLen];
                Array.Copy(data, 9, result.MsgData, 0, msgLen);
            }

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Basic + Minimal frame format helper
    /// </summary>
    class BasicMinimal : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 3;
            int totalSize = headerSize + msgData.Length;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(0); // MINIMAL = 0
            buffer[2] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 3 || data[0] != HeaderConstants.BASIC_START_BYTE || !HeaderBasic.IsSecondStartByte(data[1]))
                return result;

            int msgId = data[2];
            int msgLen = length - 3;

            result.Valid = true;
            result.MsgId = msgId;
            result.MsgSize = msgLen;
            result.MsgData = new byte[msgLen];
            Array.Copy(data, 3, result.MsgData, 0, msgLen);

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Tiny + Default frame format helper
    /// </summary>
    class TinyDefault : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 3;
            const int footerSize = 2;
            int totalSize = headerSize + msgData.Length + footerSize;

            if (msgData.Length > 255)
                return new byte[0];

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderTiny.GetStartByte(1); // DEFAULT = 1
            buffer[1] = (byte)msgData.Length;
            buffer[2] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            var (ck1, ck2) = TestCodec.FletcherChecksum(buffer, 1, headerSize + msgData.Length - 1);
            buffer[totalSize - 2] = ck1;
            buffer[totalSize - 1] = ck2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 5 || !HeaderTiny.IsStartByte(data[0]))
                return result;

            int msgLen = data[1];
            int msgId = data[2];
            int totalSize = 3 + msgLen + 2;

            if (length < totalSize)
                return result;

            var (ck1, ck2) = TestCodec.FletcherChecksum(data, 1, 3 + msgLen - 1);
            if (ck1 == data[totalSize - 2] && ck2 == data[totalSize - 1])
            {
                result.Valid = true;
                result.MsgId = msgId;
                result.MsgSize = msgLen;
                result.MsgData = new byte[msgLen];
                Array.Copy(data, 3, result.MsgData, 0, msgLen);
            }

            return result;
        }

        public override FrameParseResult ParseByte(byte b) => throw new NotImplementedException();
        public override void Reset() => throw new NotImplementedException();
    }

    /// <summary>
    /// Test codec for encoding/decoding test messages with various frame formats
    /// </summary>
    public static class TestCodecHelpers
    {
        /// <summary>
        /// Get the frame parser for a given format name or profile
        /// </summary>
        public static FrameFormatBase GetParser(string formatName)
        {
            switch (formatName)
            {
                // Profile names (preferred)
                case "profile_standard":
                case "basic_default":
                    return new BasicDefault();
                case "profile_sensor":
                case "tiny_minimal":
                    return new TinyMinimal();
                case "profile_bulk":
                case "basic_extended":
                    return new BasicExtended();
                case "profile_network":
                case "basic_extended_multi_system_stream":
                    return new BasicExtendedMultiSystemStream();
                // Legacy direct format names
                case "basic_minimal":
                    return new BasicMinimal();
                case "tiny_default":
                    return new TinyDefault();
                default:
                    throw new ArgumentException($"Unknown frame format: {formatName}");
            }
        }

        /// <summary>
        /// Encode a test message using the specified frame format
        /// </summary>
        public static byte[] EncodeTestMessage(string formatName)
        {
            var parser = GetParser(formatName);
            byte[] msgData = TestCodec.CreateTestMessageBytes();
            
            // Use MsgId from the generated struct definition
            return parser.Encode(SerializationTestSerializationTestMessage.MsgId, msgData);
        }

        /// <summary>
        /// Decode a test message using the specified frame format
        /// </summary>
        public static byte[] DecodeTestMessage(string formatName, byte[] data)
        {
            var parser = GetParser(formatName);
            
            var result = parser.ValidatePacket(data, data.Length);
            
            if (!result.Valid)
            {
                return null;
            }
            
            return result.MsgData;
        }

        /// <summary>
        /// Create serialized test message bytes with expected values
        /// </summary>
        private static byte[] CreateTestMessageBytes()
        {
            return TestCodec.CreateTestMessageBytes();
        }
    }
}
