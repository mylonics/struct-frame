/**
 * Test codec (C#) - Encode/decode and test runner infrastructure.
 *
 * This file provides:
 * 1. Config-based encode/decode functions
 * 2. Test runner utilities (file I/O, hex dump, CLI parsing)
 * 3. A unified RunTestMain() function for entry points
 */

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using StructFrame;
using StructFrame.SerializationTest;

namespace StructFrameTests
{
    public static class TestCodec
    {
        // ============================================================================
        // Utility functions
        // ============================================================================

        public static void PrintUsage(string formatsHelp)
        {
            Console.WriteLine("Usage:");
            Console.WriteLine("  test_runner encode <frame_format> <output_file>");
            Console.WriteLine("  test_runner decode <frame_format> <input_file>");
            Console.WriteLine();
            Console.WriteLine($"Frame formats: {formatsHelp}");
        }

        public static void PrintHex(byte[] data)
        {
            int displayLen = Math.Min(data.Length, 64);
            string hex = BitConverter.ToString(data, 0, displayLen).Replace("-", "").ToLower();
            string suffix = data.Length > 64 ? "..." : "";
            Console.WriteLine($"  Hex ({data.Length} bytes): {hex}{suffix}");
        }

        // ============================================================================
        // Message encoding/decoding helpers
        // ============================================================================

        private static SerializationTestMessage CreateSerializationTestMessage(Dictionary<string, object> data)
        {
            var msg = new SerializationTestMessage
            {
                MagicNumber = (uint)data["magic_number"],
                TestString = Encoding.UTF8.GetBytes((string)data["test_string"]),
                TestFloat = (float)data["test_float"],
                TestBool = (bool)data["test_bool"]
            };

            var testArray = (List<int>)data["test_array"];
            msg.TestArray = new BoundedArray<int>
            {
                Count = (ushort)testArray.Count,
                Data = testArray.ToArray()
            };

            return msg;
        }

        private static BasicTypesMessage CreateBasicTypesMessage(Dictionary<string, object> data)
        {
            return new BasicTypesMessage
            {
                SmallInt = (sbyte)data["small_int"],
                MediumInt = (short)data["medium_int"],
                RegularInt = (int)data["regular_int"],
                LargeInt = (long)data["large_int"],
                SmallUint = (byte)data["small_uint"],
                MediumUint = (ushort)data["medium_uint"],
                RegularUint = (uint)data["regular_uint"],
                LargeUint = (ulong)data["large_uint"],
                SinglePrecision = (float)data["single_precision"],
                DoublePrecision = (double)data["double_precision"],
                Flag = (bool)data["flag"],
                DeviceId = Encoding.UTF8.GetBytes((string)data["device_id"]),
                Description = Encoding.UTF8.GetBytes((string)data["description"])
            };
        }

        private static UnionTestMessage CreateUnionTestMessage(Dictionary<string, object> data)
        {
            var msg = new UnionTestMessage();
            int payloadType = (int)data["payload_type"];

            if (payloadType == 1 && data.ContainsKey("array_payload"))
            {
                var arrayData = (Dictionary<string, object>)data["array_payload"];
                // Create array payload (simplified for now - just set fields present)
                // This would need to be expanded based on actual struct definition
            }
            else if (payloadType == 2 && data.ContainsKey("test_payload"))
            {
                var testData = (Dictionary<string, object>)data["test_payload"];
                // Create test payload
            }

            return msg;
        }

        private static byte[] EncodeMessage(object msg)
        {
            if (msg is SerializationTestMessage stm)
            {
                return stm.Pack();
            }
            else if (msg is BasicTypesMessage btm)
            {
                return btm.Pack();
            }
            else if (msg is UnionTestMessage utm)
            {
                return utm.Pack();
            }
            throw new InvalidOperationException("Unknown message type");
        }

