// Payload Default (C#)
// Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
// 1-byte length, 2-byte CRC. Standard format.

using System;

namespace StructFrame.PayloadTypes
{
    public static class PayloadDefault
    {
        public static readonly PayloadConfig Config = new PayloadConfig
        {
            PayloadType = PayloadType.Default,
            Name = "Default",
            HasCrc = true,
            CrcBytes = 2,
            HasLength = true,
            LengthBytes = 1,
            HasSequence = false,
            HasSystemId = false,
            HasComponentId = false,
            HasPackageId = false,
            Description = "[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with 1-byte length and CRC."
        };
    }
}
