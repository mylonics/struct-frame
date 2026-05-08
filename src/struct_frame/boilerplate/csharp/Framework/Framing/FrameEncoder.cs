#nullable enable

using System;
using StructFrame;
using StructFrame.Profiles;

namespace StructFrame.Framing
{
    /// <summary>
    /// Generic frame encoder for frames with CRC.
    /// </summary>
    public class FrameEncoder
    {
        private readonly ProfileConfig _config;

        public FrameEncoder(ProfileConfig config)
        {
            _config = config;
        }

        /// <summary>
        /// Encode a message struct or interface.
        /// Magic numbers are automatically extracted from the message.
        /// </summary>
        public int Encode(byte[] buffer, int offset, IStructFrameMessage message, byte seq = 0, byte sysId = 0, byte compId = 0)
        {
            // For variable messages with minimal profiles (no length field), use SerializeMaxSize()
            // Otherwise, Serialize() returns the appropriate encoding
            byte[] payload;
            if (!_config.HasLength)
            {
                // Minimal profile (ProfileSensor/ProfileIPC) - need MAX_SIZE encoding
                // SerializeMaxSize() returns MAX_SIZE for variable messages, same as Serialize() for non-variable
                payload = message.SerializeMaxSize();
            }
            else
            {
                // Profile has length field - Serialize() returns the correct encoding
                // (variable-length for variable messages, MAX_SIZE for non-variable)
                payload = message.Serialize();
            }
            
            var (magic1, magic2) = message.GetMagicNumbers();
            ushort msgId = message.GetMsgId();
            int payloadSize = payload.Length;
            int totalSize = _config.Overhead + payloadSize;

            // Check buffer capacity and max payload (skip max payload check for minimal profiles without length field)
            if (buffer.Length - offset < totalSize)
            {
                return 0;
            }
            
            if (_config.HasLength && payloadSize > _config.MaxPayload)
            {
                return 0;
            }

            int idx = offset;

            // Write start bytes
            if (_config.NumStartBytes >= 1)
            {
                buffer[idx++] = _config.ComputedStartByte1;
            }
            if (_config.NumStartBytes >= 2)
            {
                buffer[idx++] = _config.ComputedStartByte2;
            }

            int crcStart = idx;

            // Write optional fields before length
            if (_config.HasSeq)
            {
                buffer[idx++] = seq;
            }
            if (_config.HasSysId)
            {
                buffer[idx++] = sysId;
            }
            if (_config.HasCompId)
            {
                buffer[idx++] = compId;
            }

            // Write length field
            if (_config.HasLength)
            {
                if (_config.LengthBytes == 1)
                {
                    buffer[idx++] = (byte)(payloadSize & 0xFF);
                }
                else
                {
                    buffer[idx++] = (byte)(payloadSize & 0xFF);
                    buffer[idx++] = (byte)((payloadSize >> 8) & 0xFF);
                }
            }

            // Write message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id)
            if (_config.HasPkgId)
            {
                buffer[idx++] = (byte)((msgId >> 8) & 0xFF);  // pkg_id (high byte)
            }
            buffer[idx++] = (byte)(msgId & 0xFF);  // msg_id (low byte)

            // Write payload
            if (payloadSize > 0 && payload != null)
            {
                Array.Copy(payload, 0, buffer, idx, payloadSize);
                idx += payloadSize;
            }

            // Calculate and write CRC (extension-aware)
            if (_config.HasCrc)
            {
                int crcLen = idx - crcStart;
                int baseSize = message.GetBaseSize();
                FrameChecksum ck;
                if (_config.HasLength && baseSize < payloadSize)
                {
                    int effectiveBase = crcLen - payloadSize + baseSize;
                    ck = FrameBase.FletcherChecksumExt(buffer, crcStart, effectiveBase, crcLen, magic1, magic2);
                }
                else
                {
                    ck = FrameBase.FletcherChecksum(buffer, crcStart, crcLen, magic1, magic2);
                }
                buffer[idx++] = ck.Byte1;
                buffer[idx++] = ck.Byte2;
            }

            return idx - offset;
        }
    }

    /// <summary>
    /// Generic frame encoder with compile-time profile selection.
    /// Usage: var encoder = new FrameEncoder&lt;StandardProfile&gt;();
    /// </summary>
    public class FrameEncoder<TProfile> : FrameEncoder where TProfile : struct, IProfileProvider
    {
        public FrameEncoder() : base(TProfile.Profile) { }
    }
}
