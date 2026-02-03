/**
 * Standard test message definitions (C#).
 * Provides GetMessage(index) function for test messages.
 *
 * This file matches the C++ standard_messages.hpp structure.
 */

using System;
using System.Text;
using StructFrame;
using StructFrame.SerializationTest;

namespace StructFrameTests
{
    /// <summary>
    /// Message provider struct for standard test messages.
    /// Provides MESSAGE_COUNT and GetMessage(index) function matching C++ pattern.
    /// </summary>
    public static class StandardMessages
    {
        // Message count
        public const int MESSAGE_COUNT = 17;

        // ============================================================================
        // Helper functions to create messages (like C++ create_* functions)
        // ============================================================================

        private static SerializationTestSerializationTestMessage CreateSerializationTest(
            uint magic, string str, float flt, bool bl, int[] arr)
        {
            var msg = new SerializationTestSerializationTestMessage();
            msg.MagicNumber = magic;
            msg.TestFloat = flt;
            msg.TestBool = bl;

            var stringBytes = Encoding.UTF8.GetBytes(str);
            msg.TestStringLength = (byte)Math.Min(stringBytes.Length, 64);
            msg.TestStringData = new byte[64];
            Array.Copy(stringBytes, msg.TestStringData, msg.TestStringLength);

            msg.TestArrayCount = (byte)Math.Min(arr.Length, 5);
            msg.TestArrayData = new int[5];
            for (int i = 0; i < msg.TestArrayCount; i++)
                msg.TestArrayData[i] = arr[i];

            return msg;
        }

        private static SerializationTestBasicTypesMessage CreateBasicTypes(
            sbyte si, short mi, int ri, long li,
            byte su, ushort mu, uint ru, ulong lu,
            float sp, double dp, bool fl, string dev, string desc)
        {
            var msg = new SerializationTestBasicTypesMessage();
            msg.SmallInt = si;
            msg.MediumInt = mi;
            msg.RegularInt = ri;
            msg.LargeInt = li;
            msg.SmallUint = su;
            msg.MediumUint = mu;
            msg.RegularUint = ru;
            msg.LargeUint = lu;
            msg.SinglePrecision = sp;
            msg.DoublePrecision = dp;
            msg.Flag = fl;

            var deviceIdBytes = Encoding.UTF8.GetBytes(dev);
            msg.DeviceId = new byte[32];
            Array.Copy(deviceIdBytes, msg.DeviceId, Math.Min(deviceIdBytes.Length, 32));

            var descBytes = Encoding.UTF8.GetBytes(desc);
            msg.DescriptionLength = (byte)Math.Min(descBytes.Length, 128);
            msg.DescriptionData = new byte[128];
            Array.Copy(descBytes, msg.DescriptionData, msg.DescriptionLength);

            return msg;
        }

        private static SerializationTestUnionTestMessage CreateUnionWithArray()
        {
            var msg = new SerializationTestUnionTestMessage();
            msg.PayloadDiscriminator = SerializationTestComprehensiveArrayMessage.MsgId;

            var arr = new SerializationTestComprehensiveArrayMessage();
            
            arr.FixedInts = new int[] { 10, 20, 30 };
            arr.FixedFloats = new float[] { 1.5f, 2.5f };
            arr.FixedBools = new bool[] { true, false, true, false };
            
            arr.BoundedUintsCount = 2;
            arr.BoundedUintsData = new ushort[] { 100, 200, 0 };
            
            arr.BoundedDoublesCount = 1;
            arr.BoundedDoublesData = new double[] { 3.14159, 0 };
            
            // Fixed strings: 2 strings, 8 chars each
            arr.FixedStrings = new byte[16];
            var hello = Encoding.UTF8.GetBytes("Hello");
            var world = Encoding.UTF8.GetBytes("World");
            Array.Copy(hello, 0, arr.FixedStrings, 0, Math.Min(hello.Length, 8));
            Array.Copy(world, 0, arr.FixedStrings, 8, Math.Min(world.Length, 8));
            
            // Bounded strings: 1 string
            arr.BoundedStringsCount = 1;
            arr.BoundedStringsData = new byte[24];
            var test = Encoding.UTF8.GetBytes("Test");
            Array.Copy(test, 0, arr.BoundedStringsData, 0, Math.Min(test.Length, 12));
            
            arr.FixedStatuses = new byte[] { (byte)SerializationTestStatus.ACTIVE, (byte)SerializationTestStatus.ERROR };
            
            arr.BoundedStatusesCount = 1;
            arr.BoundedStatusesData = new byte[] { (byte)SerializationTestStatus.INACTIVE, 0 };
            
            arr.FixedSensors = new SerializationTestSensor[1];
            arr.FixedSensors[0] = new SerializationTestSensor
            {
                Id = 1,
                Value = 25.5f,
                Status = SerializationTestStatus.ACTIVE,
                Name = new byte[16]
            };
            var sensorName = Encoding.UTF8.GetBytes("TempSensor");
            Array.Copy(sensorName, arr.FixedSensors[0].Name, Math.Min(sensorName.Length, 16));
            
            arr.BoundedSensorsCount = 0;
            arr.BoundedSensorsData = new SerializationTestSensor[1];

            msg.ArrayPayload = arr;
            return msg;
        }

