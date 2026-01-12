/**
 * Extended test message data definitions (C#).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * This module follows the same pattern as C, C++, TypeScript, and JavaScript
 * test data files.
 */

using System;
using ExtendedTest;

namespace StructFrameTests
{
    public static class ExtendedTestData
    {
        // ============================================================================
        // Message count
        // ============================================================================

        public const int MESSAGE_COUNT = 12;

        public static int GetExtendedTestMessageCount()
        {
            return MESSAGE_COUNT;
        }

        // ============================================================================
        // Message creation
        // ============================================================================

        public static (IStructFrameMessage message, string typeName) GetExtendedTestMessage(int index)
        {
            switch (index)
            {
                // Message 0: ExtendedIdMessage1
                case 0:
                    return (
                        new ExtendedIdMessage1
                        {
                            SequenceNumber = 12345678,
                            Label = System.Text.Encoding.UTF8.GetBytes("Test Label Extended 1"),
                            Value = 3.14159f,
                            Enabled = true
                        },
                        "ExtendedIdMessage1"
                    );

                // Message 1: ExtendedIdMessage2
                case 1:
                    return (
                        new ExtendedIdMessage2
                        {
                            SensorId = -42,
                            Reading = 2.718281828,
                            StatusCode = 50000,
                            Description = System.Text.Encoding.UTF8.GetBytes("Extended ID test message 2")
                        },
                        "ExtendedIdMessage2"
                    );

                // Message 2: ExtendedIdMessage3
                case 2:
                    return (
                        new ExtendedIdMessage3
                        {
                            Timestamp = 1704067200000000,
                            Temperature = -40,
                            Humidity = 85,
                            Location = System.Text.Encoding.UTF8.GetBytes("Sensor Room A")
                        },
                        "ExtendedIdMessage3"
                    );

                // Message 3: ExtendedIdMessage4
                case 3:
                    return (
                        new ExtendedIdMessage4
                        {
                            EventId = 999999,
                            EventType = 42,
                            EventTime = 1704067200000,
                            EventData = System.Text.Encoding.UTF8.GetBytes("Event payload with extended message ID")
                        },
                        "ExtendedIdMessage4"
                    );

                // Message 4: ExtendedIdMessage5
                case 4:
                    return (
                        new ExtendedIdMessage5
                        {
                            ConfigVersion = 255,
                            ConfigData = System.Text.Encoding.UTF8.GetBytes("Configuration data for extended message 5")
                        },
                        "ExtendedIdMessage5"
                    );

                // Message 5: ExtendedIdMessage6
                case 5:
                    return (
                        new ExtendedIdMessage6
                        {
                            CommandId = 12345,
                            CommandParams = System.Text.Encoding.UTF8.GetBytes("Command parameters for extended message 6")
                        },
                        "ExtendedIdMessage6"
                    );

                // Message 6: ExtendedIdMessage7
                case 6:
                    return (
                        new ExtendedIdMessage7
                        {
                            StateFlags = 0xFFFFFFFF,
                            StateInfo = System.Text.Encoding.UTF8.GetBytes("State information extended message 7")
                        },
                        "ExtendedIdMessage7"
                    );

                // Message 7: ExtendedIdMessage8
                case 7:
                    return (
                        new ExtendedIdMessage8
                        {
                            DiagnosticsCode = 8888,
                            DiagnosticsDetails = System.Text.Encoding.UTF8.GetBytes("Diagnostics details for extended message 8")
                        },
                        "ExtendedIdMessage8"
                    );

                // Message 8: ExtendedIdMessage9
                case 8:
                    return (
                        new ExtendedIdMessage9
                        {
                            MetricsCounter = 9876543210,
                            MetricsData = System.Text.Encoding.UTF8.GetBytes("Metrics data extended message 9")
                        },
                        "ExtendedIdMessage9"
                    );

                // Message 9: ExtendedIdMessage10
                case 9:
                    return (
                        new ExtendedIdMessage10
                        {
                            LogLevel = 3,
                            LogMessage = System.Text.Encoding.UTF8.GetBytes("Log message from extended message 10")
                        },
                        "ExtendedIdMessage10"
                    );

                // Message 10: LargePayloadMessage1 - payload > 255 bytes
                case 10:
                {
                    var largeData = new byte[300];
                    for (int i = 0; i < largeData.Length; i++)
                    {
                        largeData[i] = (byte)'X';
                    }
                    return (
                        new LargePayloadMessage1
                        {
                            PayloadId = 1,
                            Data = largeData
                        },
                        "LargePayloadMessage1"
                    );
                }

                // Message 11: LargePayloadMessage2 - payload > 255 bytes
                case 11:
                {
                    var largeData = new byte[400];
                    for (int i = 0; i < largeData.Length; i++)
                    {
                        largeData[i] = (byte)'Y';
                    }
                    return (
                        new LargePayloadMessage2
                        {
                            ChunkNumber = 42,
                            ChunkData = largeData
                        },
                        "LargePayloadMessage2"
                    );
                }

                default:
                    return (null, null);
            }
        }

        // ============================================================================
        // Test configuration
        // ============================================================================

        public static class Config
        {
            public const int MESSAGE_COUNT = 12;
            public const int BUFFER_SIZE = 8192;
            public const string FORMATS_HELP = "profile_bulk, profile_network";
            public const string TEST_NAME = "extended";

            public static bool SupportsFormat(string formatName)
            {
                return formatName == "profile_bulk" || formatName == "profile_network";
            }
        }
    }
}
