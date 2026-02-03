/**
 * Profile runner (C#).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 */

using System;
using StructFrame;
using StructFrame.SerializationTest;
using ExtendedMessageDefinitions = StructFrame.ExtendedTest.MessageDefinitions;

namespace StructFrameTests
{
    /// <summary>
    /// Delegate type for GetMessage function
    /// </summary>
    public delegate IStructFrameMessage GetMessageFunc(int index);

    /// <summary>
    /// Delegate type for get_message_info function
    /// </summary>
    public delegate MessageInfo? GetMessageInfoFunc(int msgId);

    /// <summary>
    /// Profile runner - Low-level encoding and decoding for message providers
    /// </summary>
    public static class ProfileRunner
    {
        private const int BUFFER_SIZE = 16384;

        /// <summary>
        /// Encode all messages to buffer using BufferWriter.
        /// Returns total bytes written.
        /// </summary>
        public static int Encode(
            int messageCount,
            GetMessageFunc getMessage,
            string profile,
            byte[] buffer)
        {
            BufferWriter writer = CreateWriter(profile);
            if (writer == null) return 0;

            writer.SetBuffer(buffer);

            for (int i = 0; i < messageCount; i++)
            {
                var msg = getMessage(i);
                writer.Write(msg);
            }

            return writer.Size;
        }

        /// <summary>
        /// Parse all messages from buffer using AccumulatingReader.
        /// Returns the number of messages that matched (messageCount if all pass).
        /// </summary>
        public static int Parse(
            int messageCount,
            GetMessageFunc getMessage,
            GetMessageInfoFunc getMessageInfo,
            string profile,
            byte[] buffer,
            int bufferLength)
        {
            AccumulatingReader reader = CreateReader(profile, getMessageInfo, BUFFER_SIZE);
            if (reader == null) return 0;

            reader.AddData(buffer, 0, bufferLength);

            int count = 0;
            while (true)
            {
                var result = reader.Next();
                if (result == null || !result.Valid) break;

                var expected = getMessage(count);
                int expectedMsgId = expected.GetMsgId();

                if (result.MsgId != expectedMsgId) break;

                // Deserialize and compare
                var decoded = DeserializeMessage(result.MsgId, result, profile);
                if (decoded == null || !MessagesEqual(decoded, expected)) break;

                count++;
            }

            return count;
        }

        private static BufferWriter CreateWriter(string profile)
        {
            switch (profile.ToLower())
            {
                case "standard": return new ProfileStandardWriter();
                case "sensor": return new ProfileSensorWriter();
                case "ipc": return new ProfileIPCWriter();
                case "bulk": return new ProfileBulkWriter();
                case "network": return new ProfileNetworkWriter();
                default: return null;
            }
        }

        private static AccumulatingReader CreateReader(string profile, GetMessageInfoFunc getMessageInfo, int bufferSize)
        {
            Func<int, MessageInfo?> msgInfoFunc = (msgId) => getMessageInfo(msgId);
            
            switch (profile.ToLower())
            {
                case "standard": return new ProfileStandardAccumulatingReader(bufferSize, msgInfoFunc);
                case "sensor": return new ProfileSensorAccumulatingReader(bufferSize, msgInfoFunc);
                case "ipc": return new ProfileIPCAccumulatingReader(bufferSize, msgInfoFunc);
                case "bulk": return new ProfileBulkAccumulatingReader(bufferSize, msgInfoFunc);
                case "network": return new ProfileNetworkAccumulatingReader(bufferSize, msgInfoFunc);
                default: return null;
            }
        }

        private static IStructFrameMessage DeserializeMessage(int msgId, FrameMsgInfo info, string profile)
        {
            // Try standard messages first
            var stdMsgInfo = MessageDefinitions.GetMessageInfo(msgId);
            if (stdMsgInfo.HasValue)
            {
                return DeserializeStandardMessage(msgId, info);
            }

            // Try extended messages
            var extMsgInfo = ExtendedMessageDefinitions.GetMessageInfo(msgId);
            if (extMsgInfo.HasValue)
            {
                return DeserializeExtendedMessage(msgId, info);
            }

            return null;
        }

        private static IStructFrameMessage DeserializeStandardMessage(int msgId, FrameMsgInfo info)
        {
            if (msgId == SerializationTestSerializationTestMessage.MsgId)
            {
                return SerializationTestSerializationTestMessage.Deserialize(info);
            }
            if (msgId == SerializationTestBasicTypesMessage.MsgId)
            {
                return SerializationTestBasicTypesMessage.Deserialize(info);
            }
            if (msgId == SerializationTestUnionTestMessage.MsgId)
            {
                return SerializationTestUnionTestMessage.Deserialize(info);
            }
            if (msgId == SerializationTestVariableSingleArray.MsgId)
            {
                return SerializationTestVariableSingleArray.Deserialize(info);
            }
            if (msgId == SerializationTestMessage.MsgId)
            {
                return SerializationTestMessage.Deserialize(info);
            }
            if (msgId == SerializationTestTruncationTestNonVariable.MsgId)
            {
                return SerializationTestTruncationTestNonVariable.Deserialize(info);
            }
            if (msgId == SerializationTestTruncationTestVariable.MsgId)
            {
                return SerializationTestTruncationTestVariable.Deserialize(info);
            }
            return null;
        }

        private static IStructFrameMessage DeserializeExtendedMessage(int msgId, FrameMsgInfo info)
        {
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage1.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage1.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage2.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage2.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage3.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage3.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage4.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage4.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage5.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage5.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage6.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage6.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage7.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage7.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage8.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage8.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage9.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage9.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage10.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedIdMessage10.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage1.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage1.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage2.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestLargePayloadMessage2.Deserialize(info);
            }
            if (msgId == StructFrame.ExtendedTest.ExtendedTestExtendedVariableSingleArray.MsgId)
            {
                return StructFrame.ExtendedTest.ExtendedTestExtendedVariableSingleArray.Deserialize(info);
            }
            return null;
        }

        private static bool MessagesEqual(IStructFrameMessage decoded, IStructFrameMessage expected)
        {
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
