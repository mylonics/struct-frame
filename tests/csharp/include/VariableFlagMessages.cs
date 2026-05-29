/**
 * Variable flag test SerializationTestMessage definitions (C#).
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
    /// SerializationTestMessage provider struct for variable flag test messages.
    /// Provides SerializationTestMessage_COUNT and GetMessage(index) function matching C++ pattern.
    /// </summary>
    public static class VariableFlagMessages
    {
        // Message count
        public const int MESSAGE_COUNT = 7;

        // ============================================================================
        // Helper functions to create messages (like C++ create_* functions)
        // ============================================================================

        private static TruncationTestNonVariable CreateNonVariable1_3Filled()
        {
            var msg = new TruncationTestNonVariable();
            msg.SequenceId = 0xDEADBEEF;
            msg.DataArrayCount = 67;
            msg.DataArrayData = new byte[200];
            for (int i = 0; i < 67; i++)
                msg.DataArrayData[i] = (byte)i;
            msg.Footer = 0xCAFE;
            return msg;
        }

        private static TruncationTestVariable CreateVariable1_3Filled()
        {
            var msg = new TruncationTestVariable();
            msg.SequenceId = 0xDEADBEEF;
            msg.DataArrayCount = 67;
            msg.DataArrayData = new byte[200];
            for (int i = 0; i < 67; i++)
                msg.DataArrayData[i] = (byte)i;
            msg.Footer = 0xCAFE;
            return msg;
        }

        private static NestedVariableMessage CreateNestedVariable()
        {
            var payload = new NestedPayload();
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

            var msg = new NestedVariableMessage();
            msg.Sequence = 0x12345678;
            msg.Payload = payload;
            msg.DescriptionLength = 20;
            msg.DescriptionData = new byte[64];
            var descBytes = System.Text.Encoding.ASCII.GetBytes("nested variable test");
            Array.Copy(descBytes, msg.DescriptionData, descBytes.Length);
            return msg;
        }

        private static VariableMultipleArrays CreateMultipleArrays()
        {
            var msg = new VariableMultipleArrays();
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

        private static VariableMixedFields CreateMixedFields()
        {
            var msg = new VariableMixedFields();
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

        private static VariableEnvelopeMessage CreateVariableEnvelopeFieldOrder()
        {
            var payload = new VarEnvPayloadA();
            payload.Code = 0x42;
            payload.Value = 0x1234;
            return VariableEnvelopeMessage.Wrap(payload, 7);
        }

        private static VariableEnvelopeMsgIdMessage CreateVariableEnvelopeMsgId()
        {
            var inner = new BasicTypesMessage();
            inner.Flag = true;
            inner.SmallUint = 0xAB;
            inner.MediumUint = 0xCDEF;
            inner.RegularUint = 0x12345678U;
            inner.DeviceId = new byte[32];
            inner.DescriptionData = new byte[128];
            return VariableEnvelopeMsgIdMessage.Wrap(inner, 3);
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
            else if (index == 4)
                return CreateMixedFields();
            else if (index == 5)
                return CreateVariableEnvelopeFieldOrder();
            else
                return CreateVariableEnvelopeMsgId();
        }

        // ============================================================================
        // CheckMessage(index, info) - validates decoded SerializationTestMessage matches expected
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
            if (info.MsgId == TruncationTestNonVariable.MsgId)
                decoded = TruncationTestNonVariable.Deserialize(info);
            else if (info.MsgId == TruncationTestVariable.MsgId)
                decoded = TruncationTestVariable.Deserialize(info);
            else if (info.MsgId == NestedVariableMessage.MsgId)
                decoded = NestedVariableMessage.Deserialize(info);
            else if (info.MsgId == VariableMultipleArrays.MsgId)
                decoded = VariableMultipleArrays.Deserialize(info);
            else if (info.MsgId == VariableMixedFields.MsgId)
                decoded = VariableMixedFields.Deserialize(info);
            else if (info.MsgId == VariableEnvelopeMessage.MsgId)
                decoded = VariableEnvelopeMessage.Deserialize(info);
            else if (info.MsgId == VariableEnvelopeMsgIdMessage.MsgId)
                decoded = VariableEnvelopeMsgIdMessage.Deserialize(info);

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
