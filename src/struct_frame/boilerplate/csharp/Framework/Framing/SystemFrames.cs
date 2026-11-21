#nullable enable

using System;
using System.Collections.Generic;
using StructFrame;
using StructFrame.Profiles;
using StructFrame.SfSystem;

namespace StructFrame.Framing
{
    /// <summary>
    /// System frames: struct-frame's own messages (heartbeat, ping, link tests, RPC).
    /// </summary>
    /// <remarks>
    /// A system frame uses the header of the profile it travels with (Basic or Tiny; profiles
    /// without start bytes cannot carry system frames) followed by a fixed payload layout:
    /// <c>[start bytes][SEQ][SYS][COMP][LEN lo][LEN hi][SYS_MSG_ID] payload [CRC1][CRC2]</c>.
    /// The second start byte (Basic) or the start byte (Tiny) is 0x79: payload type 9. System
    /// message ids are a separate id space (<see cref="StructFrame.SfSystem"/>), so they never
    /// collide with application messages. The CRC is the usual Fletcher-16 with the system
    /// message's magic bytes mixed in after the data. Some system messages carry a raw tail
    /// after their fixed fields (ping padding, link-test data, RPC payloads); its length is the
    /// frame length minus the message's fixed size.
    /// </remarks>
    public static class SystemFrames
    {
        /// <summary>Payload type of system frames.</summary>
        public const byte PayloadTypeValue = (byte)PayloadType.System;
        /// <summary>Start byte of system frames (after a Basic header's 0x90, or alone for Tiny).</summary>
        public const byte StartByte = (byte)(HeaderConstants.PayloadTypeBase + PayloadTypeValue);
        /// <summary>Largest tail accepted after a system message's fixed fields.</summary>
        public const int MaxTail = SfSystem.Constants.MAX_TAIL;

        /// <summary>System message ids that may carry a tail.</summary>
        public static readonly IReadOnlySet<ushort> TailMessages = new HashSet<ushort>
        {
            Ping.MsgId, Pong.MsgId, LinkTestData.MsgId, RpcRequest.MsgId, RpcResponse.MsgId,
        };

        private static readonly Dictionary<HeaderType, ProfileConfig> _configs = new();
        private static readonly object _configsLock = new();

        /// <summary>
        /// True when frames of <paramref name="config"/> can be told apart from system frames:
        /// the header carries the payload type in a start byte (Basic and Tiny headers).
        /// </summary>
        public static bool Supports(ProfileConfig config) =>
            config.Header.EncodesPayloadType && config.NumStartBytes >= 1;

        /// <summary>The system-frame profile for the header of <paramref name="config"/>.</summary>
        public static ProfileConfig ConfigFor(ProfileConfig config)
        {
            if (!Supports(config))
            {
                throw new ArgumentException(
                    $"profile {config.Name} has no start byte that identifies the payload type, " +
                    "so it cannot carry system frames", nameof(config));
            }
            lock (_configsLock)
            {
                if (!_configs.TryGetValue(config.Header.HeaderType, out var sys))
                {
                    sys = new ProfileConfig(config.Header.HeaderType + "System", config.Header, PayloadConfigs.System);
                    _configs[config.Header.HeaderType] = sys;
                }
                return sys;
            }
        }

        /// <summary>
        /// Size limits and magic bytes of a system message, for the frame readers. MinSize is the
        /// fixed size; Size also allows a tail for the messages that take one; BaseSize == Size so
        /// the CRC is never extension-split.
        /// </summary>
        public static MessageInfo? GetMessageInfo(int msgId)
        {
            var info = MessageDefinitions.GetMessageInfo(msgId);
            if (!info.HasValue) return null;
            int fixedSize = info.Value.Size;
            int largest = fixedSize + (TailMessages.Contains((ushort)msgId) ? MaxTail : 0);
            return new MessageInfo(largest, info.Value.Magic1, info.Value.Magic2, largest, fixedSize);
        }

