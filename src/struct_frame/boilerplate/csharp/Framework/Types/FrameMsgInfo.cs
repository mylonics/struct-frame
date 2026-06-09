#nullable enable

using System;

namespace StructFrame
{
    /// <summary>
    /// Parser status indicating the reason a FrameMsgInfo is not valid.
    /// </summary>
    public enum FrameMsgStatus
    {
        None = 0,
        WaitingForStart = 1,
        Collecting = 2,
        CrcFailure = 3,
        SyncRecovery = 4
    }

    /// <summary>
    /// Parse result structure containing message info.
    /// </summary>
    public struct FrameMsgInfo
    {
        public bool Valid { get; set; }
        public ushort MsgId { get; set; }
        public int MsgLen { get; set; }
        public int FrameSize { get; set; }
        public byte[]? MsgData { get; set; }
        public int MsgDataOffset { get; set; }
        public ReadOnlyMemory<byte> FrameData { get; set; }

        // Additional fields for extended profiles
        public byte Seq { get; set; }
        public byte SysId { get; set; }
        public byte CompId { get; set; }
        public byte PkgId { get; set; }

        /// <summary>
        /// Status indicating the reason this result is not valid (only meaningful when Valid is false).
        /// </summary>
        public FrameMsgStatus Status { get; set; }

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
        }

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
