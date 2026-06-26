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

        // Internal buffer for partial messages (stream mode and buffer-mode cross-chunk frames)
        private byte[] _internalBuffer;
        private int _internalDataLen;
        private int _expectedFrameSize;
        private State _state;

        // Buffer mode state
        private byte[]? _currentBuffer;
        private int _currentOffset;
        private int _currentSize;

        // How many bytes from _currentBuffer were appended into _internalBuffer by AddData.
        // Used in Next() to correctly advance _currentOffset after consuming a cross-chunk frame.
        private int _bytesAppendedToInternal;

        // Diagnostic counters (stream mode)
        private ParserDiagnostics _diagnostics;
        private byte _lastSeq;
        private bool _lastSeqValid;

        public AccumulatingReader(ProfileConfig config, int bufferSize = 1024, Func<int, MessageInfo?>? getMessageInfo = null)
        {
            _config = config;
            _bufferSize = bufferSize;
            _getMessageInfo = getMessageInfo;
            _parser = new BufferParser(config, getMessageInfo);
            _internalBuffer = new byte[bufferSize];
            _diagnostics = default;
            _lastSeq = 0;
            _lastSeqValid = false;
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
            _bytesAppendedToInternal = 0;
            _lastSeqValid = false;
        }

        /// <summary>
        /// Get a snapshot of the current diagnostic counters.
        /// </summary>
        public ParserDiagnostics Diagnostics => _diagnostics;

        /// <summary>
        /// Reset all diagnostic counters to zero.
        /// </summary>
        public void ResetDiagnostics()
        {
            _diagnostics = default;
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
            _currentSize = offset + size;
            _bytesAppendedToInternal = 0;
            _state = State.BufferMode;

            // If we have partial data in the internal buffer, append new data to try to complete it.
            if (_internalDataLen > 0)
            {
                int spaceAvailable = _bufferSize - _internalDataLen;
                int bytesToCopy = Math.Min(size, spaceAvailable);

                Array.Copy(buffer, offset, _internalBuffer, _internalDataLen, bytesToCopy);
                _internalDataLen += bytesToCopy;
                _bytesAppendedToInternal = bytesToCopy;
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
        /// Returns true while there is something to consume (a complete frame or a
        /// CRC-failed frame that the caller should inspect).
        /// </summary>
        public bool TryNext(out FrameMsgInfo result)
        {
            result = Next();
            return result.Valid || result.FrameSize > 0;
        }

        /// <summary>
        /// Parse the next frame (buffer mode).
        /// </summary>
        public FrameMsgInfo Next()
        {
            if (_state != State.BufferMode)
                return FrameMsgInfo.Invalid;

            // --- Try to complete a partial message from the internal buffer ---
            if (_internalDataLen > 0)
            {
                if (_bytesAppendedToInternal == 0)
                {
                    // Leftover from a previous call where the internal buffer was already full
                    // and nothing new could be appended. Discard to avoid an infinite wedge.
                    _internalDataLen = 0;
                }
                else
                {
                    var result = _parser.Parse(_internalBuffer, 0, _internalDataLen);

                    if (result.Status == FrameMsgStatus.WaitingForStart)
                    {
                        // Garbage at the start of the internal buffer. Byte 0 is not a valid
                        // start, so scan forward for the next start-byte candidate and discard
                        // everything before it — at least one byte, guaranteeing forward progress.
                        int searchLen = _internalDataLen - 1;
                        int found = (searchLen > 0 && _config.NumStartBytes > 0)
                            ? Array.IndexOf(_internalBuffer, _config.ComputedStartByte1, 1, searchLen)
                            : -1;
                        int discard = found > 0 ? found : _internalDataLen;
                        _diagnostics.CntSyncRecoveries++;
                        _diagnostics.CntFailedBytes += discard;
                        int keep = _internalDataLen - discard;
                        if (keep > 0)
                            Array.Copy(_internalBuffer, discard, _internalBuffer, 0, keep);
                        _internalDataLen = keep;
                        _bytesAppendedToInternal = Math.Max(0, _bytesAppendedToInternal - discard);
                        return StatusResult(FrameMsgStatus.SyncRecovery, discard);
                    }

                    if (result.FrameSize > 0)
                    {
                        // Frame completed (valid or CRC-failed). Advance _currentOffset past the
                        // bytes in the current buffer that formed the tail of this cross-chunk frame.
                        int internalPrior = _internalDataLen - _bytesAppendedToInternal;
                        int bytesFromCurrent = Math.Max(0, result.FrameSize - internalPrior);
                        _currentOffset += bytesFromCurrent;
                        _internalDataLen = 0;
                        _bytesAppendedToInternal = 0;
                        return result;
                    }

                    if (result.Status == FrameMsgStatus.Collecting)
                    {
                        // Still incomplete — need more data from a future AddData call.
                        return StatusResult(FrameMsgStatus.Collecting);
                    }

                    // Any other failure: drop partial and fall through to current-buffer parse.
                    _internalDataLen = 0;
                    _bytesAppendedToInternal = 0;
                }
            }

            // --- Parse from current buffer ---
            if (_currentBuffer == null || _currentOffset >= _currentSize)
                return FrameMsgInfo.Invalid;

            var parseResult = _parser.Parse(_currentBuffer, _currentOffset, _currentSize - _currentOffset);

            if (parseResult.Status == FrameMsgStatus.WaitingForStart)
            {
                // Garbage at current offset. Scan forward for the next start-byte candidate.
                int oldOffset = _currentOffset;
                int searchFrom = _currentOffset + 1;
                int searchLen = _currentSize - searchFrom;
                int skip = searchLen > 0
                    ? FindStartByteOffset(_currentBuffer, searchFrom, searchLen)
                    : searchLen;
                int delta = skip < searchLen ? skip : searchLen;
                _currentOffset = searchFrom + delta;
                int advanced = _currentOffset - oldOffset;   // >= 1
                _diagnostics.CntSyncRecoveries++;
                _diagnostics.CntFailedBytes += advanced;
                return StatusResult(FrameMsgStatus.SyncRecovery, advanced);
            }

            if (parseResult.FrameSize > 0)
            {
                _currentOffset += parseResult.FrameSize;
                return parseResult;
            }

            // Parse returned no frame — tail of buffer is a partial frame.
            int remaining = _currentSize - _currentOffset;
            if (remaining > 0 && parseResult.Status == FrameMsgStatus.Collecting)
            {
                if (remaining < _bufferSize)
                {
                    Array.Copy(_currentBuffer, _currentOffset, _internalBuffer, 0, remaining);
                    _internalDataLen = remaining;
                    _bytesAppendedToInternal = 0;
                    _currentOffset = _currentSize;
                }
                else
                {
                    // Partial too large to buffer — discard.
                    _diagnostics.CntSyncRecoveries++;
                    _diagnostics.CntFailedBytes += remaining;
                    _currentOffset = _currentSize;
                }
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

        /// <summary>
        /// True if an incomplete (partial) frame is buffered awaiting more data via AddData().
        /// Distinguishes "drained" (HasPartial == false) from "waiting for more data".
        /// </summary>
        public bool HasPartial => _internalDataLen > 0;

        /// <summary>
        /// Number of bytes held for a partial frame awaiting completion (0 if none).
        /// </summary>
        public int PartialSize => _internalDataLen;

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
                    return AttachDiagnostics(FrameMsgInfo.Invalid);
            }
        }

        private FrameMsgInfo HandleLookingForStart1(byte b)
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
            return StatusResult(_state == State.LookingForStart1
                ? FrameMsgStatus.WaitingForStart
                : FrameMsgStatus.Collecting);
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
                _diagnostics.CntSyncRecoveries++;
                _diagnostics.CntFailedBytes += _internalDataLen + 1;
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return StatusResult(FrameMsgStatus.SyncRecovery);
            }
            return StatusResult(FrameMsgStatus.Collecting);
        }

        private FrameMsgInfo HandleCollectingHeader(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _diagnostics.CntSyncRecoveries++;
                _diagnostics.CntFailedBytes += _internalDataLen + 1;
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return StatusResult(FrameMsgStatus.SyncRecovery);
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
                            _diagnostics.CntSyncRecoveries++;
                            _diagnostics.CntFailedBytes += _internalDataLen;
                            _state = State.LookingForStart1;
                            _internalDataLen = 0;
                            return StatusResult(FrameMsgStatus.SyncRecovery);
                        }

                        if (msgInfo.Value.Size == 0)
                        {
                            var result = new FrameMsgInfo(true, msgId, 0, _expectedFrameSize, _internalBuffer, _config.HeaderSize)
                            {
                                FrameData = _internalBuffer.AsMemory(0, _expectedFrameSize)
                            };
                            _state = State.LookingForStart1;
                            _internalDataLen = 0;
                            _expectedFrameSize = 0;
                            return AttachDiagnostics(result);
                        }

                        _state = State.CollectingPayload;
                    }
                    else
                    {
                        _diagnostics.CntSyncRecoveries++;
                        _diagnostics.CntFailedBytes += _internalDataLen;
                        _state = State.LookingForStart1;
                        _internalDataLen = 0;
                        return StatusResult(FrameMsgStatus.SyncRecovery);
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

                    // Only count as a length error when the payload is definitively out of
                    // range: strictly below BaseSize (can't even fill the non-variable fields)
                    // or strictly above MaxSize. Variable messages legitimately sit anywhere
                    // in [BaseSize, MaxSize], so those must NOT increment the counter.
                    if (_config.HasLength && _getMessageInfo != null)
                    {
                        int fullMsgId = 0;
                        if (_config.HasPkgId)
                        {
                            fullMsgId = _internalBuffer[_config.HeaderSize - 2] << 8;
                        }
                        fullMsgId |= _internalBuffer[_config.HeaderSize - 1];
                        var info = _getMessageInfo(fullMsgId);
                        if (info.HasValue &&
                            (payloadLen > info.Value.Size || payloadLen < info.Value.BaseSize))
                        {
                            _diagnostics.CntLenErrors++;
                        }
                    }

                    _expectedFrameSize = _config.Overhead + payloadLen;

                    if (_expectedFrameSize > _bufferSize)
                    {
                        _diagnostics.CntSyncRecoveries++;
                        _diagnostics.CntFailedBytes += _internalDataLen;
                        _state = State.LookingForStart1;
                        _internalDataLen = 0;
                        return StatusResult(FrameMsgStatus.SyncRecovery);
                    }

                    if (_internalDataLen >= _expectedFrameSize)
                    {
                        return ValidateAndReturn();
                    }

                    _state = State.CollectingPayload;
                }
            }

            return StatusResult(FrameMsgStatus.Collecting);
        }

        private FrameMsgInfo HandleCollectingPayload(byte b)
        {
            if (_internalDataLen >= _bufferSize)
            {
                _diagnostics.CntSyncRecoveries++;
                _diagnostics.CntFailedBytes += _internalDataLen + 1;
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return StatusResult(FrameMsgStatus.SyncRecovery);
            }

            _internalBuffer[_internalDataLen++] = b;

            if (_internalDataLen >= _expectedFrameSize)
            {
                return ValidateAndReturn();
            }

            return StatusResult(FrameMsgStatus.Collecting);
        }

        private FrameMsgInfo HandleMinimalMsgId(byte msgId)
        {
            var msgInfo = _getMessageInfo?.Invoke(msgId);
            if (msgInfo.HasValue)
            {
                _expectedFrameSize = _config.HeaderSize + msgInfo.Value.Size;

                if (_expectedFrameSize > _bufferSize)
                {
                    _diagnostics.CntSyncRecoveries++;
                    _diagnostics.CntFailedBytes += _internalDataLen;
                    _state = State.LookingForStart1;
                    _internalDataLen = 0;
                    return StatusResult(FrameMsgStatus.SyncRecovery);
                }

                if (msgInfo.Value.Size == 0)
                {
                    var result = new FrameMsgInfo(true, msgId, 0, _expectedFrameSize, _internalBuffer, _config.HeaderSize)
                    {
                        FrameData = _internalBuffer.AsMemory(0, _expectedFrameSize)
                    };
                    _state = State.LookingForStart1;
                    _internalDataLen = 0;
                    _expectedFrameSize = 0;
                    return AttachDiagnostics(result);
                }

                _state = State.CollectingPayload;
            }
            else
            {
                _diagnostics.CntSyncRecoveries++;
                _diagnostics.CntFailedBytes += _internalDataLen;
                _state = State.LookingForStart1;
                _internalDataLen = 0;
                return StatusResult(FrameMsgStatus.SyncRecovery);
            }
            return StatusResult(FrameMsgStatus.Collecting);
        }

        private FrameMsgInfo ValidateAndReturn()
        {
            var result = _parser.Parse(_internalBuffer, 0, _internalDataLen);

            _state = State.LookingForStart1;
            _internalDataLen = 0;
            _expectedFrameSize = 0;

            if (result.Valid)
            {
                if (_config.HasSeq)
                {
                    byte seq = _internalBuffer[_config.NumStartBytes];
                    if (_lastSeqValid)
                    {
                        byte expectedSeq = (byte)((_lastSeq + 1) & 0xFF);
                        if (seq != expectedSeq)
                        {
                            _diagnostics.CntSeqGaps++;
                        }
                    }
                    _lastSeq = seq;
                    _lastSeqValid = true;
                }
            }
            else
            {
                if (_config.HasCrc)
                {
                    _diagnostics.CntCrcFailures++;
                    result.Status = FrameMsgStatus.CrcFailure;
                }
                else
                {
                    result.Status = FrameMsgStatus.SyncRecovery;
                }
                _diagnostics.CntFailedBytes += result.FrameSize;
                _diagnostics.CntSyncRecoveries++;
            }

            if (result.FrameSize > 0)
            {
                result.FrameData = _internalBuffer.AsMemory(0, result.FrameSize);
            }

            return AttachDiagnostics(result);
        }

        // Returns the offset (relative to `start`) of the first candidate start byte,
        // or `length` if none is found.
        private int FindStartByteOffset(byte[] buf, int start, int length)
        {
            if (length <= 0 || _config.NumStartBytes == 0) return length;
            int found = Array.IndexOf(buf, _config.ComputedStartByte1, start, length);
            return found >= 0 ? found - start : length;
        }

        private FrameMsgInfo StatusResult(FrameMsgStatus status, int frameSize = 0)
        {
            var r = FrameMsgInfo.Invalid;
            r.Status = status;
            r.FrameSize = frameSize;
            return AttachDiagnostics(r);
        }

        private FrameMsgInfo AttachDiagnostics(FrameMsgInfo result)
        {
            result.Diagnostics = _diagnostics;
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
