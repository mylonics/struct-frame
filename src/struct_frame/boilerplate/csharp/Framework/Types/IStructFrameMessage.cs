namespace StructFrame
{
    /// <summary>
    /// Base interface for message types (non-generic, for encoding).
    /// </summary>
    public interface IStructFrameMessage
    {
        /// <summary>
        /// Get the message ID.
        /// </summary>
        ushort GetMsgId();

        /// <summary>
        /// Get the message size in bytes.
        /// </summary>
        int GetSize();

        /// <summary>
        /// Serialize the message into a byte array.
        /// For variable messages this returns the variable-length encoding.
        /// </summary>
        byte[] Serialize();

        /// <summary>
        /// Serialize the message to its maximum size buffer.
        /// For variable messages this pads to MaxSize (needed for minimal profiles without a length field).
        /// For non-variable messages this is identical to Serialize().
        /// </summary>
        byte[] SerializeMaxSize() => Serialize();

        /// <summary>
        /// Get the magic numbers for checksum calculation (based on field types and positions).
        /// </summary>
        (byte Magic1, byte Magic2) GetMagicNumbers();
    }

    /// <summary>
    /// Generic interface for message types with deserialization support.
    /// Uses C# 11 static abstract members for compile-time dispatch.
    /// </summary>
    public interface IStructFrameMessage<TSelf> : IStructFrameMessage where TSelf : IStructFrameMessage<TSelf>
    {
        /// <summary>
        /// Deserialize a message from frame info.
        /// </summary>
        static abstract TSelf Deserialize(FrameMsgInfo frame);
    }
}
