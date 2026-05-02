/**
 * Variable flag test message definitions (C#).
 * Provides GetMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

using System;
using StructFrame;
using StructFrame.SerializationTest;

namespace StructFrameTests
{
    /// <summary>
    /// Message provider struct for variable flag test messages.
    /// Provides MESSAGE_COUNT and GetMessage(index) function matching C++ pattern.
    /// </summary>
    public static class VariableFlagMessages
    {
        // Message count
        public const int MESSAGE_COUNT = 5;

        // ============================================================================
        // Helper functions to create messages (like C++ create_* functions)
        // ============================================================================

        private static SerializationTestTruncationTestNonVariable CreateNonVariable1_3Filled()
        {
            var msg = new SerializationTestTruncationTestNonVariable();
            msg.SequenceId = 0xDEADBEEF;
            msg.DataArrayCount = 67;
            msg.DataArrayData = new byte[200];
            for (int i = 0; i < 67; i++)
                msg.DataArrayData[i] = (byte)i;
            msg.Footer = 0xCAFE;
            return msg;
        }

        private static SerializationTestTruncationTestVariable CreateVariable1_3Filled()
        {
            var msg = new SerializationTestTruncationTestVariable();
            msg.SequenceId = 0xDEADBEEF;
            msg.DataArrayCount = 67;
            msg.DataArrayData = new byte[200];
            for (int i = 0; i < 67; i++)
                msg.DataArrayData[i] = (byte)i;
            msg.Footer = 0xCAFE;
            return msg;
        }

        private static SerializationTestNestedVariableMessage CreateNestedVariable()
        {
            var payload = new SerializationTestNestedPayload();
            payload.Id = 7;
            payload.LabelLength = 5;
            payload.LabelData = new byte[32];
            var labelBytes = System.Text.Encoding.ASCII.GetBytes("Hello");
            Array.Copy(labelBytes, payload.LabelData, labelBytes.Length);
            payload.SamplesCount = 3;
            payload.SamplesData = new ushort[16];
            payload.SamplesData[0] = 10;
            payload.SamplesData[1] = 20;
            payload.SamplesData[2] = 30;

            var msg = new SerializationTestNestedVariableMessage();
            msg.Sequence = 0x12345678;
            msg.Payload = payload;
            msg.DescriptionLength = 20;
            msg.DescriptionData = new byte[64];
            var descBytes = System.Text.Encoding.ASCII.GetBytes("nested variable test");
            Array.Copy(descBytes, msg.DescriptionData, descBytes.Length);
            return msg;
        }

        private static SerializationTestVariableMultipleArrays CreateMultipleArrays()
        {
            var msg = new SerializationTestVariableMultipleArrays();
            msg.Type = 5;
            msg.ReadingsCount = 3;
            msg.ReadingsData = new int[50];
            msg.ReadingsData[0] = 100;
            msg.ReadingsData[1] = 200;
            msg.ReadingsData[2] = 300;
            msg.ValuesCount = 2;
            msg.ValuesData = new float[25];
            msg.ValuesData[0] = 1.5f;
            msg.ValuesData[1] = 2.5f;
            msg.LabelLength = 17;
            msg.LabelData = new byte[64];
            var lbl = System.Text.Encoding.ASCII.GetBytes("multi arrays test");
            Array.Copy(lbl, msg.LabelData, lbl.Length);
            return msg;
        }

        private static SerializationTestVariableMixedFields CreateMixedFields()
        {
            var msg = new SerializationTestVariableMixedFields();
            msg.FixedId = 0xABCD1234;
            msg.FixedValue = 3.14f;
            msg.FixedName = new byte[16];
            var nameBytes = System.Text.Encoding.ASCII.GetBytes("DeviceName");
            Array.Copy(nameBytes, msg.FixedName, nameBytes.Length);
            msg.VariableDataCount = 5;
            msg.VariableDataData = new ushort[100];
            msg.VariableDataData[0] = 1000;
            msg.VariableDataData[1] = 2000;
            msg.VariableDataData[2] = 3000;
            msg.VariableDataData[3] = 4000;
            msg.VariableDataData[4] = 5000;
            msg.VariableDescLength = 17;
            msg.VariableDescData = new byte[128];
            var vdBytes = System.Text.Encoding.ASCII.GetBytes("mixed fields test");
            Array.Copy(vdBytes, msg.VariableDescData, vdBytes.Length);
            return msg;
        }

        // ============================================================================
        // GetMessage(index) - unified interface matching C++ MessageProvider pattern
        // ============================================================================

        public static IStructFrameMessage GetMessage(int index)
        {
            if (index == 0)
                return CreateNonVariable1_3Filled();
            else if (index == 1)
                return CreateVariable1_3Filled();
            else if (index == 2)
                return CreateNestedVariable();
            else if (index == 3)
                return CreateMultipleArrays();
            else
                return CreateMixedFields();
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
            if (info.MsgId == SerializationTestTruncationTestNonVariable.MsgId)
                decoded = SerializationTestTruncationTestNonVariable.Deserialize(info);
            else if (info.MsgId == SerializationTestTruncationTestVariable.MsgId)
                decoded = SerializationTestTruncationTestVariable.Deserialize(info);
            else if (info.MsgId == SerializationTestNestedVariableMessage.MsgId)
                decoded = SerializationTestNestedVariableMessage.Deserialize(info);
            else if (info.MsgId == SerializationTestVariableMultipleArrays.MsgId)
                decoded = SerializationTestVariableMultipleArrays.Deserialize(info);
            else if (info.MsgId == SerializationTestVariableMixedFields.MsgId)
                decoded = SerializationTestVariableMixedFields.Deserialize(info);

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
