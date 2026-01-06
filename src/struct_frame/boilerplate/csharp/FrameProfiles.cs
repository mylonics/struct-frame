// Frame Profiles - Pre-defined Header + Payload combinations
// 
// This file provides ready-to-use encode/parse functions for the 5 standard profiles:
// - ProfileStandard: Basic + Default (General serial/UART)
// - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
// - ProfileIPC: None + Minimal (Trusted inter-process communication)
// - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
// - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
//
// This file builds on the existing FrameHeaders and PayloadTypes boilerplate code,
// providing maximum code reuse through a generic FrameProfileConfig class.

using System;
using System.Collections.Generic;

namespace StructFrame
{
    /// <summary>
    /// Generic frame format configuration - combines header type with payload type.
    /// This allows creating any header+payload combination by specifying the configuration parameters.
    /// </summary>
    public class FrameProfileConfig
    {
        public string Name { get; set; }
        public int NumStartBytes { get; set; }
        public byte StartByte1 { get; set; }
        public byte StartByte2 { get; set; }
        public int HeaderSize { get; set; }
        public int FooterSize { get; set; }
        public bool HasLength { get; set; }
        public int LengthBytes { get; set; }
        public bool HasCrc { get; set; }
        public bool HasPkgId { get; set; }
        public bool HasSeq { get; set; }
        public bool HasSysId { get; set; }
        public bool HasCompId { get; set; }

        public int Overhead => HeaderSize + FooterSize;
        public int MaxPayload => HasLength ? (LengthBytes == 2 ? 65535 : 255) : 0;
    }

    /// <summary>
    /// Frame profile encoder and parser using generic configuration
    /// </summary>
    public class FrameProfileParser
    {
        private readonly FrameProfileConfig _config;
        private readonly Func<int, int?> _getMsgLength;
        
        /// <summary>
        /// Get the frame configuration for this parser
        /// </summary>
        public FrameProfileConfig Config => _config;
        
        // Parser state
        private enum State
        {
            LookingForStart1,
            LookingForStart2,
            ParsingHeader,
            ParsingPayload,
            ParsingFooter
        }
        
        private State _state;
        private List<byte> _buffer;
        private int _headerFieldIndex;
        private int _payloadBytesRemaining;
        private int _footerBytesRemaining;
        
        // Parsed fields
        private int _msgId;
        private int _msgLen;
        private int _pkgId;
        private int _seq;
        private int _sysId;
        private int _compId;

        public FrameProfileParser(FrameProfileConfig config, Func<int, int?> getMsgLength = null)
        {
            _config = config;
            _getMsgLength = getMsgLength;
            _buffer = new List<byte>();
            Reset();
        }

        public void Reset()
        {
            _state = _config.NumStartBytes > 0 ? State.LookingForStart1 : State.ParsingHeader;
            _buffer.Clear();
            _headerFieldIndex = 0;
            _payloadBytesRemaining = 0;
            _footerBytesRemaining = 0;
            _msgId = 0;
            _msgLen = 0;
            _pkgId = 0;
            _seq = 0;
            _sysId = 0;
            _compId = 0;
        }

        /// <summary>
        /// Parse a single byte
        /// </summary>
        public FrameParseResult ParseByte(byte b)
        {
            switch (_state)
            {
                case State.LookingForStart1:
                    return HandleLookingForStart1(b);
                case State.LookingForStart2:
                    return HandleLookingForStart2(b);
                case State.ParsingHeader:
                    return HandleParsingHeader(b);
                case State.ParsingPayload:
                    return HandleParsingPayload(b);
                case State.ParsingFooter:
                    return HandleParsingFooter(b);
                default:
                    return new FrameParseResult();
            }
        }

        private FrameParseResult HandleLookingForStart1(byte b)
        {
            if (b == _config.StartByte1)
            {
                _buffer.Clear();
                _buffer.Add(b);
                if (_config.NumStartBytes >= 2)
                {
                    _state = State.LookingForStart2;
                }
                else
                {
                    _state = State.ParsingHeader;
                    _headerFieldIndex = 0;
                }
            }
            return new FrameParseResult();
        }

        private FrameParseResult HandleLookingForStart2(byte b)
        {
            if (b == _config.StartByte2)
            {
                _buffer.Add(b);
                _state = State.ParsingHeader;
                _headerFieldIndex = 0;
            }
            else if (b == _config.StartByte1)
            {
                _buffer.Clear();
                _buffer.Add(b);
            }
            else
            {
                Reset();
            }
            return new FrameParseResult();
        }

