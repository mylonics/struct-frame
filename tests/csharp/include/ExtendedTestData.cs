/**
 * Extended test message data definitions (C#).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * This module follows the same pattern as C, C++, TypeScript, and JavaScript
 * test data files.
 */

#nullable enable

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
using ExtendedVariableSingleArray = StructFrame.ExtendedTest.ExtendedTestExtendedVariableSingleArray;

namespace StructFrameTests
{
    /// <summary>
    /// Wrapper for extended test messages that provides a common interface
    /// </summary>
    public static class ExtendedTestData
    {
        // ============================================================================
        // Message count
        // ============================================================================

        public const int MESSAGE_COUNT = 17;
        
        // Variable message index trackers
        private static int _extVarSingleEncodeIdx = 0;
        private static int _extVarSingleValidateIdx = 0;
        
        // Cached variable messages
        private static ExtendedVariableSingleArray[]? _extVarSingleMsgs = null;

        public static int GetExtendedTestMessageCount()
        {
            return MESSAGE_COUNT;
        }
        
        public static void ResetState()
        {
            _extVarSingleEncodeIdx = 0;
            _extVarSingleValidateIdx = 0;
        }
        
        private static ExtendedVariableSingleArray[] GetExtVarSingleMessages()
        {
            if (_extVarSingleMsgs != null) return _extVarSingleMsgs;
            
            _extVarSingleMsgs = new ExtendedVariableSingleArray[5];
            
            // Empty payload (0 elements)
            _extVarSingleMsgs[0] = new ExtendedVariableSingleArray
            {
                Timestamp = 0x0000000000000001UL,
                TelemetryDataCount = 0,
                TelemetryDataData = new byte[250],
                Crc = 0x00000001
            };
            
            // Single element
            _extVarSingleMsgs[1] = new ExtendedVariableSingleArray
            {
                Timestamp = 0x0000000000000002UL,
                TelemetryDataCount = 1,
                TelemetryDataData = new byte[250],
                Crc = 0x00000002
            };
            _extVarSingleMsgs[1].TelemetryDataData[0] = 42;
            
            // One-third filled (83 elements for max_size=250)
            _extVarSingleMsgs[2] = new ExtendedVariableSingleArray
            {
                Timestamp = 0x0000000000000003UL,
                TelemetryDataCount = 83,
                TelemetryDataData = new byte[250],
                Crc = 0x00000003
            };
            for (int i = 0; i < 83; i++)
            {
                _extVarSingleMsgs[2].TelemetryDataData[i] = (byte)i;
            }
            
            // One position empty (249 elements)
            _extVarSingleMsgs[3] = new ExtendedVariableSingleArray
            {
                Timestamp = 0x0000000000000004UL,
                TelemetryDataCount = 249,
                TelemetryDataData = new byte[250],
                Crc = 0x00000004
            };
            for (int i = 0; i < 249; i++)
            {
                _extVarSingleMsgs[3].TelemetryDataData[i] = (byte)(i % 256);
            }
            
            // Full (250 elements)
            _extVarSingleMsgs[4] = new ExtendedVariableSingleArray
            {
                Timestamp = 0x0000000000000005UL,
                TelemetryDataCount = 250,
                TelemetryDataData = new byte[250],
                Crc = 0x00000005
            };
            for (int i = 0; i < 250; i++)
            {
                _extVarSingleMsgs[4].TelemetryDataData[i] = (byte)(i % 256);
            }
            
            return _extVarSingleMsgs;
        }
        
        public static ExtendedVariableSingleArray GetNextExtVarSingleForEncode()
        {
            return GetExtVarSingleMessages()[_extVarSingleEncodeIdx++];
        }
        
        public static ExtendedVariableSingleArray GetNextExtVarSingleForValidate()
        {
            return GetExtVarSingleMessages()[_extVarSingleValidateIdx++];
        }

        // ============================================================================
        // Message info lookup (unified size and magic numbers)
        // ============================================================================

