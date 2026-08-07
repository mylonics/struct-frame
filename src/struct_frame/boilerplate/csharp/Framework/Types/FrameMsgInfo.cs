#nullable enable

using System;

namespace StructFrame
{
    /// <summary>
    /// Parser status indicating the reason a FrameMsgInfo is not valid.
    /// </summary>
    public enum FrameMsgStatus
    {
        /// <summary>No parser status.</summary>
        None = 0,
        /// <summary>Waiting for a frame start byte.</summary>
        WaitingForStart = 1,
        /// <summary>Collecting an incomplete frame.</summary>
        Collecting = 2,
        /// <summary>Checksum validation failed.</summary>
        CrcFailure = 3,
        /// <summary>Parser recovered by skipping invalid bytes.</summary>
        SyncRecovery = 4
    }

    /// <summary>
    /// Parse result structure containing message info.
    /// </summary>
    public struct FrameMsgInfo
    {
        /// <summary>Whether the frame is valid.</summary>
        public bool Valid { get; set; }
        /// <summary>Message identifier.</summary>
        public ushort MsgId { get; set; }
        /// <summary>Payload length in bytes.</summary>
        public int MsgLen { get; set; }
        /// <summary>Total frame size in bytes.</summary>
        public int FrameSize { get; set; }
        /// <summary>Backing buffer containing the message data.</summary>
        public byte[]? MsgData { get; set; }
        /// <summary>Payload offset within the backing buffer.</summary>
        public int MsgDataOffset { get; set; }
        /// <summary>Frame data view including framing bytes.</summary>
        public ReadOnlyMemory<byte> FrameData { get; set; }

        // Additional fields for extended profiles
        /// <summary>Sequence number.</summary>
        public byte Seq { get; set; }
        /// <summary>System identifier.</summary>
        public byte SysId { get; set; }
        /// <summary>Component identifier.</summary>
        public byte CompId { get; set; }
        /// <summary>Package identifier.</summary>
        public byte PkgId { get; set; }

        /// <summary>
        /// Status indicating the reason this result is not valid (only meaningful when Valid is false).
        /// </summary>
        public FrameMsgStatus Status { get; set; }

        /// <summary>
        /// Optional parser diagnostics snapshot attached by stream readers.
        /// </summary>
        public ParserDiagnostics? Diagnostics { get; set; }

        /// <summary>Creates frame parse information.</summary>
        public FrameMsgInfo(bool valid, ushort msgId, int msgLen, int frameSize, byte[]? msgData, int offset = 0)
        {
            Valid = valid;
            MsgId = msgId;
            MsgLen = msgLen;
            FrameSize = frameSize;
            MsgData = msgData;
            MsgDataOffset = offset;
            FrameData = default;
            Seq = 0;
            SysId = 0;
            CompId = 0;
            PkgId = 0;
            Status = FrameMsgStatus.None;
            Diagnostics = null;
        }

        /// <summary>Gets an invalid frame result.</summary>
        public static FrameMsgInfo Invalid => new FrameMsgInfo(false, 0, 0, 0, null);

        /// <summary>
        /// Allow use in boolean context.
        /// </summary>
        public static implicit operator bool(FrameMsgInfo info) => info.Valid;

        /// <summary>
        /// Extract payload from frame info, handling offset if needed.
        /// Allocates a new array. Prefer <see cref="GetPayloadSpan"/> when calling
        /// <c>Deserialize(ReadOnlySpan&lt;byte&gt;)</c> to avoid this allocation.
        /// </summary>
        public readonly byte[] ExtractPayload()
        {
            if (MsgData == null)
            {
                return Array.Empty<byte>();
            }

            // Validate buffer size
            if (MsgDataOffset + MsgLen > MsgData.Length)
            {
                throw new ArgumentException($"Invalid buffer range: MsgData length ({MsgData.Length}) is insufficient for offset {MsgDataOffset} + length {MsgLen}");
            }

            if (MsgDataOffset > 0)
            {
                // Copy from offset to new array
                byte[] payload = new byte[MsgLen];
                Array.Copy(MsgData, MsgDataOffset, payload, 0, MsgLen);
                return payload;
            }
            else if (MsgData.Length == MsgLen)
            {
                // Data is exactly the right size, use it directly
                return MsgData;
            }
            else
            {
                // Data is larger than needed, copy the required portion
                byte[] payload = new byte[MsgLen];
                Array.Copy(MsgData, 0, payload, 0, MsgLen);
                return payload;
            }
        }

        /// <summary>
        /// Get a zero-copy <see cref="ReadOnlySpan{T}"/> over the payload data.
        /// Use this with <c>Deserialize(ReadOnlySpan&lt;byte&gt;)</c> to avoid the
        /// heap allocation that <see cref="ExtractPayload"/> incurs on the hot receive path.
        /// </summary>
        public readonly ReadOnlySpan<byte> GetPayloadSpan()
        {
            if (MsgData == null) return ReadOnlySpan<byte>.Empty;
            if (MsgDataOffset + MsgLen > MsgData.Length)
                throw new ArgumentException($"Invalid buffer range: MsgData length ({MsgData.Length}) is insufficient for offset {MsgDataOffset} + length {MsgLen}");
            return MsgData.AsSpan(MsgDataOffset, MsgLen);
        }
    }
}
