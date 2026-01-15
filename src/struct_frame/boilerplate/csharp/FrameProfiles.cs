// Frame Profiles - Pre-defined Header + Payload combinations (C#)
// This file mirrors the C++ FrameProfiles.hpp structure
//
// Standard Profiles:
// - ProfileStandard: Basic + Default (General serial/UART)
// - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
// - ProfileIPC: None + Minimal (Trusted inter-process communication)
// - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
// - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
//
// Each profile provides:
// - ProfileConfig: configuration parameters
// - Encoder: encode messages into a buffer
// - BufferParser: parse/validate a complete frame in a buffer
// - BufferReader: iterate through multiple frames in a buffer
// - BufferWriter: encode multiple frames with automatic offset tracking
// - AccumulatingReader: unified parser supporting both buffer chunks and byte-by-byte streaming

#nullable enable

using System;
using StructFrame.FrameHeaders;
using StructFrame.PayloadTypes;

namespace StructFrame
{
    /// <summary>
    /// Profile configuration - combines a HeaderConfig with a PayloadConfig
    /// </summary>
    public class ProfileConfig
    {
        public string Name { get; }
        public HeaderConfig Header { get; }
        public PayloadConfig Payload { get; }

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
        }

        /// <summary>
        /// Compute start byte 1 (may be dynamic for payload type encoding)
        /// </summary>
        public byte ComputedStartByte1
        {
            get
            {
                if (Header.EncodesPayloadType && Header.NumStartBytes == 1)
                {
                    return (byte)(HeaderConstants.PayloadTypeBase + (byte)Payload.PayloadType);
                }
                return Header.StartByte1;
            }
        }

