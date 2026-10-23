using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace StructFrame
{
    /// <summary>
    /// Little-endian wire encoding for arrays of primitive values.
    /// </summary>
    /// <remarks>
    /// Scalars are always written with <c>BinaryPrimitives</c> (little-endian). Arrays are copied
    /// as raw memory, which is only correct on a little-endian host; these helpers copy and then
    /// reverse each element's bytes on a big-endian host so arrays use the same byte order as
    /// scalars everywhere. On little-endian hosts they are a plain copy.
    /// </remarks>
    public static class WireArray
    {
        /// <summary>
        /// Copies <paramref name="source"/> (wire bytes) into <paramref name="destination"/> as elements.
        /// </summary>
        public static void Read<T>(ReadOnlySpan<byte> source, Span<T> destination) where T : unmanaged
        {
            MemoryMarshal.Cast<byte, T>(source).CopyTo(destination);
            if (!BitConverter.IsLittleEndian)
            {
                int elementSize = Unsafe.SizeOf<T>();
                int count = Math.Min(source.Length / elementSize, destination.Length);
                ReverseElements(MemoryMarshal.AsBytes(destination.Slice(0, count)), elementSize);
            }
        }

        /// <summary>
        /// Copies up to <paramref name="maxBytes"/> bytes of <paramref name="source"/> into
        /// <paramref name="buffer"/> at <paramref name="offset"/> in wire (little-endian) order.
        /// </summary>
        public static void Write<T>(T[] source, byte[] buffer, int offset, int maxBytes) where T : unmanaged
        {
            int elementSize = Unsafe.SizeOf<T>();
            int bytes = Math.Min(source.Length * elementSize, maxBytes);
            Buffer.BlockCopy(source, 0, buffer, offset, bytes);
            if (!BitConverter.IsLittleEndian)
            {
                ReverseElements(buffer.AsSpan(offset, bytes - bytes % elementSize), elementSize);
            }
        }

        private static void ReverseElements(Span<byte> bytes, int elementSize)
        {
            if (elementSize <= 1)
            {
                return;
            }
            for (int i = 0; i + elementSize <= bytes.Length; i += elementSize)
            {
                bytes.Slice(i, elementSize).Reverse();
            }
        }
    }
}
