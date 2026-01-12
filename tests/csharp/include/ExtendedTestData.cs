/**
 * Extended test message data definitions (C#).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * This module follows the same pattern as C, C++, TypeScript, and JavaScript
 * test data files.
 */

using System;
using StructFrame;
using StructFrame.ExtendedTest;

// Type aliases to match expected names
using ExtendedIdMessage1 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage1;
using ExtendedIdMessage2 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage2;
using ExtendedIdMessage3 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage3;
using ExtendedIdMessage4 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage4;
using ExtendedIdMessage5 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage5;
using ExtendedIdMessage6 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage6;
using ExtendedIdMessage7 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage7;
using ExtendedIdMessage8 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage8;
using ExtendedIdMessage9 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage9;
using ExtendedIdMessage10 = StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage10;
using LargePayloadMessage1 = StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage1;
using LargePayloadMessage2 = StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage2;

namespace StructFrameTests
{
    /// <summary>
    /// Wrapper for extended test messages that provides a common interface
    /// </summary>
    public class ExtendedTestMessage
    {
        public int MsgId { get; }
        public int MaxSize { get; }
        private readonly Func<byte[]> _packFunc;

        public ExtendedTestMessage(int msgId, int maxSize, Func<byte[]> packFunc)
        {
            MsgId = msgId;
            MaxSize = maxSize;
            _packFunc = packFunc;
        }

        public byte[] Pack() => _packFunc();
    }

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
        // Message length lookup (for IPC profile without length field)
        // ============================================================================

        public static int GetMessageLength(int msgId)
        {
            // Combined message ID (pkg_id << 8 | msg_id)
            switch (msgId)
            {
                case ExtendedIdMessage1.MsgId: return ExtendedIdMessage1.MaxSize;
                case ExtendedIdMessage2.MsgId: return ExtendedIdMessage2.MaxSize;
                case ExtendedIdMessage3.MsgId: return ExtendedIdMessage3.MaxSize;
                case ExtendedIdMessage4.MsgId: return ExtendedIdMessage4.MaxSize;
                case ExtendedIdMessage5.MsgId: return ExtendedIdMessage5.MaxSize;
                case ExtendedIdMessage6.MsgId: return ExtendedIdMessage6.MaxSize;
                case ExtendedIdMessage7.MsgId: return ExtendedIdMessage7.MaxSize;
                case ExtendedIdMessage8.MsgId: return ExtendedIdMessage8.MaxSize;
                case ExtendedIdMessage9.MsgId: return ExtendedIdMessage9.MaxSize;
                case ExtendedIdMessage10.MsgId: return ExtendedIdMessage10.MaxSize;
                case LargePayloadMessage1.MsgId: return LargePayloadMessage1.MaxSize;
                case LargePayloadMessage2.MsgId: return LargePayloadMessage2.MaxSize;
                default: return 0;
            }
        }

        // ============================================================================
        // Message creation
        // ============================================================================

        private static byte[] CreateLabelBytes(string text, int size)
        {
            var bytes = new byte[size];
            var textBytes = System.Text.Encoding.UTF8.GetBytes(text);
            Array.Copy(textBytes, bytes, Math.Min(textBytes.Length, size));
            return bytes;
        }

        public static (ExtendedTestMessage message, string typeName) GetExtendedTestMessage(int index)
        {
            switch (index)
            {
                // Message 0: ExtendedIdMessage1
                case 0:
                {
                    var msg = new ExtendedIdMessage1
                    {
                        SequenceNumber = 12345678,
                        Label = CreateLabelBytes("Test Label Extended 1", 32),
                        Value = 3.14159f,
                        Enabled = true
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage1.MsgId, ExtendedIdMessage1.MaxSize, msg.Pack), "ExtendedIdMessage1");
                }

                // Message 1: ExtendedIdMessage2
                case 1:
                {
                    var msg = new ExtendedIdMessage2
                    {
                        SensorId = -42,
                        Reading = 2.718281828,
                        StatusCode = 50000,
                        DescriptionLength = 26,
                        DescriptionData = CreateLabelBytes("Extended ID test message 2", 64)
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage2.MsgId, ExtendedIdMessage2.MaxSize, msg.Pack), "ExtendedIdMessage2");
                }

