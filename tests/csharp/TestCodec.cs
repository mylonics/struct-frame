// Test codec - Encode/decode functions for all frame formats (C#)

using System;
using System.Text;
using System.Runtime.InteropServices;
using StructFrame;
using StructFrame.SerializationTest;

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
            byte[] msgData = CreateTestMessageBytes();
            
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
    }
}
