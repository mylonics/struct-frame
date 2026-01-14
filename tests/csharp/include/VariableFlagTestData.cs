/**
 * Variable flag truncation test data definitions (C#).
 * Tests that messages with variable=true properly truncate unused array space.
 *
 * Structure:
 * - Two identical messages (TruncationTestNonVariable and TruncationTestVariable)
 * - Only difference: TruncationTestVariable has option variable = true
 * - Both have data_array filled to 1/3 capacity (67 out of 200 bytes)
 * - Tests that variable message gets truncated and non-variable does not
 */

using System;
using System.Collections.Generic;
using StructFrame.SerializationTest;

namespace StructFrameTests
{
    public enum VariableMessageType
    {
        NonVariable = 0,
        Variable = 1
    }

    public class VariableMixedMessage
    {
        public VariableMessageType Type { get; set; }
        public Dictionary<string, object> Data { get; set; }
    }

    public static class VariableFlagTestData
    {
        // ============================================================================
        // Message count and order
        // ============================================================================

        public const int MESSAGE_COUNT = 2;

        public static int GetTestMessageCount()
        {
            return MESSAGE_COUNT;
        }

        // Generate byte array of sequential values (1/3 filled)
        private static List<byte> GenerateSequentialBytes()
        {
            var result = new List<byte>();
            for (int i = 0; i < 67; i++)  // 1/3 of 200
            {
                result.Add((byte)i);
            }
            return result;
        }

        // ============================================================================
        // Test message data
        // ============================================================================

        public static VariableMixedMessage GetTestMessage(int index)
        {
            if (index < 0 || index >= MESSAGE_COUNT)
            {
                return null;
            }

            var messages = new List<VariableMixedMessage>
            {
                // 0: TruncationTestNonVariable - 1/3 filled array (no truncation)
                new VariableMixedMessage
                {
                    Type = VariableMessageType.NonVariable,
                    Data = new Dictionary<string, object>
                    {
                        ["sequence_id"] = 0xDEADBEEFu,
                        ["data_array"] = GenerateSequentialBytes(),
                        ["footer"] = (ushort)0xCAFE
                    }
                },

                // 1: TruncationTestVariable - 1/3 filled array (with truncation)
                new VariableMixedMessage
                {
                    Type = VariableMessageType.Variable,
                    Data = new Dictionary<string, object>
                    {
                        ["sequence_id"] = 0xDEADBEEFu,
                        ["data_array"] = GenerateSequentialBytes(),
                        ["footer"] = (ushort)0xCAFE
                    }
                }
            };

            return messages[index];
        }

        // ============================================================================
        // Configuration
        // ============================================================================

        public static class Config
        {
            public const int MESSAGE_COUNT = VariableFlagTestData.MESSAGE_COUNT;
            public const int BUFFER_SIZE = 4096;
            public const string FORMATS_HELP = "profile_bulk";
            public const string TEST_NAME = "Variable Flag C#";

            public static bool SupportsFormat(string format)
            {
                return format == "profile_bulk";
            }
        }
    }
}
