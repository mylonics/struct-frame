// Header Tiny - 1 start byte encoding payload type (C#)
// Format: [0x70+PayloadType]

using System;

namespace StructFrame.FrameHeaders
{
    public static class HeaderTiny
    {
        public static readonly HeaderConfig Config = new HeaderConfig
        {
            HeaderType = HeaderType.Tiny,
            Name = "Tiny",
            StartBytes = new byte[] { },  // Dynamic - depends on payload type
            NumStartBytes = 1,
            EncodesPayloadType = true,
            PayloadTypeByteIndex = 0,
            Description = "1 start byte [0x70+PayloadType] - compact framing"
        };

        /// <summary>
        /// Get the start byte for a Tiny frame with given payload type
        /// </summary>
        public static byte GetStartByte(byte payloadTypeValue)
        {
            return (byte)(HeaderConstants.PAYLOAD_TYPE_BASE + payloadTypeValue);
        }

        /// <summary>
        /// Check if byte is a valid Tiny frame start byte
        /// </summary>
        public static bool IsStartByte(byte b)
        {
            return b >= HeaderConstants.PAYLOAD_TYPE_BASE && 
                   b <= (HeaderConstants.PAYLOAD_TYPE_BASE + HeaderConstants.MAX_PAYLOAD_TYPE);
        }

        /// <summary>
        /// Extract payload type value from Tiny start byte
        /// </summary>
        public static byte GetPayloadType(byte b)
        {
            return (byte)(b - HeaderConstants.PAYLOAD_TYPE_BASE);
        }
    }
}
