// Base definitions for frame headers (C#)
// Header types define start byte patterns and header-specific parsing

using System;

namespace StructFrame.FrameHeaders
{
    /// <summary>
    /// Header type enumeration
    /// </summary>
    public enum HeaderType
    {
        None = 0,       // No start bytes
        Tiny = 1,       // 1 start byte [0x70+PayloadType]
        Basic = 2,      // 2 start bytes [0x90] [0x70+PayloadType]
        Ubx = 3,        // 2 start bytes [0xB5] [0x62]
        MavlinkV1 = 4,  // 1 start byte [0xFE]
        MavlinkV2 = 5   // 1 start byte [0xFD]
    }

    /// <summary>
    /// Configuration for a header type
    /// </summary>
    public class HeaderConfig
    {
        public HeaderType HeaderType { get; set; }
        public string Name { get; set; }
        public byte[] StartBytes { get; set; }  // Fixed start bytes (empty for dynamic)
        public int NumStartBytes { get; set; }   // Number of start bytes (0, 1, or 2)
        public bool EncodesPayloadType { get; set; }  // True if start byte encodes payload type
        public int PayloadTypeByteIndex { get; set; }  // Which byte encodes payload type (-1 if none)
        public string Description { get; set; }
    }

    /// <summary>
    /// Constants used across headers
    /// </summary>
    public static class HeaderConstants
    {
        public const byte BASIC_START_BYTE = 0x90;
        public const byte PAYLOAD_TYPE_BASE = 0x70;  // Payload type encoded as 0x70 + payload_type
        public const byte UBX_SYNC1 = 0xB5;
        public const byte UBX_SYNC2 = 0x62;
        public const byte MAVLINK_V1_STX = 0xFE;
        public const byte MAVLINK_V2_STX = 0xFD;
        public const byte MAX_PAYLOAD_TYPE = 8;
    }
}
