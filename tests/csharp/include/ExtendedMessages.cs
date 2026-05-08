/**
 * Extended test message definitions (C#).
 * Three representative extended IDs (boundary/mid/high) + two large-payload
 * messages + five variable-array fill levels = 10 total.
 */

using System;
using System.Text;
using StructFrame;
using StructFrame.ExtendedTest;

namespace StructFrameTests
{
    public static class ExtendedMessages
    {
        public const int MESSAGE_COUNT = 10;

        // ============================================================================
        // Helper functions
        // ============================================================================

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

        private static ExtendedIdMessage9 CreateExtId9()
        {
            var msg = new ExtendedIdMessage9();
            msg.BigNumber = -9223372036854775807L;
            msg.BigUnsigned = 18446744073709551615UL;
            msg.PrecisionValue = 1.7976931348623157e+308;
            return msg;
        }

        private static LargePayloadMessage1 CreateLarge1()
        {
            var msg = new LargePayloadMessage1();
            msg.SensorReadings = new float[64];
            for (int i = 0; i < 64; i++) msg.SensorReadings[i] = (float)(i + 1);
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
            for (int i = 0; i < 256; i++) msg.LargeData[i] = (byte)i;
            for (int i = 256; i < 280; i++) msg.LargeData[i] = (byte)(i - 256);
            return msg;
        }

        private static ExtendedVariableSingleArray CreateExtVarSingle(ulong ts, byte count, byte[] data, uint crc)
        {
            var msg = new ExtendedVariableSingleArray();
            msg.Timestamp = ts;
            msg.TelemetryDataCount = count;
            msg.TelemetryDataData = new byte[250];
            if (data != null) Array.Copy(data, msg.TelemetryDataData, Math.Min(data.Length, 250));
            msg.Crc = crc;
            return msg;
        }

        // ============================================================================
        // GetMessage(index) - order: ExtId10, ExtId2, ExtId9, Large1, Large2, Var×5
        // ============================================================================

        public static IStructFrameMessage GetMessage(int index)
        {
            switch (index)
            {
                case 0: return CreateExtId10();
                case 1: return CreateExtId2();
                case 2: return CreateExtId9();
                case 3: return CreateLarge1();
                case 4: return CreateLarge2();
                case 5: return CreateExtVarSingle(1, 0,   null,                                          1);
                case 6: return CreateExtVarSingle(2, 1,   new byte[]{ 42 },                              2);
                case 7: { var d = new byte[83];  for (int i=0;i<83;i++)  d[i]=(byte)i;       return CreateExtVarSingle(3, 83,  d, 3); }
                case 8: { var d = new byte[249]; for (int i=0;i<249;i++) d[i]=(byte)(i%256); return CreateExtVarSingle(4, 249, d, 4); }
                default:{ var d = new byte[250]; for (int i=0;i<250;i++) d[i]=(byte)(i%256); return CreateExtVarSingle(5, 250, d, 5); }
            }
        }

        // ============================================================================
        // CheckMessage(index, info) - validates decoded message
        // ============================================================================

        public static bool CheckMessage(int index, FrameMsgInfo info)
        {
            var expected = GetMessage(index);
            if (info.MsgId != expected.GetMsgId()) return false;

            IStructFrameMessage decoded = null;
            if      (info.MsgId == ExtendedIdMessage10.MsgId)           decoded = ExtendedIdMessage10.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage2.MsgId)            decoded = ExtendedIdMessage2.Deserialize(info);
            else if (info.MsgId == ExtendedIdMessage9.MsgId)            decoded = ExtendedIdMessage9.Deserialize(info);
            else if (info.MsgId == LargePayloadMessage1.MsgId)          decoded = LargePayloadMessage1.Deserialize(info);
            else if (info.MsgId == LargePayloadMessage2.MsgId)          decoded = LargePayloadMessage2.Deserialize(info);
            else if (info.MsgId == ExtendedVariableSingleArray.MsgId)   decoded = ExtendedVariableSingleArray.Deserialize(info);

            if (decoded == null) return false;

            var decodedBytes  = decoded.Serialize();
            var expectedBytes = expected.Serialize();
            if (decodedBytes.Length != expectedBytes.Length) return false;
            for (int i = 0; i < decodedBytes.Length; i++)
                if (decodedBytes[i] != expectedBytes[i]) return false;
            return true;
        }
    }
}
