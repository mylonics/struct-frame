#nullable enable

using StructFrame.FrameHeaders;
using StructFrame.PayloadTypes;

namespace StructFrame
{
    /// <summary>
    /// Profile configuration - combines a HeaderConfig with a PayloadConfig.
    /// </summary>
    public class ProfileConfig
    {
        public string Name { get; }
        public HeaderConfig Header { get; }
        public PayloadConfig Payload { get; }

        // Cached computed values for performance
        private readonly byte _computedStartByte1;
        private readonly byte _computedStartByte2;

        // Computed properties
        public byte NumStartBytes => Header.NumStartBytes;
        public bool HasLength => Payload.HasLength;
        public byte LengthBytes => Payload.LengthBytes;
        public bool HasCrc => Payload.HasCrc;
        public bool HasPkgId => Payload.HasPkgId;
        public bool HasSeq => Payload.HasSeq;
        public bool HasSysId => Payload.HasSysId;
        public bool HasCompId => Payload.HasCompId;

        public int HeaderSize => Header.NumStartBytes + Payload.HeaderSize;
        public int FooterSize => Payload.FooterSize;
        public int Overhead => HeaderSize + FooterSize;
        public int MaxPayload => Payload.MaxPayload;

        public ProfileConfig(string name, HeaderConfig header, PayloadConfig payload)
        {
            Name = name;
            Header = header;
            Payload = payload;
            
            // Pre-compute start bytes at construction time (avoids repeated calculation)
            if (header.EncodesPayloadType && header.NumStartBytes == 1)
            {
                _computedStartByte1 = (byte)(HeaderConstants.PayloadTypeBase + (byte)payload.PayloadType);
            }
            else
            {
                _computedStartByte1 = header.StartByte1;
            }
            
            if (header.EncodesPayloadType && header.NumStartBytes == 2)
            {
                _computedStartByte2 = (byte)(HeaderConstants.PayloadTypeBase + (byte)payload.PayloadType);
            }
            else
            {
                _computedStartByte2 = header.StartByte2;
            }
        }

        /// <summary>
        /// Compute start byte 1 (cached at construction time).
        /// </summary>
        public byte ComputedStartByte1 => _computedStartByte1;

        /// <summary>
        /// Compute start byte 2 (cached at construction time).
        /// </summary>
        public byte ComputedStartByte2 => _computedStartByte2;
    }
}