        /// <summary>Encode a system message (and its tail) as a system frame for the header of <paramref name="config"/>.</summary>
        public static byte[] Encode(ProfileConfig config, IStructFrameMessage message, ReadOnlySpan<byte> tail = default,
                                    byte seq = 0, byte sysId = 0, byte compId = 0)
        {
            var sys = ConfigFor(config);
            ushort msgId = message.GetMsgId();
            var info = MessageDefinitions.GetMessageInfo(msgId);
            if (!info.HasValue || message.GetType().Namespace != typeof(Ping).Namespace)
            {
                throw new ArgumentException($"{message.GetType().Name} is not a system message", nameof(message));
            }
            if (tail.Length > 0 && !TailMessages.Contains(msgId))
            {
                throw new ArgumentException($"{message.GetType().Name} does not take a tail", nameof(tail));
            }
            if (tail.Length > MaxTail)
            {
                throw new ArgumentOutOfRangeException(nameof(tail), $"tail of {tail.Length} bytes exceeds MaxTail ({MaxTail})");
            }
            byte[] fixedPart = message.Serialize();
            int payloadLen = fixedPart.Length + tail.Length;
            byte[] frame = new byte[sys.Overhead + payloadLen];
            int idx = 0;
            frame[idx++] = sys.ComputedStartByte1;
            if (sys.NumStartBytes >= 2) frame[idx++] = sys.ComputedStartByte2;
            int crcStart = idx;
            frame[idx++] = seq;
            frame[idx++] = sysId;
            frame[idx++] = compId;
            frame[idx++] = (byte)(payloadLen & 0xFF);
            frame[idx++] = (byte)((payloadLen >> 8) & 0xFF);
            frame[idx++] = (byte)msgId;
            fixedPart.CopyTo(frame, idx);
            idx += fixedPart.Length;
            tail.CopyTo(frame.AsSpan(idx));
            idx += tail.Length;
            var (magic1, magic2) = message.GetMagicNumbers();
            var ck = FrameBase.FletcherChecksum(frame, crcStart, idx - crcStart, magic1, magic2);
            frame[idx++] = ck.Byte1;
            frame[idx] = ck.Byte2;
            return frame;
        }

        /// <summary>The message and tail of a valid system frame returned by a reader (<see cref="FrameMsgInfo.IsSystem"/>).</summary>
        public static (IStructFrameMessage Message, byte[] Tail) Decode(FrameMsgInfo frame)
        {
            var info = MessageDefinitions.GetMessageInfo(frame.MsgId);
            if (!frame.Valid || !frame.IsSystem || !info.HasValue)
            {
                throw new ArgumentException($"not a valid system frame (id 0x{frame.MsgId:X2})", nameof(frame));
            }
            var payload = frame.GetPayloadSpan();
            int fixedSize = info.Value.Size;
            if (payload.Length < fixedSize)
            {
                throw new ArgumentException("system frame shorter than its message", nameof(frame));
            }
            var message = MessageDefinitions.Deserialize(frame.MsgId, payload.Slice(0, fixedSize).ToArray())!;
            return (message, payload.Slice(fixedSize).ToArray());
        }

        // ---------------------------------------------------------------------------------
        // Helpers shared by the readers
        // ---------------------------------------------------------------------------------

        /// <summary>The system profile of <paramref name="config"/>, or null when it cannot carry system frames.</summary>
        internal static ProfileConfig? ConfigOrNull(ProfileConfig config) => Supports(config) ? ConfigFor(config) : null;

        /// <summary>True when buf[offset..offset+length) starts with the start bytes of a system frame.</summary>
        internal static bool IsSystemStart(ProfileConfig? sys, byte[] buf, int offset, int length)
        {
            if (sys == null || length < 1 || buf[offset] != sys.ComputedStartByte1) return false;
            if (sys.NumStartBytes >= 2) return length >= 2 && buf[offset + 1] == sys.ComputedStartByte2;
            return true;
        }

        /// <summary>
        /// Check the header of a candidate system frame: 1 when the system message id is known and
        /// the length fits it, 0 when not, -1 while the header is incomplete.
        /// </summary>
        internal static int HeaderCheck(ProfileConfig sys, byte[] buf, int offset, int length)
        {
            if (length < sys.HeaderSize) return -1;
            int off = offset + sys.NumStartBytes + 3;  // after SEQ, SYS, COMP
            int len = buf[off] | (buf[off + 1] << 8);
            var info = GetMessageInfo(buf[offset + sys.HeaderSize - 1]);
            return info.HasValue && len >= info.Value.MinSize && len <= info.Value.Size ? 1 : 0;
        }

        /// <summary>Parse a frame known to start with system start bytes.</summary>
        internal static FrameMsgInfo Parse(ProfileConfig sys, BufferParser parser, byte[] buf, int offset, int length)
        {
            FrameMsgInfo result;
            if (HeaderCheck(sys, buf, offset, length) == 0)
            {
                result = FrameMsgInfo.Invalid;
                result.Status = FrameMsgStatus.WaitingForStart;
            }
            else
            {
                result = parser.Parse(buf, offset, length);
            }
            result.IsSystem = true;
            return result;
        }

        /// <summary>
        /// Index of the next byte in buf[begin..end) that can start a frame of <paramref name="config"/>
        /// or a system frame, or <paramref name="end"/> when there is none.
        /// </summary>
        internal static int FindStart(ProfileConfig config, ProfileConfig? sys, byte[] buf, int begin, int end)
        {
            if (begin >= end) return end;
            int nxt = Array.IndexOf(buf, config.ComputedStartByte1, begin, end - begin);
            if (nxt < 0) nxt = end;
            if (sys != null && sys.ComputedStartByte1 != config.ComputedStartByte1 && nxt > begin)
            {
                int alt = Array.IndexOf(buf, sys.ComputedStartByte1, begin, nxt - begin);
                if (alt >= 0) nxt = alt;
            }
            return nxt;
        }
    }
}
