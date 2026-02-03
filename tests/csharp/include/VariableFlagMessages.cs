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
        public const int MESSAGE_COUNT = 2;

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

        // ============================================================================
        // GetMessage(index) - unified interface matching C++ MessageProvider pattern
        // ============================================================================

        public static IStructFrameMessage GetMessage(int index)
        {
            if (index == 0)
                return CreateNonVariable1_3Filled();
            else
                return CreateVariable1_3Filled();
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
