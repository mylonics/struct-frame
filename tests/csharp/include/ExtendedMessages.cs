/**
 * Extended test message definitions (C#).
 * Provides GetMessage(index) function for extended message ID and payload testing.
 *
 * This file matches the C++ extended_messages.hpp structure.
 */

using System;
using System.Text;
using StructFrame;
using StructFrame.ExtendedTest;

namespace StructFrameTests
{
    /// <summary>
    /// Message provider struct for extended test messages.
    /// Provides MESSAGE_COUNT and GetMessage(index) function matching C++ pattern.
    /// </summary>
    public static class ExtendedMessages
    {
        // Message count
        public const int MESSAGE_COUNT = 17;

        // ============================================================================
        // Helper functions to create messages (like C++ create_* functions)
        // ============================================================================

        private static ExtendedIdMessage1 CreateExtId1()
        {
            var msg = new ExtendedIdMessage1();
            msg.SequenceNumber = 12345678;
            var label = Encoding.UTF8.GetBytes("Test Label Extended 1");
            msg.Label = new byte[32];
            Array.Copy(label, msg.Label, Math.Min(label.Length, 32));
            msg.Value = 3.14159f;
            msg.Enabled = true;
            return msg;
        }

        private static ExtendedIdMessage2 CreateExtId2()
        {
            var msg = new ExtendedIdMessage2();
            msg.SensorId = -42;
            msg.Reading = 2.718281828;
            msg.StatusCode = 50000;
            var desc = "Extended ID test message 2";
            msg.DescriptionLength = (byte)desc.Length;
            msg.DescriptionData = new byte[64];
            Array.Copy(Encoding.UTF8.GetBytes(desc), msg.DescriptionData, desc.Length);
            return msg;
        }

        private static ExtendedIdMessage3 CreateExtId3()
        {
            var msg = new ExtendedIdMessage3();
            msg.Timestamp = 1704067200000000UL;
            msg.Temperature = -40;
            msg.Humidity = 85;
            var locationBytes = Encoding.UTF8.GetBytes("Sensor Room A");
            msg.Location = new byte[32];
            Array.Copy(locationBytes, msg.Location, Math.Min(locationBytes.Length, 32));
            return msg;
        }

        private static ExtendedIdMessage4 CreateExtId4()
        {
            var msg = new ExtendedIdMessage4();
            msg.EventId = 999999;
            msg.EventType = 42;
            msg.EventTime = 1704067200000L;
            var data = "Event payload with extended message ID";
            msg.EventDataLength = (byte)data.Length;
            msg.EventDataData = new byte[64];
            Array.Copy(Encoding.UTF8.GetBytes(data), msg.EventDataData, data.Length);
            return msg;
        }

        private static ExtendedIdMessage5 CreateExtId5()
        {
            var msg = new ExtendedIdMessage5();
            msg.XPosition = 100.5f;
            msg.YPosition = -200.25f;
            msg.ZPosition = 50.125f;
            msg.FrameNumber = 1000000;
            return msg;
        }

        private static ExtendedIdMessage6 CreateExtId6()
        {
            var msg = new ExtendedIdMessage6();
            msg.CommandId = -12345;
            msg.Parameter1 = 1000;
            msg.Parameter2 = 2000;
            msg.Acknowledged = false;
            var name = Encoding.UTF8.GetBytes("CALIBRATE_SENSOR");
            msg.CommandName = new byte[32];
            Array.Copy(name, msg.CommandName, Math.Min(name.Length, 32));
            return msg;
        }

        private static ExtendedIdMessage7 CreateExtId7()
        {
            var msg = new ExtendedIdMessage7();
            msg.Counter = 4294967295;
            msg.Average = 123.456789;
            msg.Minimum = -999.99f;
            msg.Maximum = 999.99f;
            return msg;
        }

        private static ExtendedIdMessage8 CreateExtId8()
        {
            var msg = new ExtendedIdMessage8();
            msg.Level = 255;
            msg.Offset = -32768;
            msg.Duration = 86400000;
            var tag = Encoding.UTF8.GetBytes("TEST123");
            msg.Tag = new byte[16];
            Array.Copy(tag, msg.Tag, Math.Min(tag.Length, 16));
            return msg;
        }

        private static ExtendedIdMessage9 CreateExtId9()
        {
            var msg = new ExtendedIdMessage9();
            msg.BigNumber = -9223372036854775807L;
            msg.BigUnsigned = 18446744073709551615UL;
            msg.PrecisionValue = 1.7976931348623157e+308;
            return msg;
        }

        private static ExtendedIdMessage10 CreateExtId10()
        {
            var msg = new ExtendedIdMessage10();
            msg.SmallValue = 256;
            var text = Encoding.UTF8.GetBytes("Boundary Test");
            msg.ShortText = new byte[16];
            Array.Copy(text, msg.ShortText, Math.Min(text.Length, 16));
            msg.Flag = true;
            return msg;
        }

