// Struct-frame boilerplate: frame base for C#
// This file provides base utilities for struct frame parsing and encoding

using System;
using System.Runtime.InteropServices;

namespace StructFrame
{
    /// <summary>
    /// Represents the result of parsing a frame
    /// </summary>
    public struct FrameParseResult
    {
        public bool Valid;
        public int MsgId;
        public byte[] MsgData;
        public int MsgSize;
    }

    /// <summary>
    /// Base class for frame format implementations
    /// </summary>
    public abstract class FrameFormatBase
    {
        /// <summary>
        /// Encodes a message into a byte array
        /// </summary>
        public abstract byte[] Encode(int msgId, byte[] msgData);

        /// <summary>
        /// Validates and parses a packet
        /// </summary>
        public abstract FrameParseResult ValidatePacket(byte[] data, int length);

        /// <summary>
        /// Parses a single byte (for streaming parsers)
        /// </summary>
        public abstract FrameParseResult ParseByte(byte b);

        /// <summary>
        /// Resets the parser state
        /// </summary>
        public abstract void Reset();
    }

    /// <summary>
    /// Helper methods for struct serialization
    /// </summary>
    public static class StructHelper
    {
        /// <summary>
        /// Converts a struct to a byte array
        /// </summary>
        public static byte[] StructToBytes<T>(T structure) where T : struct
        {
            int size = Marshal.SizeOf(typeof(T));
            byte[] buffer = new byte[size];
            IntPtr ptr = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.StructureToPtr(structure, ptr, false);
                Marshal.Copy(ptr, buffer, 0, size);
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
            return buffer;
        }

        /// <summary>
        /// Converts a byte array to a struct
        /// </summary>
        public static T BytesToStruct<T>(byte[] buffer) where T : struct
        {
            return BytesToStruct<T>(buffer, 0);
        }

        /// <summary>
        /// Converts a byte array to a struct starting at an offset
        /// </summary>
        public static T BytesToStruct<T>(byte[] buffer, int offset) where T : struct
        {
            int size = Marshal.SizeOf(typeof(T));
            IntPtr ptr = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.Copy(buffer, offset, ptr, size);
                return Marshal.PtrToStructure<T>(ptr);
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
        }
    }
}
