// Base definitions for payload types (C#)
// Payload types define message structure (length fields, CRC, extra fields)

using System;

namespace StructFrame.PayloadTypes
{
    /// <summary>
    /// Payload type enumeration
    /// </summary>
    public enum PayloadType
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
    public class PayloadConfig
    {
        public PayloadType PayloadType { get; set; }
        public string Name { get; set; }
        public bool HasCrc { get; set; }
        public int CrcBytes { get; set; }
        public bool HasLength { get; set; }
        public int LengthBytes { get; set; }  // 1 or 2
        public bool HasSequence { get; set; }
        public bool HasSystemId { get; set; }
        public bool HasComponentId { get; set; }
        public bool HasPackageId { get; set; }
        public string Description { get; set; }

        /// <summary>
        /// Calculate header size from payload config
        /// </summary>
        public int HeaderSize
        {
            get
            {
                int size = 1;  // msg_id
                if (HasLength) size += LengthBytes;
                if (HasSequence) size += 1;
                if (HasSystemId) size += 1;
                if (HasComponentId) size += 1;
                if (HasPackageId) size += 1;
                return size;
            }
        }

        /// <summary>
        /// Calculate footer size from payload config
        /// </summary>
        public int FooterSize => CrcBytes;

        /// <summary>
        /// Calculate overhead from payload config
        /// </summary>
        public int Overhead => HeaderSize + FooterSize;
    }
}
