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
using ExtendedMessageDefinitions = StructFrame.ExtendedTest.MessageDefinitions;

// Type aliases to match expected names
using Message = StructFrame.SerializationTest.SerializationTestMessage;
using SerializationTestMessage = StructFrame.SerializationTest.SerializationTestSerializationTestMessage;
using BasicTypesMessage = StructFrame.SerializationTest.SerializationTestBasicTypesMessage;
using UnionTestMessage = StructFrame.SerializationTest.SerializationTestUnionTestMessage;
using ComprehensiveArrayMessage = StructFrame.SerializationTest.SerializationTestComprehensiveArrayMessage;
using VariableSingleArrayMessage = StructFrame.SerializationTest.SerializationTestVariableSingleArray;
using Sensor = StructFrame.SerializationTest.SerializationTestSensor;
using SerializationTestStatus = StructFrame.SerializationTest.SerializationTestStatus;

namespace StructFrameTests
{
    public static class TestCodec
    {
        // ============================================================================
        // Utility functions
        // ============================================================================

        /// <summary>
        /// Extract the message payload from FrameMsgInfo
        /// </summary>
        private static byte[] ExtractPayload(FrameMsgInfo info)
        {
            if (!info.Valid || info.MsgData == null)
                return null;

            byte[] payload = new byte[info.MsgLen];
            Array.Copy(info.MsgData, info.MsgDataOffset, payload, 0, info.MsgLen);
            return payload;
        }

        /// <summary>
        /// Generic field validation with automatic error reporting
        /// </summary>
        private static bool ValidateField<T>(T actual, T expected, string fieldName)
        {
            if (!EqualityComparer<T>.Default.Equals(actual, expected))
            {
                Console.WriteLine($"  {fieldName} mismatch: expected {expected}, got {actual}");
                return false;
            }
            return true;
        }

        /// <summary>
        /// Validate float with tolerance
        /// </summary>
        private static bool ValidateFloatField(float actual, float expected, string fieldName, float? tolerance = null)
        {
            float tol = tolerance ?? Math.Max(Math.Abs(expected) * 1e-4f, 1e-4f);
            if (Math.Abs(actual - expected) > tol)
            {
                Console.WriteLine($"  {fieldName} mismatch: expected {expected}, got {actual}");
                return false;
            }
            return true;
        }

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
            var msg = new SerializationTestMessage();
            msg.MagicNumber = (uint)data["magic_number"];
            msg.TestFloat = (float)data["test_float"];
            msg.TestBool = (bool)data["test_bool"];

            // Handle variable-length string
            string testString = (string)data["test_string"];
            var stringBytes = Encoding.UTF8.GetBytes(testString);
            msg.TestStringLength = (byte)Math.Min(stringBytes.Length, 64);
            msg.TestStringData = new byte[64];
            Array.Copy(stringBytes, msg.TestStringData, msg.TestStringLength);

            // Handle variable-length array
            var testArray = (List<int>)data["test_array"];
            msg.TestArrayCount = (byte)Math.Min(testArray.Count, 5);
            msg.TestArrayData = new int[5];
            for (int i = 0; i < msg.TestArrayCount; i++)
            {
                msg.TestArrayData[i] = testArray[i];
            }

            return msg;
        }

        private static BasicTypesMessage CreateBasicTypesMessage(Dictionary<string, object> data)
        {
            var msg = new BasicTypesMessage();
            msg.SmallInt = (sbyte)data["small_int"];
            msg.MediumInt = (short)data["medium_int"];
            msg.RegularInt = (int)data["regular_int"];
            msg.LargeInt = (long)data["large_int"];
            msg.SmallUint = (byte)data["small_uint"];
            msg.MediumUint = (ushort)data["medium_uint"];
            msg.RegularUint = (uint)data["regular_uint"];
            msg.LargeUint = (ulong)data["large_uint"];
            msg.SinglePrecision = (float)data["single_precision"];
            msg.DoublePrecision = (double)data["double_precision"];
            msg.Flag = (bool)data["flag"];

            // Handle fixed string (device_id)
            string deviceId = (string)data["device_id"];
            var deviceIdBytes = Encoding.UTF8.GetBytes(deviceId);
            msg.DeviceId = new byte[32];
            Array.Copy(deviceIdBytes, msg.DeviceId, Math.Min(deviceIdBytes.Length, 32));

            // Handle variable string (description)
            string description = (string)data["description"];
            var descBytes = Encoding.UTF8.GetBytes(description);
            msg.DescriptionLength = (byte)Math.Min(descBytes.Length, 128);
            msg.DescriptionData = new byte[128];
            Array.Copy(descBytes, msg.DescriptionData, msg.DescriptionLength);

            return msg;
        }

