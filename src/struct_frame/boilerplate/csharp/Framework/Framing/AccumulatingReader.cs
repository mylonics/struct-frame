#nullable enable

using System;
using StructFrame;
using StructFrame.Profiles;

namespace StructFrame.Framing
{
    /// <summary>
    /// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
    /// </summary>
    public class AccumulatingReader
    {
        /// <summary>
        /// Parser state for streaming mode.
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
        /// Reset the reader, clearing any partial message data.
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
        /// Get current parser state.
        /// </summary>
        public State CurrentState => _state;

        /// <summary>
        /// Check if there's a partial message waiting for more data.
        /// </summary>
        public bool HasPartial => _internalDataLen > 0;

        /// <summary>
        /// Get the size of the partial message data.
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
        /// Parse the next frame (buffer mode).
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
        /// Check if there might be more data to parse (buffer mode only).
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
        /// Push a single byte for parsing (stream mode).
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

    /// <summary>
    /// Generic accumulating reader with compile-time profile selection.
    /// </summary>
    public class AccumulatingReader<TProfile> : AccumulatingReader where TProfile : struct, IProfileProvider
    {
        public AccumulatingReader(int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null) 
            : base(TProfile.Profile, bufferSize, getMessageInfo) { }
    }
}
