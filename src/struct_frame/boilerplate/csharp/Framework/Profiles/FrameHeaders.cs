// Frame Headers - Start byte patterns and header configurations (C#)
// This file mirrors the C++ frame_headers.hpp structure

namespace StructFrame.Profiles
{
    /// <summary>
    /// Header type enumeration
    /// </summary>
    public enum HeaderType : byte
    {
        /// <summary>No start bytes.</summary>
        None = 0,       // No start bytes
        /// <summary>One dynamic start byte.</summary>
        Tiny = 1,       // 1 start byte [0x70+PayloadType]
        /// <summary>Two start bytes with a dynamic payload type byte.</summary>
        Basic = 2,      // 2 start bytes [0x90] [0x70+PayloadType]
        /// <summary>u-blox two-byte synchronization header.</summary>
        Ubx = 3,        // 2 start bytes [0xB5] [0x62]
        /// <summary>MAVLink version 1 start byte.</summary>
        MavlinkV1 = 4,  // 1 start byte [0xFE]
        /// <summary>MAVLink version 2 start byte.</summary>
        MavlinkV2 = 5   // 1 start byte [0xFD]
    }

    /// <summary>
    /// Constants used across headers
    /// </summary>
    public static class HeaderConstants
    {
        /// <summary>Basic profile start byte.</summary>
        public const byte BasicStartByte = 0x90;
        /// <summary>Base value for dynamic payload-type start bytes.</summary>
        public const byte PayloadTypeBase = 0x70;  // Payload type encoded as 0x70 + payload_type
        /// <summary>First u-blox synchronization byte.</summary>
        public const byte UbxSync1 = 0xB5;
        /// <summary>Second u-blox synchronization byte.</summary>
        public const byte UbxSync2 = 0x62;
        /// <summary>MAVLink version 1 start byte.</summary>
        public const byte MavlinkV1Stx = 0xFE;
        /// <summary>MAVLink version 2 start byte.</summary>
        public const byte MavlinkV2Stx = 0xFD;
        /// <summary>Maximum supported payload type value.</summary>
        public const byte MaxPayloadType = 8;
    }

    /// <summary>
    /// Configuration for a header type
    /// </summary>
    public readonly struct HeaderConfig
    {
        /// <summary>Configured header type.</summary>
        public HeaderType HeaderType { get; }
        /// <summary>First start byte.</summary>
        public byte StartByte1 { get; }       // First start byte (0 if none or dynamic)
        /// <summary>Second start byte.</summary>
        public byte StartByte2 { get; }       // Second start byte (0 if none or dynamic)
        /// <summary>Number of start bytes.</summary>
        public byte NumStartBytes { get; }    // Number of start bytes (0, 1, or 2)
        /// <summary>Whether the start byte encodes the payload type.</summary>
        public bool EncodesPayloadType { get; } // True if start byte encodes payload type

        /// <summary>Creates a header configuration.</summary>
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
        /// <summary>Header configuration without start bytes.</summary>
        public static readonly HeaderConfig None = new HeaderConfig(
            HeaderType.None, 0, 0, 0, false
        );

        /// <summary>Header configuration with one dynamic start byte.</summary>
        public static readonly HeaderConfig Tiny = new HeaderConfig(
            HeaderType.Tiny, 0, 0, 1, true  // dynamic - 0x70 + payload_type
        );

        /// <summary>Header configuration with two start bytes.</summary>
        public static readonly HeaderConfig Basic = new HeaderConfig(
            HeaderType.Basic, HeaderConstants.BasicStartByte, 0, 2, true
        );

        /// <summary>u-blox header configuration.</summary>
        public static readonly HeaderConfig Ubx = new HeaderConfig(
            HeaderType.Ubx, HeaderConstants.UbxSync1, HeaderConstants.UbxSync2, 2, false
        );

        /// <summary>MAVLink version 1 header configuration.</summary>
        public static readonly HeaderConfig MavlinkV1 = new HeaderConfig(
            HeaderType.MavlinkV1, HeaderConstants.MavlinkV1Stx, 0, 1, false
        );

        /// <summary>MAVLink version 2 header configuration.</summary>
        public static readonly HeaderConfig MavlinkV2 = new HeaderConfig(
            HeaderType.MavlinkV2, HeaderConstants.MavlinkV2Stx, 0, 1, false
        );
    }
}
