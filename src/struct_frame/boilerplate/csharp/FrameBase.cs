// Struct-frame boilerplate: frame parser base utilities (C#)
// This file mirrors the C++ frame_base.hpp structure

#nullable enable

using System;

namespace StructFrame
{
    /// <summary>
    /// Message info structure - unified type for size and magic numbers lookup
    /// </summary>
    public struct MessageInfo
    {
        public int Size;
        public byte Magic1;
        public byte Magic2;

        public MessageInfo(int size, byte magic1 = 0, byte magic2 = 0)
        {
            Size = size;
            Magic1 = magic1;
            Magic2 = magic2;
        }
    }

    /// <summary>
    /// Checksum result structure
    /// </summary>
    public struct FrameChecksum
    {
        public byte Byte1;
        public byte Byte2;

        public FrameChecksum(byte b1, byte b2)
        {
            Byte1 = b1;
            Byte2 = b2;
        }
    }

    /// <summary>
    /// Parse result structure containing message info
    /// </summary>
    public struct FrameMsgInfo
    {
        public bool Valid;
        public ushort MsgId;
        public int MsgLen;      // Payload length (message data only)
        public int FrameSize;   // Total frame size (header + payload + footer)
        public byte[]? MsgData;
        public int MsgDataOffset;  // Offset into MsgData where the actual data starts

        // Additional fields for extended profiles
        public byte Seq;
        public byte SysId;
        public byte CompId;
        public byte PkgId;

        public FrameMsgInfo(bool valid, ushort msgId, int msgLen, int frameSize, byte[]? msgData, int offset = 0)
        {
            Valid = valid;
            MsgId = msgId;
            MsgLen = msgLen;
            FrameSize = frameSize;
            MsgData = msgData;
            MsgDataOffset = offset;
            Seq = 0;
            SysId = 0;
            CompId = 0;
            PkgId = 0;
        }

        public static FrameMsgInfo Invalid => new FrameMsgInfo(false, 0, 0, 0, null);

        /// <summary>
        /// Allow use in boolean context
        /// </summary>
        public static implicit operator bool(FrameMsgInfo info) => info.Valid;
    }

    /// <summary>
    /// Base utilities for struct frame parsing and encoding
    /// </summary>
    public static class FrameBase
    {
        /// <summary>
        /// Fletcher-16 checksum calculation
        /// </summary>
        public static FrameChecksum FletcherChecksum(byte[] data, int offset, int length, byte magic1 = 0, byte magic2 = 0)
        {
            byte ck1 = 0;
            byte ck2 = 0;
            for (int i = 0; i < length; i++)
            {
                ck1 = (byte)(ck1 + data[offset + i]);
                ck2 = (byte)(ck2 + ck1);
            }
            // Add magic numbers at the end
            ck1 = (byte)(ck1 + magic1);
            ck2 = (byte)(ck2 + ck1);
            ck1 = (byte)(ck1 + magic2);
            ck2 = (byte)(ck2 + ck1);
            return new FrameChecksum(ck1, ck2);
        }

        /// <summary>
        /// Fletcher-16 checksum calculation (convenience overload)
        /// </summary>
        public static FrameChecksum FletcherChecksum(byte[] data)
        {
            return FletcherChecksum(data, 0, data.Length, 0, 0);
        }

        /// <summary>
        /// Fletcher-16 checksum calculation on a span
        /// </summary>
        public static FrameChecksum FletcherChecksum(ReadOnlySpan<byte> data, byte magic1 = 0, byte magic2 = 0)
        {
            byte ck1 = 0;
            byte ck2 = 0;
            for (int i = 0; i < data.Length; i++)
            {
                ck1 = (byte)(ck1 + data[i]);
                ck2 = (byte)(ck2 + ck1);
            }
            // Add magic numbers at the end
            ck1 = (byte)(ck1 + magic1);
            ck2 = (byte)(ck2 + ck1);
            ck1 = (byte)(ck1 + magic2);
            ck2 = (byte)(ck2 + ck1);
            return new FrameChecksum(ck1, ck2);
        }
    }

    /// <summary>
    /// Base interface for message types (non-generic, for encoding)
    /// </summary>
    public interface IStructFrameMessage
    {
        /// <summary>
        /// Get the message ID
        /// </summary>
        ushort GetMsgId();

        /// <summary>
        /// Get the message size in bytes
        /// </summary>
        int GetSize();

        /// <summary>
        /// Serialize the message into a byte array
        /// </summary>
        byte[] Serialize();

        /// <summary>
        /// Get the magic numbers for checksum calculation (based on field types and positions)
        /// </summary>
        (byte Magic1, byte Magic2) GetMagicNumbers();
    }

    /// <summary>
    /// Generic interface for message types with deserialization support.
    /// Uses C# 11 static abstract members for compile-time dispatch.
    /// </summary>
    public interface IStructFrameMessage<TSelf> : IStructFrameMessage where TSelf : IStructFrameMessage<TSelf>
    {
        /// <summary>
        /// Deserialize a message from frame info
        /// </summary>
        static abstract TSelf Deserialize(FrameMsgInfo frame);
    }

    /// <summary>
    /// A bounded array type for variable-length arrays in structs.
    /// This is used for arrays with a count field followed by data.
    /// </summary>
    public struct BoundedArray<T> where T : unmanaged
    {
        public int Count;
        public T[] Data;

        public BoundedArray(int capacity)
        {
            Count = 0;
            Data = new T[capacity];
        }

        public BoundedArray(T[]? data)
        {
            Count = data?.Length ?? 0;
            Data = data ?? Array.Empty<T>();
        }

        public T this[int index]
        {
            get => Data[index];
            set => Data[index] = value;
        }

        public void Add(T item)
        {
            if (Data == null)
                Data = new T[16]; // Default capacity
            if (Count >= Data.Length)
                Array.Resize(ref Data, Data.Length * 2);
            Data[Count++] = item;
        }

        public Span<T> AsSpan() => new Span<T>(Data, 0, Count);
        public ReadOnlySpan<T> AsReadOnlySpan() => new ReadOnlySpan<T>(Data, 0, Count);
    }

    /// <summary>
    /// A fixed-size string buffer stored as bytes
    /// </summary>
    public struct FixedString
    {
        public byte Length;
        public byte[] Data;

        public FixedString()
        {
            Length = 0;
            Data = Array.Empty<byte>();
        }

        public FixedString(int maxLength)
        {
            Length = 0;
            Data = new byte[maxLength];
        }

        public FixedString(string value, int maxLength)
        {
            Data = new byte[maxLength];
            if (string.IsNullOrEmpty(value))
            {
                Length = 0;
            }
            else
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(value);
                Length = (byte)Math.Min(bytes.Length, maxLength);
                Array.Copy(bytes, Data, Length);
            }
        }

        public override string ToString()
        {
            if (Data == null || Length == 0)
                return string.Empty;
            return System.Text.Encoding.UTF8.GetString(Data, 0, Length);
        }

        public static implicit operator string(FixedString fs) => fs.ToString();
    }
}