        private FrameParseResult HandleParsingHeader(byte b)
        {
            _buffer.Add(b);
            
            // Build field order based on config
            var fields = new List<string>();
            if (_config.HasSeq) fields.Add("seq");
            if (_config.HasSysId) fields.Add("sys_id");
            if (_config.HasCompId) fields.Add("comp_id");
            if (_config.HasLength)
            {
                if (_config.LengthBytes == 2)
                {
                    fields.Add("len_lo");
                    fields.Add("len_hi");
                }
                else
                {
                    fields.Add("len");
                }
            }
            if (_config.HasPkgId) fields.Add("pkg_id");
            fields.Add("msg_id");

            if (_headerFieldIndex < fields.Count)
            {
                string field = fields[_headerFieldIndex];
                switch (field)
                {
                    case "seq": _seq = b; break;
                    case "sys_id": _sysId = b; break;
                    case "comp_id": _compId = b; break;
                    case "len": _msgLen = b; break;
                    case "len_lo": _msgLen = b; break;
                    case "len_hi": _msgLen |= (b << 8); break;
                    case "pkg_id": _pkgId = b; break;
                    case "msg_id": _msgId = b; break;
                }
                _headerFieldIndex++;
            }

            // Check if header is complete
            if (_headerFieldIndex >= fields.Count)
            {
                // Determine payload length
                if (_config.HasLength)
                {
                    _payloadBytesRemaining = _msgLen;
                }
                else if (_getMsgLength != null)
                {
                    var len = _getMsgLength(_msgId);
                    if (len.HasValue)
                    {
                        _payloadBytesRemaining = len.Value;
                    }
                    else
                    {
                        Reset();
                        return new FrameParseResult();
                    }
                }
                else
                {
                    Reset();
                    return new FrameParseResult();
                }

                _footerBytesRemaining = _config.FooterSize;
                _state = _payloadBytesRemaining > 0 ? State.ParsingPayload : 
                         _footerBytesRemaining > 0 ? State.ParsingFooter : State.LookingForStart1;
                
                if (_payloadBytesRemaining == 0 && _footerBytesRemaining == 0)
                {
                    return CompleteMessage();
                }
            }

            return new FrameParseResult();
        }

        private FrameParseResult HandleParsingPayload(byte b)
        {
            _buffer.Add(b);
            _payloadBytesRemaining--;

            if (_payloadBytesRemaining <= 0)
            {
                if (_footerBytesRemaining > 0)
                {
                    _state = State.ParsingFooter;
                }
                else
                {
                    return CompleteMessage();
                }
            }
            return new FrameParseResult();
        }

        private FrameParseResult HandleParsingFooter(byte b)
        {
            _buffer.Add(b);
            _footerBytesRemaining--;

            if (_footerBytesRemaining <= 0)
            {
                return CompleteMessage();
            }
            return new FrameParseResult();
        }

        private FrameParseResult CompleteMessage()
        {
            var result = new FrameParseResult();

            // Validate CRC if present
            if (_config.HasCrc)
            {
                int crcStart = _config.NumStartBytes;
                int crcEnd = _buffer.Count - _config.FooterSize;
                var ck = FletcherChecksum(_buffer.ToArray(), crcStart, crcEnd);
                
                if (ck.Item1 != _buffer[_buffer.Count - 2] || ck.Item2 != _buffer[_buffer.Count - 1])
                {
                    Reset();
                    return result;
                }
            }

            // Extract message data
            int dataStart = _config.HeaderSize;
            int dataEnd = _buffer.Count - _config.FooterSize;
            int dataLen = dataEnd - dataStart;
            
            result.Valid = true;
            result.MsgId = _msgId;
            result.MsgSize = dataLen;
            result.MsgData = new byte[dataLen];
            for (int i = 0; i < dataLen; i++)
            {
                result.MsgData[i] = _buffer[dataStart + i];
            }

            Reset();
            return result;
        }

