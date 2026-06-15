#nullable enable

using System;
using StructFrame;
using StructFrame.Profiles;

namespace StructFrame.Framing
{
    /// <summary>
    /// BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
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
        /// Set the buffer to write to.
        /// </summary>
        public void SetBuffer(byte[] buffer, int offset, int capacity)
        {
            _buffer = buffer;
            _offset = offset;
            _capacity = capacity;
        }

        /// <summary>
        /// Set the buffer to write to (convenience overload).
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
        /// Reset the writer to the beginning of the buffer.
        /// </summary>
        public void Reset()
        {
            _offset = 0;
        }

        /// <summary>
        /// Get the total number of bytes written.
        /// </summary>
        public int Size => _offset;

        /// <summary>
        /// Get the remaining capacity in the buffer.
        /// </summary>
        public int Remaining => _capacity > _offset ? _capacity - _offset : 0;

        /// <summary>
        /// Get the buffer data as a new array.
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

        /// <summary>
        /// Get the written bytes as a zero-copy view over the internal buffer.
        /// Avoids the allocation + copy that <see cref="GetData"/> incurs; the returned
        /// memory is only valid until the next write to this BufferWriter.
        /// </summary>
        public ReadOnlyMemory<byte> GetWrittenMemory()
            => _buffer == null ? ReadOnlyMemory<byte>.Empty : _buffer.AsMemory(0, _offset);

        /// <summary>
        /// Get the written bytes as a zero-copy span over the internal buffer.
        /// Valid only until the next write to this BufferWriter.
        /// </summary>
        public ReadOnlySpan<byte> GetWrittenSpan()
            => _buffer == null ? ReadOnlySpan<byte>.Empty : _buffer.AsSpan(0, _offset);
    }

    /// <summary>
    /// Generic buffer writer with compile-time profile selection.
    /// </summary>
    public class BufferWriter<TProfile> : BufferWriter where TProfile : struct, IProfileProvider
    {
        public BufferWriter() : base(TProfile.Profile) { }
    }
}
