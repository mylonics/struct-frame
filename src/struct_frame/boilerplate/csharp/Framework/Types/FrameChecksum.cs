namespace StructFrame
{
    /// <summary>
    /// Checksum result structure.
    /// </summary>
    public readonly struct FrameChecksum
    {
        /// <summary>First checksum byte.</summary>
        public byte Byte1 { get; }
        /// <summary>Second checksum byte.</summary>
        public byte Byte2 { get; }

        /// <summary>Creates a checksum result.</summary>
        public FrameChecksum(byte b1, byte b2)
        {
            Byte1 = b1;
            Byte2 = b2;
        }
    }
}