        /// <summary>
        /// Encode a message using this profile
        /// </summary>
        public byte[] Encode(int msgId, byte[] payload, int seq = 0, int sysId = 0, int compId = 0, int pkgId = 0)
        {
            var output = new List<byte>();
            int payloadSize = payload?.Length ?? 0;

            // Start bytes
            if (_config.NumStartBytes >= 1)
                output.Add(_config.StartByte1);
            if (_config.NumStartBytes >= 2)
                output.Add(_config.StartByte2);

            int crcStart = output.Count;

            // Optional fields before length
            if (_config.HasSeq)
                output.Add((byte)(seq & 0xFF));
            if (_config.HasSysId)
                output.Add((byte)(sysId & 0xFF));
            if (_config.HasCompId)
                output.Add((byte)(compId & 0xFF));

            // Length field
            if (_config.HasLength)
            {
                if (_config.LengthBytes == 1)
                {
                    output.Add((byte)(payloadSize & 0xFF));
                }
                else
                {
                    output.Add((byte)(payloadSize & 0xFF));
                    output.Add((byte)((payloadSize >> 8) & 0xFF));
                }
            }

            // Package ID
            if (_config.HasPkgId)
                output.Add((byte)(pkgId & 0xFF));

            // Message ID
            output.Add((byte)(msgId & 0xFF));

            // Payload
            if (payload != null && payloadSize > 0)
            {
                output.AddRange(payload);
            }

            // CRC
            if (_config.HasCrc)
            {
                var ck = FletcherChecksum(output.ToArray(), crcStart, output.Count);
                output.Add(ck.Item1);
                output.Add(ck.Item2);
            }

            return output.ToArray();
        }

        /// <summary>
        /// Validate a complete frame in a buffer
        /// </summary>
        public FrameParseResult ValidateBuffer(byte[] buffer)
        {
            var result = new FrameParseResult();
            int length = buffer?.Length ?? 0;

            if (length < _config.Overhead)
                return result;

            int idx = 0;

            // Verify start bytes
            if (_config.NumStartBytes >= 1)
            {
                if (buffer[idx++] != _config.StartByte1)
                    return result;
            }
            if (_config.NumStartBytes >= 2)
            {
                if (buffer[idx++] != _config.StartByte2)
                    return result;
            }

            int crcStart = idx;

            // Skip optional fields before length
            if (_config.HasSeq) idx++;
            if (_config.HasSysId) idx++;
            if (_config.HasCompId) idx++;

            // Read length
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
            else if (_getMsgLength != null)
            {
                // For minimal profiles, read msg_id first to get length
                int msgIdPeek = buffer[idx];
                var lenResult = _getMsgLength(msgIdPeek);
                if (!lenResult.HasValue)
                    return result;
                msgLen = lenResult.Value;
            }

            // Skip package ID
            if (_config.HasPkgId) idx++;

            // Read message ID
            int msgId = buffer[idx++];

            // Verify total size
            int totalSize = _config.Overhead + msgLen;
            if (length < totalSize)
                return result;

            // Verify CRC
            if (_config.HasCrc)
            {
                int crcLen = totalSize - crcStart - _config.FooterSize;
                var ck = FletcherChecksum(buffer, crcStart, crcStart + crcLen);
                if (ck.Item1 != buffer[totalSize - 2] || ck.Item2 != buffer[totalSize - 1])
                    return result;
            }

            // Extract message data
            int dataStart = _config.HeaderSize;
            result.Valid = true;
            result.MsgId = msgId;
            result.MsgSize = msgLen;
            result.MsgData = new byte[msgLen];
            Array.Copy(buffer, dataStart, result.MsgData, 0, msgLen);

            return result;
        }

        private static (byte, byte) FletcherChecksum(byte[] buffer, int start, int end)
        {
            byte byte1 = 0;
            byte byte2 = 0;
            for (int i = start; i < end; i++)
            {
                byte1 = (byte)((byte1 + buffer[i]) % 256);
                byte2 = (byte)((byte2 + byte1) % 256);
            }
            return (byte1, byte2);
        }
    }

    /// <summary>
    /// Pre-defined profile configurations
    /// </summary>
    public static class FrameProfiles
    {
        // Constants from FrameHeaders
        public const byte BASIC_START_BYTE = 0x90;
        public const byte PAYLOAD_TYPE_BASE = 0x70;

        /// <summary>
        /// Profile Standard: Basic + Default
        /// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly FrameProfileConfig Standard = new FrameProfileConfig
        {
            Name = "ProfileStandard",
            NumStartBytes = 2,
            StartByte1 = BASIC_START_BYTE,
            StartByte2 = PAYLOAD_TYPE_BASE + 1, // DEFAULT = 1
            HeaderSize = 4,
            FooterSize = 2,
            HasLength = true,
            LengthBytes = 1,
            HasCrc = true,
            HasPkgId = false,
            HasSeq = false,
            HasSysId = false,
            HasCompId = false
        };

