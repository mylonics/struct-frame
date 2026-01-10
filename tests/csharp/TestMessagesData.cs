/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 * Replaces JSON-based test data loading.
 */

using System;
using System.Collections.Generic;
using SerializationTest;

namespace StructFrameTests
{
    public enum MessageType
    {
        SerializationTest = 0,
        BasicTypes = 1,
        UnionTest = 2
    }

    public class MixedMessage
    {
        public MessageType Type { get; set; }
        public object Data { get; set; }
    }

    public static class TestMessagesData
    {
        /// <summary>
        /// Get the total number of test messages.
        /// </summary>
        public static int GetTestMessageCount()
        {
            return 11;
        }

        /// <summary>
        /// Get a test message by index.
        /// </summary>
        /// <param name="index">Message index (0-based)</param>
        /// <returns>Mixed message or null if invalid index</returns>
        public static MixedMessage GetTestMessage(int index)
        {
            if (index < 0 || index >= GetTestMessageCount())
            {
                return null;
            }

            var messages = new List<MixedMessage>
            {
                // 0: SerializationTestMessage - basic_values
                new MixedMessage
                {
                    Type = MessageType.SerializationTest,
                    Data = new Dictionary<string, object>
                    {
                        ["magic_number"] = 0xDEADBEEFu,
                        ["test_string"] = "Cross-platform test!",
                        ["test_float"] = 3.14159f,
                        ["test_bool"] = true,
                        ["test_array"] = new List<int> { 100, 200, 300 }
                    }
                },

                // 1: SerializationTestMessage - zero_values
                new MixedMessage
                {
                    Type = MessageType.SerializationTest,
                    Data = new Dictionary<string, object>
                    {
                        ["magic_number"] = 0u,
                        ["test_string"] = "",
                        ["test_float"] = 0.0f,
                        ["test_bool"] = false,
                        ["test_array"] = new List<int>()
                    }
                },

                // 2: SerializationTestMessage - max_values
                new MixedMessage
                {
                    Type = MessageType.SerializationTest,
                    Data = new Dictionary<string, object>
                    {
                        ["magic_number"] = 0xFFFFFFFFu,
                        ["test_string"] = "Maximum length test string for coverage!",
                        ["test_float"] = 999999.9f,
                        ["test_bool"] = true,
                        ["test_array"] = new List<int> { 2147483647, -2147483648, 0, 1, -1 }
                    }
                },

                // 3: SerializationTestMessage - negative_values
                new MixedMessage
                {
                    Type = MessageType.SerializationTest,
                    Data = new Dictionary<string, object>
                    {
                        ["magic_number"] = 0xAAAAAAAAu,
                        ["test_string"] = "Negative test",
                        ["test_float"] = -273.15f,
                        ["test_bool"] = false,
                        ["test_array"] = new List<int> { -100, -200, -300, -400 }
                    }
                },

                // 4: SerializationTestMessage - special_chars
                new MixedMessage
                {
                    Type = MessageType.SerializationTest,
                    Data = new Dictionary<string, object>
                    {
                        ["magic_number"] = 1234567890u,
                        ["test_string"] = "Special: !@#$%^&*()",
                        ["test_float"] = 2.71828f,
                        ["test_bool"] = true,
                        ["test_array"] = new List<int> { 0, 1, 1, 2, 3 }
                    }
                },

                // 5: BasicTypesMessage - basic_values
                new MixedMessage
                {
                    Type = MessageType.BasicTypes,
                    Data = new Dictionary<string, object>
                    {
                        ["small_int"] = (sbyte)42,
                        ["medium_int"] = (short)1000,
                        ["regular_int"] = 123456,
                        ["large_int"] = 9876543210L,
                        ["small_uint"] = (byte)200,
                        ["medium_uint"] = (ushort)50000,
                        ["regular_uint"] = 4000000000u,
                        ["large_uint"] = 9223372036854775807uL,
                        ["single_precision"] = 3.14159f,
                        ["double_precision"] = 2.718281828459045,
                        ["flag"] = true,
                        ["device_id"] = "DEVICE-001",
                        ["description"] = "Basic test values"
                    }
                },

                // 6: BasicTypesMessage - zero_values
                new MixedMessage
                {
                    Type = MessageType.BasicTypes,
                    Data = new Dictionary<string, object>
                    {
                        ["small_int"] = (sbyte)0,
                        ["medium_int"] = (short)0,
                        ["regular_int"] = 0,
                        ["large_int"] = 0L,
                        ["small_uint"] = (byte)0,
                        ["medium_uint"] = (ushort)0,
                        ["regular_uint"] = 0u,
                        ["large_uint"] = 0uL,
                        ["single_precision"] = 0.0f,
                        ["double_precision"] = 0.0,
                        ["flag"] = false,
                        ["device_id"] = "",
                        ["description"] = ""
                    }
                },

                // 7: BasicTypesMessage - negative_values
                new MixedMessage
                {
                    Type = MessageType.BasicTypes,
                    Data = new Dictionary<string, object>
                    {
                        ["small_int"] = (sbyte)-128,
                        ["medium_int"] = (short)-32768,
                        ["regular_int"] = -2147483648,
                        ["large_int"] = -9223372036854775807L,
                        ["small_uint"] = (byte)255,
                        ["medium_uint"] = (ushort)65535,
                        ["regular_uint"] = 4294967295u,
                        ["large_uint"] = 9223372036854775807uL,
                        ["single_precision"] = -273.15f,
                        ["double_precision"] = -9999.999999,
                        ["flag"] = false,
                        ["device_id"] = "NEG-TEST",
                        ["description"] = "Negative and max values"
                    }
                },

                // 8: UnionTestMessage - with_array_payload
                new MixedMessage
                {
                    Type = MessageType.UnionTest,
                    Data = new Dictionary<string, object>
                    {
                        ["payload_type"] = 1, // UNION_PAYLOAD_COMPREHENSIVE_ARRAY
                        ["payload_type_name"] = "UNION_PAYLOAD_COMPREHENSIVE_ARRAY",
                        ["array_payload"] = new Dictionary<string, object>
                        {
                            ["fixed_ints"] = new List<int> { 10, 20, 30 },
                            ["fixed_floats"] = new List<float> { 1.5f, 2.5f },
                            ["fixed_bools"] = new List<bool> { true, false, true, false },
                            ["bounded_uints"] = new List<ushort> { 100, 200 },
                            ["bounded_doubles"] = new List<double> { 3.14159 },
                            ["fixed_strings"] = new List<string> { "Hello", "World" },
                            ["bounded_strings"] = new List<string> { "Test" },
                            ["fixed_statuses"] = new List<int> { 1, 2 }, // ACTIVE, ERROR
                            ["bounded_statuses"] = new List<int> { 0 }, // INACTIVE
                            ["fixed_sensors"] = new List<Dictionary<string, object>>
                            {
                                new Dictionary<string, object>
                                {
                                    ["id"] = (byte)1,
                                    ["value"] = 25.5f,
                                    ["status"] = 1,
                                    ["name"] = "TempSensor"
                                }
                            },
                            ["bounded_sensors"] = new List<Dictionary<string, object>>()
                        },
                        ["test_payload"] = null
                    }
                },

                // 9: UnionTestMessage - with_test_payload
                new MixedMessage
                {
                    Type = MessageType.UnionTest,
                    Data = new Dictionary<string, object>
                    {
                        ["payload_type"] = 2, // UNION_PAYLOAD_SERIALIZATION_TEST
                        ["payload_type_name"] = "UNION_PAYLOAD_SERIALIZATION_TEST",
                        ["array_payload"] = null,
                        ["test_payload"] = new Dictionary<string, object>
                        {
                            ["magic_number"] = 0x12345678u,
                            ["test_string"] = "Union test message",
                            ["test_float"] = 99.99f,
                            ["test_bool"] = true,
                            ["test_array"] = new List<int> { 1, 2, 3, 4, 5 }
                        }
                    }
                },

                // 10: BasicTypesMessage - negative_values (duplicate)
                new MixedMessage
                {
                    Type = MessageType.BasicTypes,
                    Data = new Dictionary<string, object>
                    {
                        ["small_int"] = (sbyte)-128,
                        ["medium_int"] = (short)-32768,
                        ["regular_int"] = -2147483648,
                        ["large_int"] = -9223372036854775807L,
                        ["small_uint"] = (byte)255,
                        ["medium_uint"] = (ushort)65535,
                        ["regular_uint"] = 4294967295u,
                        ["large_uint"] = 9223372036854775807uL,
                        ["single_precision"] = -273.15f,
                        ["double_precision"] = -9999.999999,
                        ["flag"] = false,
                        ["device_id"] = "NEG-TEST",
                        ["description"] = "Negative and max values"
                    }
                }
            };

            return messages[index];
        }
    }
}
