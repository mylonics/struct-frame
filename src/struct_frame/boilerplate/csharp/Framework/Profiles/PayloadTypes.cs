// Payload Types - Message structure configurations (C#)
// This file mirrors the C++ payload_types.hpp structure

namespace StructFrame.Profiles
{
    /// <summary>
    /// Payload type enumeration
    /// </summary>
    public enum PayloadType : byte
    {
        /// <summary>Minimal payload without length or checksum.</summary>
        Minimal = 0,                      // [MSG_ID] [PACKET]
        /// <summary>Default payload with one-byte length.</summary>
        Default = 1,                      // [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with extended message IDs.</summary>
        ExtendedMsgIds = 2,               // [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with a two-byte length.</summary>
        ExtendedLength = 3,               // [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with extended length and message IDs.</summary>
        Extended = 4,                     // [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with system and component IDs.</summary>
        SysComp = 5,                      // [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with a sequence number.</summary>
        Seq = 6,                          // [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Payload with sequence, system, and component IDs.</summary>
        MultiSystemStream = 7,            // [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        /// <summary>Extended payload with sequence, system, and component IDs.</summary>
        ExtendedMultiSystemStream = 8     // [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    }

    /// <summary>
    /// Configuration for a payload type
    /// </summary>
    public readonly struct PayloadConfig
    {
        /// <summary>Configured payload type.</summary>
        public PayloadType PayloadType { get; }
        /// <summary>Whether the payload has a checksum.</summary>
        public bool HasCrc { get; }
        /// <summary>Checksum size in bytes.</summary>
        public byte CrcBytes { get; }      // 0 or 2
        /// <summary>Whether the payload has a length field.</summary>
        public bool HasLength { get; }
        /// <summary>Length field size in bytes.</summary>
        public byte LengthBytes { get; }   // 0, 1, or 2
        /// <summary>Whether the payload has a sequence number.</summary>
        public bool HasSeq { get; }
        /// <summary>Whether the payload has a system ID.</summary>
        public bool HasSysId { get; }
        /// <summary>Whether the payload has a component ID.</summary>
        public bool HasCompId { get; }
        /// <summary>Whether the payload has a package ID.</summary>
        public bool HasPkgId { get; }

        /// <summary>Creates a payload configuration.</summary>
        public PayloadConfig(PayloadType payloadType, bool hasCrc, byte crcBytes,
                            bool hasLength, byte lengthBytes, bool hasSeq,
                            bool hasSysId, bool hasCompId, bool hasPkgId)
        {
            PayloadType = payloadType;
            HasCrc = hasCrc;
            CrcBytes = crcBytes;
            HasLength = hasLength;
            LengthBytes = lengthBytes;
            HasSeq = hasSeq;
            HasSysId = hasSysId;
            HasCompId = hasCompId;
            HasPkgId = hasPkgId;
        }

        /// <summary>
        /// Calculate header size (fields before payload, excluding start bytes)
        /// </summary>
        public byte HeaderSize
        {
            get
            {
                byte size = 1; // msg_id always present
                if (HasLength) size += LengthBytes;
                if (HasSeq) size += 1;
                if (HasSysId) size += 1;
                if (HasCompId) size += 1;
                if (HasPkgId) size += 1;
                return size;
            }
        }

        /// <summary>
        /// Calculate footer size
        /// </summary>
        public byte FooterSize => CrcBytes;

        /// <summary>
        /// Calculate total overhead (header + footer, excluding start bytes)
        /// </summary>
        public byte Overhead => (byte)(HeaderSize + FooterSize);

        /// <summary>
        /// Calculate max payload size based on length field
        /// </summary>
        public int MaxPayload
        {
            get
            {
                if (LengthBytes == 1) return 255;
                if (LengthBytes == 2) return 65535;
                return 0; // No length field - requires external knowledge
            }
        }
    }

    /// <summary>
    /// Pre-defined payload configurations
    /// </summary>
    public static class PayloadConfigs
    {
        /// <summary>Minimal payload configuration.</summary>
        public static readonly PayloadConfig Minimal = new PayloadConfig(
            PayloadType.Minimal,
            false, 0,   // no CRC
            false, 0,   // no length
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        /// <summary>Default payload configuration.</summary>
        public static readonly PayloadConfig Default = new PayloadConfig(
            PayloadType.Default,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        /// <summary>Extended message ID payload configuration.</summary>
        public static readonly PayloadConfig ExtendedMsgIds = new PayloadConfig(
            PayloadType.ExtendedMsgIds,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            true        // has pkg_id
        );

        /// <summary>Extended length payload configuration.</summary>
        public static readonly PayloadConfig ExtendedLength = new PayloadConfig(
            PayloadType.ExtendedLength,
            true, 2,    // has CRC, 2 bytes
            true, 2,    // has length, 2 bytes
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        /// <summary>Extended payload configuration.</summary>
        public static readonly PayloadConfig Extended = new PayloadConfig(
            PayloadType.Extended,
            true, 2,    // has CRC, 2 bytes
            true, 2,    // has length, 2 bytes
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            true        // has pkg_id
        );

        /// <summary>System/component payload configuration.</summary>
        public static readonly PayloadConfig SysComp = new PayloadConfig(
            PayloadType.SysComp,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            true,       // has sys_id
            true,       // has comp_id
            false       // no pkg_id
        );

        /// <summary>Sequence-number payload configuration.</summary>
        public static readonly PayloadConfig Seq = new PayloadConfig(
            PayloadType.Seq,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            true,       // has seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        /// <summary>Multi-system stream payload configuration.</summary>
        public static readonly PayloadConfig MultiSystemStream = new PayloadConfig(
            PayloadType.MultiSystemStream,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            true,       // has seq
            true,       // has sys_id
            true,       // has comp_id
            false       // no pkg_id
        );

        /// <summary>Extended multi-system stream payload configuration.</summary>
        public static readonly PayloadConfig ExtendedMultiSystemStream = new PayloadConfig(
            PayloadType.ExtendedMultiSystemStream,
            true, 2,    // has CRC, 2 bytes
            true, 2,    // has length, 2 bytes
            true,       // has seq
            true,       // has sys_id
            true,       // has comp_id
            true        // has pkg_id
        );
    }
}
