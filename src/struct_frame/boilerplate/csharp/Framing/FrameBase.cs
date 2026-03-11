using System;
using StructFrame;

namespace StructFrame.Framing
{
    /// <summary>
    /// Base utilities for struct frame parsing and encoding.
    /// </summary>
    public static class FrameBase
    {
        /// <summary>
        /// Fletcher-16 checksum calculation.
        /// </summary>
        public static FrameChecksum FletcherChecksum(byte[] data, int offset, int length, byte magic1 = 0, byte magic2 = 0)
        {
            byte ck1 = 0;
            byte ck2 = 0;
            for (int i = 0; i < length; i++)
            {
                ck1 = (byte)(ck1 + data[offset + i]);
                ck2 = (byte)(ck2 + ck1);
            }
            // Add magic numbers at the end
            ck1 = (byte)(ck1 + magic1);
            ck2 = (byte)(ck2 + ck1);
            ck1 = (byte)(ck1 + magic2);
            ck2 = (byte)(ck2 + ck1);
            return new FrameChecksum(ck1, ck2);
        }

        /// <summary>
        /// Fletcher-16 checksum calculation (convenience overload).
        /// </summary>
        public static FrameChecksum FletcherChecksum(byte[] data)
        {
            return FletcherChecksum(data, 0, data.Length, 0, 0);
        }

        /// <summary>
        /// Fletcher-16 checksum calculation on a span.
        /// </summary>
        public static FrameChecksum FletcherChecksum(ReadOnlySpan<byte> data, byte magic1 = 0, byte magic2 = 0)
        {
            byte ck1 = 0;
            byte ck2 = 0;
            for (int i = 0; i < data.Length; i++)
            {
                ck1 = (byte)(ck1 + data[i]);
                ck2 = (byte)(ck2 + ck1);
            }
            // Add magic numbers at the end
            ck1 = (byte)(ck1 + magic1);
            ck2 = (byte)(ck2 + ck1);
            ck1 = (byte)(ck1 + magic2);
            ck2 = (byte)(ck2 + ck1);
            return new FrameChecksum(ck1, ck2);
        }
    }
}