        private static UnionTestMessage CreateUnionTestMessage(Dictionary<string, object> data)
        {
            var msg = new UnionTestMessage();
            int payloadType = (int)data["payload_type"];
            
            if (payloadType == 1 && data.ContainsKey("array_payload"))
            {
                // Create union with array_payload (matches C++ create_union_with_array)
                var arrayData = (Dictionary<string, object>)data["array_payload"];
                msg.PayloadDiscriminator = ComprehensiveArrayMessage.MsgId;
                msg.ArrayPayload = CreateComprehensiveArrayMessage(arrayData);
            }
            else if (payloadType == 2 && data.ContainsKey("test_payload"))
            {
                // Create union with test_payload (matches C++ create_union_with_test)
                var testData = (Dictionary<string, object>)data["test_payload"];
                msg.PayloadDiscriminator = SerializationTestMessage.MsgId;
                msg.TestPayload = CreateSerializationTestMessage(testData);
            }
            
            return msg;
        }

        private static ComprehensiveArrayMessage CreateComprehensiveArrayMessage(Dictionary<string, object> data)
        {
            var msg = new ComprehensiveArrayMessage();
            
            // Fixed arrays of primitives
            var fixedInts = (List<int>)data["fixed_ints"];
            msg.FixedInts = fixedInts.ToArray();
            
            var fixedFloats = (List<float>)data["fixed_floats"];
            msg.FixedFloats = fixedFloats.ToArray();
            
            var fixedBools = (List<bool>)data["fixed_bools"];
            msg.FixedBools = fixedBools.ToArray();
            
            // Bounded arrays of primitives
            var boundedUints = (List<ushort>)data["bounded_uints"];
            msg.BoundedUintsCount = (byte)boundedUints.Count;
            msg.BoundedUintsData = new ushort[3];
            for (int i = 0; i < boundedUints.Count && i < 3; i++)
                msg.BoundedUintsData[i] = boundedUints[i];
            
            var boundedDoubles = (List<double>)data["bounded_doubles"];
            msg.BoundedDoublesCount = (byte)boundedDoubles.Count;
            msg.BoundedDoublesData = new double[2];
            for (int i = 0; i < boundedDoubles.Count && i < 2; i++)
                msg.BoundedDoublesData[i] = boundedDoubles[i];
            
            // Fixed string arrays (2 strings, each max 8 chars)
            var fixedStrings = (List<string>)data["fixed_strings"];
            msg.FixedStrings = new byte[16];
            for (int i = 0; i < Math.Min(fixedStrings.Count, 2); i++)
            {
                var strBytes = Encoding.UTF8.GetBytes(fixedStrings[i]);
                Array.Copy(strBytes, 0, msg.FixedStrings, i * 8, Math.Min(strBytes.Length, 8));
            }
            
            // Bounded string arrays (up to 2 strings, each max 12 chars)
            var boundedStrings = (List<string>)data["bounded_strings"];
            msg.BoundedStringsCount = (byte)boundedStrings.Count;
            msg.BoundedStringsData = new byte[24];
            for (int i = 0; i < Math.Min(boundedStrings.Count, 2); i++)
            {
                var strBytes = Encoding.UTF8.GetBytes(boundedStrings[i]);
                Array.Copy(strBytes, 0, msg.BoundedStringsData, i * 12, Math.Min(strBytes.Length, 12));
            }
            
            // Enum arrays
            var fixedStatuses = (List<byte>)data["fixed_statuses"];
            msg.FixedStatuses = fixedStatuses.ToArray();
            
            var boundedStatuses = (List<byte>)data["bounded_statuses"];
            msg.BoundedStatusesCount = (byte)boundedStatuses.Count;
            msg.BoundedStatusesData = new byte[2];
            for (int i = 0; i < Math.Min(boundedStatuses.Count, 2); i++)
                msg.BoundedStatusesData[i] = boundedStatuses[i];
            
            // Fixed sensors (1 element)
            var fixedSensors = (List<Dictionary<string, object>>)data["fixed_sensors"];
            msg.FixedSensors = new Sensor[1];
            for (int i = 0; i < Math.Min(fixedSensors.Count, 1); i++)
            {
                msg.FixedSensors[i] = CreateSensor(fixedSensors[i]);
            }
            
            // Bounded sensors (up to 1 element)
            var boundedSensors = (List<Dictionary<string, object>>)data["bounded_sensors"];
            msg.BoundedSensorsCount = (byte)boundedSensors.Count;
            msg.BoundedSensorsData = new Sensor[1];
            for (int i = 0; i < Math.Min(boundedSensors.Count, 1); i++)
            {
                msg.BoundedSensorsData[i] = CreateSensor(boundedSensors[i]);
            }
            
            return msg;
        }