        private static SerializationTestUnionTestMessage CreateUnionWithTest()
        {
            var msg = new SerializationTestUnionTestMessage();
            msg.PayloadDiscriminator = SerializationTestSerializationTestMessage.MsgId;

            msg.TestPayload = CreateSerializationTest(
                0x12345678,
                "Union test message",
                99.99f,
                true,
                new int[] { 1, 2, 3, 4, 5 }
            );

            return msg;
        }

        private static SerializationTestVariableSingleArray CreateVariableSingleArrayEmpty()
        {
            var msg = new SerializationTestVariableSingleArray();
            msg.MessageId = 0x00000001;
            msg.PayloadCount = 0;
            msg.PayloadData = new byte[200];
            msg.Checksum = 0x0001;
            return msg;
        }

        private static SerializationTestVariableSingleArray CreateVariableSingleArraySingle()
        {
            var msg = new SerializationTestVariableSingleArray();
            msg.MessageId = 0x00000002;
            msg.PayloadCount = 1;
            msg.PayloadData = new byte[200];
            msg.PayloadData[0] = 42;
            msg.Checksum = 0x0002;
            return msg;
        }

        private static SerializationTestVariableSingleArray CreateVariableSingleArrayThird()
        {
            var msg = new SerializationTestVariableSingleArray();
            msg.MessageId = 0x00000003;
            msg.PayloadCount = 67;
            msg.PayloadData = new byte[200];
            for (int i = 0; i < 67; i++)
                msg.PayloadData[i] = (byte)i;
            msg.Checksum = 0x0003;
            return msg;
        }

        private static SerializationTestVariableSingleArray CreateVariableSingleArrayAlmost()
        {
            var msg = new SerializationTestVariableSingleArray();
            msg.MessageId = 0x00000004;
            msg.PayloadCount = 199;
            msg.PayloadData = new byte[200];
            for (int i = 0; i < 199; i++)
                msg.PayloadData[i] = (byte)i;
            msg.Checksum = 0x0004;
            return msg;
        }

        private static SerializationTestVariableSingleArray CreateVariableSingleArrayFull()
        {
            var msg = new SerializationTestVariableSingleArray();
            msg.MessageId = 0x00000005;
            msg.PayloadCount = 200;
            msg.PayloadData = new byte[200];
            for (int i = 0; i < 200; i++)
                msg.PayloadData[i] = (byte)i;
            msg.Checksum = 0x0005;
            return msg;
        }

        private static SerializationTestMessage CreateMessageTest()
        {
            var msg = new SerializationTestMessage();
            msg.Severity = SerializationTestMsgSeverity.SEV_MSG;
            var module = "test";
            msg.ModuleLength = (byte)module.Length;
            msg.ModuleData = Encoding.UTF8.GetBytes(module);
            var msgText = "A really good";
            msg.MsgLength = (byte)msgText.Length;
            msg.MsgData = Encoding.UTF8.GetBytes(msgText);
            return msg;
        }

        // ============================================================================
        // GetMessage(index) - unified interface matching C++ MessageProvider pattern
        // ============================================================================

        public static IStructFrameMessage GetMessage(int index)
        {
            switch (index)
            {
                case 0: return CreateSerializationTest(0xDEADBEEF, "Cross-platform test!", 3.14159f, true, new int[] { 100, 200, 300 });
                case 1: return CreateSerializationTest(0, "", 0.0f, false, new int[] { });
                case 2: return CreateSerializationTest(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true, new int[] { 2147483647, -2147483648, 0, 1, -1 });
                case 3: return CreateSerializationTest(0xAAAAAAAA, "Negative test", -273.15f, false, new int[] { -100, -200, -300, -400 });
                case 4: return CreateSerializationTest(1234567890, "Special: !@#$%^&*()", 2.71828f, true, new int[] { 0, 1, 1, 2, 3 });
                case 5: return CreateBasicTypes(42, 1000, 123456, 9876543210L, 200, 50000, 4000000000, 9223372036854775807UL, 3.14159f, 2.718281828459045, true, "DEVICE-001", "Basic test values");
                case 6: return CreateBasicTypes(0, 0, 0, 0L, 0, 0, 0, 0UL, 0.0f, 0.0, false, "", "");
                case 7: return CreateBasicTypes(-128, -32768, -2147483648, -9223372036854775807L, 255, 65535, 4294967295, 9223372036854775807UL, -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values");
                case 8: return CreateUnionWithArray();
                case 9: return CreateUnionWithTest();
                case 10: return CreateBasicTypes(-128, -32768, -2147483648, -9223372036854775807L, 255, 65535, 4294967295, 9223372036854775807UL, -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values");
                case 11: return CreateVariableSingleArrayEmpty();
                case 12: return CreateVariableSingleArraySingle();
                case 13: return CreateVariableSingleArrayThird();
                case 14: return CreateVariableSingleArrayAlmost();
                case 15: return CreateVariableSingleArrayFull();
                default: return CreateMessageTest();
            }
        }
    }
}
