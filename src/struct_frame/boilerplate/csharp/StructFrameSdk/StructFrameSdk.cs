// Struct Frame SDK Client for C#
// High-level interface for sending and receiving framed messages
// Uses the unified FrameProfiles infrastructure for encoding/parsing

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// Message handler delegate - receives deserialized messages
    /// </summary>
    public delegate void MessageHandler<T>(T message) where T : IStructFrameMessage<T>;

    /// <summary>
    /// Raw message handler delegate (for unregistered message types)
    /// </summary>
    public delegate void RawMessageHandler(FrameMsgInfo frame);

    /// <summary>
    /// Struct Frame SDK Configuration
    /// </summary>
    public class StructFrameSdkConfig
    {
        /// <summary>
        /// Transport layer for communication
        /// </summary>
        public ITransport Transport { get; }

        /// <summary>
        /// Profile configuration (e.g., Profiles.Standard, Profiles.Sensor)
        /// </summary>
        public ProfileConfig Profile { get; }

        /// <summary>
        /// Callback to get message info by ID. Required for:
        /// - CRC validation (provides magic numbers for checksum)
        /// - Minimal profiles (provides message size when no length field)
        /// Use the generated MessageDefinitions.GetMessageInfo method.
        /// </summary>
        public Func<int, MessageInfo?> GetMessageInfo { get; }

        /// <summary>
        /// Internal buffer size for the accumulating reader
        /// </summary>
        public int BufferSize { get; }

        /// <summary>
        /// Enable debug logging
        /// </summary>
        public bool Debug { get; }

        /// <summary>
        /// Create SDK configuration with required parameters
        /// </summary>
        /// <param name="transport">Transport layer for communication</param>
        /// <param name="getMessageInfo">Message info callback (use MessageDefinitions.GetMessageInfo)</param>
        /// <param name="profile">Profile configuration (default: Profiles.Standard)</param>
        /// <param name="bufferSize">Internal buffer size (default: 1024)</param>
        /// <param name="debug">Enable debug logging (default: false)</param>
        public StructFrameSdkConfig(
            ITransport transport,
            Func<int, MessageInfo?> getMessageInfo,
            ProfileConfig? profile = null,
            int bufferSize = 1024,
            bool debug = false)
        {
            Transport = transport ?? throw new ArgumentNullException(nameof(transport));
            GetMessageInfo = getMessageInfo ?? throw new ArgumentNullException(nameof(getMessageInfo));
            Profile = profile ?? Profiles.Standard;
            BufferSize = bufferSize;
            Debug = debug;
        }
    }

    /// <summary>
    /// Internal interface for type-erased handler invocation
    /// </summary>
    internal interface IMessageHandler
    {
        void Invoke(FrameMsgInfo frame);
    }

    /// <summary>
    /// Typed message handler wrapper - deserializes and invokes handler
    /// </summary>
    internal class TypedMessageHandler<T> : IMessageHandler where T : IStructFrameMessage<T>, new()
    {
        private readonly MessageHandler<T> _handler;

        public TypedMessageHandler(MessageHandler<T> handler)
        {
            _handler = handler;
        }

        public void Invoke(FrameMsgInfo frame)
        {
            var message = T.Deserialize(frame);
            _handler(message);
        }
    }

    /// <summary>
    /// Main SDK Client - uses FrameProfiles infrastructure for encoding/parsing
    /// </summary>
    public class StructFrameSdk
    {
        private readonly ITransport _transport;
        private readonly ProfileConfig _profile;
        private readonly FrameEncoder _encoder;
        private readonly AccumulatingReader _reader;
        private readonly bool _debug;
        private readonly Dictionary<ushort, List<IMessageHandler>> _messageHandlers;
        private readonly byte[] _writeBuffer;

        /// <summary>
        /// Event fired when an unhandled message is received
        /// </summary>
        public event RawMessageHandler? UnhandledMessage;

        public StructFrameSdk(StructFrameSdkConfig config)
        {
            _transport = config.Transport;
            _profile = config.Profile;
            _debug = config.Debug;
            _messageHandlers = new Dictionary<ushort, List<IMessageHandler>>();

            // Create encoder and reader using FrameProfiles infrastructure
            _encoder = new FrameEncoder(_profile);
            _reader = new AccumulatingReader(_profile, config.BufferSize, config.GetMessageInfo);
            _writeBuffer = new byte[config.BufferSize];

            // Set up transport callbacks
            _transport.DataReceived += (sender, data) => HandleIncomingData(data);
            _transport.ErrorOccurred += (sender, error) => HandleError(error);
            _transport.ConnectionClosed += (sender, args) => HandleClose();
        }

        /// <summary>
        /// Get the profile configuration
        /// </summary>
        public ProfileConfig Profile => _profile;

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
        /// Subscribe to messages of a specific type.
        /// The message ID is automatically inferred from the message type.
        /// </summary>
        public Action Subscribe<T>(MessageHandler<T> handler) where T : IStructFrameMessage<T>, new()
        {
            var temp = new T();
            ushort msgId = temp.GetMsgId();
            
            var typedHandler = new TypedMessageHandler<T>(handler);
            
            if (!_messageHandlers.TryGetValue(msgId, out var handlers))
            {
                handlers = new List<IMessageHandler>();
                _messageHandlers[msgId] = handlers;
            }
            handlers.Add(typedHandler);
            Log($"Subscribed to message ID {msgId} ({typeof(T).Name})");

            // Return unsubscribe action
            return () => handlers.Remove(typedHandler);
        }

        /// <summary>
        /// Send a message object
        /// </summary>
        public async Task SendAsync<T>(T message, byte seq = 0, byte sysId = 0, byte compId = 0) where T : IStructFrameMessage<T>
        {
            int bytesWritten = _encoder.Encode(_writeBuffer, 0, message, seq, sysId, compId);
            if (bytesWritten == 0)
            {
                throw new InvalidOperationException("Failed to encode message - buffer too small or payload exceeds max size");
            }

            byte[] framedData = new byte[bytesWritten];
            Buffer.BlockCopy(_writeBuffer, 0, framedData, 0, bytesWritten);
            await _transport.SendAsync(framedData);
            Log($"Sent message ID {message.GetMsgId()}, {bytesWritten} bytes total");
        }

        /// <summary>
        /// Check if connected
        /// </summary>
        public bool IsConnected => _transport.IsConnected;

        private void HandleIncomingData(byte[] data)
        {
            _reader.AddData(data);
            while (_reader.TryNext(out var frame))
            {
                ProcessFrame(frame);
            }
        }

        private void ProcessFrame(FrameMsgInfo frame)
        {
            Log($"Received message ID {frame.MsgId}, {frame.MsgLen} bytes payload");

            if (_messageHandlers.TryGetValue(frame.MsgId, out var handlers))
            {
                // Create a copy to avoid collection modification during enumeration
                var handlersCopy = handlers.ToArray();
                foreach (var handler in handlersCopy)
                {
                    try
                    {
                        handler.Invoke(frame);
                    }
                    catch (Exception ex)
                    {
                        Log($"Handler error for message ID {frame.MsgId}: {ex.Message}");
                    }
                }
            }
            else
            {
                UnhandledMessage?.Invoke(frame);
            }
        }

        private void HandleError(Exception error)
        {
            Log($"Transport error: {error.Message}");
        }

        private void HandleClose()
        {
            Log("Transport closed");
            _reader.Reset();
        }

        private void Log(string message)
        {
            if (_debug)
            {
                Console.WriteLine($"[StructFrameSdk] {message}");
            }
        }
    }
}
