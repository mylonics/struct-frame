// Payload Types - Message structure configurations (C#)
// This file mirrors the C++ payload_types.hpp structure

namespace StructFrame.PayloadTypes
{
    /// <summary>
    /// Payload type enumeration
    /// </summary>
    public enum PayloadType : byte
    {
        Minimal = 0,                      // [MSG_ID] [PACKET]
        Default = 1,                      // [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        ExtendedMsgIds = 2,               // [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
        ExtendedLength = 3,               // [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
        Extended = 4,                     // [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
        SysComp = 5,                      // [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        Seq = 6,                          // [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        MultiSystemStream = 7,            // [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
        ExtendedMultiSystemStream = 8     // [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    }

    /// <summary>
    /// Configuration for a payload type
    /// </summary>
    public readonly struct PayloadConfig
    {
        public readonly PayloadType PayloadType;
        public readonly bool HasCrc;
        public readonly byte CrcBytes;      // 0 or 2
        public readonly bool HasLength;
        public readonly byte LengthBytes;   // 0, 1, or 2
        public readonly bool HasSeq;
        public readonly bool HasSysId;
        public readonly bool HasCompId;
        public readonly bool HasPkgId;

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
        public static readonly PayloadConfig Minimal = new PayloadConfig(
            PayloadType.Minimal,
            false, 0,   // no CRC
            false, 0,   // no length
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        public static readonly PayloadConfig Default = new PayloadConfig(
            PayloadType.Default,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        public static readonly PayloadConfig ExtendedMsgIds = new PayloadConfig(
            PayloadType.ExtendedMsgIds,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            true        // has pkg_id
        );

        public static readonly PayloadConfig ExtendedLength = new PayloadConfig(
            PayloadType.ExtendedLength,
            true, 2,    // has CRC, 2 bytes
            true, 2,    // has length, 2 bytes
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        public static readonly PayloadConfig Extended = new PayloadConfig(
            PayloadType.Extended,
            true, 2,    // has CRC, 2 bytes
            true, 2,    // has length, 2 bytes
            false,      // no seq
            false,      // no sys_id
            false,      // no comp_id
            true        // has pkg_id
        );

        public static readonly PayloadConfig SysComp = new PayloadConfig(
            PayloadType.SysComp,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            false,      // no seq
            true,       // has sys_id
            true,       // has comp_id
            false       // no pkg_id
        );

        public static readonly PayloadConfig Seq = new PayloadConfig(
            PayloadType.Seq,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            true,       // has seq
            false,      // no sys_id
            false,      // no comp_id
            false       // no pkg_id
        );

        public static readonly PayloadConfig MultiSystemStream = new PayloadConfig(
            PayloadType.MultiSystemStream,
            true, 2,    // has CRC, 2 bytes
            true, 1,    // has length, 1 byte
            true,       // has seq
            true,       // has sys_id
            true,       // has comp_id
            false       // no pkg_id
        );

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
