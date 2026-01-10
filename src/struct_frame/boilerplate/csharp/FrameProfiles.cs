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
        public byte[] Encode(int msgId, byte[] payload, int seq = 0, int sysId = 0, int compId = 0, int pkgId = -1)
        {
            // For extended profiles with pkg_id, split the 16-bit msgId into pkg_id and msg_id
            // unless pkgId is explicitly provided (not -1)
            int pkgIdValue;
            int msgIdValue;
            if (_config.HasPkgId && pkgId == -1)
            {
                pkgIdValue = (msgId >> 8) & 0xFF;  // high byte
                msgIdValue = msgId & 0xFF;          // low byte
            }
            else
            {
                pkgIdValue = pkgId == -1 ? 0 : pkgId;
                msgIdValue = msgId;
            }
            
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
                output.Add((byte)(pkgIdValue & 0xFF));

            // Message ID
            output.Add((byte)(msgIdValue & 0xFF));

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

            // Read message ID (16-bit: high byte is pkg_id when HasPkgId, low byte is msg_id)
            int msgId = 0;
            if (_config.HasPkgId)
            {
                msgId = buffer[idx++] << 8;  // pkg_id (high byte)
            }
            msgId |= buffer[idx++];  // msg_id (low byte)

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
    /// BufferReader - Iterate through a buffer parsing multiple frames.
    /// 
    /// Usage:
    ///   var reader = new BufferReader(FrameProfiles.Standard, buffer);
    ///   while (true) {
    ///       var result = reader.Next();
    ///       if (!result.Valid) break;
    ///       // Process result.MsgId, result.MsgData, result.MsgSize
    ///   }
    /// 
    /// For minimal profiles that need getMsgLength:
    ///   var reader = new BufferReader(FrameProfiles.Sensor, buffer, getMsgLength);
    /// </summary>
    public class BufferReader
    {
        private readonly FrameProfileConfig _config;
        private readonly byte[] _buffer;
        private readonly int _size;
        private int _offset;
        private readonly Func<int, int?> _getMsgLength;

        public BufferReader(FrameProfileConfig config, byte[] buffer, Func<int, int?> getMsgLength = null)
        {
            _config = config;
            _buffer = buffer;
            _size = buffer?.Length ?? 0;
            _offset = 0;
            _getMsgLength = getMsgLength;
        }

        /// <summary>
        /// Parse the next frame in the buffer.
        /// Returns FrameParseResult with Valid=true if successful, Valid=false if no more frames.
        /// </summary>
        public FrameParseResult Next()
        {
            if (_offset >= _size)
                return new FrameParseResult();

            // For minimal profiles, check if getMsgLength callback is provided
            if (!_config.HasCrc && !_config.HasLength && _getMsgLength == null)
            {
                _offset = _size;
                return new FrameParseResult();
            }

            int remaining = _size - _offset;
            byte[] remainingBuffer = new byte[remaining];
            Array.Copy(_buffer, _offset, remainingBuffer, 0, remaining);

            var parser = new FrameProfileParser(_config, _getMsgLength);
            var result = parser.ValidateBuffer(remainingBuffer);

            if (result.Valid)
            {
                int frameSize = _config.Overhead + result.MsgSize;
                _offset += frameSize;
            }
            else
            {
                // No more valid frames - stop parsing
                _offset = _size;
            }

            return result;
        }

        /// <summary>
        /// Reset the reader to the beginning of the buffer.
        /// </summary>
        public void Reset() => _offset = 0;

        /// <summary>
        /// Get the current offset in the buffer.
        /// </summary>
        public int Offset => _offset;

        /// <summary>
        /// Get the remaining bytes in the buffer.
        /// </summary>
        public int Remaining => Math.Max(0, _size - _offset);

        /// <summary>
        /// Check if there are more bytes to parse.
        /// </summary>
        public bool HasMore => _offset < _size;
    }

    /// <summary>
    /// BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
    /// 
    /// Usage:
    ///   var writer = new BufferWriter(FrameProfiles.Standard, 1024);
    ///   writer.Write(0x01, msg1Payload);
    ///   writer.Write(0x02, msg2Payload);
    ///   byte[] encodedData = writer.Data();
    ///   int totalBytes = writer.Size;
    /// 
    /// For profiles with extra header fields:
    ///   var writer = new BufferWriter(FrameProfiles.Network, 1024);
    ///   writer.Write(0x01, payload, seq: 1, sysId: 1, compId: 1);
    /// </summary>
    public class BufferWriter
    {
        private readonly FrameProfileConfig _config;
        private readonly int _capacity;
        private readonly byte[] _buffer;
        private int _offset;
        private readonly FrameProfileParser _encoder;

        public BufferWriter(FrameProfileConfig config, int capacity)
        {
            _config = config;
            _capacity = capacity;
            _buffer = new byte[capacity];
            _offset = 0;
            _encoder = new FrameProfileParser(config);
        }

        /// <summary>
        /// Write a message to the buffer.
        /// Returns the number of bytes written, or 0 on failure.
        /// </summary>
        public int Write(int msgId, byte[] payload, int seq = 0, int sysId = 0, int compId = 0, int pkgId = -1)
        {
            byte[] encoded = _encoder.Encode(msgId, payload, seq, sysId, compId, pkgId);
            int written = encoded.Length;

            if (_offset + written > _capacity)
                return 0;

            Array.Copy(encoded, 0, _buffer, _offset, written);
            _offset += written;
            return written;
        }

        /// <summary>
        /// Reset the writer to the beginning of the buffer.
        /// </summary>
        public void Reset() => _offset = 0;

        /// <summary>
        /// Get the total number of bytes written.
        /// </summary>
        public int Size => _offset;

        /// <summary>
        /// Get the remaining capacity in the buffer.
        /// </summary>
        public int Remaining => Math.Max(0, _capacity - _offset);

        /// <summary>
        /// Get the written data as a new byte array.
        /// </summary>
        public byte[] Data()
        {
            byte[] result = new byte[_offset];
            Array.Copy(_buffer, 0, result, 0, _offset);
            return result;
        }
    }

    /// <summary>
    /// Parser state for AccumulatingReader
    /// </summary>
    public enum AccumulatingReaderState
    {
        Idle = 0,
        LookingForStart1 = 1,
        LookingForStart2 = 2,
        CollectingHeader = 3,
        CollectingPayload = 4,
        BufferMode = 5
    }

    /// <summary>
    /// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
    /// 
    /// Handles partial messages across buffer boundaries and supports both:
    /// - Buffer mode: AddData() for processing chunks of data
    /// - Stream mode: PushByte() for byte-by-byte processing (e.g., UART)
    /// 
    /// Buffer mode usage:
    ///   var reader = new AccumulatingReader(FrameProfiles.Standard);
    ///   reader.AddData(chunk1);
    ///   while (true) {
    ///       var result = reader.Next();
    ///       if (!result.Valid) break;
    ///       // Process complete messages
    ///   }
    /// 
    /// Stream mode usage:
    ///   var reader = new AccumulatingReader(FrameProfiles.Standard);
    ///   while (receiving) {
    ///       byte b = ReadByte();
    ///       var result = reader.PushByte(b);
    ///       if (result.Valid) {
    ///           // Process complete message
    ///       }
    ///   }
    /// 
    /// For minimal profiles:
    ///   var reader = new AccumulatingReader(FrameProfiles.Sensor, getMsgLength);
    /// </summary>
    public class AccumulatingReader
    {
        private readonly FrameProfileConfig _config;
        private readonly Func<int, int?> _getMsgLength;
        private readonly int _bufferSize;

        // Internal buffer for partial messages
        private readonly byte[] _internalBuffer;
        private int _internalDataLen;
        private int _expectedFrameSize;
        private AccumulatingReaderState _state;

        // Buffer mode state
        private byte[] _currentBuffer;
        private int _currentSize;
        private int _currentOffset;

        public AccumulatingReader(FrameProfileConfig config, Func<int, int?> getMsgLength = null, int bufferSize = 1024)
        {
            _config = config;
            _getMsgLength = getMsgLength;
            _bufferSize = bufferSize;

            _internalBuffer = new byte[bufferSize];
            _internalDataLen = 0;
            _expectedFrameSize = 0;
            _state = AccumulatingReaderState.Idle;

            _currentBuffer = null;
            _currentSize = 0;
            _currentOffset = 0;
        }

        // =========================================================================
        // Buffer Mode API
        // =========================================================================

        /// <summary>
        /// Add a new buffer of data to process.
        /// </summary>
        public void AddData(byte[] buffer)
        {
            _currentBuffer = buffer;
            _currentSize = buffer?.Length ?? 0;
            _currentOffset = 0;
            _state = AccumulatingReaderState.BufferMode;

            // If we have partial data in internal buffer, try to complete it
            if (_internalDataLen > 0 && buffer != null)
            {
                int spaceAvailable = _bufferSize - _internalDataLen;
                int bytesToCopy = Math.Min(buffer.Length, spaceAvailable);
                Array.Copy(buffer, 0, _internalBuffer, _internalDataLen, bytesToCopy);
                _internalDataLen += bytesToCopy;
            }
        }

        /// <summary>
        /// Parse the next frame (buffer mode).
        /// </summary>
        public FrameParseResult Next()
        {
            if (_state != AccumulatingReaderState.BufferMode)
                return new FrameParseResult();

            // First, try to complete a partial message from the internal buffer
            if (_internalDataLen > 0 && _currentOffset == 0)
            {
                byte[] internalBytes = new byte[_internalDataLen];
                Array.Copy(_internalBuffer, 0, internalBytes, 0, _internalDataLen);
                var result = ParseBuffer(internalBytes);

                if (result.Valid)
                {
                    int frameSize = _config.Overhead + result.MsgSize;
                    int partialLen = _internalDataLen > _currentSize ? _internalDataLen - _currentSize : 0;
                    int bytesFromCurrent = frameSize > partialLen ? frameSize - partialLen : 0;
                    _currentOffset = bytesFromCurrent;

                    _internalDataLen = 0;
                    _expectedFrameSize = 0;

                    return result;
                }
                else
                {
                    return new FrameParseResult();
                }
            }

            // Parse from current buffer
            if (_currentBuffer == null || _currentOffset >= _currentSize)
                return new FrameParseResult();

            int remaining = _currentSize - _currentOffset;
            byte[] remainingBuffer = new byte[remaining];
            Array.Copy(_currentBuffer, _currentOffset, remainingBuffer, 0, remaining);
            var parseResult = ParseBuffer(remainingBuffer);

            if (parseResult.Valid)
            {
                int frameSize = _config.Overhead + parseResult.MsgSize;
                _currentOffset += frameSize;
                return parseResult;
            }

            // Parse failed - might be partial message at end of buffer
            int remainingLen = _currentSize - _currentOffset;
            if (remainingLen > 0 && remainingLen < _bufferSize)
            {
                Array.Copy(_currentBuffer, _currentOffset, _internalBuffer, 0, remainingLen);
                _internalDataLen = remainingLen;
                _currentOffset = _currentSize;
            }

            return new FrameParseResult();
        }

        // =========================================================================
        // Stream Mode API
        // =========================================================================

        /// <summary>
        /// Push a single byte for parsing (stream mode).
        /// </summary>
        public FrameParseResult PushByte(byte b)
        {
            // Initialize state on first byte if idle
            if (_state == AccumulatingReaderState.Idle || _state == AccumulatingReaderState.BufferMode)
            {
                _state = AccumulatingReaderState.LookingForStart1;
                _internalDataLen = 0;
                _expectedFrameSize = 0;
            }

            switch (_state)
            {
                case AccumulatingReaderState.LookingForStart1:
                    return HandleLookingForStart1(b);
                case AccumulatingReaderState.LookingForStart2:
                    return HandleLookingForStart2(b);
                case AccumulatingReaderState.CollectingHeader:
                    return HandleCollectingHeader(b);
                case AccumulatingReaderState.CollectingPayload:
                    return HandleCollectingPayload(b);
                default:
                    _state = AccumulatingReaderState.LookingForStart1;
                    return new FrameParseResult();
            }
        }

        private FrameParseResult HandleLookingForStart1(byte b)
        {
            if (_config.NumStartBytes == 0)
            {
                _internalBuffer[0] = b;
                _internalDataLen = 1;

                if (!_config.HasLength && !_config.HasCrc)
                {
                    return HandleMinimalMsgId(b);
                }
                else
                {
                    _state = AccumulatingReaderState.CollectingHeader;
                }
            }
            else
            {
                if (b == _config.StartByte1)
                {
                    _internalBuffer[0] = b;
                    _internalDataLen = 1;

                    if (_config.NumStartBytes == 1)
                    {
                        _state = AccumulatingReaderState.CollectingHeader;
                    }
                    else
                    {
                        _state = AccumulatingReaderState.LookingForStart2;
                    }
                }
            }
            return new FrameParseResult();
        }

        private FrameParseResult HandleLookingForStart2(byte b)
        {
            if (b == _config.StartByte2)
            {
                _internalBuffer[_internalDataLen++] = b;
                _state = AccumulatingReaderState.CollectingHeader;
            }
            else if (b == _config.StartByte1)
            {
                _internalBuffer[0] = b;
                _internalDataLen = 1;
            }
            else
            {
                _state = AccumulatingReaderState.LookingForStart1;
                _internalDataLen = 0;
            }
            return new FrameParseResult();
        }

        private FrameParseResult HandleCollectingHeader(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _state = AccumulatingReaderState.LookingForStart1;
                _internalDataLen = 0;
                return new FrameParseResult();
            }

            _internalBuffer[_internalDataLen++] = b;

            if (_internalDataLen >= _config.HeaderSize)
            {
                if (!_config.HasLength && !_config.HasCrc)
                {
                    int msgId = _internalBuffer[_config.HeaderSize - 1];
                    if (_getMsgLength != null)
                    {
                        int? msgLen = _getMsgLength(msgId);
                        if (msgLen.HasValue)
                        {
                            _expectedFrameSize = _config.HeaderSize + msgLen.Value;

                            if (_expectedFrameSize > _bufferSize)
                            {
                                _state = AccumulatingReaderState.LookingForStart1;
                                _internalDataLen = 0;
                                return new FrameParseResult();
                            }

                            if (msgLen.Value == 0)
                            {
                                var result = new FrameParseResult
                                {
                                    Valid = true,
                                    MsgId = msgId,
                                    MsgSize = 0,
                                    MsgData = new byte[0]
                                };
                                _state = AccumulatingReaderState.LookingForStart1;
                                _internalDataLen = 0;
                                _expectedFrameSize = 0;
                                return result;
                            }

                            _state = AccumulatingReaderState.CollectingPayload;
                        }
                        else
                        {
                            _state = AccumulatingReaderState.LookingForStart1;
                            _internalDataLen = 0;
                        }
                    }
                    else
                    {
                        _state = AccumulatingReaderState.LookingForStart1;
                        _internalDataLen = 0;
                    }
                }
                else
                {
                    int lenOffset = _config.NumStartBytes;
                    if (_config.HasSeq) lenOffset++;
                    if (_config.HasSysId) lenOffset++;
                    if (_config.HasCompId) lenOffset++;

                    int payloadLen = 0;
                    if (_config.HasLength)
                    {
                        if (_config.LengthBytes == 1)
                        {
                            payloadLen = _internalBuffer[lenOffset];
                        }
                        else
                        {
                            payloadLen = _internalBuffer[lenOffset] | (_internalBuffer[lenOffset + 1] << 8);
                        }
                    }

                    _expectedFrameSize = _config.Overhead + payloadLen;

                    if (_expectedFrameSize > _bufferSize)
                    {
                        _state = AccumulatingReaderState.LookingForStart1;
                        _internalDataLen = 0;
                        return new FrameParseResult();
                    }

                    if (_internalDataLen >= _expectedFrameSize)
                    {
                        return ValidateAndReturn();
                    }

                    _state = AccumulatingReaderState.CollectingPayload;
                }
            }

            return new FrameParseResult();
        }

        private FrameParseResult HandleCollectingPayload(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _state = AccumulatingReaderState.LookingForStart1;
                _internalDataLen = 0;
                return new FrameParseResult();
            }

            _internalBuffer[_internalDataLen++] = b;

            if (_internalDataLen >= _expectedFrameSize)
            {
                return ValidateAndReturn();
            }

            return new FrameParseResult();
        }

        private FrameParseResult HandleMinimalMsgId(byte msgId)
        {
            if (_getMsgLength != null)
            {
                int? msgLen = _getMsgLength(msgId);
                if (msgLen.HasValue)
                {
                    _expectedFrameSize = _config.HeaderSize + msgLen.Value;

                    if (_expectedFrameSize > _bufferSize)
                    {
                        _state = AccumulatingReaderState.LookingForStart1;
                        _internalDataLen = 0;
                        return new FrameParseResult();
                    }

                    if (msgLen.Value == 0)
                    {
                        var result = new FrameParseResult
                        {
                            Valid = true,
                            MsgId = msgId,
                            MsgSize = 0,
                            MsgData = new byte[0]
                        };
                        _state = AccumulatingReaderState.LookingForStart1;
                        _internalDataLen = 0;
                        _expectedFrameSize = 0;
                        return result;
                    }

                    _state = AccumulatingReaderState.CollectingPayload;
                }
                else
                {
                    _state = AccumulatingReaderState.LookingForStart1;
                    _internalDataLen = 0;
                }
            }
            else
            {
                _state = AccumulatingReaderState.LookingForStart1;
                _internalDataLen = 0;
            }
            return new FrameParseResult();
        }

        private FrameParseResult ValidateAndReturn()
        {
            byte[] internalBytes = new byte[_internalDataLen];
            Array.Copy(_internalBuffer, 0, internalBytes, 0, _internalDataLen);
            var result = ParseBuffer(internalBytes);

            _state = AccumulatingReaderState.LookingForStart1;
            _internalDataLen = 0;
            _expectedFrameSize = 0;

            return result;
        }

        private FrameParseResult ParseBuffer(byte[] buffer)
        {
            var parser = new FrameProfileParser(_config, _getMsgLength);
            return parser.ValidateBuffer(buffer);
        }

        // =========================================================================
        // Common API
        // =========================================================================

        /// <summary>
        /// Check if there might be more data to parse (buffer mode only).
        /// </summary>
        public bool HasMore
        {
            get
            {
                if (_state != AccumulatingReaderState.BufferMode) return false;
                return (_internalDataLen > 0) || (_currentBuffer != null && _currentOffset < _currentSize);
            }
        }

        /// <summary>
        /// Check if there's a partial message waiting for more data.
        /// </summary>
        public bool HasPartial => _internalDataLen > 0;

        /// <summary>
        /// Get the size of the partial message data (0 if none).
        /// </summary>
        public int PartialSize => _internalDataLen;

        /// <summary>
        /// Get current parser state (for debugging).
        /// </summary>
        public AccumulatingReaderState State => _state;

        /// <summary>
        /// Reset the reader, clearing any partial message data.
        /// </summary>
        public void Reset()
        {
            _internalDataLen = 0;
            _expectedFrameSize = 0;
            _state = AccumulatingReaderState.Idle;
            _currentBuffer = null;
            _currentSize = 0;
            _currentOffset = 0;
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

        // =========================================================================
        // Convenience factory functions for BufferReader/BufferWriter/AccumulatingReader
        // =========================================================================

        /// <summary>
        /// Create a BufferReader for Profile Standard
        /// </summary>
        public static BufferReader CreateStandardReader(byte[] buffer) => new BufferReader(Standard, buffer);

        /// <summary>
        /// Create a BufferWriter for Profile Standard
        /// </summary>
        public static BufferWriter CreateStandardWriter(int capacity = 1024) => new BufferWriter(Standard, capacity);

        /// <summary>
        /// Create an AccumulatingReader for Profile Standard
        /// </summary>
        public static AccumulatingReader CreateStandardAccumulatingReader(int bufferSize = 1024) => 
            new AccumulatingReader(Standard, null, bufferSize);

        /// <summary>
        /// Create a BufferReader for Profile Sensor
        /// </summary>
        public static BufferReader CreateSensorReader(byte[] buffer, Func<int, int?> getMsgLength) => 
            new BufferReader(Sensor, buffer, getMsgLength);

        /// <summary>
        /// Create a BufferWriter for Profile Sensor
        /// </summary>
        public static BufferWriter CreateSensorWriter(int capacity = 1024) => new BufferWriter(Sensor, capacity);

        /// <summary>
        /// Create an AccumulatingReader for Profile Sensor
        /// </summary>
        public static AccumulatingReader CreateSensorAccumulatingReader(Func<int, int?> getMsgLength, int bufferSize = 1024) => 
            new AccumulatingReader(Sensor, getMsgLength, bufferSize);

        /// <summary>
        /// Create a BufferReader for Profile IPC
        /// </summary>
        public static BufferReader CreateIPCReader(byte[] buffer, Func<int, int?> getMsgLength) => 
            new BufferReader(IPC, buffer, getMsgLength);

        /// <summary>
        /// Create a BufferWriter for Profile IPC
        /// </summary>
        public static BufferWriter CreateIPCWriter(int capacity = 1024) => new BufferWriter(IPC, capacity);

        /// <summary>
        /// Create an AccumulatingReader for Profile IPC
        /// </summary>
        public static AccumulatingReader CreateIPCAccumulatingReader(Func<int, int?> getMsgLength, int bufferSize = 1024) => 
            new AccumulatingReader(IPC, getMsgLength, bufferSize);

        /// <summary>
        /// Create a BufferReader for Profile Bulk
        /// </summary>
        public static BufferReader CreateBulkReader(byte[] buffer) => new BufferReader(Bulk, buffer);

        /// <summary>
        /// Create a BufferWriter for Profile Bulk
        /// </summary>
        public static BufferWriter CreateBulkWriter(int capacity = 1024) => new BufferWriter(Bulk, capacity);

        /// <summary>
        /// Create an AccumulatingReader for Profile Bulk
        /// </summary>
        public static AccumulatingReader CreateBulkAccumulatingReader(int bufferSize = 1024) => 
            new AccumulatingReader(Bulk, null, bufferSize);

        /// <summary>
        /// Create a BufferReader for Profile Network
        /// </summary>
        public static BufferReader CreateNetworkReader(byte[] buffer) => new BufferReader(Network, buffer);

        /// <summary>
        /// Create a BufferWriter for Profile Network
        /// </summary>
        public static BufferWriter CreateNetworkWriter(int capacity = 1024) => new BufferWriter(Network, capacity);

        /// <summary>
        /// Create an AccumulatingReader for Profile Network
        /// </summary>
        public static AccumulatingReader CreateNetworkAccumulatingReader(int bufferSize = 1024) => 
            new AccumulatingReader(Network, null, bufferSize);

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
