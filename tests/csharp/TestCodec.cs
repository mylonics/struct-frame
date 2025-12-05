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
    /// Test codec for encoding/decoding test messages with various frame formats
    /// </summary>
    public static class TestCodec
    {
        /// <summary>
        /// Create and populate a test message with expected values
        /// </summary>
        public static SerializationTestSerializationTestMessage CreateTestMessage()
        {
            var msg = new SerializationTestSerializationTestMessage();
            
            msg.MagicNumber = ExpectedValues.MagicNumber;
            
            // Set string field
            byte[] strBytes = Encoding.UTF8.GetBytes(ExpectedValues.TestString);
            msg.TestStringLength = (byte)strBytes.Length;
            msg.TestStringData = new byte[64];
            Array.Copy(strBytes, msg.TestStringData, Math.Min(strBytes.Length, 64));
            
            msg.TestFloat = ExpectedValues.TestFloat;
            msg.TestBool = ExpectedValues.TestBool;
            
            // Set array field
            msg.TestArrayCount = (byte)ExpectedValues.TestArray.Length;
            msg.TestArrayData = new int[5];
            Array.Copy(ExpectedValues.TestArray, msg.TestArrayData, ExpectedValues.TestArray.Length);
            
            return msg;
        }

        /// <summary>
        /// Validate that a decoded message matches expected values
        /// </summary>
        public static bool ValidateTestMessage(SerializationTestSerializationTestMessage msg)
        {
            bool valid = true;

            if (msg.MagicNumber != ExpectedValues.MagicNumber)
            {
                Console.WriteLine($"  Value mismatch: magic_number: expected {ExpectedValues.MagicNumber}, got {msg.MagicNumber}");
                valid = false;
            }

            // Check string
            string testString = Encoding.UTF8.GetString(msg.TestStringData, 0, msg.TestStringLength);
            if (!testString.StartsWith(ExpectedValues.TestString))
            {
                Console.WriteLine($"  Value mismatch: test_string: expected '{ExpectedValues.TestString}', got '{testString}'");
                valid = false;
            }

            if (Math.Abs(msg.TestFloat - ExpectedValues.TestFloat) > 0.0001f)
            {
                Console.WriteLine($"  Value mismatch: test_float: expected {ExpectedValues.TestFloat}, got {msg.TestFloat}");
                valid = false;
            }

            if (msg.TestBool != ExpectedValues.TestBool)
            {
                Console.WriteLine($"  Value mismatch: test_bool: expected {ExpectedValues.TestBool}, got {msg.TestBool}");
                valid = false;
            }

            // Check array
            if (msg.TestArrayCount != ExpectedValues.TestArray.Length)
            {
                Console.WriteLine($"  Value mismatch: test_array count: expected {ExpectedValues.TestArray.Length}, got {msg.TestArrayCount}");
                valid = false;
            }
            else
            {
                for (int i = 0; i < msg.TestArrayCount; i++)
                {
                    if (msg.TestArrayData[i] != ExpectedValues.TestArray[i])
                    {
                        Console.WriteLine($"  Value mismatch: test_array[{i}]: expected {ExpectedValues.TestArray[i]}, got {msg.TestArrayData[i]}");
                        valid = false;
                    }
                }
            }

            return valid;
        }

        /// <summary>
        /// Get the frame parser for a given format name
        /// </summary>
        public static FrameFormatBase GetParser(string formatName)
        {
            switch (formatName)
            {
                case "basic_default":
                    return new BasicDefault();
                case "basic_minimal":
                    return new BasicMinimal();
                case "tiny_default":
                    return new TinyDefault();
                case "tiny_minimal":
                    return new TinyMinimal();
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
            var msg = CreateTestMessage();
            
            // Convert struct to bytes
            byte[] msgData = StructHelper.StructToBytes(msg);
            
            // Encode with frame format
            return parser.Encode(SerializationTestSerializationTestMessage.MsgId, msgData);
        }

        /// <summary>
        /// Decode a test message using the specified frame format
        /// </summary>
        public static SerializationTestSerializationTestMessage? DecodeTestMessage(string formatName, byte[] data)
        {
            var parser = GetParser(formatName);
            
            // Validate and parse the packet
            var result = parser.ValidatePacket(data, data.Length);
            
            if (!result.Valid)
            {
                return null;
            }
            
            // Convert bytes to struct
            return StructHelper.BytesToStruct<SerializationTestSerializationTestMessage>(result.MsgData);
        }
    }
}