        /// <summary>
        /// Profile Sensor: Tiny + Minimal
        /// Frame: [0x70] [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly FrameProfileConfig Sensor = new FrameProfileConfig
        {
            Name = "ProfileSensor",
            NumStartBytes = 1,
            StartByte1 = PAYLOAD_TYPE_BASE + 0, // MINIMAL = 0
            StartByte2 = 0,
            HeaderSize = 2,
            FooterSize = 0,
            HasLength = false,
            LengthBytes = 0,
            HasCrc = false,
            HasPkgId = false,
            HasSeq = false,
            HasSysId = false,
            HasCompId = false
        };

        /// <summary>
        /// Profile IPC: None + Minimal
        /// Frame: [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly FrameProfileConfig IPC = new FrameProfileConfig
        {
            Name = "ProfileIPC",
            NumStartBytes = 0,
            StartByte1 = 0,
            StartByte2 = 0,
            HeaderSize = 1,
            FooterSize = 0,
            HasLength = false,
            LengthBytes = 0,
            HasCrc = false,
            HasPkgId = false,
            HasSeq = false,
            HasSysId = false,
            HasCompId = false
        };

        /// <summary>
        /// Profile Bulk: Basic + Extended
        /// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly FrameProfileConfig Bulk = new FrameProfileConfig
        {
            Name = "ProfileBulk",
            NumStartBytes = 2,
            StartByte1 = BASIC_START_BYTE,
            StartByte2 = PAYLOAD_TYPE_BASE + 4, // EXTENDED = 4
            HeaderSize = 6,
            FooterSize = 2,
            HasLength = true,
            LengthBytes = 2,
            HasCrc = true,
            HasPkgId = true,
            HasSeq = false,
            HasSysId = false,
            HasCompId = false
        };

        /// <summary>
        /// Profile Network: Basic + ExtendedMultiSystemStream
        /// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly FrameProfileConfig Network = new FrameProfileConfig
        {
            Name = "ProfileNetwork",
            NumStartBytes = 2,
            StartByte1 = BASIC_START_BYTE,
            StartByte2 = PAYLOAD_TYPE_BASE + 8, // EXTENDED_MULTI_SYSTEM_STREAM = 8
            HeaderSize = 9,
            FooterSize = 2,
            HasLength = true,
            LengthBytes = 2,
            HasCrc = true,
            HasPkgId = true,
            HasSeq = true,
            HasSysId = true,
            HasCompId = true
        };

        /// <summary>
        /// Create a parser for Profile Standard
        /// </summary>
        public static FrameProfileParser CreateStandardParser() => new FrameProfileParser(Standard);

        /// <summary>
        /// Create a parser for Profile Sensor (requires get_msg_length callback)
        /// </summary>
        public static FrameProfileParser CreateSensorParser(Func<int, int?> getMsgLength) => 
            new FrameProfileParser(Sensor, getMsgLength);

        /// <summary>
        /// Create a parser for Profile IPC (requires get_msg_length callback)
        /// </summary>
        public static FrameProfileParser CreateIPCParser(Func<int, int?> getMsgLength) => 
            new FrameProfileParser(IPC, getMsgLength);

        /// <summary>
        /// Create a parser for Profile Bulk
        /// </summary>
        public static FrameProfileParser CreateBulkParser() => new FrameProfileParser(Bulk);

        /// <summary>
        /// Create a parser for Profile Network
        /// </summary>
        public static FrameProfileParser CreateNetworkParser() => new FrameProfileParser(Network);

        /// <summary>
        /// Create a custom profile configuration
        /// </summary>
        public static FrameProfileConfig CreateCustomConfig(
            string name,
            int numStartBytes,
            byte startByte1,
            byte startByte2,
            bool hasLength,
            int lengthBytes,
            bool hasCrc,
            bool hasPkgId = false,
            bool hasSeq = false,
            bool hasSysId = false,
            bool hasCompId = false)
        {
            // Calculate header size
            int headerSize = numStartBytes + 1; // start bytes + msg_id
            if (hasSeq) headerSize++;
            if (hasSysId) headerSize++;
            if (hasCompId) headerSize++;
            if (hasLength) headerSize += lengthBytes;
            if (hasPkgId) headerSize++;

            return new FrameProfileConfig
            {
                Name = name,
                NumStartBytes = numStartBytes,
                StartByte1 = startByte1,
                StartByte2 = startByte2,
                HeaderSize = headerSize,
                FooterSize = hasCrc ? 2 : 0,
                HasLength = hasLength,
                LengthBytes = lengthBytes,
                HasCrc = hasCrc,
                HasPkgId = hasPkgId,
                HasSeq = hasSeq,
                HasSysId = hasSysId,
                HasCompId = hasCompId
            };
        }
    }
}
