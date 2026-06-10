// Struct Frame SDK Client for C#
// High-level interface for sending and receiving framed messages
// Uses the unified FrameProfiles infrastructure for encoding/parsing

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;
using StructFrame.Framing;
using StructFrame.Profiles;

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
        /// When true, messages are sent in strict FIFO order using an internal
        /// queue with a dedicated background consumer. When false (default),
        /// messages are sent directly through the transport — concurrent calls
        /// are safe but ordering is not guaranteed.
        /// </summary>
        public bool StrictOrdering { get; }

        /// <summary>
        /// Create SDK configuration with required parameters
        /// </summary>
        /// <param name="transport">Transport layer for communication</param>
        /// <param name="getMessageInfo">Message info callback (use MessageDefinitions.GetMessageInfo)</param>
        /// <param name="profile">Profile configuration (default: Profiles.Standard)</param>
        /// <param name="bufferSize">Internal buffer size (default: 1024)</param>
        /// <param name="debug">Enable debug logging (default: false)</param>
        /// <param name="strictOrdering">Enforce strict FIFO send ordering (default: false)</param>
        public StructFrameSdkConfig(
            ITransport transport,
            Func<int, MessageInfo?> getMessageInfo,
            ProfileConfig? profile = null,
            int bufferSize = 1024,
            bool debug = false,
            bool strictOrdering = false)
        {
            Transport = transport ?? throw new ArgumentNullException(nameof(transport));
            GetMessageInfo = getMessageInfo ?? throw new ArgumentNullException(nameof(getMessageInfo));
            Profile = profile ?? StructFrame.Profiles.Profiles.Standard;
            BufferSize = bufferSize;
            Debug = debug;
            StrictOrdering = strictOrdering;
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
    /// Main SDK Client - uses FrameProfiles infrastructure for encoding/parsing.
    /// Implements IDisposable to clean up internal resources.
    /// </summary>
    public class StructFrameSdk : IDisposable
    {
        private readonly ITransport _transport;
        private readonly ProfileConfig _profile;
        private readonly FrameEncoder _encoder;
        private readonly AccumulatingReader _reader;
        private readonly Func<int, MessageInfo?> _getMessageInfo;
        private readonly bool _debug;
        private readonly Dictionary<ushort, List<IMessageHandler>> _messageHandlers;
        private readonly int _bufferSize;
        private readonly bool _strictOrdering;

        // Send queue infrastructure (only used when StrictOrdering is enabled)
        private readonly Channel<QueuedMessage>? _sendQueue;
        private CancellationTokenSource? _sendQueueCts;
        private Task? _sendQueueTask;

        /// <summary>
        /// A queued send operation: encoded frame data + completion signal.
        /// </summary>
        private readonly struct QueuedMessage
        {
            public readonly byte[] Data;
            public readonly TaskCompletionSource<SendResult> Completion;

            public QueuedMessage(byte[] data, TaskCompletionSource<SendResult> completion)
            {
                Data = data;
                Completion = completion;
            }
        }

        /// <summary>
        /// Event fired when an unhandled message is received
        /// </summary>
        public event RawMessageHandler? FrameReceived;

        /// <summary>
        /// Event fired when a frame is received but no typed handler is registered.
        /// </summary>
        public event RawMessageHandler? UnhandledMessage;

        public StructFrameSdk(StructFrameSdkConfig config)
        {
            _transport = config.Transport;
            _profile = config.Profile;
            _getMessageInfo = config.GetMessageInfo;
            _debug = config.Debug;
            _messageHandlers = new Dictionary<ushort, List<IMessageHandler>>();

            // Create encoder and reader using FrameProfiles infrastructure
            _encoder = new FrameEncoder(_profile);
            _reader = new AccumulatingReader(_profile, config.BufferSize, config.GetMessageInfo);
            _bufferSize = config.BufferSize;
            _strictOrdering = config.StrictOrdering;

            // Create send queue only when strict ordering is enabled
            if (_strictOrdering)
            {
                _sendQueue = Channel.CreateUnbounded<QueuedMessage>(new UnboundedChannelOptions
                {
                    SingleReader = true
                });
            }

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
        /// Connect to the transport. When strict ordering is enabled,
        /// starts the background send queue consumer.
        /// If the transport is already connected, skips the transport connect
        /// and only starts the send queue.
        /// </summary>
        public async Task ConnectAsync()
        {
            if (!_transport.IsConnected)
            {
                await _transport.ConnectAsync();
            }
            if (_strictOrdering) StartSendQueue();
            Log("Connected");
        }

        /// <summary>
        /// Disconnect from the transport. When strict ordering is enabled,
        /// stops the send queue consumer and cancels any pending queued messages.
        /// </summary>
        public async Task DisconnectAsync()
        {
            if (_strictOrdering) StopSendQueue();
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
        /// Send a framed message through the transport.
        /// <para>
        /// When <c>StrictOrdering</c> is enabled (set in config), messages are
        /// placed into an internal FIFO queue and sent sequentially by a
        /// background consumer, guaranteeing order even with concurrent callers.
        /// The returned Task completes when the message has actually been sent.
        /// </para>
        /// <para>
        /// When <c>StrictOrdering</c> is disabled (default), messages are sent
        /// directly through the transport. Concurrent calls are safe (serialized
        /// at the transport level) but ordering is not guaranteed. To ensure
        /// order without strict ordering, await each call sequentially:
        /// <code>
        /// await sdk.SendAsync(msg1);  // sent first
        /// await sdk.SendAsync(msg2);  // guaranteed after msg1
        /// </code>
        /// </para>
        /// </summary>
        public async Task<SendResult> SendAsync<T>(T message, byte seq = 0, byte sysId = 0, byte compId = 0) where T : IStructFrameMessage<T>
        {
            return await SendRawAsync(message, seq, sysId, compId).ConfigureAwait(false);
        }

        /// <summary>
        /// Send any <see cref="IStructFrameMessage"/> (including non-generic wrappers).
        /// Prefer <see cref="SendAsync{T}"/> for normal messages.
        /// </summary>
        public async Task<SendResult> SendRawAsync(IStructFrameMessage message, byte seq = 0, byte sysId = 0, byte compId = 0)
        {
            byte[] buffer = new byte[_profile.MaxPayload + _profile.Overhead];
            int bytesWritten = _encoder.Encode(buffer, 0, message, seq, sysId, compId);
            if (bytesWritten == 0)
            {
                throw new InvalidOperationException("Failed to encode message - buffer too small or payload exceeds max size");
            }

            byte[] framedData = new byte[bytesWritten];
            Buffer.BlockCopy(buffer, 0, framedData, 0, bytesWritten);

            var result = await SendFramedBytesAsync(framedData).ConfigureAwait(false);

            Log($"Sent message ID {message.GetMsgId()}, {bytesWritten} bytes total");
            return result;
        }

        /// <summary>
        /// Send a parsed frame using the current profile. This re-encodes from
        /// payload metadata rather than forwarding the original wire bytes.
        /// </summary>
        public async Task<SendResult> Send(FrameMsgInfo frame)
        {
            if (frame.MsgData == null)
            {
                throw new InvalidOperationException("Cannot re-encode an empty frame");
            }

            byte[] buffer = new byte[_profile.MaxPayload + _profile.Overhead];
            var info = _getMessageInfo(frame.MsgId);
            int bytesWritten = _encoder.EncodeRaw(
                buffer,
                0,
                frame.MsgId,
                frame.GetPayloadSpan(),
                frame.Seq,
                frame.SysId,
                frame.CompId,
                frame.PkgId,
                info);

            if (bytesWritten == 0)
            {
                throw new InvalidOperationException("Failed to re-encode frame - buffer too small or payload exceeds max size");
            }

            byte[] framedData = new byte[bytesWritten];
            Buffer.BlockCopy(buffer, 0, framedData, 0, bytesWritten);
            var result = await SendFramedBytesAsync(framedData).ConfigureAwait(false);
            Log($"Sent frame ID {frame.MsgId}, {bytesWritten} bytes total");
            return result;
        }

        /// <summary>
        /// Directly forward an already framed message without re-encoding.
        /// Assumes the source and destination profiles are the same.
        /// </summary>
        public async Task<SendResult> SendDirect(FrameMsgInfo frame)
        {
            if (frame.FrameData.IsEmpty)
            {
                throw new InvalidOperationException("FrameData is required for direct forwarding");
            }

            var result = await SendFramedBytesAsync(frame.FrameData).ConfigureAwait(false);
            Log($"Directly forwarded frame ID {frame.MsgId}, {frame.FrameData.Length} bytes total");
            return result;
        }

        /// <summary>
        /// Check if connected
        /// </summary>
        public bool IsConnected => _transport.IsConnected;

        private void HandleIncomingData(byte[] data)
        {
            _reader.AddData(data);
            while (true)
            {
                var frame = _reader.Next();
                if (!frame.Valid && frame.FrameData.Length == 0)
                {
                    break;
                }
                ProcessFrame(frame);
            }
        }

        private void ProcessFrame(FrameMsgInfo frame)
        {
            Log($"Received message ID {frame.MsgId}, {frame.MsgLen} bytes payload");

            FrameReceived?.Invoke(frame);

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
            else if (frame.Valid)
            {
                UnhandledMessage?.Invoke(frame);
            }
        }

        private async Task<SendResult> SendFramedBytesAsync(ReadOnlyMemory<byte> framedData)
        {
            if (_strictOrdering)
            {
                var tcs = new TaskCompletionSource<SendResult>(TaskCreationOptions.RunContinuationsAsynchronously);

                byte[] bytes = framedData.ToArray();
                if (!_sendQueue!.Writer.TryWrite(new QueuedMessage(bytes, tcs)))
                {
                    throw new InvalidOperationException("Send queue is closed - transport may be disconnected");
                }

                return await tcs.Task.ConfigureAwait(false);
            }
            else
            {
                int attempted = framedData.Length;
                int bytesWritten = await _transport.SendAsync(framedData).ConfigureAwait(false);
                return new SendResult(bytesWritten == attempted, attempted, bytesWritten);
            }
        }

        private void HandleError(Exception error)
        {
            Log($"Transport error: {error.Message}");
        }

        private void HandleClose()
        {
            Log("Transport closed");
            if (_strictOrdering) StopSendQueue();
            _reader.Reset();
        }

        private void StartSendQueue()
        {
            _sendQueueCts = new CancellationTokenSource();
            _sendQueueTask = SendQueueConsumerAsync(_sendQueueCts.Token);
        }

        private void StopSendQueue()
        {
            if (_sendQueueCts != null)
            {
                _sendQueueCts.Cancel();
                _sendQueueCts.Dispose();
                _sendQueueCts = null;
            }

            // Drain remaining queued messages and cancel them
            while (_sendQueue!.Reader.TryRead(out var queued))
            {
                queued.Completion.TrySetCanceled();
            }

            _sendQueueTask = null;
        }

        private async Task SendQueueConsumerAsync(CancellationToken ct)
        {
            try
            {
                await foreach (var queued in _sendQueue!.Reader.ReadAllAsync(ct).ConfigureAwait(false))
                {
                    try
                    {
                        int attempted = queued.Data.Length;
                        int bytesWritten = await _transport.SendAsync(queued.Data).ConfigureAwait(false);
                        queued.Completion.TrySetResult(new SendResult(bytesWritten == attempted, attempted, bytesWritten));
                    }
                    catch (Exception ex)
                    {
                        queued.Completion.TrySetException(ex);
                        Log($"Send queue error: {ex.Message}");
                    }
                }
            }
            catch (OperationCanceledException)
            {
                // Expected on disconnect
            }
        }

        private void Log(string message)
        {
            if (_debug)
            {
                Console.WriteLine($"[StructFrameSdk] {message}");
            }
        }

        private bool _disposed;

        /// <summary>
        /// Releases resources used by the SDK.
        /// </summary>
        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        /// Releases the unmanaged resources and optionally releases the managed resources.
        /// </summary>
        protected virtual void Dispose(bool disposing)
        {
            if (!_disposed)
            {
                if (disposing)
                {
                    if (_strictOrdering) StopSendQueue();
                    _sendQueueCts?.Dispose();
                }
                _disposed = true;
            }
        }
    }
}