        private static int GetMessageId(object msg)
        {
            if (msg is SerializationTestMessage)
                return SerializationTestMessage.MsgId;
            else if (msg is BasicTypesMessage)
                return BasicTypesMessage.MsgId;
            else if (msg is UnionTestMessage)
                return UnionTestMessage.MsgId;
            throw new InvalidOperationException("Unknown message type");
        }

        // ============================================================================
        // Encoding functions
        // ============================================================================

        public static byte[] EncodeStandardMessages(string formatName)
        {
            var writer = CreateWriter(formatName, 4096);

            for (int i = 0; i < StandardTestData.MESSAGE_COUNT; i++)
            {
                var mixedMsg = StandardTestData.GetTestMessage(i);
                object msg;

                if (mixedMsg.Type == MessageType.SerializationTest)
                {
                    msg = CreateSerializationTestMessage(mixedMsg.Data);
                }
                else if (mixedMsg.Type == MessageType.BasicTypes)
                {
                    msg = CreateBasicTypesMessage(mixedMsg.Data);
                }
                else if (mixedMsg.Type == MessageType.UnionTest)
                {
                    msg = CreateUnionTestMessage(mixedMsg.Data);
                }
                else
                {
                    throw new Exception($"Unknown message type: {mixedMsg.Type}");
                }

                byte[] msgData = EncodeMessage(msg);
                int msgId = GetMessageId(msg);
                
                int bytesWritten = writer.Write(msgId, msgData);
                if (bytesWritten == 0)
                {
                    throw new Exception($"Failed to encode message {i}");
                }
            }

            return writer.GetData();
        }

        public static byte[] EncodeExtendedMessages(string formatName)
        {
            var writer = CreateWriter(formatName, 8192);

            for (int i = 0; i < ExtendedTestData.MESSAGE_COUNT; i++)
            {
                var (msg, typeName) = ExtendedTestData.GetExtendedTestMessage(i);
                if (msg == null)
                {
                    throw new Exception($"Failed to get extended message {i}");
                }

                byte[] msgData = msg.Pack();
                int msgId = msg.MsgId;

                int bytesWritten = writer.Write(msgId, msgData);
                if (bytesWritten == 0)
                {
                    throw new Exception($"Failed to encode extended message {i}");
                }
            }

            return writer.GetData();
        }

        // ============================================================================
        // Decoding functions
        // ============================================================================

        private static bool ValidateSerializationTestMessage(SerializationTestMessage msg, Dictionary<string, object> expected)
        {
            if (msg.MagicNumber != (uint)expected["magic_number"])
            {
                Console.WriteLine($"  magic_number mismatch: expected {expected["magic_number"]}, got {msg.MagicNumber}");
                return false;
            }

            string testString = Encoding.UTF8.GetString(msg.TestString).TrimEnd('\0');
            string expectedString = (string)expected["test_string"];
            if (testString != expectedString)
            {
                Console.WriteLine($"  test_string mismatch: expected '{expectedString}', got '{testString}'");
                return false;
            }

            float expectedFloat = (float)expected["test_float"];
            float tolerance = Math.Max(Math.Abs(expectedFloat) * 1e-4f, 1e-4f);
            if (Math.Abs(msg.TestFloat - expectedFloat) > tolerance)
            {
                Console.WriteLine($"  test_float mismatch: expected {expectedFloat}, got {msg.TestFloat}");
                return false;
            }

            if (msg.TestBool != (bool)expected["test_bool"])
            {
                Console.WriteLine($"  test_bool mismatch: expected {expected["test_bool"]}, got {msg.TestBool}");
                return false;
            }

            var expectedArray = (List<int>)expected["test_array"];
            if (msg.TestArray.Count != expectedArray.Count)
            {
                Console.WriteLine($"  test_array count mismatch: expected {expectedArray.Count}, got {msg.TestArray.Count}");
                return false;
            }

            for (int i = 0; i < expectedArray.Count; i++)
            {
                if (msg.TestArray.Data[i] != expectedArray[i])
                {
                    Console.WriteLine($"  test_array[{i}] mismatch: expected {expectedArray[i]}, got {msg.TestArray.Data[i]}");
                    return false;
                }
            }

            return true;
        }

