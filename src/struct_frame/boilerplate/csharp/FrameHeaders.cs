// Frame Headers - Start byte patterns and header configurations (C#)
// This file mirrors the C++ frame_headers.hpp structure

namespace StructFrame.FrameHeaders
{
    /// <summary>
    /// Header type enumeration
    /// </summary>
    public enum HeaderType : byte
    {
        None = 0,       // No start bytes
        Tiny = 1,       // 1 start byte [0x70+PayloadType]
        Basic = 2,      // 2 start bytes [0x90] [0x70+PayloadType]
        Ubx = 3,        // 2 start bytes [0xB5] [0x62]
        MavlinkV1 = 4,  // 1 start byte [0xFE]
        MavlinkV2 = 5   // 1 start byte [0xFD]
    }

    /// <summary>
    /// Constants used across headers
    /// </summary>
    public static class HeaderConstants
    {
        public const byte BasicStartByte = 0x90;
        public const byte PayloadTypeBase = 0x70;  // Payload type encoded as 0x70 + payload_type
        public const byte UbxSync1 = 0xB5;
        public const byte UbxSync2 = 0x62;
        public const byte MavlinkV1Stx = 0xFE;
        public const byte MavlinkV2Stx = 0xFD;
        public const byte MaxPayloadType = 8;
    }

    /// <summary>
    /// Configuration for a header type
    /// </summary>
    public readonly struct HeaderConfig
    {
        public readonly HeaderType HeaderType;
        public readonly byte StartByte1;       // First start byte (0 if none or dynamic)
        public readonly byte StartByte2;       // Second start byte (0 if none or dynamic)
        public readonly byte NumStartBytes;    // Number of start bytes (0, 1, or 2)
        public readonly bool EncodesPayloadType; // True if start byte encodes payload type

        public HeaderConfig(HeaderType headerType, byte startByte1, byte startByte2, 
                           byte numStartBytes, bool encodesPayloadType)
        {
            HeaderType = headerType;
            StartByte1 = startByte1;
            StartByte2 = startByte2;
            NumStartBytes = numStartBytes;
            EncodesPayloadType = encodesPayloadType;
        }

        /// <summary>
        /// Calculate total header contribution (just start bytes)
        /// </summary>
        public byte Size => NumStartBytes;
    }

    /// <summary>
    /// Pre-defined header configurations
    /// </summary>
    public static class HeaderConfigs
    {
        public static readonly HeaderConfig None = new HeaderConfig(
            HeaderType.None, 0, 0, 0, false
        );

        public static readonly HeaderConfig Tiny = new HeaderConfig(
            HeaderType.Tiny, 0, 0, 1, true  // dynamic - 0x70 + payload_type
        );

        public static readonly HeaderConfig Basic = new HeaderConfig(
            HeaderType.Basic, HeaderConstants.BasicStartByte, 0, 2, true
        );

        public static readonly HeaderConfig Ubx = new HeaderConfig(
            HeaderType.Ubx, HeaderConstants.UbxSync1, HeaderConstants.UbxSync2, 2, false
        );

        public static readonly HeaderConfig MavlinkV1 = new HeaderConfig(
            HeaderType.MavlinkV1, HeaderConstants.MavlinkV1Stx, 0, 1, false
        );

        public static readonly HeaderConfig MavlinkV2 = new HeaderConfig(
            HeaderType.MavlinkV2, HeaderConstants.MavlinkV2Stx, 0, 1, false
        );
    }
}
