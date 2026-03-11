#nullable enable

using System;
using StructFrame;
using StructFrame.Profiles;

namespace StructFrame.Framing
{
    /// <summary>
    /// Generic buffer parser for frames.
    /// </summary>
    public class BufferParser
    {
        private readonly ProfileConfig _config;
        private readonly Func<int, MessageInfo?>? _getMessageInfo;

        public BufferParser(ProfileConfig config, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            _config = config;
            _getMessageInfo = getMessageInfo;
        }

        /// <summary>
        /// Parse a frame from a buffer.
        /// </summary>
        public FrameMsgInfo Parse(byte[] buffer, int offset, int length)
        {
            if (_config.HasLength || _config.HasCrc)
            {
                return ParseWithCrc(buffer, offset, length);
            }
            else
            {
                return ParseMinimal(buffer, offset, length);
            }
        }

        private FrameMsgInfo ParseWithCrc(byte[] buffer, int offset, int length)
        {
            if (length < _config.Overhead)
            {
                return FrameMsgInfo.Invalid;
            }

            int idx = offset;

            // Verify start bytes
            if (_config.NumStartBytes >= 1)
            {
                if (buffer[idx++] != _config.ComputedStartByte1)
                {
                    return FrameMsgInfo.Invalid;
                }
            }
            if (_config.NumStartBytes >= 2)
            {
                if (buffer[idx++] != _config.ComputedStartByte2)
                {
                    return FrameMsgInfo.Invalid;
                }
            }

            int crcStart = idx;

            // Read optional fields before length
            byte seq = 0, sysId = 0, compId = 0;
            if (_config.HasSeq) seq = buffer[idx++];
            if (_config.HasSysId) sysId = buffer[idx++];
            if (_config.HasCompId) compId = buffer[idx++];

            // Read length field
            int msgLen = 0;
            if (_config.HasLength)
            {
                if (_config.LengthBytes == 1)
                {
                    msgLen = buffer[idx++];
                }
                else
                {
                    msgLen = buffer[idx] | (buffer[idx + 1] << 8);
                    idx += 2;
                }
            }

            // Read message ID
            ushort msgId = 0;
            byte pkgId = 0;
            if (_config.HasPkgId)
            {
                pkgId = buffer[idx++];
                msgId = (ushort)(pkgId << 8);
            }
            msgId |= buffer[idx++];

            // Verify total size
            int totalSize = _config.Overhead + msgLen;
            if (length < totalSize)
            {
                return FrameMsgInfo.Invalid;
            }

            // Verify CRC
            if (_config.HasCrc)
            {
                int crcLen = totalSize - (crcStart - offset) - _config.FooterSize;
                byte magic1 = 0, magic2 = 0;
                if (_getMessageInfo != null)
                {
                    var info = _getMessageInfo(msgId);
                    if (info.HasValue)
                    {
                        magic1 = info.Value.Magic1;
                        magic2 = info.Value.Magic2;
                    }
                }
                var ck = FrameBase.FletcherChecksum(buffer, crcStart, crcLen, magic1, magic2);
                if (ck.Byte1 != buffer[offset + totalSize - 2] || ck.Byte2 != buffer[offset + totalSize - 1])
                {
                    return FrameMsgInfo.Invalid;
                }
            }

            var result = new FrameMsgInfo(true, msgId, msgLen, totalSize, buffer, offset + _config.HeaderSize);
            result.Seq = seq;
            result.SysId = sysId;
            result.CompId = compId;
            result.PkgId = pkgId;
            return result;
        }

        private FrameMsgInfo ParseMinimal(byte[] buffer, int offset, int length)
        {
            if (length < _config.HeaderSize)
            {
                return FrameMsgInfo.Invalid;
            }

            int idx = offset;

            // Verify start bytes
            if (_config.NumStartBytes >= 1)
            {
                if (buffer[idx++] != _config.ComputedStartByte1)
                {
                    return FrameMsgInfo.Invalid;
                }
            }
            if (_config.NumStartBytes >= 2)
            {
                if (buffer[idx++] != _config.ComputedStartByte2)
                {
                    return FrameMsgInfo.Invalid;
                }
            }

            // Read message ID
            byte msgId = buffer[idx];

            // Get message length from callback
            if (_getMessageInfo == null)
            {
                return FrameMsgInfo.Invalid;
            }

            var msgInfo = _getMessageInfo(msgId);
            if (!msgInfo.HasValue)
            {
                return FrameMsgInfo.Invalid;
            }

            int totalSize = _config.HeaderSize + msgInfo.Value.Size;
            if (length < totalSize)
            {
                return FrameMsgInfo.Invalid;
            }

            return new FrameMsgInfo(true, msgId, msgInfo.Value.Size, totalSize, buffer, offset + _config.HeaderSize);
        }
    }

    /// <summary>
    /// Generic buffer parser with compile-time profile selection.
    /// </summary>
    public class BufferParser<TProfile> : BufferParser where TProfile : struct, IProfileProvider
    {
        public BufferParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(TProfile.Profile, getMessageInfo) { }
    }
}