        private static bool ValidateBasicTypesMessage(BasicTypesMessage msg, Dictionary<string, object> expected)
        {
            // Validate all fields (simplified - add all fields)
            if (msg.SmallInt != (sbyte)expected["small_int"])
            {
                Console.WriteLine($"  small_int mismatch");
                return false;
            }
            // Add more validations as needed
            return true;
        }

        public static (bool success, int messageCount) DecodeStandardMessages(string formatName, byte[] data)
        {
            var reader = CreateReader(formatName, data);
            int messageCount = 0;

            while (reader.HasMore() && messageCount < StandardTestData.MESSAGE_COUNT)
            {
                var result = reader.Next();
                if (!result.Valid)
                {
                    Console.WriteLine($"  Decoding failed for message {messageCount}");
                    return (false, messageCount);
                }

                var expected = StandardTestData.GetTestMessage(messageCount);
                int expectedMsgId;

                if (expected.Type == MessageType.SerializationTest)
                {
                    expectedMsgId = SerializationTestMessage.MsgId;
                }
                else if (expected.Type == MessageType.BasicTypes)
                {
                    expectedMsgId = BasicTypesMessage.MsgId;
                }
                else if (expected.Type == MessageType.UnionTest)
                {
                    expectedMsgId = UnionTestMessage.MsgId;
                }
                else
                {
                    Console.WriteLine($"  Unknown message type: {expected.Type}");
                    return (false, messageCount);
                }

                if (result.MsgId != expectedMsgId)
                {
                    Console.WriteLine($"  Message ID mismatch for message {messageCount}: expected {expectedMsgId}, got {result.MsgId}");
                    return (false, messageCount);
                }

                // Decode and validate
                if (expected.Type == MessageType.SerializationTest)
                {
                    var msg = SerializationTestMessage.Unpack(result.MsgData);
                    if (!ValidateSerializationTestMessage(msg, expected.Data))
                    {
                        Console.WriteLine($"  Validation failed for message {messageCount}");
                        return (false, messageCount);
                    }
                }
                else if (expected.Type == MessageType.BasicTypes)
                {
                    var msg = BasicTypesMessage.Unpack(result.MsgData);
                    if (!ValidateBasicTypesMessage(msg, expected.Data))
                    {
                        Console.WriteLine($"  Validation failed for message {messageCount}");
                        return (false, messageCount);
                    }
                }
                else if (expected.Type == MessageType.UnionTest)
                {
                    var msg = UnionTestMessage.Unpack(result.MsgData);
                    // Just verify it decoded without error
                }

                messageCount++;
            }

            if (messageCount != StandardTestData.MESSAGE_COUNT)
            {
                Console.WriteLine($"  Expected {StandardTestData.MESSAGE_COUNT} messages, but decoded {messageCount}");
                return (false, messageCount);
            }

            if (reader.Remaining != 0)
            {
                Console.WriteLine($"  Extra data after messages: {reader.Remaining} bytes remaining");
                return (false, messageCount);
            }

            return (true, messageCount);
        }

