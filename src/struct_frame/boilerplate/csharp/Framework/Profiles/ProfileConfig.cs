#nullable enable

namespace StructFrame.Profiles
{
    /// <summary>
    /// Profile configuration - combines a HeaderConfig with a PayloadConfig.
    /// </summary>
    public class ProfileConfig
    {
        /// <summary>Profile name.</summary>
        public string Name { get; }
        /// <summary>Frame header configuration.</summary>
        public HeaderConfig Header { get; }
        /// <summary>Payload configuration.</summary>
        public PayloadConfig Payload { get; }

        // Cached computed values for performance
        private readonly byte _computedStartByte1;
        private readonly byte _computedStartByte2;

        // Computed properties
        /// <summary>Number of frame start bytes.</summary>
        public byte NumStartBytes => Header.NumStartBytes;
        /// <summary>Whether the profile includes a length field.</summary>
        public bool HasLength => Payload.HasLength;
        /// <summary>Length field size in bytes.</summary>
        public byte LengthBytes => Payload.LengthBytes;
        /// <summary>Whether the profile includes a checksum.</summary>
        public bool HasCrc => Payload.HasCrc;
        /// <summary>Whether the profile includes a package ID.</summary>
        public bool HasPkgId => Payload.HasPkgId;
        /// <summary>Whether the profile includes a sequence number.</summary>
        public bool HasSeq => Payload.HasSeq;
        /// <summary>Whether the profile includes a system ID.</summary>
        public bool HasSysId => Payload.HasSysId;
        /// <summary>Whether the profile includes a component ID.</summary>
        public bool HasCompId => Payload.HasCompId;

        /// <summary>Total header size including start bytes.</summary>
        public int HeaderSize => Header.NumStartBytes + Payload.HeaderSize;
        /// <summary>Footer size in bytes.</summary>
        public int FooterSize => Payload.FooterSize;
        /// <summary>Total framing overhead in bytes.</summary>
        public int Overhead => HeaderSize + FooterSize;
        /// <summary>Maximum payload size allowed by the profile.</summary>
        public int MaxPayload => Payload.MaxPayload;

        /// <summary>Creates a profile configuration.</summary>
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
