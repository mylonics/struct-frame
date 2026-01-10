// Struct-frame boilerplate: frame parsers for C#

// This file serves as a namespace entry point.
// Frame headers are in FrameHeaders/ directory
// Payload types are in PayloadTypes/ directory

namespace StructFrame
{
    /// <summary>
    /// Frame format type enumeration
    /// </summary>
    public enum FrameFormatType
    {
        TINY_MINIMAL = 0,
        TINY_DEFAULT = 1,
        TINY_EXTENDED_MSG_IDS = 2,
        TINY_EXTENDED_LENGTH = 3,
        TINY_EXTENDED = 4,
        TINY_SYS_COMP = 5,
        TINY_SEQ = 6,
        TINY_MULTI_SYSTEM_STREAM = 7,
        TINY_EXTENDED_MULTI_SYSTEM_STREAM = 8,
        BASIC_MINIMAL = 9,
        BASIC_DEFAULT = 10,
        BASIC_EXTENDED_MSG_IDS = 11,
        BASIC_EXTENDED_LENGTH = 12,
        BASIC_EXTENDED = 13,
        BASIC_SYS_COMP = 14,
        BASIC_SEQ = 15,
        BASIC_MULTI_SYSTEM_STREAM = 16,
        BASIC_EXTENDED_MULTI_SYSTEM_STREAM = 17,
        UBX_FRAME = 18,
        MAVLINK_V1_FRAME = 19,
        MAVLINK_V2_FRAME = 20,
        FRAME_FORMAT_CONFIG = 21
    }
}
