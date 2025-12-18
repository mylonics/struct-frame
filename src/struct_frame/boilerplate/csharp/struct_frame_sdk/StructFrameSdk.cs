// Struct Frame SDK Client for C#
// High-level interface for sending and receiving framed messages

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// Frame parser interface - must be implemented by generated frame parsers
    /// </summary>
    public interface IFrameParser
    {
        /// <summary>
        /// Parse incoming data and extract message
        /// </summary>
        FrameMsgInfo Parse(byte[] data);

        /// <summary>
        /// Frame a message for sending
        /// </summary>
        byte[] Frame(byte msgId, byte[] data);
    }

    /// <summary>
    /// Frame message info (compatible with generated parsers)
    /// </summary>
    public class FrameMsgInfo
    {
        public bool Valid { get; set; }
        public byte MsgId { get; set; }
        public int MsgLen { get; set; }
        public byte[] MsgData { get; set; }
    }

    /// <summary>
    /// Message codec interface - deserializes raw bytes into message objects
    /// </summary>
    public interface IMessageCodec<T>
    {
        byte MsgId { get; }
        T Deserialize(byte[] data);
    }

    /// <summary>
    /// Message handler delegate
    /// </summary>
    public delegate void MessageHandler<T>(T message, byte msgId);

    /// <summary>
    /// Struct Frame SDK Configuration
    /// </summary>
    public class StructFrameSdkConfig
    {
        public ITransport Transport { get; set; }
        public IFrameParser FrameParser { get; set; }
        public bool Debug { get; set; } = false;
    }

    /// <summary>
    /// Main SDK Client
    /// </summary>
    public class StructFrameSdk
    {
        private readonly ITransport _transport;
        private readonly IFrameParser _frameParser;
        private readonly bool _debug;
        private readonly Dictionary<byte, List<Delegate>> _messageHandlers;
        private readonly Dictionary<byte, object> _messageCodecs;
        private byte[] _buffer;

        public StructFrameSdk(StructFrameSdkConfig config)
        {
            _transport = config.Transport;
            _frameParser = config.FrameParser;
            _debug = config.Debug;
            _messageHandlers = new Dictionary<byte, List<Delegate>>();
            _messageCodecs = new Dictionary<byte, object>();
            _buffer = Array.Empty<byte>();

            // Set up transport callbacks
            _transport.DataReceived += (sender, data) => HandleIncomingData(data);
            _transport.ErrorOccurred += (sender, error) => HandleError(error);
            _transport.ConnectionClosed += (sender, args) => HandleClose();
        }

        /// <summary>
        /// Connect to the transport
        /// </summary>
        public async Task ConnectAsync()
        {
            await _transport.ConnectAsync();
            Log("Connected");
        }

        /// <summary>
        /// Disconnect from the transport
        /// </summary>
        public async Task DisconnectAsync()
        {
            await _transport.DisconnectAsync();
            Log("Disconnected");
        }

        /// <summary>
        /// Register a message codec for automatic deserialization
        /// </summary>
        public void RegisterCodec<T>(IMessageCodec<T> codec)
        {
            _messageCodecs[codec.MsgId] = codec;
        }

        /// <summary>
        /// Subscribe to messages with a specific message ID
        /// </summary>
        public Action Subscribe<T>(byte msgId, MessageHandler<T> handler)
        {
            if (!_messageHandlers.ContainsKey(msgId))
            {
                _messageHandlers[msgId] = new List<Delegate>();
            }
            _messageHandlers[msgId].Add(handler);
            Log($"Subscribed to message ID {msgId}");

            // Return unsubscribe action
            return () =>
            {
                if (_messageHandlers.ContainsKey(msgId))
                {
                    _messageHandlers[msgId].Remove(handler);
                }
            };
        }

        /// <summary>
        /// Send a raw message (already serialized)
        /// </summary>
        public async Task SendRawAsync(byte msgId, byte[] data)
        {
            byte[] framedData = _frameParser.Frame(msgId, data);
            await _transport.SendAsync(framedData);
            Log($"Sent message ID {msgId}, {data.Length} bytes");
        }

        /// <summary>
        /// Send a message object (requires Pack() method and MsgId property)
        /// </summary>
        public async Task SendAsync<T>(T message) where T : IPackableMessage
        {
            byte[] data = message.Pack();
            await SendRawAsync(message.MsgId, data);
        }

        /// <summary>
        /// Check if connected
        /// </summary>
        public bool IsConnected => _transport.IsConnected;

        private void HandleIncomingData(byte[] data)
        {
            // Append to buffer
            byte[] newBuffer = new byte[_buffer.Length + data.Length];
            Buffer.BlockCopy(_buffer, 0, newBuffer, 0, _buffer.Length);
            Buffer.BlockCopy(data, 0, newBuffer, _buffer.Length, data.Length);
            _buffer = newBuffer;

            // Try to parse messages from buffer
            ParseBuffer();
        }

        private void ParseBuffer()
        {
            while (_buffer.Length > 0)
            {
                FrameMsgInfo result = _frameParser.Parse(_buffer);

                if (!result.Valid)
                {
                    // No valid frame found
                    break;
                }

                // Valid message found
                Log($"Received message ID {result.MsgId}, {result.MsgLen} bytes");

                // Notify handlers
                if (_messageHandlers.ContainsKey(result.MsgId))
                {
                    // Try to deserialize with registered codec
                    object message = result.MsgData;
                    if (_messageCodecs.ContainsKey(result.MsgId))
                    {
                        try
                        {
                            var codec = _messageCodecs[result.MsgId];
                            var deserializeMethod = codec.GetType().GetMethod("Deserialize");
                            message = deserializeMethod.Invoke(codec, new object[] { result.MsgData });
                        }
                        catch (Exception ex)
                        {
                            Log($"Failed to deserialize message ID {result.MsgId}: {ex.Message}");
                        }
                    }

                    // Call all handlers
                    foreach (var handler in _messageHandlers[result.MsgId])
                    {
                        try
                        {
                            handler.DynamicInvoke(message, result.MsgId);
                        }
                        catch (Exception ex)
                        {
                            Log($"Handler error for message ID {result.MsgId}: {ex.Message}");
                        }
                    }
                }

                // Remove parsed data from buffer
                int totalFrameSize = CalculateFrameSize(result);
                byte[] newBuffer = new byte[_buffer.Length - totalFrameSize];
                Buffer.BlockCopy(_buffer, totalFrameSize, newBuffer, 0, newBuffer.Length);
                _buffer = newBuffer;
            }
        }

        private int CalculateFrameSize(FrameMsgInfo result)
        {
            // Calculate total frame size including headers and footers
            // Frame overhead by format:
            // - BasicDefault: 2 start + 1 length + 1 msg_id + payload + 2 crc = 6 + payload
            // - TinyDefault: 1 start + 1 length + 1 msg_id + payload + 2 crc = 5 + payload
            // Using conservative estimate of 10 bytes to handle all frame formats
            // TODO: Query frame parser for exact overhead to avoid buffering issues
            return result.MsgLen + 10;
        }

        private void HandleError(Exception error)
        {
            Log($"Transport error: {error.Message}");
        }

        private void HandleClose()
        {
            Log("Transport closed");
            _buffer = Array.Empty<byte>();
        }

        private void Log(string message)
        {
            if (_debug)
            {
                Console.WriteLine($"[StructFrameSdk] {message}");
            }
        }
    }

    /// <summary>
    /// Interface for messages that can be packed
    /// </summary>
    public interface IPackableMessage
    {
        byte MsgId { get; }
        byte[] Pack();
    }
}
