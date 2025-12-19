// Compatibility layer for frame parser functions (C#)
// Provides encode/decode functions composed from separated header and payload types

using System;
using StructFrame.FrameHeaders;
using StructFrame.PayloadTypes;

namespace StructFrame
{
    /// <summary>
    /// Base class for frame formats using compositional approach
    /// </summary>
    public abstract class FrameCompat : FrameFormatBase
    {
        protected static (byte, byte) Fletcher16Checksum(byte[] buffer, int start, int length)
        {
            byte byte1 = 0;
            byte byte2 = 0;

            for (int i = start; i < start + length; i++)
            {
                byte1 = (byte)((byte1 + buffer[i]) % 256);
                byte2 = (byte)((byte2 + byte1) % 256);
            }

            return (byte1, byte2);
        }
    }

    public class BasicDefault : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 4;
            int footerSize = 2;
            int totalSize = headerSize + msg.Length + footerSize;

            if (msg.Length > 255)
                return null;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(1); // DEFAULT = 1
            buffer[2] = (byte)msg.Length;
            buffer[3] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            var ck = Fletcher16Checksum(buffer, 2, msg.Length + 2);
            buffer[totalSize - 2] = ck.Item1;
            buffer[totalSize - 1] = ck.Item2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 6 || buffer[0] != HeaderConstants.BASIC_START_BYTE ||
                !HeaderBasic.IsSecondStartByte(buffer[1]))
            {
                return new FrameParseResult { Valid = false };
            }

            int msgLen = buffer[2];
            byte msgId = buffer[3];
            int totalSize = 4 + msgLen + 2;

            if (length < totalSize)
                return new FrameParseResult { Valid = false };

            var ck = Fletcher16Checksum(buffer, 2, msgLen + 2);
            if (ck.Item1 == buffer[totalSize - 2] && ck.Item2 == buffer[totalSize - 1])
            {
                byte[] msgData = new byte[msgLen];
                Array.Copy(buffer, 4, msgData, 0, msgLen);
                return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
            }

            return new FrameParseResult { Valid = false };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }

    public class TinyMinimal : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 2;
            int totalSize = headerSize + msg.Length;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderTiny.GetStartByte(0); // MINIMAL = 0
            buffer[1] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 2 || !HeaderTiny.IsStartByte(buffer[0]))
            {
                return new FrameParseResult { Valid = false };
            }

            byte msgId = buffer[1];
            int msgLen = length - 2;

            byte[] msgData = new byte[msgLen];
            Array.Copy(buffer, 2, msgData, 0, msgLen);
            return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }

    public class BasicExtended : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 6;
            int footerSize = 2;
            int totalSize = headerSize + msg.Length + footerSize;

            if (msg.Length > 65535)
                return null;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(4); // EXTENDED = 4
            buffer[2] = (byte)(msg.Length & 0xFF);
            buffer[3] = (byte)((msg.Length >> 8) & 0xFF);
            buffer[4] = 0; // PKG_ID = 0
            buffer[5] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            var ck = Fletcher16Checksum(buffer, 2, msg.Length + 4);
            buffer[totalSize - 2] = ck.Item1;
            buffer[totalSize - 1] = ck.Item2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 8 || buffer[0] != HeaderConstants.BASIC_START_BYTE ||
                !HeaderBasic.IsSecondStartByte(buffer[1]))
            {
                return new FrameParseResult { Valid = false };
            }

            int msgLen = buffer[2] | (buffer[3] << 8);
            byte msgId = buffer[5];
            int totalSize = 6 + msgLen + 2;

            if (length < totalSize)
                return new FrameParseResult { Valid = false };

            var ck = Fletcher16Checksum(buffer, 2, msgLen + 4);
            if (ck.Item1 == buffer[totalSize - 2] && ck.Item2 == buffer[totalSize - 1])
            {
                byte[] msgData = new byte[msgLen];
                Array.Copy(buffer, 6, msgData, 0, msgLen);
                return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
            }

            return new FrameParseResult { Valid = false };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }

    public class BasicExtendedMultiSystemStream : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 9;
            int footerSize = 2;
            int totalSize = headerSize + msg.Length + footerSize;

            if (msg.Length > 65535)
                return null;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(8); // EXTENDED_MULTI_SYSTEM_STREAM = 8
            buffer[2] = 0; // SEQ = 0
            buffer[3] = 0; // SYS_ID = 0
            buffer[4] = 0; // COMP_ID = 0
            buffer[5] = (byte)(msg.Length & 0xFF);
            buffer[6] = (byte)((msg.Length >> 8) & 0xFF);
            buffer[7] = 0; // PKG_ID = 0
            buffer[8] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            var ck = Fletcher16Checksum(buffer, 2, msg.Length + 7);
            buffer[totalSize - 2] = ck.Item1;
            buffer[totalSize - 1] = ck.Item2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 11 || buffer[0] != HeaderConstants.BASIC_START_BYTE ||
                !HeaderBasic.IsSecondStartByte(buffer[1]))
            {
                return new FrameParseResult { Valid = false };
            }

            int msgLen = buffer[5] | (buffer[6] << 8);
            byte msgId = buffer[8];
            int totalSize = 9 + msgLen + 2;

            if (length < totalSize)
                return new FrameParseResult { Valid = false };

            var ck = Fletcher16Checksum(buffer, 2, msgLen + 7);
            if (ck.Item1 == buffer[totalSize - 2] && ck.Item2 == buffer[totalSize - 1])
            {
                byte[] msgData = new byte[msgLen];
                Array.Copy(buffer, 9, msgData, 0, msgLen);
                return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
            }

            return new FrameParseResult { Valid = false };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }

    public class BasicMinimal : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 3;
            int totalSize = headerSize + msg.Length;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderConstants.BASIC_START_BYTE;
            buffer[1] = HeaderBasic.GetSecondStartByte(0); // MINIMAL = 0
            buffer[2] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 3 || buffer[0] != HeaderConstants.BASIC_START_BYTE ||
                !HeaderBasic.IsSecondStartByte(buffer[1]))
            {
                return new FrameParseResult { Valid = false };
            }

            byte msgId = buffer[2];
            int msgLen = length - 3;

            byte[] msgData = new byte[msgLen];
            Array.Copy(buffer, 3, msgData, 0, msgLen);
            return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }

    public class TinyDefault : FrameCompat
    {
        public override byte[] Encode(int msgId, byte[] msg)
        {
            int headerSize = 3;
            int footerSize = 2;
            int totalSize = headerSize + msg.Length + footerSize;

            if (msg.Length > 255)
                return null;

            byte[] buffer = new byte[totalSize];
            buffer[0] = HeaderTiny.GetStartByte(1); // DEFAULT = 1
            buffer[1] = (byte)msg.Length;
            buffer[2] = (byte)msgId;
            Array.Copy(msg, 0, buffer, headerSize, msg.Length);

            var ck = Fletcher16Checksum(buffer, 1, msg.Length + 2);
            buffer[totalSize - 2] = ck.Item1;
            buffer[totalSize - 1] = ck.Item2;

            return buffer;
        }

        public override FrameParseResult ValidatePacket(byte[] buffer, int length)
        {
            if (length < 5 || !HeaderTiny.IsStartByte(buffer[0]))
            {
                return new FrameParseResult { Valid = false };
            }

            int msgLen = buffer[1];
            byte msgId = buffer[2];
            int totalSize = 3 + msgLen + 2;

            if (length < totalSize)
                return new FrameParseResult { Valid = false };

            var ck = Fletcher16Checksum(buffer, 1, msgLen + 2);
            if (ck.Item1 == buffer[totalSize - 2] && ck.Item2 == buffer[totalSize - 1])
            {
                byte[] msgData = new byte[msgLen];
                Array.Copy(buffer, 3, msgData, 0, msgLen);
                return new FrameParseResult { Valid = true, MsgId = msgId, MsgSize = msgLen, MsgData = msgData };
            }

            return new FrameParseResult { Valid = false };
        }

        public override FrameParseResult ParseByte(byte b)
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }

        public override void Reset()
        {
            throw new NotImplementedException("Streaming parser not implemented for compat layer");
        }
    }
}
