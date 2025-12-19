// Header Basic - 2 start bytes with payload type encoding (C#)
// Format: [0x90] [0x70+PayloadType]

using System;

namespace StructFrame.FrameHeaders
{
    public static class HeaderBasic
    {
        public static readonly HeaderConfig Config = new HeaderConfig
        {
            HeaderType = HeaderType.Basic,
            Name = "Basic",
            StartBytes = new byte[] { HeaderConstants.BASIC_START_BYTE },  // First byte fixed, second dynamic
            NumStartBytes = 2,
            EncodesPayloadType = true,
            PayloadTypeByteIndex = 1,
            Description = "2 start bytes [0x90] [0x70+PayloadType] - standard framing"
        };

        /// <summary>
        /// Get the second start byte for a Basic frame with given payload type
        /// </summary>
        public static byte GetSecondStartByte(byte payloadTypeValue)
        {
            return (byte)(HeaderConstants.PAYLOAD_TYPE_BASE + payloadTypeValue);
        }

        /// <summary>
        /// Check if byte is a valid Basic frame second start byte
        /// </summary>
        public static bool IsSecondStartByte(byte b)
        {
            return b >= HeaderConstants.PAYLOAD_TYPE_BASE && 
                   b <= (HeaderConstants.PAYLOAD_TYPE_BASE + HeaderConstants.MAX_PAYLOAD_TYPE);
        }

        /// <summary>
        /// Extract payload type value from Basic second start byte
        /// </summary>
        public static byte GetPayloadType(byte b)
        {
            return (byte)(b - HeaderConstants.PAYLOAD_TYPE_BASE);
        }
    }
}