        private static Sensor CreateSensor(Dictionary<string, object> data)
        {
            var sensor = new Sensor();
            sensor.Id = (byte)(ushort)data["id"];
            sensor.Value = (float)data["value"];
            sensor.Status = (SerializationTestStatus)(byte)data["status"];
            
            string name = (string)data["name"];
            var nameBytes = Encoding.UTF8.GetBytes(name);
            sensor.Name = new byte[16];
            Array.Copy(nameBytes, sensor.Name, Math.Min(nameBytes.Length, 16));
            
            return sensor;
        }

        private static VariableSingleArrayMessage CreateVariableSingleArrayMessage(Dictionary<string, object> data)
        {
            var msg = new VariableSingleArrayMessage();
            msg.MessageId = (uint)data["message_id"];
            
            var payloadData = (byte[])data["payload"];
            msg.PayloadCount = (byte)payloadData.Length;
            msg.PayloadData = new byte[200];
            Array.Copy(payloadData, msg.PayloadData, payloadData.Length);
            
            msg.Checksum = (ushort)data["checksum"];
            return msg;
        }

        private static Message CreateMessage(Dictionary<string, object> data)
        {
            var msg = new Message();
            msg.Severity = (SerializationTestMsgSeverity)Convert.ToByte(data["severity"]);
            var module = (string)data["module"];
            msg.ModuleLength = (byte)module.Length;
            msg.ModuleData = Encoding.UTF8.GetBytes(module);
            var msgText = (string)data["msg"];
            msg.MsgLength = (byte)msgText.Length;
            msg.MsgData = Encoding.UTF8.GetBytes(msgText);
            return msg;
        }

        private static byte[] EncodeMessage(IStructFrameMessage msg) => msg.Serialize();

        private static int GetMessageId(IStructFrameMessage msg) => msg.GetMsgId();

        private static (byte magic1, byte magic2) GetMessageMagicNumbers(IStructFrameMessage msg) => msg.GetMagicNumbers();

        // ============================================================================
        // Generic encoding/decoding (unified logic)
        // ============================================================================

        /// <summary>
        /// Generic message encoding for any test data source
        /// </summary>
        /// <param name="formatName">Frame format profile name</param>
        /// <param name="messageCount">Total number of messages to encode</param>
        /// <param name="bufferSize">Buffer size for encoded data</param>
        /// <param name="getMessage">Delegate to get IStructFrameMessage for each index</param>
        public static byte[] EncodeMessages<T>(
            string formatName,
            int messageCount,
            int bufferSize,
            Func<int, T> getMessage) where T : struct, IStructFrameMessage
        {
            var writer = Profiles.CreateWriter(formatName);
            writer.SetBuffer(new byte[bufferSize]);

            for (int i = 0; i < messageCount; i++)
            {
                T msg = getMessage(i);
                int bytesWritten = writer.Write(msg);
                if (bytesWritten == 0)
                    throw new Exception($"Failed to encode message {i}");
            }

            return writer.GetData();
        }