        public static MessageInfo? GetMessageInfo(int msgId)
        {
            // Combined message ID (pkg_id << 8 | msg_id)
            switch (msgId)
            {
                case ExtendedIdMessage1.MsgId: return new MessageInfo(ExtendedIdMessage1.MaxSize, ExtendedIdMessage1.Magic1, ExtendedIdMessage1.Magic2);
                case ExtendedIdMessage2.MsgId: return new MessageInfo(ExtendedIdMessage2.MaxSize, ExtendedIdMessage2.Magic1, ExtendedIdMessage2.Magic2);
                case ExtendedIdMessage3.MsgId: return new MessageInfo(ExtendedIdMessage3.MaxSize, ExtendedIdMessage3.Magic1, ExtendedIdMessage3.Magic2);
                case ExtendedIdMessage4.MsgId: return new MessageInfo(ExtendedIdMessage4.MaxSize, ExtendedIdMessage4.Magic1, ExtendedIdMessage4.Magic2);
                case ExtendedIdMessage5.MsgId: return new MessageInfo(ExtendedIdMessage5.MaxSize, ExtendedIdMessage5.Magic1, ExtendedIdMessage5.Magic2);
                case ExtendedIdMessage6.MsgId: return new MessageInfo(ExtendedIdMessage6.MaxSize, ExtendedIdMessage6.Magic1, ExtendedIdMessage6.Magic2);
                case ExtendedIdMessage7.MsgId: return new MessageInfo(ExtendedIdMessage7.MaxSize, ExtendedIdMessage7.Magic1, ExtendedIdMessage7.Magic2);
                case ExtendedIdMessage8.MsgId: return new MessageInfo(ExtendedIdMessage8.MaxSize, ExtendedIdMessage8.Magic1, ExtendedIdMessage8.Magic2);
                case ExtendedIdMessage9.MsgId: return new MessageInfo(ExtendedIdMessage9.MaxSize, ExtendedIdMessage9.Magic1, ExtendedIdMessage9.Magic2);
                case ExtendedIdMessage10.MsgId: return new MessageInfo(ExtendedIdMessage10.MaxSize, ExtendedIdMessage10.Magic1, ExtendedIdMessage10.Magic2);
                case LargePayloadMessage1.MsgId: return new MessageInfo(LargePayloadMessage1.MaxSize, LargePayloadMessage1.Magic1, LargePayloadMessage1.Magic2);
                case LargePayloadMessage2.MsgId: return new MessageInfo(LargePayloadMessage2.MaxSize, LargePayloadMessage2.Magic1, LargePayloadMessage2.Magic2);
                case ExtendedVariableSingleArray.MsgId: return new MessageInfo(ExtendedVariableSingleArray.MaxSize, ExtendedVariableSingleArray.Magic1, ExtendedVariableSingleArray.Magic2);
                default: return null;
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

        public static (IStructFrameMessage? message, string? typeName) GetExtendedTestMessage(int index)
        {
            switch (index)
            {
                // Message 0: ExtendedIdMessage1 (matches C++ create_ext_id_1)
                case 0:
                {
                    var msg = new ExtendedIdMessage1
                    {
                        SequenceNumber = 12345678,
                        Label = CreateLabelBytes("Test Label Extended 1", 32),
                        Value = 3.14159f,
                        Enabled = true
                    };
                    return (msg, "ExtendedIdMessage1");
                }

                // Message 1: ExtendedIdMessage2 (matches C++ create_ext_id_2)
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
                    return (msg, "ExtendedIdMessage2");
                }

                // Message 2: ExtendedIdMessage3 (matches C++ create_ext_id_3)
                case 2:
                {
                    var msg = new ExtendedIdMessage3
                    {
                        Timestamp = 1704067200000000,
                        Temperature = -40,
                        Humidity = 85,
                        Location = CreateLabelBytes("Sensor Room A", 16)
                    };
                    return (msg, "ExtendedIdMessage3");
                }

                // Message 3: ExtendedIdMessage4 (matches C++ create_ext_id_4)
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
                    return (msg, "ExtendedIdMessage4");
                }

                // Message 4: ExtendedIdMessage5 (matches C++ create_ext_id_5)
                case 4:
                {
                    var msg = new ExtendedIdMessage5
                    {
                        XPosition = 100.5f,
                        YPosition = -200.25f,
                        ZPosition = 50.125f,
                        FrameNumber = 1000000
                    };
                    return (msg, "ExtendedIdMessage5");
                }

                // Message 5: ExtendedIdMessage6 (matches C++ create_ext_id_6)
                case 5:
                {
                    var msg = new ExtendedIdMessage6
                    {
                        CommandId = -12345,
                        Parameter1 = 1000,
                        Parameter2 = 2000,
                        Acknowledged = false,
                        CommandName = CreateLabelBytes("CALIBRATE_SENSOR", 24)
                    };
                    return (msg, "ExtendedIdMessage6");
                }

                // Message 6: ExtendedIdMessage7 (matches C++ create_ext_id_7)
                case 6:
                {
                    var msg = new ExtendedIdMessage7
                    {
                        Counter = 4294967295,
                        Average = 123.456789,
                        Minimum = -999.99f,
                        Maximum = 999.99f
                    };
                    return (msg, "ExtendedIdMessage7");
                }

                // Message 7: ExtendedIdMessage8 (matches C++ create_ext_id_8)
                case 7:
                {
                    var msg = new ExtendedIdMessage8
                    {
                        Level = 255,
                        Offset = -32768,
                        Duration = 86400000,
                        Tag = CreateLabelBytes("TEST123", 8)
                    };
                    return (msg, "ExtendedIdMessage8");
                }

                // Message 8: ExtendedIdMessage9 (matches C++ create_ext_id_9)
                case 8:
                {
                    var msg = new ExtendedIdMessage9
                    {
                        BigNumber = -9223372036854775807,
                        BigUnsigned = 18446744073709551615,
                        PrecisionValue = 1.7976931348623157e+308
                    };
                    return (msg, "ExtendedIdMessage9");
                }

                // Message 9: ExtendedIdMessage10 (matches C++ create_ext_id_10)
                case 9:
                {
                    var msg = new ExtendedIdMessage10
                    {
                        SmallValue = 256,
                        ShortText = CreateLabelBytes("Boundary Test", 16),
                        Flag = true
                    };
                    return (msg, "ExtendedIdMessage10");
                }

                // Message 10: LargePayloadMessage1 (matches C++ create_large_1)
                case 10:
                {
                    var sensorReadings = new float[64];
                    for (int i = 0; i < 64; i++)
                    {
                        sensorReadings[i] = (float)(i + 1);
                    }
                    var msg = new LargePayloadMessage1
                    {
                        SensorReadings = sensorReadings,
                        ReadingCount = 64,
                        Timestamp = 1704067200000000,
                        DeviceName = CreateLabelBytes("Large Sensor Array Device", 32)
                    };
                    return (msg, "LargePayloadMessage1");
                }

                // Message 11: LargePayloadMessage2 (matches C++ create_large_2)
                case 11:
                {
                    var largeData = new byte[280];
                    for (int i = 0; i < 256; i++)
                    {
                        largeData[i] = (byte)i;
                    }
                    for (int i = 256; i < 280; i++)
                    {
                        largeData[i] = (byte)(i - 256);
                    }
                    var msg = new LargePayloadMessage2
                    {
                        LargeData = largeData
                    };
                    return (msg, "LargePayloadMessage2");
                }

                // Messages 12-16: ExtendedVariableSingleArray with different fill levels
                case 12:
                case 13:
                case 14:
                case 15:
                case 16:
                {
                    var msg = GetNextExtVarSingleForEncode();
                    return (msg, "ExtendedVariableSingleArray");
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
            public const int MESSAGE_COUNT = 17;
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