                // Message 2: ExtendedIdMessage3
                case 2:
                {
                    var msg = new ExtendedIdMessage3
                    {
                        Timestamp = 1704067200000000,
                        Temperature = -40,
                        Humidity = 85,
                        Location = CreateLabelBytes("Sensor Room A", 16)
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage3.MsgId, ExtendedIdMessage3.MaxSize, msg.Pack), "ExtendedIdMessage3");
                }

                // Message 3: ExtendedIdMessage4
                case 3:
                {
                    var msg = new ExtendedIdMessage4
                    {
                        EventId = 999999,
                        EventType = 42,
                        EventTime = 1704067200000,
                        EventDataLength = 38,
                        EventDataData = CreateLabelBytes("Event payload with extended message ID", 128)
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage4.MsgId, ExtendedIdMessage4.MaxSize, msg.Pack), "ExtendedIdMessage4");
                }

                // Message 4: ExtendedIdMessage5
                case 4:
                {
                    var msg = new ExtendedIdMessage5
                    {
                        XPosition = 1.0f,
                        YPosition = 2.0f,
                        ZPosition = 3.0f,
                        FrameNumber = 255
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage5.MsgId, ExtendedIdMessage5.MaxSize, msg.Pack), "ExtendedIdMessage5");
                }

                // Message 5: ExtendedIdMessage6
                case 5:
                {
                    var msg = new ExtendedIdMessage6
                    {
                        CommandId = 12345,
                        Parameter1 = 100,
                        Parameter2 = 200,
                        Acknowledged = true,
                        CommandName = CreateLabelBytes("Command parameters ext 6", 24)
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage6.MsgId, ExtendedIdMessage6.MaxSize, msg.Pack), "ExtendedIdMessage6");
                }

                // Message 6: ExtendedIdMessage7
                case 6:
                {
                    var msg = new ExtendedIdMessage7
                    {
                        Counter = 0xFFFFFFFF,
                        Average = 3.14159265,
                        Minimum = 1.0f,
                        Maximum = 100.0f
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage7.MsgId, ExtendedIdMessage7.MaxSize, msg.Pack), "ExtendedIdMessage7");
                }

                // Message 7: ExtendedIdMessage8
                case 7:
                {
                    var msg = new ExtendedIdMessage8
                    {
                        Level = 8,
                        Offset = 888,
                        Duration = 8888,
                        Tag = CreateLabelBytes("Tag8----", 8)
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage8.MsgId, ExtendedIdMessage8.MaxSize, msg.Pack), "ExtendedIdMessage8");
                }

                // Message 8: ExtendedIdMessage9
                case 8:
                {
                    var msg = new ExtendedIdMessage9
                    {
                        BigNumber = 9876543210,
                        BigUnsigned = 9876543210,
                        PrecisionValue = 9.87654321
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage9.MsgId, ExtendedIdMessage9.MaxSize, msg.Pack), "ExtendedIdMessage9");
                }

                // Message 9: ExtendedIdMessage10
                case 9:
                {
                    var msg = new ExtendedIdMessage10
                    {
                        SmallValue = 1000,
                        ShortText = CreateLabelBytes("Log message 10--", 16),
                        Flag = true
                    };
                    return (new ExtendedTestMessage(ExtendedIdMessage10.MsgId, ExtendedIdMessage10.MaxSize, msg.Pack), "ExtendedIdMessage10");
                }

                // Message 10: LargePayloadMessage1 - payload > 255 bytes
                case 10:
                {
                    var sensorReadings = new float[64];
                    for (int i = 0; i < 64; i++)
                    {
                        sensorReadings[i] = (float)i;
                    }
                    var msg = new LargePayloadMessage1
                    {
                        SensorReadings = sensorReadings,
                        ReadingCount = 64,
                        Timestamp = 1704067200000,
                        DeviceName = CreateLabelBytes("Large Payload Device 1", 32)
                    };
                    return (new ExtendedTestMessage(LargePayloadMessage1.MsgId, LargePayloadMessage1.MaxSize, msg.Pack), "LargePayloadMessage1");
                }

                // Message 11: LargePayloadMessage2 - payload > 255 bytes
                case 11:
                {
                    var largeData = new byte[280];
                    for (int i = 0; i < 280; i++)
                    {
                        largeData[i] = (byte)'Y';
                    }
                    var msg = new LargePayloadMessage2
                    {
                        LargeData = largeData
                    };
                    return (new ExtendedTestMessage(LargePayloadMessage2.MsgId, LargePayloadMessage2.MaxSize, msg.Pack), "LargePayloadMessage2");
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
