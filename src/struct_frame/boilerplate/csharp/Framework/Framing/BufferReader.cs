#nullable enable

using System;
using StructFrame;
using StructFrame.Profiles;

namespace StructFrame.Framing
{
    /// <summary>
    /// BufferReader - Iterate through a buffer parsing multiple frames.
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
        /// Set the buffer to read from.
        /// </summary>
        public void SetBuffer(byte[] buffer, int offset, int size)
        {
            _buffer = buffer;
            _offset = offset;
            _size = size;
        }

        /// <summary>
        /// Set the buffer to read from (convenience overload).
        /// </summary>
        public void SetBuffer(byte[] buffer)
        {
            SetBuffer(buffer, 0, buffer.Length);
        }

        /// <summary>
        /// Parse the next frame in the buffer.
        /// </summary>
        public FrameMsgInfo Next()
        {
            if (_buffer == null || _offset >= _size)
            {
                return FrameMsgInfo.Invalid;
            }

            var result = _parser.Parse(_buffer, _offset, _size - _offset);

            if (result.FrameSize > 0)
            {
                // Advance past the frame whether valid (good frame) or not (CRC failure).
                // CRC-failed frames are returned once to the caller with Status=CrcFailure.
                _offset += result.FrameSize;
            }
            else if (result.Status == FrameMsgStatus.WaitingForStart)
            {
                // Start byte mismatch at current offset: scan forward for the next candidate.
                // Skip the bad byte and look for start byte 1 in the remaining data.
                int searchFrom = _offset + 1;
                int searchLen = _size - searchFrom;
                if (searchLen > 0 && _config.NumStartBytes > 0)
                {
                    int found = Array.IndexOf(_buffer, _config.ComputedStartByte1, searchFrom, searchLen);
                    _offset = found >= 0 ? found : _size;
                }
                else
                {
                    _offset = _size; // nothing useful left
                }
            }
            // Status == Collecting: genuinely incomplete data — do not advance; let caller stop.

            return result;
        }

        /// <summary>
        /// Reset the reader to the beginning of the buffer.
        /// </summary>
        public void Reset()
        {
            _offset = 0;
        }

        /// <summary>
        /// Get the current offset in the buffer.
        /// </summary>
        public int Offset => _offset;

        /// <summary>
        /// Get the remaining bytes in the buffer.
        /// </summary>
        public int Remaining => _size > _offset ? _size - _offset : 0;

        /// <summary>
        /// Check if there are more bytes to parse.
        /// </summary>
        public bool HasMore => _offset < _size;
    }

    /// <summary>
    /// Generic buffer reader with compile-time profile selection.
    /// </summary>
    public class BufferReader<TProfile> : BufferReader where TProfile : struct, IProfileProvider
    {
        public BufferReader(Func<int, MessageInfo?>? getMessageInfo = null) : base(TProfile.Profile, getMessageInfo) { }
    }
}