        /// <summary>
        /// Compute start byte 2 (may be dynamic for payload type encoding)
        /// </summary>
        public byte ComputedStartByte2
        {
            get
            {
                if (Header.EncodesPayloadType && Header.NumStartBytes == 2)
                {
                    return (byte)(HeaderConstants.PayloadTypeBase + (byte)Payload.PayloadType);
                }
                return Header.StartByte2;
            }
        }
    }

    /// <summary>
    /// Pre-defined profile configurations
    /// </summary>
    public static class Profiles
    {
        /// <summary>
        /// ProfileStandard: Basic + Default
        /// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Standard = new ProfileConfig(
            "ProfileStandard",
            HeaderConfigs.Basic,
            PayloadConfigs.Default
        );

        /// <summary>
        /// ProfileSensor: Tiny + Minimal
        /// Frame: [0x70] [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly ProfileConfig Sensor = new ProfileConfig(
            "ProfileSensor",
            HeaderConfigs.Tiny,
            PayloadConfigs.Minimal
        );

        /// <summary>
        /// ProfileIPC: None + Minimal
        /// Frame: [MSG_ID] [PAYLOAD]
        /// </summary>
        public static readonly ProfileConfig IPC = new ProfileConfig(
            "ProfileIPC",
            HeaderConfigs.None,
            PayloadConfigs.Minimal
        );

        /// <summary>
        /// ProfileBulk: Basic + Extended
        /// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Bulk = new ProfileConfig(
            "ProfileBulk",
            HeaderConfigs.Basic,
            PayloadConfigs.Extended
        );

        /// <summary>
        /// ProfileNetwork: Basic + ExtendedMultiSystemStream
        /// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
        /// </summary>
        public static readonly ProfileConfig Network = new ProfileConfig(
            "ProfileNetwork",
            HeaderConfigs.Basic,
            PayloadConfigs.ExtendedMultiSystemStream
        );

        /// <summary>
        /// Get a profile by name
        /// </summary>
        public static ProfileConfig GetByName(string name)
        {
            return name.ToLowerInvariant() switch
            {
                "profile_standard" or "profilestandard" or "standard" => Standard,
                "profile_sensor" or "profilesensor" or "sensor" => Sensor,
                "profile_ipc" or "profileipc" or "ipc" => IPC,
                "profile_bulk" or "profilebulk" or "bulk" => Bulk,
                "profile_network" or "profilenetwork" or "network" => Network,
                _ => throw new ArgumentException($"Unknown profile: {name}")
            };
        }

        /// <summary>
        /// Create a BufferWriter for the specified profile name
        /// </summary>
        public static BufferWriter CreateWriter(string profileName)
        {
            return new BufferWriter(GetByName(profileName));
        }

        /// <summary>
        /// Create a BufferReader for the specified profile name
        /// </summary>
        public static BufferReader CreateReader(string profileName, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            return new BufferReader(GetByName(profileName), getMessageInfo);
        }

        /// <summary>
        /// Create a FrameEncoder for the specified profile name
        /// </summary>
        public static FrameEncoder CreateEncoder(string profileName)
        {
            return new FrameEncoder(GetByName(profileName));
        }

        /// <summary>
        /// Create a BufferParser for the specified profile name
        /// </summary>
        public static BufferParser CreateParser(string profileName, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            return new BufferParser(GetByName(profileName), getMessageInfo);
        }
    }

    /// <summary>
    /// Generic frame encoder for frames with CRC
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
                // Check if message has SerializeMaxSize() method (variable messages only)
                var serializeMaxSizeMethod = message.GetType().GetMethod("SerializeMaxSize", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                if (serializeMaxSizeMethod != null)
                {
                    var result = serializeMaxSizeMethod.Invoke(message, null);
                    payload = result as byte[] ?? Array.Empty<byte>();
                }
                else
                {
                    // Non-variable message - Serialize() always returns MAX_SIZE
                    payload = message.Serialize();
                }
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

            // Calculate and write CRC
            if (_config.HasCrc)
            {
                int crcLen = idx - crcStart;
                var ck = FrameBase.FletcherChecksum(buffer, crcStart, crcLen, magic1, magic2);
                buffer[idx++] = ck.Byte1;
                buffer[idx++] = ck.Byte2;
            }

            return idx - offset;
        }
    }

    /// <summary>
    /// Generic buffer parser for frames
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
        /// Parse a frame from a buffer
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
    /// BufferReader - Iterate through a buffer parsing multiple frames
    /// </summary>
    public class BufferReader
    {
        private readonly ProfileConfig _config;
        private readonly BufferParser _parser;
        private byte[]? _buffer;
        private int _offset;
        private int _size;

        public BufferReader(ProfileConfig config, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            _config = config;
            _parser = new BufferParser(config, getMessageInfo);
        }

        /// <summary>
        /// Set the buffer to read from
        /// </summary>
        public void SetBuffer(byte[] buffer, int offset, int size)
        {
            _buffer = buffer;
            _offset = offset;
            _size = size;
        }

        /// <summary>
        /// Set the buffer to read from (convenience overload)
        /// </summary>
        public void SetBuffer(byte[] buffer)
        {
            SetBuffer(buffer, 0, buffer.Length);
        }

        /// <summary>
        /// Parse the next frame in the buffer
        /// </summary>
        public FrameMsgInfo Next()
        {
            if (_buffer == null || _offset >= _size)
            {
                return FrameMsgInfo.Invalid;
            }

            var result = _parser.Parse(_buffer, _offset, _size - _offset);

            if (result.Valid && result.FrameSize > 0)
            {
                _offset += result.FrameSize;
            }

            return result;
        }

        /// <summary>
        /// Reset the reader to the beginning of the buffer
        /// </summary>
        public void Reset()
        {
            _offset = 0;
        }

        /// <summary>
        /// Get the current offset in the buffer
        /// </summary>
        public int Offset => _offset;

        /// <summary>
        /// Get the remaining bytes in the buffer
        /// </summary>
        public int Remaining => _size > _offset ? _size - _offset : 0;

        /// <summary>
        /// Check if there are more bytes to parse
        /// </summary>
        public bool HasMore => _offset < _size;
    }

    /// <summary>
    /// BufferWriter - Encode multiple frames into a buffer with automatic offset tracking
    /// </summary>
    public class BufferWriter
    {
        private readonly ProfileConfig _config;
        private readonly FrameEncoder _encoder;
        private byte[]? _buffer;
        private int _offset;
        private int _capacity;

        public BufferWriter(ProfileConfig config)
        {
            _config = config;
            _encoder = new FrameEncoder(config);
        }

        /// <summary>
        /// Set the buffer to write to
        /// </summary>
        public void SetBuffer(byte[] buffer, int offset, int capacity)
        {
            _buffer = buffer;
            _offset = offset;
            _capacity = capacity;
        }

        /// <summary>
        /// Set the buffer to write to (convenience overload)
        /// </summary>
        public void SetBuffer(byte[] buffer)
        {
            SetBuffer(buffer, 0, buffer.Length);
        }

        /// <summary>
        /// Write a message implementing IStructFrameMessage to the buffer.
        /// Magic numbers for checksum are automatically extracted from the message.
        /// </summary>
        public int Write(IStructFrameMessage message, byte seq = 0, byte sysId = 0, byte compId = 0)
        {
            if (_buffer == null)
            {
                return 0;
            }

            int written = _encoder.Encode(_buffer, _offset, message, seq, sysId, compId);
            if (written > 0)
            {
                _offset += written;
            }
            return written;
        }

        /// <summary>
        /// Reset the writer to the beginning of the buffer
        /// </summary>
        public void Reset()
        {
            _offset = 0;
        }

        /// <summary>
        /// Get the total number of bytes written
        /// </summary>
        public int Size => _offset;

        /// <summary>
        /// Get the remaining capacity in the buffer
        /// </summary>
        public int Remaining => _capacity > _offset ? _capacity - _offset : 0;

        /// <summary>
        /// Get the buffer data as a new array
        /// </summary>
        public byte[] GetData()
        {
            if (_buffer == null || _offset == 0)
            {
                return Array.Empty<byte>();
            }
            byte[] result = new byte[_offset];
            Array.Copy(_buffer, 0, result, 0, _offset);
            return result;
        }
    }

    /// <summary>
    /// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input
    /// </summary>
    public class AccumulatingReader
    {
        /// <summary>
        /// Parser state for streaming mode
        /// </summary>
        public enum State
        {
            Idle = 0,
            LookingForStart1,
            LookingForStart2,
            CollectingHeader,
            CollectingPayload,
            BufferMode
        }

        private readonly ProfileConfig _config;
        private readonly BufferParser _parser;
        private readonly Func<int, MessageInfo?>? _getMessageInfo;
        private readonly int _bufferSize;

        // Internal buffer for partial messages
        private byte[] _internalBuffer;
        private int _internalDataLen;
        private int _expectedFrameSize;
        private State _state;

        // Buffer mode state
        private byte[]? _currentBuffer;
        private int _currentOffset;
        private int _currentSize;

        public AccumulatingReader(ProfileConfig config, int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            _config = config;
            _bufferSize = bufferSize;
            _getMessageInfo = getMessageInfo;
            _parser = new BufferParser(config, getMessageInfo);
            _internalBuffer = new byte[bufferSize];
            Reset();
        }

        /// <summary>
        /// Reset the reader, clearing any partial message data
        /// </summary>
        public void Reset()
        {
            _internalDataLen = 0;
            _expectedFrameSize = 0;
            _state = State.Idle;
            _currentBuffer = null;
            _currentOffset = 0;
            _currentSize = 0;
        }

        /// <summary>
        /// Get current parser state
        /// </summary>
        public State CurrentState => _state;

        /// <summary>
        /// Check if there's a partial message waiting for more data
        /// </summary>
        public bool HasPartial => _internalDataLen > 0;

        /// <summary>
        /// Get the size of the partial message data
        /// </summary>
        public int PartialSize => _internalDataLen;

        // =========================================================================
        // Buffer Mode API
        // =========================================================================

        /// <summary>
        /// Add a new buffer of data to process.
        /// Note: The buffer is NOT copied. Ensure it remains valid until parsing is complete.
        /// </summary>
        public void AddData(byte[] buffer, int offset, int size)
        {
            _currentBuffer = buffer;
            _currentOffset = offset;
            _currentSize = size;
            _state = State.BufferMode;

            // If we have partial data in internal buffer, append new data to complete it
            if (_internalDataLen > 0)
            {
                int spaceAvailable = _bufferSize - _internalDataLen;
                int bytesToCopy = Math.Min(size, spaceAvailable);

                Array.Copy(buffer, offset, _internalBuffer, _internalDataLen, bytesToCopy);
                _internalDataLen += bytesToCopy;
            }
        }

        /// <summary>
        /// Add a new buffer of data to process (convenience overload).
        /// Note: The buffer is NOT copied. Ensure it remains valid until parsing is complete.
        /// </summary>
        public void AddData(byte[] buffer)
        {
            AddData(buffer, 0, buffer.Length);
        }

        /// <summary>
        /// Try to parse the next frame (buffer mode).
        /// Returns true if a valid frame was found, false otherwise.
        /// This method is useful for high-throughput scenarios where you want to avoid
        /// checking the Valid property separately.
        /// </summary>
        public bool TryNext(out FrameMsgInfo result)
        {
            result = Next();
            return result.Valid;
        }

        /// <summary>
        /// Parse the next frame (buffer mode)
        /// </summary>
        public FrameMsgInfo Next()
        {
            if (_state != State.BufferMode)
            {
                return FrameMsgInfo.Invalid;
            }

            // First, try to complete a partial message from the internal buffer
            if (_internalDataLen > 0 && _currentOffset == 0)
            {
                var result = _parser.Parse(_internalBuffer, 0, _internalDataLen);

                if (result.Valid)
                {
                    int partialLen = _internalDataLen > _currentSize ? _internalDataLen - _currentSize : 0;
                    int bytesFromCurrent = result.FrameSize > partialLen ? result.FrameSize - partialLen : 0;
                    _currentOffset = bytesFromCurrent;
                    _internalDataLen = 0;
                    _expectedFrameSize = 0;
                    return result;
                }
                else
                {
                    return FrameMsgInfo.Invalid;
                }
            }

            // Parse from current buffer
            if (_currentBuffer == null || _currentOffset >= _currentSize)
            {
                return FrameMsgInfo.Invalid;
            }

            var parseResult = _parser.Parse(_currentBuffer, _currentOffset, _currentSize - _currentOffset);

            if (parseResult.Valid && parseResult.FrameSize > 0)
            {
                _currentOffset += parseResult.FrameSize;
                return parseResult;
            }

            // Parse failed - might be partial message at end of buffer
            int remaining = _currentSize - _currentOffset;
            if (remaining > 0 && remaining < _bufferSize)
            {
                Array.Copy(_currentBuffer, _currentOffset, _internalBuffer, 0, remaining);
                _internalDataLen = remaining;
                _currentOffset = _currentSize;
            }

            return FrameMsgInfo.Invalid;
        }

        /// <summary>
        /// Check if there might be more data to parse (buffer mode only)
        /// </summary>
        public bool HasMore
        {
            get
            {
                if (_state != State.BufferMode) return false;
                return (_internalDataLen > 0) || (_currentBuffer != null && _currentOffset < _currentSize);
            }
        }

        // =========================================================================
        // Stream Mode API
        // =========================================================================

        /// <summary>
        /// Push a single byte for parsing (stream mode)
        /// </summary>
        public FrameMsgInfo PushByte(byte b)
        {
            if (_state == State.Idle || _state == State.BufferMode)
            {
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                _expectedFrameSize = 0;
            }

            switch (_state)
            {
                case State.LookingForStart1:
                    return HandleLookingForStart1(b);
                case State.LookingForStart2:
                    return HandleLookingForStart2(b);
                case State.CollectingHeader:
                    return HandleCollectingHeader(b);
                case State.CollectingPayload:
                    return HandleCollectingPayload(b);
                default:
                    _state = State.LookingForStart1;
                    return FrameMsgInfo.Invalid;
            }
        }

        private FrameMsgInfo HandleLookingForStart1(byte b)
        {
            if (_config.NumStartBytes == 0)
            {
                // No start bytes - this byte is the beginning of the frame
                _internalBuffer[0] = b;
                _internalDataLen = 1;

                if (!_config.HasLength && !_config.HasCrc)
                {
                    return HandleMinimalMsgId(b);
                }
                else
                {
                    _state = State.CollectingHeader;
                }
            }
            else
            {
                if (b == _config.ComputedStartByte1)
                {
                    _internalBuffer[0] = b;
                    _internalDataLen = 1;

                    if (_config.NumStartBytes == 1)
                    {
                        _state = State.CollectingHeader;
                    }
                    else
                    {
                        _state = State.LookingForStart2;
                    }
                }
            }
            return FrameMsgInfo.Invalid;
        }

        private FrameMsgInfo HandleLookingForStart2(byte b)
        {
            if (b == _config.ComputedStartByte2)
            {
                _internalBuffer[_internalDataLen++] = b;
                _state = State.CollectingHeader;
            }
            else if (b == _config.ComputedStartByte1)
            {
                _internalBuffer[0] = b;
                _internalDataLen = 1;
            }
            else
            {
                _state = State.LookingForStart1;
                _internalDataLen = 0;
            }
            return FrameMsgInfo.Invalid;
        }

        private FrameMsgInfo HandleCollectingHeader(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return FrameMsgInfo.Invalid;
            }

            _internalBuffer[_internalDataLen++] = b;

            if (_internalDataLen >= _config.HeaderSize)
            {
                if (!_config.HasLength && !_config.HasCrc)
                {
                    byte msgId = _internalBuffer[_config.HeaderSize - 1];
                    var msgInfo = _getMessageInfo?.Invoke(msgId);
                    if (msgInfo.HasValue)
                    {
                        _expectedFrameSize = _config.HeaderSize + msgInfo.Value.Size;

                        if (_expectedFrameSize > _bufferSize)
                        {
                            _state = State.LookingForStart1;
                            _internalDataLen = 0;
                            return FrameMsgInfo.Invalid;
                        }

                        if (msgInfo.Value.Size == 0)
                        {
                            var result = new FrameMsgInfo(true, msgId, 0, _expectedFrameSize, _internalBuffer, _config.HeaderSize);
                            _state = State.LookingForStart1;
                            _internalDataLen = 0;
                            _expectedFrameSize = 0;
                            return result;
                        }

                        _state = State.CollectingPayload;
                    }
                    else
                    {
                        _state = State.LookingForStart1;
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
                        _state = State.LookingForStart1;
                        _internalDataLen = 0;
                        return FrameMsgInfo.Invalid;
                    }

                    if (_internalDataLen >= _expectedFrameSize)
                    {
                        return ValidateAndReturn();
                    }

                    _state = State.CollectingPayload;
                }
            }

            return FrameMsgInfo.Invalid;
        }

        private FrameMsgInfo HandleCollectingPayload(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return FrameMsgInfo.Invalid;
            }

            _internalBuffer[_internalDataLen++] = b;

            if (_internalDataLen >= _expectedFrameSize)
            {
                return ValidateAndReturn();
            }

            return FrameMsgInfo.Invalid;
        }

        private FrameMsgInfo HandleMinimalMsgId(byte msgId)
        {
            var msgInfo = _getMessageInfo?.Invoke(msgId);
            if (msgInfo.HasValue)
            {
                _expectedFrameSize = _config.HeaderSize + msgInfo.Value.Size;

                if (_expectedFrameSize > _bufferSize)
                {
                    _state = State.LookingForStart1;
                    _internalDataLen = 0;
                    return FrameMsgInfo.Invalid;
                }

                if (msgInfo.Value.Size == 0)
                {
                    var result = new FrameMsgInfo(true, msgId, 0, _expectedFrameSize, _internalBuffer, _config.HeaderSize);
                    _state = State.LookingForStart1;
                    _internalDataLen = 0;
                    _expectedFrameSize = 0;
                    return result;
                }

                _state = State.CollectingPayload;
            }
            else
            {
                _state = State.LookingForStart1;
                _internalDataLen = 0;
            }
            return FrameMsgInfo.Invalid;
        }

        private FrameMsgInfo ValidateAndReturn()
        {
            var result = _parser.Parse(_internalBuffer, 0, _internalDataLen);

            _state = State.LookingForStart1;
            _internalDataLen = 0;
            _expectedFrameSize = 0;

            return result;
        }
    }

    // ============================================================================
    // Profile Providers - Compile-time profile selection using generics
    // ============================================================================

    /// <summary>
    /// Interface for profile providers - enables compile-time profile selection
    /// </summary>
    public interface IProfileProvider
    {
        static abstract ProfileConfig Profile { get; }
    }

    public struct StandardProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Standard;
    }

    public struct SensorProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Sensor;
    }

    public struct IPCProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.IPC;
    }

    public struct BulkProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Bulk;
    }

    public struct NetworkProfile : IProfileProvider
    {
        public static ProfileConfig Profile => Profiles.Network;
    }

    // ============================================================================
    // Generic Profile-Based Classes
    // ============================================================================

    /// <summary>
    /// Generic frame encoder with compile-time profile selection
    /// Usage: var encoder = new FrameEncoder&lt;StandardProfile&gt;();
    /// </summary>
    public class FrameEncoder<TProfile> : FrameEncoder where TProfile : struct, IProfileProvider
    {
        public FrameEncoder() : base(TProfile.Profile) { }
    }

    /// <summary>
    /// Generic buffer parser with compile-time profile selection
    /// </summary>
    public class BufferParser<TProfile> : BufferParser where TProfile : struct, IProfileProvider
    {
        public BufferParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(TProfile.Profile, getMessageInfo) { }
    }

    /// <summary>
    /// Generic buffer reader with compile-time profile selection
    /// </summary>
    public class BufferReader<TProfile> : BufferReader where TProfile : struct, IProfileProvider
    {
        public BufferReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(TProfile.Profile, getMessageInfo) { }
    }

    /// <summary>
    /// Generic buffer writer with compile-time profile selection
    /// </summary>
    public class BufferWriter<TProfile> : BufferWriter where TProfile : struct, IProfileProvider
    {
        public BufferWriter() : base(TProfile.Profile) { }
    }

    /// <summary>
    /// Generic accumulating reader with compile-time profile selection
    /// </summary>
    public class AccumulatingReader<TProfile> : AccumulatingReader where TProfile : struct, IProfileProvider
    {
        public AccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) 
            : base(TProfile.Profile, bufferSize, getMessageInfo) { }
    }

    // ============================================================================
    // Type Aliases for Backwards Compatibility (optional - can be removed)
    // ============================================================================

    // FrameEncoder aliases
    public class ProfileStandardEncoder : FrameEncoder<StandardProfile> { }
    public class ProfileSensorEncoder : FrameEncoder<SensorProfile> { }
    public class ProfileIPCEncoder : FrameEncoder<IPCProfile> { }
    public class ProfileBulkEncoder : FrameEncoder<BulkProfile> { }
    public class ProfileNetworkEncoder : FrameEncoder<NetworkProfile> { }

    // BufferParser aliases
    public class ProfileStandardParser : BufferParser<StandardProfile> { public ProfileStandardParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileSensorParser : BufferParser<SensorProfile> { public ProfileSensorParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileIPCParser : BufferParser<IPCProfile> { public ProfileIPCParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileBulkParser : BufferParser<BulkProfile> { public ProfileBulkParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileNetworkParser : BufferParser<NetworkProfile> { public ProfileNetworkParser(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }

    // BufferReader aliases
    public class ProfileStandardReader : BufferReader<StandardProfile> { public ProfileStandardReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileSensorReader : BufferReader<SensorProfile> { public ProfileSensorReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileIPCReader : BufferReader<IPCProfile> { public ProfileIPCReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileBulkReader : BufferReader<BulkProfile> { public ProfileBulkReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }
    public class ProfileNetworkReader : BufferReader<NetworkProfile> { public ProfileNetworkReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(getMessageInfo) { } }

    // BufferWriter aliases
    public class ProfileStandardWriter : BufferWriter<StandardProfile> { }
    public class ProfileSensorWriter : BufferWriter<SensorProfile> { }
    public class ProfileIPCWriter : BufferWriter<IPCProfile> { }
    public class ProfileBulkWriter : BufferWriter<BulkProfile> { }
    public class ProfileNetworkWriter : BufferWriter<NetworkProfile> { }

    // AccumulatingReader aliases
    public class ProfileStandardAccumulatingReader : AccumulatingReader<StandardProfile> { public ProfileStandardAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileSensorAccumulatingReader : AccumulatingReader<SensorProfile> { public ProfileSensorAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileIPCAccumulatingReader : AccumulatingReader<IPCProfile> { public ProfileIPCAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileBulkAccumulatingReader : AccumulatingReader<BulkProfile> { public ProfileBulkAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
    public class ProfileNetworkAccumulatingReader : AccumulatingReader<NetworkProfile> { public ProfileNetworkAccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) : base(bufferSize, getMessageInfo) { } }
}