        public static (bool success, int messageCount) DecodeExtendedMessages(string formatName, byte[] data)
        {
            var reader = CreateReader(formatName, data);
            int messageCount = 0;

            while (reader.HasMore() && messageCount < ExtendedTestData.MESSAGE_COUNT)
            {
                var result = reader.Next();
                if (!result.Valid)
                {
                    Console.WriteLine($"  Decoding failed for message {messageCount}");
                    return (false, messageCount);
                }

                var (expectedMsg, typeName) = ExtendedTestData.GetExtendedTestMessage(messageCount);
                int expectedMsgId = expectedMsg.MsgId;

                // For extended profiles, combine pkg_id and msg_id
                int decodedMsgId = (result.PackageId << 8) | result.MsgId;

                if (decodedMsgId != expectedMsgId)
                {
                    Console.WriteLine($"  Message ID mismatch for message {messageCount}: expected {expectedMsgId}, got {decodedMsgId}");
                    return (false, messageCount);
                }

                // Just verify it decodes without error
                var msg = expectedMsg.GetType().GetMethod("Unpack").Invoke(null, new object[] { result.MsgData });

                messageCount++;
            }

            if (messageCount != ExtendedTestData.MESSAGE_COUNT)
            {
                Console.WriteLine($"  Expected {ExtendedTestData.MESSAGE_COUNT} messages, but decoded {messageCount}");
                return (false, messageCount);
            }

            if (reader.Remaining != 0)
            {
                Console.WriteLine($"  Extra data after messages: {reader.Remaining} bytes remaining");
                return (false, messageCount);
            }

            return (true, messageCount);
        }

        // ============================================================================
        // Frame format helpers (BufferWriter/BufferReader)
        // ============================================================================

        // Placeholder implementations - these would need to be implemented based on the C# frame profiles
        private static dynamic CreateWriter(string formatName, int capacity)
        {
            // This would use the appropriate profile writer based on formatName
            throw new NotImplementedException("CreateWriter needs to be implemented with C# frame profiles");
        }

        private static dynamic CreateReader(string formatName, byte[] data)
        {
            // This would use the appropriate profile reader based on formatName
            throw new NotImplementedException("CreateReader needs to be implemented with C# frame profiles");
        }

        // ============================================================================
        // Test runner main
        // ============================================================================

        public static int RunEncode<TConfig>(
            string formatName,
            string outputFile,
            Func<string, byte[]> encodeFunc)
        {
            Console.WriteLine($"[ENCODE] Format: {formatName}");

            byte[] encodedData;
            try
            {
                encodedData = encodeFunc(formatName);
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

        public static int RunDecode<TConfig>(
            string formatName,
            string inputFile,
            Func<string, byte[], (bool, int)> decodeFunc)
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

            (bool success, int messageCount) result;
            try
            {
                result = decodeFunc(formatName, data);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[DECODE] FAILED: Decoding error - {e.Message}");
                PrintHex(data);
                return 1;
            }

            if (!result.success)
            {
                Console.WriteLine("[DECODE] FAILED: Validation error");
                PrintHex(data);
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: {result.messageCount} messages validated correctly");
            return 0;
        }

        public static int RunTestMain<TConfig>(
            string[] args,
            Func<string, bool> supportsFormat,
            string formatsHelp,
            string testName,
            Func<string, byte[]> encodeFunc,
            Func<string, byte[], (bool, int)> decodeFunc)
        {
            if (args.Length < 3)
            {
                PrintUsage(formatsHelp);
                return 1;
            }

            string mode = args[0].ToLower();
            string formatName = args[1];
            string filePath = args[2];

            // Validate format
            if (!supportsFormat(formatName))
            {
                Console.WriteLine($"Error: Unsupported format '{formatName}' for {testName} tests");
                Console.WriteLine($"Supported formats: {formatsHelp}");
                return 1;
            }

            Console.WriteLine($"\n[TEST START] C# {formatName} {mode} ({testName})");

            int result;
            if (mode == "encode")
            {
                result = RunEncode<TConfig>(formatName, filePath, encodeFunc);
            }
            else if (mode == "decode")
            {
                result = RunDecode<TConfig>(formatName, filePath, decodeFunc);
            }
            else
            {
                Console.WriteLine($"Unknown mode: {mode}");
                PrintUsage(formatsHelp);
                result = 1;
            }

            string status = result == 0 ? "PASS" : "FAIL";
            Console.WriteLine($"[TEST END] C# {formatName} {mode}: {status}\n");

            return result;
        }
    }
}