        private static LargePayloadMessage1 CreateLarge1()
        {
            var msg = new LargePayloadMessage1();
            msg.SensorReadings = new float[64];
            for (int i = 0; i < 64; i++)
                msg.SensorReadings[i] = (float)(i + 1);
            msg.ReadingCount = 64;
            msg.Timestamp = 1704067200000000L;
            var name = Encoding.UTF8.GetBytes("Large Sensor Array Device");
            msg.DeviceName = new byte[32];
            Array.Copy(name, msg.DeviceName, Math.Min(name.Length, 32));
            return msg;
        }

        private static LargePayloadMessage2 CreateLarge2()
        {
            var msg = new LargePayloadMessage2();
            msg.LargeData = new byte[280];
            for (int i = 0; i < 256; i++)
                msg.LargeData[i] = (byte)i;
            for (int i = 256; i < 280; i++)
                msg.LargeData[i] = (byte)(i - 256);
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingleEmpty()
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = 0x0000000000000001UL;
            msg.TelemetryDataCount = 0;
            msg.TelemetryDataData = new byte[250];
            msg.Crc = 0x00000001;
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingleSingle()
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = 0x0000000000000002UL;
            msg.TelemetryDataCount = 1;
            msg.TelemetryDataData = new byte[250];
            msg.TelemetryDataData[0] = 42;
            msg.Crc = 0x00000002;
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingleThird()
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = 0x0000000000000003UL;
            msg.TelemetryDataCount = 83;
            msg.TelemetryDataData = new byte[250];
            for (int i = 0; i < 83; i++)
                msg.TelemetryDataData[i] = (byte)i;
            msg.Crc = 0x00000003;
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingleAlmost()
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = 0x0000000000000004UL;
            msg.TelemetryDataCount = 249;
            msg.TelemetryDataData = new byte[250];
            for (int i = 0; i < 249; i++)
                msg.TelemetryDataData[i] = (byte)(i % 256);
            msg.Crc = 0x00000004;
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingleFull()
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = 0x0000000000000005UL;
            msg.TelemetryDataCount = 250;
            msg.TelemetryDataData = new byte[250];
            for (int i = 0; i < 250; i++)
                msg.TelemetryDataData[i] = (byte)(i % 256);
            msg.Crc = 0x00000005;
            return msg;
        }

        // ============================================================================
        // GetMessage(index) - unified interface matching C++ MessageProvider pattern
        // ============================================================================

        public static IStructFrameMessage GetMessage(int index)
        {
            switch (index)
            {
                case 0: return CreateExtId1();
                case 1: return CreateExtId2();
                case 2: return CreateExtId3();
                case 3: return CreateExtId4();
                case 4: return CreateExtId5();
                case 5: return CreateExtId6();
                case 6: return CreateExtId7();
                case 7: return CreateExtId8();
                case 8: return CreateExtId9();
                case 9: return CreateExtId10();
                case 10: return CreateLarge1();
                case 11: return CreateLarge2();
                case 12: return CreateExtVarSingleEmpty();
                case 13: return CreateExtVarSingleSingle();
                case 14: return CreateExtVarSingleThird();
                case 15: return CreateExtVarSingleAlmost();
                default: return CreateExtVarSingleFull();
            }
        }

        // ============================================================================
        // CheckMessage(index, info) - validates decoded message matches expected
        // This is the callback passed to ProfileRunner.Parse()
        // ============================================================================

        public static bool CheckMessage(int index, FrameMsgInfo info)
        {
            var expected = GetMessage(index);
            int expectedMsgId = expected.GetMsgId();

            // Check msg_id matches
            if (info.MsgId != expectedMsgId) return false;

            // Deserialize based on msg_id
            IStructFrameMessage decoded = null;
            if (info.MsgId == ExtendedIdMessage1.MsgId)
                decoded = ExtendedIdMessage1.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage2.MsgId)
                decoded = ExtendedIdMessage2.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage3.MsgId)
                decoded = ExtendedIdMessage3.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage4.MsgId)
                decoded = ExtendedIdMessage4.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage5.MsgId)
                decoded = ExtendedIdMessage5.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage6.MsgId)
                decoded = ExtendedIdMessage6.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage7.MsgId)
                decoded = ExtendedIdMessage7.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage8.MsgId)
                decoded = ExtendedIdMessage8.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage9.MsgId)
                decoded = ExtendedIdMessage9.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage10.MsgId)
                decoded = ExtendedIdMessage10.Deserialize(info);
            else if (info.MsgId == LargePayloadMessage1.MsgId)
                decoded = LargePayloadMessage1.Deserialize(info);
            else if (info.MsgId == LargePayloadMessage2.MsgId)
                decoded = LargePayloadMessage2.Deserialize(info);
            else if (info.MsgId == ExtendedVariableSingleArray.MsgId)
                decoded = ExtendedVariableSingleArray.Deserialize(info);

            if (decoded == null) return false;

            // Compare serialized bytes
            var decodedBytes = decoded.Serialize();
            var expectedBytes = expected.Serialize();

            if (decodedBytes.Length != expectedBytes.Length) return false;
            for (int i = 0; i < decodedBytes.Length; i++)
            {
                if (decodedBytes[i] != expectedBytes[i]) return false;
            }

            return true;
        }
    }
}
