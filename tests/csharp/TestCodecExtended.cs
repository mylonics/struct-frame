// Test codec - Extended message ID and payload tests (C#)

using System;
using System.Collections.Generic;
using System.Text;
using System.IO;
using StructFrame;
using StructFrame.ExtendedTest;

namespace StructFrameTests
{
    /// <summary>
    /// Extended message item for JSON parsing
    /// </summary>
    public class ExtendedMessageItem
    {
        public string Type { get; set; }
        public object Data { get; set; }
    }

    /// <summary>
    /// Extended message data classes
    /// </summary>
    public class ExtendedIdMessage1Data
    {
        public uint SequenceNumber { get; set; }
        public string Label { get; set; }
        public float Value { get; set; }
        public bool Enabled { get; set; }
    }

    public class ExtendedIdMessage2Data
    {
        public int SensorId { get; set; }
        public double Reading { get; set; }
        public ushort StatusCode { get; set; }
        public string Description { get; set; }
    }

    public class ExtendedIdMessage3Data
    {
        public ulong Timestamp { get; set; }
        public short Temperature { get; set; }
        public byte Humidity { get; set; }
        public string Location { get; set; }
    }

    public class ExtendedIdMessage4Data
    {
        public uint EventId { get; set; }
        public byte EventType { get; set; }
        public long EventTime { get; set; }
        public string EventData { get; set; }
    }

    public class ExtendedIdMessage5Data
    {
        public float XPosition { get; set; }
        public float YPosition { get; set; }
        public float ZPosition { get; set; }
        public uint FrameNumber { get; set; }
    }

    public class ExtendedIdMessage6Data
    {
        public short CommandId { get; set; }
        public ushort Parameter1 { get; set; }
        public ushort Parameter2 { get; set; }
        public bool Acknowledged { get; set; }
        public string CommandName { get; set; }
    }

    public class ExtendedIdMessage7Data
    {
        public uint Counter { get; set; }
        public double Average { get; set; }
        public float Minimum { get; set; }
        public float Maximum { get; set; }
    }

    public class ExtendedIdMessage8Data
    {
        public byte Level { get; set; }
        public short Offset { get; set; }
        public uint Duration { get; set; }
        public string Tag { get; set; }
    }

    public class ExtendedIdMessage9Data
    {
        public long BigNumber { get; set; }
        public ulong BigUnsigned { get; set; }
        public double PrecisionValue { get; set; }
    }

    public class ExtendedIdMessage10Data
    {
        public ushort SmallValue { get; set; }
        public string ShortText { get; set; }
        public bool Flag { get; set; }
    }

    public class LargePayloadMessage1Data
    {
        public float[] SensorReadings { get; set; }
        public byte ReadingCount { get; set; }
        public long Timestamp { get; set; }
        public string DeviceName { get; set; }
    }

    public class LargePayloadMessage2Data
    {
        public byte[] LargeData { get; set; }
    }

    /// <summary>
    /// Extended test codec for encoding/decoding extended messages
    /// </summary>
    public static class ExtendedTestCodec
    {
        /// <summary>
        /// Load extended messages from extended_messages.json
        /// </summary>
        public static ExtendedMessageItem[] LoadExtendedMessages()
        {
            string[] possiblePaths = new string[]
            {
                "../extended_messages.json",
                "../../tests/extended_messages.json",
                "extended_messages.json",
                "../../../tests/extended_messages.json",
                "../../extended_messages.json",
                "../../../../../tests/extended_messages.json"
            };

            foreach (var path in possiblePaths)
            {
                try
                {
                    if (File.Exists(path))
                    {
                        string jsonContent = File.ReadAllText(path);
                        return ParseExtendedMessagesJson(jsonContent);
                    }
                }
                catch
                {
                    continue;
                }
            }

            Console.WriteLine("Error: Could not load extended_messages.json");
            return new ExtendedMessageItem[] { };
        }

