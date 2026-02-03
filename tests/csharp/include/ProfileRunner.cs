/**
 * Profile runner (C#).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 * ProfileRunner has NO knowledge of message types - all message-specific
 * logic is handled via callbacks (GetMessage, CheckMessage).
 */

using System;
using StructFrame;

namespace StructFrameTests
{
    /// <summary>
    /// Delegate type for GetMessage function
    /// </summary>
    public delegate IStructFrameMessage GetMessageFunc(int index);

    /// <summary>
    /// Delegate type for CheckMessage function - validates decoded message at index
    /// </summary>
    public delegate bool CheckMessageFunc(int index, FrameMsgInfo info);

    /// <summary>
    /// Delegate type for get_message_info function
    /// </summary>
    public delegate MessageInfo? GetMessageInfoFunc(int msgId);

    /// <summary>
    /// Profile runner - Low-level encoding and decoding for message providers.
    /// This class has NO knowledge of message types - all message-specific
    /// logic is handled via callbacks.
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
        /// Uses checkMessage callback to validate each decoded message.
        /// Returns the number of messages that matched (messageCount if all pass).
        /// </summary>
        public static int Parse(
            int messageCount,
            CheckMessageFunc checkMessage,
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

                // Use callback to check if message matches expected
                if (!checkMessage(count, result)) break;

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
    }
}
