// Payload Minimal (C#)
// Format: [MSG_ID] [PACKET]
// No length field, no CRC. Requires external synchronization.

using System;

namespace StructFrame.PayloadTypes
{
    public static class PayloadMinimal
    {
        public static readonly PayloadConfig Config = new PayloadConfig
        {
            PayloadType = PayloadType.Minimal,
            Name = "Minimal",
            HasCrc = false,
            CrcBytes = 0,
            HasLength = false,
            LengthBytes = 0,
            HasSequence = false,
            HasSystemId = false,
            HasComponentId = false,
            HasPackageId = false,
            Description = "[MSG_ID] [PACKET] - Minimal format with no length field and no CRC."
        };
    }
}