        /// <summary>
        /// Generic message decoding and validation for any test data source
        /// </summary>
        /// <param name="formatName">Frame format profile name</param>
        /// <param name="data">Encoded data buffer</param>
        /// <param name="expectedCount">Expected number of messages</param>
        /// <param name="getMessageInfo">Delegate to get message info from ID</param>
        /// <param name="validateMessage">Delegate to validate message at index, returns (expectedMsgId, isValid)</param>
        /// <param name="usePkgId">Whether to combine pkg_id with msg_id</param>
        public static (bool success, int messageCount) DecodeMessages(
            string formatName,
            byte[] data,
            int expectedCount,
            Func<int, MessageInfo?> getMessageInfo,
            Func<int, FrameMsgInfo, (int expectedMsgId, bool isValid)> validateMessage,
            bool usePkgId = false)
        {
            var reader = Profiles.CreateReader(formatName, getMessageInfo);
            reader.SetBuffer(data);
            int messageCount = 0;

            while (reader.HasMore && messageCount < expectedCount)
            {
                var result = reader.Next();
                if (!result.Valid)
                {
                    Console.WriteLine($"  Decoding failed for message {messageCount}");
                    return (false, messageCount);
                }

                var (expectedMsgId, isValid) = validateMessage(messageCount, result);

                // Get decoded message ID (handle extended profiles with pkg_id)
                int decodedMsgId = usePkgId ? (result.PkgId << 8) | result.MsgId : result.MsgId;

                if (decodedMsgId != expectedMsgId)
                {
                    Console.WriteLine($"  Message ID mismatch for message {messageCount}: expected {expectedMsgId}, got {decodedMsgId}");
                    return (false, messageCount);
                }

                if (!isValid)
                {
                    Console.WriteLine($"  Validation failed for message {messageCount}");
                    return (false, messageCount);
                }

                messageCount++;
            }

            if (messageCount != expectedCount)
            {
                Console.WriteLine($"  Expected {expectedCount} messages, but decoded {messageCount}");
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
        // Encoding functions (using generic implementation)
        // ============================================================================

        public static byte[] EncodeStandardMessages(string formatName)
        {
            // Create a generic encoder that handles dynamic message types
            var writer = Profiles.CreateWriter(formatName);
            writer.SetBuffer(new byte[4096]);

            for (int i = 0; i < StandardTestData.MESSAGE_COUNT; i++)
            {
                var mixedMsg = StandardTestData.GetTestMessage(i);
                int bytesWritten = 0;

                if (mixedMsg.Type == MessageType.SerializationTest)
                {
                    var msg = CreateSerializationTestMessage(mixedMsg.Data);
                    bytesWritten = writer.Write(msg);
                }
                else if (mixedMsg.Type == MessageType.BasicTypes)
                {
                    var msg = CreateBasicTypesMessage(mixedMsg.Data);
                    bytesWritten = writer.Write(msg);
                }
                else if (mixedMsg.Type == MessageType.UnionTest)
                {
                    var msg = CreateUnionTestMessage(mixedMsg.Data);
                    bytesWritten = writer.Write(msg);
                }
                else if (mixedMsg.Type == MessageType.VariableSingleArray)
                {
                    var msg = CreateVariableSingleArrayMessage(mixedMsg.Data);
                    bytesWritten = writer.Write(msg);
                }
                else if (mixedMsg.Type == MessageType.Message)
                {
                    var msg = CreateMessage(mixedMsg.Data);
                    bytesWritten = writer.Write(msg);
                }
                else
                {
                    throw new Exception($"Unknown message type: {mixedMsg.Type}");
                }

                if (bytesWritten == 0)
                    throw new Exception($"Failed to encode message {i}");
            }

            return writer.GetData();
        }

        public static byte[] EncodeExtendedMessages(string formatName)
        {
            var writer = Profiles.CreateWriter(formatName);
            writer.SetBuffer(new byte[8192]);

            for (int i = 0; i < ExtendedTestData.MESSAGE_COUNT; i++)
            {
                var (msg, _) = ExtendedTestData.GetExtendedTestMessage(i);
                if (msg == null)
                    throw new Exception($"Failed to get extended message {i}");
                
                int bytesWritten = writer.Write(msg);
                if (bytesWritten == 0)
                    throw new Exception($"Failed to encode message {i}");
            }

            return writer.GetData();
        }

        public static byte[] EncodeVariableFlagMessages(string formatName)
        {
            var writer = Profiles.CreateWriter(formatName);
            writer.SetBuffer(new byte[4096]);

            for (int i = 0; i < VariableFlagTestData.MESSAGE_COUNT; i++)
            {
                var mixedMsg = VariableFlagTestData.GetTestMessage(i);
                if (mixedMsg == null)
                    throw new Exception($"Failed to get variable flag message {i}");
                
                IStructFrameMessage msg;
                int payloadSize;
                string msgName;
                
                if (mixedMsg.Type == VariableMessageType.NonVariable)
                {
                    msg = CreateTruncationTestNonVariable(mixedMsg.Data);
                    payloadSize = msg.GetSize();
                    msgName = "MSG1";
                }
                else
                {
                    msg = CreateTruncationTestVariable(mixedMsg.Data);
                    payloadSize = msg.GetSize();
                    msgName = "MSG2";
                }
                
                int bytesWritten = writer.Write(msg);
                if (bytesWritten == 0)
                    throw new Exception($"Failed to encode message {i}");
                
                string truncationNote = mixedMsg.Type == VariableMessageType.Variable ? "TRUNCATED" : "no truncation";
                Console.WriteLine($"{msgName}: {bytesWritten} bytes (payload={payloadSize}, {truncationNote})");
            }

            Console.WriteLine($"Total: {writer.Size} bytes");
            return writer.GetData();
        }

        private static StructFrame.SerializationTest.SerializationTestTruncationTestNonVariable CreateTruncationTestNonVariable(Dictionary<string, object> data)
        {
            var msg = new StructFrame.SerializationTest.SerializationTestTruncationTestNonVariable();
            msg.SequenceId = (uint)data["sequence_id"];
            var dataArray = (List<byte>)data["data_array"];
            msg.DataArrayCount = (byte)dataArray.Count;
            msg.DataArrayData = dataArray.ToArray();
            msg.Footer = (ushort)data["footer"];
            return msg;
        }

        private static StructFrame.SerializationTest.SerializationTestTruncationTestVariable CreateTruncationTestVariable(Dictionary<string, object> data)
        {
            var msg = new StructFrame.SerializationTest.SerializationTestTruncationTestVariable();
            msg.SequenceId = (uint)data["sequence_id"];
            var dataArray = (List<byte>)data["data_array"];
            msg.DataArrayCount = (byte)dataArray.Count;
            msg.DataArrayData = dataArray.ToArray();
            msg.Footer = (ushort)data["footer"];
            return msg;
        }

        // ============================================================================
        // Decoding functions (using generic implementation)
        // ============================================================================

        private static MessageInfo? GetStandardMessageInfo(int msgId)
        {
            return MessageDefinitions.GetMessageInfo(msgId);
        }

        private static MessageInfo? GetExtendedMessageInfo(int msgId)
        {
            return ExtendedTestData.GetMessageInfo(msgId);
        }

        private static bool ValidateSerializationTestMessage(SerializationTestMessage msg, Dictionary<string, object> expected)
        {
            if (!ValidateField(msg.MagicNumber, (uint)expected["magic_number"], "magic_number"))
                return false;

            // Get string from length + data fields
            string testString = Encoding.UTF8.GetString(msg.TestStringData, 0, msg.TestStringLength);
            string expectedString = (string)expected["test_string"];
            if (!ValidateField(testString, expectedString, "test_string"))
                return false;

            if (!ValidateFloatField(msg.TestFloat, (float)expected["test_float"], "test_float"))
                return false;

            if (!ValidateField(msg.TestBool, (bool)expected["test_bool"], "test_bool"))
                return false;

            var expectedArray = (List<int>)expected["test_array"];
            if (!ValidateField(msg.TestArrayCount, (byte)expectedArray.Count, "test_array count"))
                return false;

            for (int i = 0; i < expectedArray.Count; i++)
            {
                if (!ValidateField(msg.TestArrayData[i], expectedArray[i], $"test_array[{i}]"))
                    return false;
            }

            return true;
        }

        private static bool ValidateBasicTypesMessage(BasicTypesMessage msg, Dictionary<string, object> expected)
        {
            return ValidateField(msg.SmallInt, (sbyte)expected["small_int"], "small_int")
                && ValidateField(msg.MediumInt, (short)expected["medium_int"], "medium_int")
                && ValidateField(msg.RegularInt, (int)expected["regular_int"], "regular_int")
                && ValidateField(msg.LargeInt, (long)expected["large_int"], "large_int")
                && ValidateField(msg.SmallUint, (byte)expected["small_uint"], "small_uint")
                && ValidateField(msg.MediumUint, (ushort)expected["medium_uint"], "medium_uint")
                && ValidateField(msg.RegularUint, (uint)expected["regular_uint"], "regular_uint")
                && ValidateField(msg.LargeUint, (ulong)expected["large_uint"], "large_uint")
                && ValidateField(msg.Flag, (bool)expected["flag"], "flag");
        }

        private static bool ValidateUnionTestMessage(FrameMsgInfo frameInfo, Dictionary<string, object> expected)
        {
            // Extract payload from FrameMsgInfo
            byte[] decodedPayload = new byte[frameInfo.MsgLen];
            Array.Copy(frameInfo.MsgData, frameInfo.MsgDataOffset, decodedPayload, 0, frameInfo.MsgLen);
            
            // Create expected message and compare packed bytes
            var expectedMsg = CreateUnionTestMessage(expected);
            var expectedBytes = expectedMsg.Serialize();
            
            if (decodedPayload.Length != expectedBytes.Length)
            {
                Console.WriteLine($"  UnionTest size mismatch: expected {expectedBytes.Length}, got {decodedPayload.Length}");
                return false;
            }
            
            for (int i = 0; i < expectedBytes.Length; i++)
            {
                if (decodedPayload[i] != expectedBytes[i])
                {
                    Console.WriteLine($"  UnionTest byte {i} mismatch: expected {expectedBytes[i]:X2}, got {decodedPayload[i]:X2}");
                    return false;
                }
            }
            
            return true;
        }

        private static bool ValidateVariableSingleArrayMessage(VariableSingleArrayMessage msg, Dictionary<string, object> expected)
        {
            if (!ValidateField(msg.MessageId, (uint)expected["message_id"], "message_id"))
                return false;

            var expectedPayload = (byte[])expected["payload"];
            if (!ValidateField(msg.PayloadCount, (byte)expectedPayload.Length, "payload_count"))
                return false;

            for (int i = 0; i < expectedPayload.Length; i++)
            {
                if (!ValidateField(msg.PayloadData[i], expectedPayload[i], $"payload_data[{i}]"))
                    return false;
            }

            if (!ValidateField(msg.Checksum, (ushort)expected["checksum"], "checksum"))
                return false;

            return true;
        }

        private static bool ValidateMessage(Message msg, Dictionary<string, object> expected)
        {
            if (!ValidateField((byte)msg.Severity, Convert.ToByte(expected["severity"]), "severity"))
                return false;

            var expectedModule = (string)expected["module"];
            if (!ValidateField(msg.ModuleLength, (byte)expectedModule.Length, "module_length"))
                return false;
            var actualModule = Encoding.UTF8.GetString(msg.ModuleData, 0, msg.ModuleLength);
            if (!ValidateField(actualModule, expectedModule, "module"))
                return false;

            var expectedMsg = (string)expected["msg"];
            if (!ValidateField(msg.MsgLength, (byte)expectedMsg.Length, "msg_length"))
                return false;
            var actualMsg = Encoding.UTF8.GetString(msg.MsgData, 0, msg.MsgLength);
            if (!ValidateField(actualMsg, expectedMsg, "msg"))
                return false;

            return true;
        }

        public static (bool success, int messageCount) DecodeStandardMessages(string formatName, byte[] data)
        {
            return DecodeMessages(
                formatName,
                data,
                StandardTestData.MESSAGE_COUNT,
                GetStandardMessageInfo,
                (i, result) =>
                {
                    var expected = StandardTestData.GetTestMessage(i);
                    int expectedMsgId;
                    bool isValid = true;

                    if (expected.Type == MessageType.SerializationTest)
                    {
                        expectedMsgId = SerializationTestMessage.MsgId;
                        var msg = SerializationTestMessage.Deserialize(result);
                        isValid = ValidateSerializationTestMessage(msg, expected.Data);
                    }
                    else if (expected.Type == MessageType.BasicTypes)
                    {
                        expectedMsgId = BasicTypesMessage.MsgId;
                        var msg = BasicTypesMessage.Deserialize(result);
                        isValid = ValidateBasicTypesMessage(msg, expected.Data);
                    }
                    else if (expected.Type == MessageType.UnionTest)
                    {
                        expectedMsgId = UnionTestMessage.MsgId;
                        isValid = ValidateUnionTestMessage(result, expected.Data);
                    }
                    else if (expected.Type == MessageType.VariableSingleArray)
                    {
                        expectedMsgId = VariableSingleArrayMessage.MsgId;
                        var msg = VariableSingleArrayMessage.Deserialize(result);
                        isValid = ValidateVariableSingleArrayMessage(msg, expected.Data);
                    }
                    else if (expected.Type == MessageType.Message)
                    {
                        expectedMsgId = Message.MsgId;
                        var msg = Message.Deserialize(result);
                        isValid = ValidateMessage(msg, expected.Data);
                    }
                    else
                    {
                        throw new Exception($"Unknown message type: {expected.Type}");
                    }

                    return (expectedMsgId, isValid);
                },
                usePkgId: false);
        }

        public static (bool success, int messageCount) DecodeVariableFlagMessages(string formatName, byte[] data)
        {
            return DecodeMessages(
                formatName,
                data,
                VariableFlagTestData.MESSAGE_COUNT,
                GetStandardMessageInfo,
                (i, result) =>
                {
                    var expected = VariableFlagTestData.GetTestMessage(i);
                    int expectedMsgId;
                    bool isValid = true;

                    if (expected.Type == VariableMessageType.NonVariable)
                    {
                        expectedMsgId = StructFrame.SerializationTest.SerializationTestTruncationTestNonVariable.MsgId;
                        var msg = StructFrame.SerializationTest.SerializationTestTruncationTestNonVariable.Deserialize(result);
                        isValid = ValidateTruncationTestNonVariable(msg, expected.Data);
                    }
                    else if (expected.Type == VariableMessageType.Variable)
                    {
                        expectedMsgId = StructFrame.SerializationTest.SerializationTestTruncationTestVariable.MsgId;
                        var msg = StructFrame.SerializationTest.SerializationTestTruncationTestVariable.Deserialize(result);
                        isValid = ValidateTruncationTestVariable(msg, expected.Data);
                    }
                    else
                    {
                        throw new Exception($"Unknown variable message type: {expected.Type}");
                    }

                    return (expectedMsgId, isValid);
                },
                usePkgId: false);
        }

        private static bool ValidateTruncationTestNonVariable(StructFrame.SerializationTest.SerializationTestTruncationTestNonVariable msg, Dictionary<string, object> expected)
        {
            if (!ValidateField(msg.SequenceId, (uint)expected["sequence_id"], "sequence_id"))
                return false;

            var expectedArray = (List<byte>)expected["data_array"];
            if (!ValidateField(msg.DataArrayCount, (byte)expectedArray.Count, "data_array count"))
                return false;

            for (int i = 0; i < expectedArray.Count; i++)
            {
                if (!ValidateField(msg.DataArrayData[i], expectedArray[i], $"data_array[{i}]"))
                    return false;
            }

            if (!ValidateField(msg.Footer, (ushort)expected["footer"], "footer"))
                return false;

            return true;
        }

        private static bool ValidateTruncationTestVariable(StructFrame.SerializationTest.SerializationTestTruncationTestVariable msg, Dictionary<string, object> expected)
        {
            if (!ValidateField(msg.SequenceId, (uint)expected["sequence_id"], "sequence_id"))
                return false;

            var expectedArray = (List<byte>)expected["data_array"];
            if (!ValidateField(msg.DataArrayCount, (byte)expectedArray.Count, "data_array count"))
                return false;

            for (int i = 0; i < expectedArray.Count; i++)
            {
                if (!ValidateField(msg.DataArrayData[i], expectedArray[i], $"data_array[{i}]"))
                    return false;
            }

            if (!ValidateField(msg.Footer, (ushort)expected["footer"], "footer"))
                return false;

            return true;
        }

        public static (bool success, int messageCount) DecodeExtendedMessages(string formatName, byte[] data)
        {
            return DecodeMessages(
                formatName,
                data,
                ExtendedTestData.MESSAGE_COUNT,
                GetExtendedMessageInfo,
                (i, result) =>
                {
                    var (expectedMsg, _) = ExtendedTestData.GetExtendedTestMessage(i);
                    if (expectedMsg == null) return (0, false);
                    
                    // Extract the actual payload from the result
                    var decodedPayload = ExtractPayload(result);
                    if (decodedPayload == null)
                    {
                        Console.WriteLine($"    Failed to extract payload for message {i}");
                        return (expectedMsg.GetMsgId(), false);
                    }
                    
                    // Get expected data
                    // For variable messages: Pack() returns variable encoding, PackMaxSize() returns MAX_SIZE
                    // Check if we received MAX_SIZE or variable encoding
                    byte[] expectedData;
                    var msgType = expectedMsg.GetType();
                    var maxSizeField = msgType.GetField("MaxSize", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                    int maxSize = maxSizeField != null ? (int)maxSizeField.GetValue(null) : expectedMsg.GetSize();
                    
                    if (decodedPayload.Length == maxSize)
                    {
                        // Received MAX_SIZE format (minimal profiles or non-variable messages)
                        var packMaxSizeMethod = msgType.GetMethod("PackMaxSize", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                        if (packMaxSizeMethod != null)
                        {
                            // Variable message with MAX_SIZE encoding
                            expectedData = (byte[])packMaxSizeMethod.Invoke(expectedMsg, null);
                        }
                        else
                        {
                            // Non-variable message
                            expectedData = expectedMsg.Serialize();
                        }
                    }
                    else
                    {
                        // Received variable-length format - Pack() returns this for variable messages
                        expectedData = expectedMsg.Serialize();
                    }
                    
                    if (decodedPayload.Length != expectedData.Length)
                    {
                        Console.WriteLine($"    Size mismatch: expected {expectedData.Length}, got {decodedPayload.Length}");
                        return (expectedMsg.GetMsgId(), false);
                    }
                    
                    for (int j = 0; j < expectedData.Length; j++)
                    {
                        if (decodedPayload[j] != expectedData[j])
                        {
                            Console.WriteLine($"    Byte {j} mismatch: expected {expectedData[j]:X2}, got {decodedPayload[j]:X2}");
                            return (expectedMsg.GetMsgId(), false);
                        }
                    }
                    
                    return (expectedMsg.GetMsgId(), true);
                },
                usePkgId: true);
        }

        // ============================================================================
        // Test runner main
        // ============================================================================

        public static int RunEncode(
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

        public static int RunDecode(
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
                Console.WriteLine($"[DECODE] FAILED: {result.messageCount} messages validated before error");
                PrintHex(data);
                return 1;
            }

            Console.WriteLine($"[DECODE] SUCCESS: {result.messageCount} messages validated correctly");
            return 0;
        }

        public static int RunTestMain(
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
                result = RunEncode(formatName, filePath, encodeFunc);
            else if (mode == "decode")
                result = RunDecode(formatName, filePath, decodeFunc);
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
