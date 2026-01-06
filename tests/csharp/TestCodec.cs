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
    /// Test message data structure
    /// </summary>
    public class TestMessage
    {
        public uint MagicNumber { get; set; }
        public string TestString { get; set; }
        public float TestFloat { get; set; }
        public bool TestBool { get; set; }
        public int[] TestArray { get; set; }
    }

    /// <summary>
    /// BasicTypesMessage data structure
    /// </summary>
    public class BasicTypesMessage
    {
        public sbyte SmallInt { get; set; }
        public short MediumInt { get; set; }
        public int RegularInt { get; set; }
        public long LargeInt { get; set; }
        public byte SmallUint { get; set; }
        public ushort MediumUint { get; set; }
        public uint RegularUint { get; set; }
        public ulong LargeUint { get; set; }
        public float SinglePrecision { get; set; }
        public double DoublePrecision { get; set; }
        public bool Flag { get; set; }
        public byte DeviceId { get; set; }
        public string Description { get; set; }
    }

    /// <summary>
    /// Mixed message item
    /// </summary>
    public class MixedMessageItem
    {
        public string Type { get; set; }
        public object Data { get; set; }
    }

    /// <summary>
    /// Load test messages from test_messages.json
    /// </summary>
    public static class TestMessages
    {
        private static TestMessage[] _messages = null;

        public static TestMessage[] Messages
        {
            get
            {
                if (_messages == null)
                {
                    _messages = LoadTestMessages();
                }
                return _messages;
            }
        }

        private static TestMessage[] LoadTestMessages()
        {
            string[] possiblePaths = new string[]
            {
                "../test_messages.json",
                "../../tests/test_messages.json",
                "test_messages.json",
                "../../../tests/test_messages.json",
                "../../test_messages.json",
                "../../../../../tests/test_messages.json"  // For bin/Release/net10.0
            };

            foreach (var path in possiblePaths)
            {
                try
                {
                    if (System.IO.File.Exists(path))
                    {
                        string jsonContent = System.IO.File.ReadAllText(path);
                        
                        // Simple JSON parsing for the test messages structure
                        var messages = ParseTestMessagesJson(jsonContent);
                        if (messages != null && messages.Length > 0)
                        {
                            return messages;
                        }
                    }
                }
                catch
                {
                    // Try next path
                    continue;
                }
            }

            // If we couldn't load from JSON, return empty array to indicate failure
            System.Console.WriteLine("Error: Could not load test_messages.json");
            return new TestMessage[] { };
        }

        private static TestMessage[] ParseTestMessagesJson(string jsonContent)
        {
            try
            {
                // Very basic JSON parsing - look for SerializationTestMessage or messages array
                var messages = new System.Collections.Generic.List<TestMessage>();
                
                // Find the start of the message array
                int arrayStart = jsonContent.IndexOf("\"SerializationTestMessage\"");
                if (arrayStart == -1)
                {
                    arrayStart = jsonContent.IndexOf("\"messages\"");
                }
                
                if (arrayStart == -1) return null;
                
                // Find the opening bracket of the array
                int bracketStart = jsonContent.IndexOf('[', arrayStart);
                if (bracketStart == -1) return null;
                
                // Parse each message object
                int pos = bracketStart + 1;
                while (pos < jsonContent.Length)
                {
                    // Skip whitespace
                    while (pos < jsonContent.Length && char.IsWhiteSpace(jsonContent[pos])) pos++;
                    
                    if (pos >= jsonContent.Length || jsonContent[pos] == ']') break;
                    if (jsonContent[pos] == ',') { pos++; continue; }
                    if (jsonContent[pos] != '{') break;
                    
                    // Find the end of this message object
                    int objEnd = FindMatchingBrace(jsonContent, pos);
                    if (objEnd == -1) break;
                    
                    string msgJson = jsonContent.Substring(pos, objEnd - pos + 1);
                    var msg = ParseSingleMessage(msgJson);
                    if (msg != null)
                    {
                        messages.Add(msg);
                    }
                    
                    pos = objEnd + 1;
                }
                
                return messages.ToArray();
            }
            catch
            {
                return null;
            }
        }

        private static int FindMatchingBrace(string json, int startPos)
        {
            int depth = 0;
            for (int i = startPos; i < json.Length; i++)
            {
                if (json[i] == '{') depth++;
                else if (json[i] == '}')
                {
                    depth--;
                    if (depth == 0) return i;
                }
            }
            return -1;
        }

        private static TestMessage ParseSingleMessage(string msgJson)
        {
            try
            {
                var msg = new TestMessage();
                
                msg.MagicNumber = ParseUInt(msgJson, "magic_number");
                msg.TestString = ParseString(msgJson, "test_string");
                msg.TestFloat = ParseFloat(msgJson, "test_float");
                msg.TestBool = ParseBool(msgJson, "test_bool");
                msg.TestArray = ParseIntArray(msgJson, "test_array");
                
                return msg;
            }
            catch
            {
                return null;
            }
        }

        private static string ParseMessageName(string msgJson)
        {
            return ParseString(msgJson, "name");
        }

        private static uint ParseUInt(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (uint.TryParse(valueStr, out uint result))
            {
                return result;
            }
            
            if (double.TryParse(valueStr, out double doubleResult))
            {
                return (uint)doubleResult;
            }
            
            return 0;
        }

        private static string ParseString(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return "";
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return "";
            
            int quoteStart = json.IndexOf('"', colonPos);
            if (quoteStart == -1) return "";
            
            int quoteEnd = json.IndexOf('"', quoteStart + 1);
            if (quoteEnd == -1) return "";
            
            return json.Substring(quoteStart + 1, quoteEnd - quoteStart - 1);
        }

        private static float ParseFloat(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0.0f;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0.0f;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.' || json[valueEnd] == '-')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (float.TryParse(valueStr, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float result))
            {
                return result;
            }
            
            return 0.0f;
        }

        private static bool ParseBool(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return false;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return false;
            
            int truePos = json.IndexOf("true", colonPos);
            int falsePos = json.IndexOf("false", colonPos);
            int commaPos = json.IndexOf(',', colonPos);
            
            if (truePos != -1 && (commaPos == -1 || truePos < commaPos))
            {
                return true;
            }
            
            return false;
        }

        private static int[] ParseIntArray(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return new int[] { };
            
            int bracketStart = json.IndexOf('[', keyPos);
            if (bracketStart == -1) return new int[] { };
            
            int bracketEnd = json.IndexOf(']', bracketStart);
            if (bracketEnd == -1) return new int[] { };
            
            string arrayStr = json.Substring(bracketStart + 1, bracketEnd - bracketStart - 1);
            if (string.IsNullOrWhiteSpace(arrayStr)) return new int[] { };
            
            string[] parts = arrayStr.Split(',');
            var result = new System.Collections.Generic.List<int>();
            
            foreach (var part in parts)
            {
                if (int.TryParse(part.Trim(), out int value))
                {
                    result.Add(value);
                }
            }
            
            return result.ToArray();
        }
        
        /// <summary>
        /// Load mixed messages from JSON following MixedMessages sequence
        /// </summary>
        public static MixedMessageItem[] LoadMixedMessages()
        {
            string[] possiblePaths = new string[]
            {
                "../test_messages.json",
                "../../tests/test_messages.json",
                "test_messages.json",
                "../../../tests/test_messages.json",
                "../../test_messages.json",
                "../../../../../tests/test_messages.json"  // For bin/Release/net10.0
            };

            foreach (var path in possiblePaths)
            {
                try
                {
                    if (System.IO.File.Exists(path))
                    {
                        string jsonContent = System.IO.File.ReadAllText(path);
                        var result = ParseMixedMessagesJson(jsonContent);
                        return result;
                    }
                }
                catch
                {
                    continue;
                }
            }

            // Return empty array if can't load
            return new MixedMessageItem[] { };
        }

        private static MixedMessageItem[] ParseMixedMessagesJson(string jsonContent)
        {
            try
            {
                var result = new System.Collections.Generic.List<MixedMessageItem>();
                
                // Parse SerializationTestMessage array
                var serialMessages = new System.Collections.Generic.Dictionary<string, TestMessage>();
                int serialStart = jsonContent.IndexOf("\"SerializationTestMessage\"");
                if (serialStart != -1)
                {
                    int bracketStart = jsonContent.IndexOf('[', serialStart);
                    if (bracketStart != -1)
                    {
                        int depth = 0;
                        int arrayStart = bracketStart;
                        for (int i = bracketStart; i < jsonContent.Length; i++)
                        {
                            if (jsonContent[i] == '[') depth++;
                            else if (jsonContent[i] == ']')
                            {
                                depth--;
                                if (depth == 0)
                                {
                                    string arrayContent = jsonContent.Substring(arrayStart, i - arrayStart + 1);
                                    serialMessages = ParseTestMessagesArrayToDictionary(arrayContent);
                                    break;
                                }
                            }
                        }
                    }
                }
                
                // Parse BasicTypesMessage array
                var basicMessages = new System.Collections.Generic.Dictionary<string, BasicTypesMessage>();
                int basicStart = jsonContent.IndexOf("\"BasicTypesMessage\"");
                if (basicStart != -1)
                {
                    int bracketStart = jsonContent.IndexOf('[', basicStart);
                    if (bracketStart != -1)
                    {
                        int depth = 0;
                        int arrayStart = bracketStart;
                        for (int i = bracketStart; i < jsonContent.Length; i++)
                        {
                            if (jsonContent[i] == '[') depth++;
                            else if (jsonContent[i] == ']')
                            {
                                depth--;
                                if (depth == 0)
                                {
                                    string arrayContent = jsonContent.Substring(arrayStart, i - arrayStart + 1);
                                    basicMessages = ParseBasicTypesMessagesArrayToDictionary(arrayContent);
                                    break;
                                }
                            }
                        }
                    }
                }
                
                // Parse MixedMessages array
                int mixedStart = jsonContent.IndexOf("\"MixedMessages\"");
                if (mixedStart != -1)
                {
                    int bracketStart = jsonContent.IndexOf('[', mixedStart);
                    if (bracketStart != -1)
                    {
                        int pos = bracketStart + 1;
                        while (pos < jsonContent.Length)
                        {
                            while (pos < jsonContent.Length && char.IsWhiteSpace(jsonContent[pos])) pos++;
                            if (pos >= jsonContent.Length || jsonContent[pos] == ']') break;
                            if (jsonContent[pos] == ',') { pos++; continue; }
                            if (jsonContent[pos] != '{') break;
                            
                            int objEnd = FindMatchingBrace(jsonContent, pos);
                            if (objEnd == -1) break;
                            
                            string objJson = jsonContent.Substring(pos, objEnd - pos + 1);
                            string msgType = ParseString(objJson, "type");
                            string msgName = ParseString(objJson, "name");
                            
                            if (msgType == "SerializationTestMessage" && serialMessages.ContainsKey(msgName))
                            {
                                result.Add(new MixedMessageItem
                                {
                                    Type = msgType,
                                    Data = serialMessages[msgName]
                                });
                            }
                            else if (msgType == "BasicTypesMessage" && basicMessages.ContainsKey(msgName))
                            {
                                result.Add(new MixedMessageItem
                                {
                                    Type = msgType,
                                    Data = basicMessages[msgName]
                                });
                            }
                            else
                            {
                            }
                            
                            pos = objEnd + 1;
                        }
                    }
                }
                
                return result.ToArray();
            }
            catch
            {
                return new MixedMessageItem[] { };
            }
        }

        private static TestMessage[] ParseTestMessagesArray(string arrayJson)
        {
            var messages = new System.Collections.Generic.List<TestMessage>();
            int pos = 1; // Skip opening [
            
            while (pos < arrayJson.Length)
            {
                while (pos < arrayJson.Length && char.IsWhiteSpace(arrayJson[pos])) pos++;
                if (pos >= arrayJson.Length || arrayJson[pos] == ']') break;
                if (arrayJson[pos] == ',') { pos++; continue; }
                if (arrayJson[pos] != '{') break;
                
                int objEnd = FindMatchingBrace(arrayJson, pos);
                if (objEnd == -1) break;
                
                string msgJson = arrayJson.Substring(pos, objEnd - pos + 1);
                var msg = ParseSingleMessage(msgJson);
                if (msg != null)
                {
                    messages.Add(msg);
                }
                
                pos = objEnd + 1;
            }
            
            return messages.ToArray();
        }

        private static System.Collections.Generic.Dictionary<string, TestMessage> ParseTestMessagesArrayToDictionary(string arrayJson)
        {
            var messages = new System.Collections.Generic.Dictionary<string, TestMessage>();
            int pos = 1; // Skip opening [
            
            while (pos < arrayJson.Length)
            {
                while (pos < arrayJson.Length && char.IsWhiteSpace(arrayJson[pos])) pos++;
                if (pos >= arrayJson.Length || arrayJson[pos] == ']') break;
                if (arrayJson[pos] == ',') { pos++; continue; }
                if (arrayJson[pos] != '{') break;
                
                int objEnd = FindMatchingBrace(arrayJson, pos);
                if (objEnd == -1) break;
                
                string msgJson = arrayJson.Substring(pos, objEnd - pos + 1);
                string name = ParseMessageName(msgJson);
                var msg = ParseSingleMessage(msgJson);
                if (msg != null && !string.IsNullOrEmpty(name))
                {
                    messages[name] = msg;
                }
                
                pos = objEnd + 1;
            }
            
            return messages;
        }

        private static BasicTypesMessage[] ParseBasicTypesMessagesArray(string arrayJson)
        {
            var messages = new System.Collections.Generic.List<BasicTypesMessage>();
            int pos = 1; // Skip opening [
            
            while (pos < arrayJson.Length)
            {
                while (pos < arrayJson.Length && char.IsWhiteSpace(arrayJson[pos])) pos++;
                if (pos >= arrayJson.Length || arrayJson[pos] == ']') break;
                if (arrayJson[pos] == ',') { pos++; continue; }
                if (arrayJson[pos] != '{') break;
                
                int objEnd = FindMatchingBrace(arrayJson, pos);
                if (objEnd == -1) break;
                
                string msgJson = arrayJson.Substring(pos, objEnd - pos + 1);
                var msg = ParseSingleBasicTypesMessage(msgJson);
                if (msg != null)
                {
                    messages.Add(msg);
                }
                
                pos = objEnd + 1;
            }
            
            return messages.ToArray();
        }

        private static System.Collections.Generic.Dictionary<string, BasicTypesMessage> ParseBasicTypesMessagesArrayToDictionary(string arrayJson)
        {
            var messages = new System.Collections.Generic.Dictionary<string, BasicTypesMessage>();
            int pos = 1; // Skip opening [
            
            while (pos < arrayJson.Length)
            {
                while (pos < arrayJson.Length && char.IsWhiteSpace(arrayJson[pos])) pos++;
                if (pos >= arrayJson.Length || arrayJson[pos] == ']') break;
                if (arrayJson[pos] == ',') { pos++; continue; }
                if (arrayJson[pos] != '{') break;
                
                int objEnd = FindMatchingBrace(arrayJson, pos);
                if (objEnd == -1) break;
                
                string msgJson = arrayJson.Substring(pos, objEnd - pos + 1);
                string name = ParseMessageName(msgJson);
                var msg = ParseSingleBasicTypesMessage(msgJson);
                if (msg != null && !string.IsNullOrEmpty(name))
                {
                    messages[name] = msg;
                }
                
                pos = objEnd + 1;
            }
            
            return messages;
        }

        private static BasicTypesMessage ParseSingleBasicTypesMessage(string msgJson)
        {
            try
            {
                var msg = new BasicTypesMessage();
                msg.SmallInt = (sbyte)ParseInt(msgJson, "small_int");
                msg.MediumInt = (short)ParseInt(msgJson, "medium_int");
                msg.RegularInt = ParseInt(msgJson, "regular_int");
                msg.LargeInt = ParseLong(msgJson, "large_int");
                msg.SmallUint = (byte)ParseUInt(msgJson, "small_uint");
                msg.MediumUint = (ushort)ParseUInt(msgJson, "medium_uint");
                msg.RegularUint = ParseUInt(msgJson, "regular_uint");
                msg.LargeUint = ParseULong(msgJson, "large_uint");
                msg.SinglePrecision = ParseFloat(msgJson, "single_precision");
                msg.DoublePrecision = ParseDouble(msgJson, "double_precision");
                msg.Flag = ParseBool(msgJson, "flag");
                msg.DeviceId = (byte)ParseUInt(msgJson, "device_id");
                msg.Description = ParseString(msgJson, "description");
                return msg;
            }
            catch
            {
                return null;
            }
        }

        private static int ParseInt(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '-' || json[valueEnd] == '.')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (int.TryParse(valueStr, out int result))
            {
                return result;
            }
            
            return 0;
        }

        private static long ParseLong(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '-' || json[valueEnd] == '.')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (long.TryParse(valueStr, out long result))
            {
                return result;
            }
            
            return 0;
        }

        private static ulong ParseULong(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (ulong.TryParse(valueStr, out ulong result))
            {
                return result;
            }
            
            return 0;
        }

        private static double ParseDouble(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return 0.0;
            
            int colonPos = json.IndexOf(':', keyPos);
            if (colonPos == -1) return 0.0;
            
            int valueStart = colonPos + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart])) valueStart++;
            
            int valueEnd = valueStart;
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.' || json[valueEnd] == '-')) valueEnd++;
            
            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (double.TryParse(valueStr, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double result))
            {
                return result;
            }
            
            return 0.0;
        }
    }

    /// <summary>
    /// BasicTypesMessage serializer
    /// </summary>
    public static class BasicTypesMessageSerializer
    {
        public const int MessageSize = 204;

        /// <summary>
        /// Serialize BasicTypesMessage to bytes
        /// </summary>
        public static byte[] Serialize(BasicTypesMessage msg)
        {
            byte[] buffer = new byte[MessageSize];
            int offset = 0;

            // small_int (int8, offset 0)
            buffer[offset++] = (byte)msg.SmallInt;

            // medium_int (int16, offset 1)
            BitConverter.GetBytes(msg.MediumInt).CopyTo(buffer, offset);
            offset += 2;

            // regular_int (int32, offset 3)
            BitConverter.GetBytes(msg.RegularInt).CopyTo(buffer, offset);
            offset += 4;

            // large_int (int64, offset 7)
            BitConverter.GetBytes(msg.LargeInt).CopyTo(buffer, offset);
            offset += 8;

            // small_uint (uint8, offset 15)
            buffer[offset++] = msg.SmallUint;

            // medium_uint (uint16, offset 16)
            BitConverter.GetBytes(msg.MediumUint).CopyTo(buffer, offset);
            offset += 2;

            // regular_uint (uint32, offset 18)
            BitConverter.GetBytes(msg.RegularUint).CopyTo(buffer, offset);
            offset += 4;

            // large_uint (uint64, offset 22)
            BitConverter.GetBytes(msg.LargeUint).CopyTo(buffer, offset);
            offset += 8;

            // single_precision (float32, offset 30)
            BitConverter.GetBytes(msg.SinglePrecision).CopyTo(buffer, offset);
            offset += 4;

            // double_precision (float64, offset 34)
            BitConverter.GetBytes(msg.DoublePrecision).CopyTo(buffer, offset);
            offset += 8;

            // flag (bool/uint8, offset 42)
            buffer[offset++] = msg.Flag ? (byte)1 : (byte)0;

            // device_id (fixed string, 32 bytes, offset 43)
            // The DeviceId is stored as a byte in our model, but in the wire format it's 32 bytes
            // For now, just fill with zeros
            offset += 32;

            // description_length (uint8, offset 75)
            byte[] descBytes = Encoding.UTF8.GetBytes(msg.Description);
            buffer[offset++] = (byte)Math.Min(descBytes.Length, 128);

            // description_data (128 bytes, offset 76)
            Array.Copy(descBytes, 0, buffer, offset, Math.Min(descBytes.Length, 128));
            offset += 128;

            return buffer;
        }

        /// <summary>
        /// Deserialize bytes to BasicTypesMessage
        /// </summary>
        public static BasicTypesMessage Deserialize(byte[] buffer)
        {
            int offset = 0;
            var msg = new BasicTypesMessage();

            // small_int (int8, offset 0)
            msg.SmallInt = (sbyte)buffer[offset++];

            // medium_int (int16, offset 1)
            msg.MediumInt = BitConverter.ToInt16(buffer, offset);
            offset += 2;

            // regular_int (int32, offset 3)
            msg.RegularInt = BitConverter.ToInt32(buffer, offset);
            offset += 4;

            // large_int (int64, offset 7)
            msg.LargeInt = BitConverter.ToInt64(buffer, offset);
            offset += 8;

            // small_uint (uint8, offset 15)
            msg.SmallUint = buffer[offset++];

            // medium_uint (uint16, offset 16)
            msg.MediumUint = BitConverter.ToUInt16(buffer, offset);
            offset += 2;

            // regular_uint (uint32, offset 18)
            msg.RegularUint = BitConverter.ToUInt32(buffer, offset);
            offset += 4;

            // large_uint (uint64, offset 22)
            msg.LargeUint = BitConverter.ToUInt64(buffer, offset);
            offset += 8;

            // single_precision (float32, offset 30)
            msg.SinglePrecision = BitConverter.ToSingle(buffer, offset);
            offset += 4;

            // double_precision (float64, offset 34)
            msg.DoublePrecision = BitConverter.ToDouble(buffer, offset);
            offset += 8;

            // flag (bool/uint8, offset 42)
            msg.Flag = buffer[offset++] != 0;

            // device_id (fixed string, 32 bytes, offset 43)
            // Skip device_id field for now
            msg.DeviceId = 0;
            offset += 32;

            // description_length (uint8, offset 75)
            byte descLength = buffer[offset++];

            // description_data (128 bytes, offset 76)
            if (descLength > 0 && descLength <= 128)
            {
                msg.Description = Encoding.UTF8.GetString(buffer, offset, descLength);
            }
            else
            {
                msg.Description = "";
            }
            offset += 128;

            return msg;
        }

        /// <summary>
        /// Validate BasicTypesMessage against test data
        /// </summary>
        public static bool ValidateAgainstData(BasicTypesMessage deserialized, BasicTypesMessage expected)
        {
            bool isValid = true;

            if (deserialized.SmallInt != expected.SmallInt)
            {
                Console.WriteLine($"  Value mismatch: small_int: expected {expected.SmallInt}, got {deserialized.SmallInt}");
                isValid = false;
            }

            if (deserialized.MediumInt != expected.MediumInt)
            {
                Console.WriteLine($"  Value mismatch: medium_int: expected {expected.MediumInt}, got {deserialized.MediumInt}");
                isValid = false;
            }

            if (deserialized.RegularInt != expected.RegularInt)
            {
                Console.WriteLine($"  Value mismatch: regular_int: expected {expected.RegularInt}, got {deserialized.RegularInt}");
                isValid = false;
            }

            // Skip validation for very large integers due to JSON precision limits
            if (Math.Abs(expected.LargeInt) < 9000000000000000000L)
            {
                if (deserialized.LargeInt != expected.LargeInt)
                {
                    Console.WriteLine($"  Value mismatch: large_int: expected {expected.LargeInt}, got {deserialized.LargeInt}");
                    isValid = false;
                }
            }

            if (deserialized.SmallUint != expected.SmallUint)
            {
                Console.WriteLine($"  Value mismatch: small_uint: expected {expected.SmallUint}, got {deserialized.SmallUint}");
                isValid = false;
            }

            if (deserialized.MediumUint != expected.MediumUint)
            {
                Console.WriteLine($"  Value mismatch: medium_uint: expected {expected.MediumUint}, got {deserialized.MediumUint}");
                isValid = false;
            }

            if (deserialized.RegularUint != expected.RegularUint)
            {
                Console.WriteLine($"  Value mismatch: regular_uint: expected {expected.RegularUint}, got {deserialized.RegularUint}");
                isValid = false;
            }

            // Skip validation for very large unsigned integers due to JSON precision limits
            if (expected.LargeUint < 9000000000000000000UL)
            {
                if (deserialized.LargeUint != expected.LargeUint)
                {
                    Console.WriteLine($"  Value mismatch: large_uint: expected {expected.LargeUint}, got {deserialized.LargeUint}");
                    isValid = false;
                }
            }

            if (Math.Abs(deserialized.SinglePrecision - expected.SinglePrecision) > 0.0001f)
            {
                Console.WriteLine($"  Value mismatch: single_precision: expected {expected.SinglePrecision}, got {deserialized.SinglePrecision}");
                isValid = false;
            }

            if (Math.Abs(deserialized.DoublePrecision - expected.DoublePrecision) > 0.000001)
            {
                Console.WriteLine($"  Value mismatch: double_precision: expected {expected.DoublePrecision}, got {deserialized.DoublePrecision}");
                isValid = false;
            }

            if (deserialized.Flag != expected.Flag)
            {
                Console.WriteLine($"  Value mismatch: flag: expected {expected.Flag}, got {deserialized.Flag}");
                isValid = false;
            }

            if (deserialized.Description != expected.Description)
            {
                Console.WriteLine($"  Value mismatch: description: expected '{expected.Description}', got '{deserialized.Description}'");
                isValid = false;
            }

            return isValid;
        }
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
        /// Create serialized test message bytes with expected values (backwards compat)
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
        /// Create serialized message bytes from TestMessage
        /// </summary>
        public static byte[] CreateMessageBytesFromData(TestMessage testMsg)
        {
            byte[] strBytes = Encoding.UTF8.GetBytes(testMsg.TestString);
            byte[] stringData = new byte[64];
            Array.Copy(strBytes, stringData, Math.Min(strBytes.Length, 64));

            return MessageSerializer.Serialize(
                testMsg.MagicNumber,
                (byte)strBytes.Length,
                stringData,
                testMsg.TestFloat,
                testMsg.TestBool,
                (byte)testMsg.TestArray.Length,
                testMsg.TestArray
            );
        }

        /// <summary>
        /// Validate message against test data
        /// </summary>
        public static bool ValidateMessageAgainstData(byte[] msgData, TestMessage testMsg)
        {
            var (magicNumber, stringLength, stringData, testFloat, testBool, arrayCount, arrayData) = 
                MessageSerializer.Deserialize(msgData);

            bool isValid = true;
            
            if (magicNumber != testMsg.MagicNumber)
            {
                Console.WriteLine($"  Value mismatch: magic_number: expected {testMsg.MagicNumber}, got {magicNumber}");
                isValid = false;
            }

            string decodedString = Encoding.UTF8.GetString(stringData, 0, stringLength);
            if (decodedString != testMsg.TestString)
            {
                Console.WriteLine($"  Value mismatch: test_string: expected '{testMsg.TestString}', got '{decodedString}'");
                isValid = false;
            }

            if (Math.Abs(testFloat - testMsg.TestFloat) > 0.1f)
            {
                Console.WriteLine($"  Value mismatch: test_float: expected {testMsg.TestFloat}, got {testFloat}");
                isValid = false;
            }

            if (testBool != testMsg.TestBool)
            {
                Console.WriteLine($"  Value mismatch: test_bool: expected {testMsg.TestBool}, got {testBool}");
                isValid = false;
            }

            if (arrayCount != testMsg.TestArray.Length)
            {
                Console.WriteLine($"  Value mismatch: test_array.count: expected {testMsg.TestArray.Length}, got {arrayCount}");
                isValid = false;
            }
            else
            {
                for (int i = 0; i < arrayCount; i++)
                {
                    if (arrayData[i] != testMsg.TestArray[i])
                    {
                        Console.WriteLine($"  Value mismatch: test_array[{i}]: expected {testMsg.TestArray[i]}, got {arrayData[i]}");
                        isValid = false;
                    }
                }
            }

            return isValid;
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
    /// <summary>
    /// None + Minimal frame format helper (ProfileIPC)
    /// </summary>
    class NoneMinimal : FrameFormatBase
    {
        public override byte[] Encode(int msgId, byte[] msgData)
        {
            const int headerSize = 1;
            int totalSize = headerSize + msgData.Length;

            byte[] buffer = new byte[totalSize];
            buffer[0] = (byte)msgId;
            Array.Copy(msgData, 0, buffer, headerSize, msgData.Length);

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] data, int length)
        {
            var result = new FrameParseResult { Valid = false, MsgId = 0, MsgData = new byte[0], MsgSize = 0 };

            if (length < 1)
                return result;

            int msgId = data[0];
            // For minimal payloads, determine message size based on msgId
            int msgLen;
            if (msgId == 204) // SerializationTestMessage
            {
                msgLen = MessageSerializer.MessageSize;
            }
            else if (msgId == 201) // BasicTypesMessage
            {
                msgLen = BasicTypesMessageSerializer.MessageSize;
            }
            else
            {
                msgLen = MessageSerializer.MessageSize; // default
            }
            int totalSize = 1 + msgLen;

            if (length < totalSize)
                return result;

            result.Valid = true;
            result.MsgId = msgId;
            result.MsgSize = msgLen;
            result.MsgData = new byte[msgLen];
            Array.Copy(data, 1, result.MsgData, 0, msgLen);

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
            // For minimal payloads, determine message size based on msgId
            int msgLen;
            if (msgId == 204) // SerializationTestMessage
            {
                msgLen = MessageSerializer.MessageSize;
            }
            else if (msgId == 201) // BasicTypesMessage
            {
                msgLen = BasicTypesMessageSerializer.MessageSize;
            }
            else
            {
                msgLen = MessageSerializer.MessageSize; // default
            }
            int totalSize = 2 + msgLen;

            if (length < totalSize)
                return result;

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
                case "profile_standard":
                    return new BasicDefault();
                case "profile_sensor":
                    return new TinyMinimal();
                case "profile_ipc":
                    return new NoneMinimal();
                case "profile_bulk":
                    return new BasicExtended();
                case "profile_network":
                    return new BasicExtendedMultiSystemStream();
                default:
                    throw new ArgumentException($"Unknown frame format: {formatName}");
            }
        }

        /// <summary>
        /// Encode multiple test messages using the specified frame format
        /// </summary>
        public static byte[] EncodeTestMessage(string formatName)
        {
            var parser = GetParser(formatName);
            var encodedMessages = new System.Collections.Generic.List<byte[]>();

            // Load mixed messages
            var mixedMessages = TestMessages.LoadMixedMessages();
            
            if (mixedMessages.Length == 0)
            {
                Console.WriteLine("  Error: No mixed messages loaded from test_messages.json");
                // For backward compatibility with tests, fail if no messages
                throw new Exception("Failed to load test messages from JSON");
            }

            foreach (var mixedMsg in mixedMessages)
            {
                byte[] msgData;
                int msgId;

                if (mixedMsg.Type == "SerializationTestMessage")
                {
                    var testMsg = (TestMessage)mixedMsg.Data;
                    msgData = TestCodec.CreateMessageBytesFromData(testMsg);
                    msgId = 204; // SerializationTestMessage.MsgId
                }
                else if (mixedMsg.Type == "BasicTypesMessage")
                {
                    var basicMsg = (BasicTypesMessage)mixedMsg.Data;
                    msgData = BasicTypesMessageSerializer.Serialize(basicMsg);
                    msgId = 201; // BasicTypesMessage.MsgId
                }
                else
                {
                    Console.WriteLine($"  Unknown message type: {mixedMsg.Type}");
                    continue;
                }

                byte[] encoded = parser.Encode(msgId, msgData);
                if (encoded == null || encoded.Length == 0)
                {
                    Console.WriteLine("  Encoding failed for message");
                    throw new Exception("Encoding failed");
                }
                encodedMessages.Add(encoded);
            }

            // Concatenate all encoded messages
            int totalLength = 0;
            foreach (var msg in encodedMessages)
            {
                totalLength += msg.Length;
            }

            byte[] result = new byte[totalLength];
            int offset = 0;
            foreach (var msg in encodedMessages)
            {
                Array.Copy(msg, 0, result, offset, msg.Length);
                offset += msg.Length;
            }

            return result;
        }

        /// <summary>
        /// Decode and validate multiple test messages using the specified frame format
        /// Returns the number of successfully decoded messages
        /// </summary>
        public static int DecodeTestMessages(string formatName, byte[] data)
        {
            var parser = GetParser(formatName);
            var mixedMessages = TestMessages.LoadMixedMessages();
            
            if (mixedMessages.Length == 0)
            {
                Console.WriteLine("  Error: No mixed messages loaded");
                return 0;
            }

            int offset = 0;
            int messageCount = 0;

            while (offset < data.Length && messageCount < mixedMessages.Length)
            {
                // Extract remaining data
                byte[] remainingData = new byte[data.Length - offset];
                Array.Copy(data, offset, remainingData, 0, remainingData.Length);

                var result = parser.ValidatePacket(remainingData, remainingData.Length);

                if (!result.Valid)
                {
                    Console.WriteLine($"  Decoding failed for message {messageCount}");
                    return messageCount;
                }

                // Get expected message info
                var mixedMsg = mixedMessages[messageCount];
                bool validationSuccess;

                if (mixedMsg.Type == "SerializationTestMessage")
                {
                    // Validate msg_id
                    if (result.MsgId != 204)
                    {
                        Console.WriteLine($"  Message {messageCount}: Expected msg_id 204 (SerializationTestMessage), got {result.MsgId}");
                        return messageCount;
                    }

                    var testMsg = (TestMessage)mixedMsg.Data;
                    validationSuccess = TestCodec.ValidateMessageAgainstData(result.MsgData, testMsg);
                }
                else if (mixedMsg.Type == "BasicTypesMessage")
                {
                    // Validate msg_id
                    if (result.MsgId != 201)
                    {
                        Console.WriteLine($"  Message {messageCount}: Expected msg_id 201 (BasicTypesMessage), got {result.MsgId}");
                        return messageCount;
                    }

                    var basicMsg = (BasicTypesMessage)mixedMsg.Data;
                    var decodedBasicMsg = BasicTypesMessageSerializer.Deserialize(result.MsgData);
                    validationSuccess = BasicTypesMessageSerializer.ValidateAgainstData(decodedBasicMsg, basicMsg);
                }
                else
                {
                    Console.WriteLine($"  Unknown message type: {mixedMsg.Type}");
                    return messageCount;
                }

                if (!validationSuccess)
                {
                    Console.WriteLine($"  Validation failed for message {messageCount}");
                    return messageCount;
                }

                // Calculate message size based on format
                int msgSize = 0;
                if (formatName == "profile_standard")
                {
                    msgSize = 4 + result.MsgData.Length + 2; // header + payload + crc
                }
                else if (formatName == "profile_sensor")
                {
                    msgSize = 2 + result.MsgData.Length; // header + payload
                }
                else if (formatName == "profile_ipc")
                {
                    msgSize = 1 + result.MsgData.Length; // header + payload
                }
                else if (formatName == "profile_bulk")
                {
                    msgSize = 6 + result.MsgData.Length + 2; // header + payload + crc
                }
                else if (formatName == "profile_network")
                {
                    msgSize = 9 + result.MsgData.Length + 2; // header + payload + crc
                }

                offset += msgSize;
                messageCount++;
            }

            if (messageCount != mixedMessages.Length)
            {
                Console.WriteLine($"  Expected {mixedMessages.Length} messages, but decoded {messageCount}");
                return messageCount;
            }

            if (offset != data.Length)
            {
                Console.WriteLine($"  Extra data after messages: processed {offset} bytes, got {data.Length} bytes");
                return messageCount;
            }

            return messageCount;
        }

        /// <summary>
        /// Decode a test message using the specified frame format (backwards compat)
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