        private static ExtendedMessageItem[] ParseExtendedMessagesJson(string jsonContent)
        {
            var result = new List<ExtendedMessageItem>();
            
            // Parse message type arrays into dictionaries
            var extMsg1Dict = ParseExtendedIdMessage1Array(jsonContent);
            var extMsg2Dict = ParseExtendedIdMessage2Array(jsonContent);
            var extMsg3Dict = ParseExtendedIdMessage3Array(jsonContent);
            var extMsg4Dict = ParseExtendedIdMessage4Array(jsonContent);
            var extMsg5Dict = ParseExtendedIdMessage5Array(jsonContent);
            var extMsg6Dict = ParseExtendedIdMessage6Array(jsonContent);
            var extMsg7Dict = ParseExtendedIdMessage7Array(jsonContent);
            var extMsg8Dict = ParseExtendedIdMessage8Array(jsonContent);
            var extMsg9Dict = ParseExtendedIdMessage9Array(jsonContent);
            var extMsg10Dict = ParseExtendedIdMessage10Array(jsonContent);
            var largeMsg1Dict = ParseLargePayloadMessage1Array(jsonContent);
            var largeMsg2Dict = ParseLargePayloadMessage2Array(jsonContent);

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

                        if (msgType == "ExtendedIdMessage1" && extMsg1Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg1Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage2" && extMsg2Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg2Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage3" && extMsg3Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg3Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage4" && extMsg4Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg4Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage5" && extMsg5Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg5Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage6" && extMsg6Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg6Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage7" && extMsg7Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg7Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage8" && extMsg8Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg8Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage9" && extMsg9Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg9Dict[msgName] });
                        }
                        else if (msgType == "ExtendedIdMessage10" && extMsg10Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = extMsg10Dict[msgName] });
                        }
                        else if (msgType == "LargePayloadMessage1" && largeMsg1Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = largeMsg1Dict[msgName] });
                        }
                        else if (msgType == "LargePayloadMessage2" && largeMsg2Dict.ContainsKey(msgName))
                        {
                            result.Add(new ExtendedMessageItem { Type = msgType, Data = largeMsg2Dict[msgName] });
                        }

                        pos = objEnd + 1;
                    }
                }
            }

            return result.ToArray();
        }

        // JSON parsing helpers
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

        private static int FindMatchingBracket(string json, int startPos)
        {
            int depth = 0;
            for (int i = startPos; i < json.Length; i++)
            {
                if (json[i] == '[') depth++;
                else if (json[i] == ']')
                {
                    depth--;
                    if (depth == 0) return i;
                }
            }
            return -1;
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

            // Check if value is a string
            if (json[valueStart] == '"')
            {
                valueStart++;
                int valueEnd = json.IndexOf('"', valueStart);
                if (valueEnd == -1) return 0;
                string valueStr = json.Substring(valueStart, valueEnd - valueStart);
                if (long.TryParse(valueStr, out long strResult))
                {
                    return strResult;
                }
                return 0;
            }

            int numEnd = valueStart;
            while (numEnd < json.Length && (char.IsDigit(json[numEnd]) || json[numEnd] == '-' || json[numEnd] == '.')) numEnd++;

            string numStr = json.Substring(valueStart, numEnd - valueStart);
            if (long.TryParse(numStr, out long result))
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

            // Check if value is a string
            if (json[valueStart] == '"')
            {
                valueStart++;
                int valueEnd = json.IndexOf('"', valueStart);
                if (valueEnd == -1) return 0;
                string valueStr = json.Substring(valueStart, valueEnd - valueStart);
                if (ulong.TryParse(valueStr, out ulong strResult))
                {
                    return strResult;
                }
                return 0;
            }

            int numEnd = valueStart;
            while (numEnd < json.Length && char.IsDigit(json[numEnd])) numEnd++;

            string numStr = json.Substring(valueStart, numEnd - valueStart);
            if (ulong.TryParse(numStr, out ulong result))
            {
                return result;
            }

            return 0;
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
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.' || json[valueEnd] == '-' || json[valueEnd] == 'e' || json[valueEnd] == 'E' || json[valueEnd] == '+')) valueEnd++;

            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (float.TryParse(valueStr, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float result))
            {
                return result;
            }

            return 0.0f;
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
            while (valueEnd < json.Length && (char.IsDigit(json[valueEnd]) || json[valueEnd] == '.' || json[valueEnd] == '-' || json[valueEnd] == 'e' || json[valueEnd] == 'E' || json[valueEnd] == '+')) valueEnd++;

            string valueStr = json.Substring(valueStart, valueEnd - valueStart);
            if (double.TryParse(valueStr, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double result))
            {
                return result;
            }

            return 0.0;
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
            int bracePos = json.IndexOf('}', colonPos);

            int endPos = Math.Min(commaPos != -1 ? commaPos : int.MaxValue, bracePos != -1 ? bracePos : int.MaxValue);

            if (truePos != -1 && truePos < endPos)
            {
                return true;
            }

            return false;
        }

        private static float[] ParseFloatArray(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return new float[0];

            int bracketStart = json.IndexOf('[', keyPos);
            if (bracketStart == -1) return new float[0];

            int bracketEnd = FindMatchingBracket(json, bracketStart);
            if (bracketEnd == -1) return new float[0];

            string arrayStr = json.Substring(bracketStart + 1, bracketEnd - bracketStart - 1);
            if (string.IsNullOrWhiteSpace(arrayStr)) return new float[0];

            string[] parts = arrayStr.Split(',');
            var result = new List<float>();

            foreach (var part in parts)
            {
                if (float.TryParse(part.Trim(), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float value))
                {
                    result.Add(value);
                }
            }

            return result.ToArray();
        }

        private static byte[] ParseByteArray(string json, string key)
        {
            int keyPos = json.IndexOf($"\"{key}\"");
            if (keyPos == -1) return new byte[0];

            int bracketStart = json.IndexOf('[', keyPos);
            if (bracketStart == -1) return new byte[0];

            int bracketEnd = FindMatchingBracket(json, bracketStart);
            if (bracketEnd == -1) return new byte[0];

            string arrayStr = json.Substring(bracketStart + 1, bracketEnd - bracketStart - 1);
            if (string.IsNullOrWhiteSpace(arrayStr)) return new byte[0];

            string[] parts = arrayStr.Split(',');
            var result = new List<byte>();

            foreach (var part in parts)
            {
                if (int.TryParse(part.Trim(), out int value) && value >= 0 && value <= 255)
                {
                    result.Add((byte)value);
                }
            }

            return result.ToArray();
        }

        // Parse message type arrays
        private static Dictionary<string, ExtendedIdMessage1Data> ParseExtendedIdMessage1Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage1Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage1\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage1\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage1Data
                {
                    SequenceNumber = ParseUInt(msgJson, "sequence_number"),
                    Label = ParseString(msgJson, "label"),
                    Value = ParseFloat(msgJson, "value"),
                    Enabled = ParseBool(msgJson, "enabled")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage2Data> ParseExtendedIdMessage2Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage2Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage2\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage2\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage2Data
                {
                    SensorId = ParseInt(msgJson, "sensor_id"),
                    Reading = ParseDouble(msgJson, "reading"),
                    StatusCode = (ushort)ParseUInt(msgJson, "status_code"),
                    Description = ParseString(msgJson, "description")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage3Data> ParseExtendedIdMessage3Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage3Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage3\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage3\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage3Data
                {
                    Timestamp = ParseULong(msgJson, "timestamp"),
                    Temperature = (short)ParseInt(msgJson, "temperature"),
                    Humidity = (byte)ParseUInt(msgJson, "humidity"),
                    Location = ParseString(msgJson, "location")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage4Data> ParseExtendedIdMessage4Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage4Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage4\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage4\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage4Data
                {
                    EventId = ParseUInt(msgJson, "event_id"),
                    EventType = (byte)ParseUInt(msgJson, "event_type"),
                    EventTime = ParseLong(msgJson, "event_time"),
                    EventData = ParseString(msgJson, "event_data")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage5Data> ParseExtendedIdMessage5Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage5Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage5\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage5\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage5Data
                {
                    XPosition = ParseFloat(msgJson, "x_position"),
                    YPosition = ParseFloat(msgJson, "y_position"),
                    ZPosition = ParseFloat(msgJson, "z_position"),
                    FrameNumber = ParseUInt(msgJson, "frame_number")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage6Data> ParseExtendedIdMessage6Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage6Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage6\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage6\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage6Data
                {
                    CommandId = (short)ParseInt(msgJson, "command_id"),
                    Parameter1 = (ushort)ParseUInt(msgJson, "parameter1"),
                    Parameter2 = (ushort)ParseUInt(msgJson, "parameter2"),
                    Acknowledged = ParseBool(msgJson, "acknowledged"),
                    CommandName = ParseString(msgJson, "command_name")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage7Data> ParseExtendedIdMessage7Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage7Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage7\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage7\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage7Data
                {
                    Counter = ParseUInt(msgJson, "counter"),
                    Average = ParseDouble(msgJson, "average"),
                    Minimum = ParseFloat(msgJson, "minimum"),
                    Maximum = ParseFloat(msgJson, "maximum")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage8Data> ParseExtendedIdMessage8Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage8Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage8\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage8\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage8Data
                {
                    Level = (byte)ParseUInt(msgJson, "level"),
                    Offset = (short)ParseInt(msgJson, "offset"),
                    Duration = ParseUInt(msgJson, "duration"),
                    Tag = ParseString(msgJson, "tag")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage9Data> ParseExtendedIdMessage9Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage9Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage9\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage9\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage9Data
                {
                    BigNumber = ParseLong(msgJson, "big_number"),
                    BigUnsigned = ParseULong(msgJson, "big_unsigned"),
                    PrecisionValue = ParseDouble(msgJson, "precision_value")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, ExtendedIdMessage10Data> ParseExtendedIdMessage10Array(string jsonContent)
        {
            var dict = new Dictionary<string, ExtendedIdMessage10Data>();
            int arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage10\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"ExtendedIdMessage10\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new ExtendedIdMessage10Data
                {
                    SmallValue = (ushort)ParseUInt(msgJson, "small_value"),
                    ShortText = ParseString(msgJson, "short_text"),
                    Flag = ParseBool(msgJson, "flag")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, LargePayloadMessage1Data> ParseLargePayloadMessage1Array(string jsonContent)
        {
            var dict = new Dictionary<string, LargePayloadMessage1Data>();
            int arrayStart = jsonContent.IndexOf("\"LargePayloadMessage1\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"LargePayloadMessage1\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new LargePayloadMessage1Data
                {
                    SensorReadings = ParseFloatArray(msgJson, "sensor_readings"),
                    ReadingCount = (byte)ParseUInt(msgJson, "reading_count"),
                    Timestamp = ParseLong(msgJson, "timestamp"),
                    DeviceName = ParseString(msgJson, "device_name")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        private static Dictionary<string, LargePayloadMessage2Data> ParseLargePayloadMessage2Array(string jsonContent)
        {
            var dict = new Dictionary<string, LargePayloadMessage2Data>();
            int arrayStart = jsonContent.IndexOf("\"LargePayloadMessage2\": [");
            if (arrayStart == -1) arrayStart = jsonContent.IndexOf("\"LargePayloadMessage2\":[");
            if (arrayStart == -1) return dict;

            int bracketStart = jsonContent.IndexOf('[', arrayStart);
            if (bracketStart == -1) return dict;

            int bracketEnd = FindMatchingBracket(jsonContent, bracketStart);
            if (bracketEnd == -1) return dict;

            string arrayContent = jsonContent.Substring(bracketStart, bracketEnd - bracketStart + 1);
            int pos = 1;

            while (pos < arrayContent.Length)
            {
                while (pos < arrayContent.Length && char.IsWhiteSpace(arrayContent[pos])) pos++;
                if (pos >= arrayContent.Length || arrayContent[pos] == ']') break;
                if (arrayContent[pos] == ',') { pos++; continue; }
                if (arrayContent[pos] != '{') break;

                int objEnd = FindMatchingBrace(arrayContent, pos);
                if (objEnd == -1) break;

                string msgJson = arrayContent.Substring(pos, objEnd - pos + 1);
                string name = ParseString(msgJson, "name");
                
                dict[name] = new LargePayloadMessage2Data
                {
                    LargeData = ParseByteArray(msgJson, "large_data")
                };

                pos = objEnd + 1;
            }

            return dict;
        }

        /// <summary>
        /// Encode extended messages using the specified frame format
        /// </summary>
        public static byte[] EncodeExtendedMessages(string formatName)
        {
            var parser = GetExtendedParser(formatName);
            var encodedMessages = new List<byte[]>();

            var messages = LoadExtendedMessages();

            if (messages.Length == 0)
            {
                throw new Exception("Failed to load extended test messages from JSON");
            }

            foreach (var msg in messages)
            {
                byte[] msgData;
                int msgId;

                var (data, id) = SerializeExtendedMessage(msg);
                msgData = data;
                msgId = id;

                byte[] encoded = parser.Encode(msgId, msgData);
                if (encoded == null || encoded.Length == 0)
                {
                    throw new Exception($"Encoding failed for message type {msg.Type}");
                }
                encodedMessages.Add(encoded);
            }

            // Concatenate all encoded messages
            int totalLength = 0;
            foreach (var m in encodedMessages)
            {
                totalLength += m.Length;
            }

            byte[] result = new byte[totalLength];
            int offset = 0;
            foreach (var m in encodedMessages)
            {
                Array.Copy(m, 0, result, offset, m.Length);
                offset += m.Length;
            }

            return result;
        }

        /// <summary>
        /// Decode and validate extended messages
        /// </summary>
        public static int DecodeExtendedMessages(string formatName, byte[] data)
        {
            var parser = GetExtendedParser(formatName);
            var messages = LoadExtendedMessages();

            if (messages.Length == 0)
            {
                Console.WriteLine("  Error: No extended messages loaded");
                return 0;
            }

            int offset = 0;
            int messageCount = 0;

            while (offset < data.Length && messageCount < messages.Length)
            {
                byte[] remainingData = new byte[data.Length - offset];
                Array.Copy(data, offset, remainingData, 0, remainingData.Length);

                var result = parser.ValidateBuffer(remainingData);

                if (!result.Valid)
                {
                    Console.WriteLine($"  Decoding failed for message {messageCount}");
                    return messageCount;
                }

                var msg = messages[messageCount];
                var (_, expectedMsgId) = SerializeExtendedMessage(msg);

                if (result.MsgId != expectedMsgId)
                {
                    Console.WriteLine($"  Message {messageCount}: Expected msg_id {expectedMsgId} ({msg.Type}), got {result.MsgId}");
                    return messageCount;
                }

                var config = parser.Config;
                int msgSize = config.HeaderSize + result.MsgSize + config.FooterSize;

                offset += msgSize;
                messageCount++;
            }

            if (messageCount != messages.Length)
            {
                Console.WriteLine($"  Expected {messages.Length} messages, but decoded {messageCount}");
                return messageCount;
            }

            if (offset != data.Length)
            {
                Console.WriteLine($"  Extra data after messages: processed {offset} bytes, got {data.Length} bytes");
                return messageCount;
            }

            return messageCount;
        }

        private static FrameProfileParser GetExtendedParser(string formatName)
        {
            switch (formatName)
            {
                case "profile_bulk":
                    return FrameProfiles.CreateBulkParser();
                case "profile_network":
                    return FrameProfiles.CreateNetworkParser();
                default:
                    throw new ArgumentException($"Format not supported for extended messages: {formatName}. Use profile_bulk or profile_network.");
            }
        }

        private static (byte[], int) SerializeExtendedMessage(ExtendedMessageItem msg)
        {
            switch (msg.Type)
            {
                case "ExtendedIdMessage1":
                    return SerializeExtendedIdMessage1((ExtendedIdMessage1Data)msg.Data);
                case "ExtendedIdMessage2":
                    return SerializeExtendedIdMessage2((ExtendedIdMessage2Data)msg.Data);
                case "ExtendedIdMessage3":
                    return SerializeExtendedIdMessage3((ExtendedIdMessage3Data)msg.Data);
                case "ExtendedIdMessage4":
                    return SerializeExtendedIdMessage4((ExtendedIdMessage4Data)msg.Data);
                case "ExtendedIdMessage5":
                    return SerializeExtendedIdMessage5((ExtendedIdMessage5Data)msg.Data);
                case "ExtendedIdMessage6":
                    return SerializeExtendedIdMessage6((ExtendedIdMessage6Data)msg.Data);
                case "ExtendedIdMessage7":
                    return SerializeExtendedIdMessage7((ExtendedIdMessage7Data)msg.Data);
                case "ExtendedIdMessage8":
                    return SerializeExtendedIdMessage8((ExtendedIdMessage8Data)msg.Data);
                case "ExtendedIdMessage9":
                    return SerializeExtendedIdMessage9((ExtendedIdMessage9Data)msg.Data);
                case "ExtendedIdMessage10":
                    return SerializeExtendedIdMessage10((ExtendedIdMessage10Data)msg.Data);
                case "LargePayloadMessage1":
                    return SerializeLargePayloadMessage1((LargePayloadMessage1Data)msg.Data);
                case "LargePayloadMessage2":
                    return SerializeLargePayloadMessage2((LargePayloadMessage2Data)msg.Data);
                default:
                    throw new ArgumentException($"Unknown message type: {msg.Type}");
            }
        }

        private static (byte[], int) SerializeExtendedIdMessage1(ExtendedIdMessage1Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage1.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.SequenceNumber).CopyTo(buffer, offset);
            offset += 4;

            byte[] labelBytes = Encoding.UTF8.GetBytes(data.Label);
            Array.Copy(labelBytes, 0, buffer, offset, Math.Min(labelBytes.Length, 32));
            offset += 32;

            BitConverter.GetBytes(data.Value).CopyTo(buffer, offset);
            offset += 4;

            buffer[offset] = data.Enabled ? (byte)1 : (byte)0;

            return (buffer, ExtendedTestExtendedIdMessage1.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage2(ExtendedIdMessage2Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage2.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.SensorId).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.Reading).CopyTo(buffer, offset);
            offset += 8;

            BitConverter.GetBytes(data.StatusCode).CopyTo(buffer, offset);
            offset += 2;

            byte[] descBytes = Encoding.UTF8.GetBytes(data.Description);
            buffer[offset++] = (byte)Math.Min(descBytes.Length, 64);
            Array.Copy(descBytes, 0, buffer, offset, Math.Min(descBytes.Length, 64));

            return (buffer, ExtendedTestExtendedIdMessage2.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage3(ExtendedIdMessage3Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage3.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.Timestamp).CopyTo(buffer, offset);
            offset += 8;

            BitConverter.GetBytes(data.Temperature).CopyTo(buffer, offset);
            offset += 2;

            buffer[offset++] = data.Humidity;

            byte[] locBytes = Encoding.UTF8.GetBytes(data.Location);
            Array.Copy(locBytes, 0, buffer, offset, Math.Min(locBytes.Length, 16));

            return (buffer, ExtendedTestExtendedIdMessage3.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage4(ExtendedIdMessage4Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage4.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.EventId).CopyTo(buffer, offset);
            offset += 4;

            buffer[offset++] = data.EventType;

            BitConverter.GetBytes(data.EventTime).CopyTo(buffer, offset);
            offset += 8;

            byte[] eventDataBytes = Encoding.UTF8.GetBytes(data.EventData);
            buffer[offset++] = (byte)Math.Min(eventDataBytes.Length, 64);
            Array.Copy(eventDataBytes, 0, buffer, offset, Math.Min(eventDataBytes.Length, 64));

            return (buffer, ExtendedTestExtendedIdMessage4.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage5(ExtendedIdMessage5Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage5.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.XPosition).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.YPosition).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.ZPosition).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.FrameNumber).CopyTo(buffer, offset);

            return (buffer, ExtendedTestExtendedIdMessage5.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage6(ExtendedIdMessage6Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage6.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.CommandId).CopyTo(buffer, offset);
            offset += 2;

            BitConverter.GetBytes(data.Parameter1).CopyTo(buffer, offset);
            offset += 2;

            BitConverter.GetBytes(data.Parameter2).CopyTo(buffer, offset);
            offset += 2;

            buffer[offset++] = data.Acknowledged ? (byte)1 : (byte)0;

            byte[] nameBytes = Encoding.UTF8.GetBytes(data.CommandName);
            Array.Copy(nameBytes, 0, buffer, offset, Math.Min(nameBytes.Length, 24));

            return (buffer, ExtendedTestExtendedIdMessage6.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage7(ExtendedIdMessage7Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage7.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.Counter).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.Average).CopyTo(buffer, offset);
            offset += 8;

            BitConverter.GetBytes(data.Minimum).CopyTo(buffer, offset);
            offset += 4;

            BitConverter.GetBytes(data.Maximum).CopyTo(buffer, offset);

            return (buffer, ExtendedTestExtendedIdMessage7.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage8(ExtendedIdMessage8Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage8.MaxSize];
            int offset = 0;

            buffer[offset++] = data.Level;

            BitConverter.GetBytes(data.Offset).CopyTo(buffer, offset);
            offset += 2;

            BitConverter.GetBytes(data.Duration).CopyTo(buffer, offset);
            offset += 4;

            byte[] tagBytes = Encoding.UTF8.GetBytes(data.Tag);
            Array.Copy(tagBytes, 0, buffer, offset, Math.Min(tagBytes.Length, 16));

            return (buffer, ExtendedTestExtendedIdMessage8.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage9(ExtendedIdMessage9Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage9.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.BigNumber).CopyTo(buffer, offset);
            offset += 8;

            BitConverter.GetBytes(data.BigUnsigned).CopyTo(buffer, offset);
            offset += 8;

            BitConverter.GetBytes(data.PrecisionValue).CopyTo(buffer, offset);

            return (buffer, ExtendedTestExtendedIdMessage9.MsgId);
        }

        private static (byte[], int) SerializeExtendedIdMessage10(ExtendedIdMessage10Data data)
        {
            byte[] buffer = new byte[ExtendedTestExtendedIdMessage10.MaxSize];
            int offset = 0;

            BitConverter.GetBytes(data.SmallValue).CopyTo(buffer, offset);
            offset += 2;

            byte[] textBytes = Encoding.UTF8.GetBytes(data.ShortText);
            Array.Copy(textBytes, 0, buffer, offset, Math.Min(textBytes.Length, 16));
            offset += 16;

            buffer[offset] = data.Flag ? (byte)1 : (byte)0;

            return (buffer, ExtendedTestExtendedIdMessage10.MsgId);
        }

        private static (byte[], int) SerializeLargePayloadMessage1(LargePayloadMessage1Data data)
        {
            byte[] buffer = new byte[ExtendedTestLargePayloadMessage1.MaxSize];
            int offset = 0;

            // sensor_readings (64 floats)
            for (int i = 0; i < 64; i++)
            {
                float value = i < data.SensorReadings.Length ? data.SensorReadings[i] : 0;
                BitConverter.GetBytes(value).CopyTo(buffer, offset);
                offset += 4;
            }

            buffer[offset++] = data.ReadingCount;

            BitConverter.GetBytes(data.Timestamp).CopyTo(buffer, offset);
            offset += 8;

            byte[] nameBytes = Encoding.UTF8.GetBytes(data.DeviceName);
            Array.Copy(nameBytes, 0, buffer, offset, Math.Min(nameBytes.Length, 32));

            return (buffer, ExtendedTestLargePayloadMessage1.MsgId);
        }

        private static (byte[], int) SerializeLargePayloadMessage2(LargePayloadMessage2Data data)
        {
            byte[] buffer = new byte[ExtendedTestLargePayloadMessage2.MaxSize];

            Array.Copy(data.LargeData, 0, buffer, 0, Math.Min(data.LargeData.Length, 280));

            return (buffer, ExtendedTestLargePayloadMessage2.MsgId);
        }
    }
}
