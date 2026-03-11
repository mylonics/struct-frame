namespace StructFrame
{
    /// <summary>
    /// Checksum result structure.
    /// </summary>
    public readonly struct FrameChecksum
    {
        public byte Byte1 { get; }
        public byte Byte2 { get; }

        public FrameChecksum(byte b1, byte b2)
        {
            Byte1 = b1;
            Byte2 = b2;
        }
    }
}
