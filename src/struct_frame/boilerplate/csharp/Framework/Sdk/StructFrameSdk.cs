// Struct Frame SDK Client for C#
// High-level interface for sending and receiving framed messages
// Uses the unified FrameProfiles infrastructure for encoding/parsing

#nullable enable

using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
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
    /// <para>
    /// Thread-safety: <see cref="Subscribe{T}"/> and the returned unsubscribe action may
    /// be called from any thread. <see cref="SendAsync{T}"/> is thread-safe and re-entrant.
    /// Callbacks (<see cref="FrameReceived"/>, typed subscribers) are invoked on the
    /// transport's receive thread — do not block inside them.
    /// </para>
    /// </summary>
    public class StructFrameSdk : IDisposable
    {
        private readonly ITransport _transport;
        private readonly ProfileConfig _profile;
        private readonly FrameEncoder _encoder;
        private readonly AccumulatingReader _reader;
        private readonly Func<int, MessageInfo?> _getMessageInfo;
        private readonly bool _debug;
        // Copy-on-write handler arrays: Subscribe/Unsubscribe swap in a new array under lock,
        // so the hot receive path can read the array reference without allocating a snapshot.
        private readonly Dictionary<ushort, IMessageHandler[]> _messageHandlers;
        private readonly object _handlersLock = new object();
        private readonly int _bufferSize;
        private readonly bool _strictOrdering;

        // Transport event delegates kept as fields so they can be unsubscribed in Dispose.
        private readonly EventHandler<byte[]>? _onDataReceived;
        private readonly EventHandler<ReadOnlyMemory<byte>>? _onDataReceivedMemory;
        private readonly IBufferReceiveTransport? _bufferReceiveTransport;
        private readonly EventHandler<Exception> _onErrorOccurred;
        private readonly EventHandler _onConnectionClosed;

        // Send queue infrastructure (only used when StrictOrdering is enabled)
        private Channel<QueuedMessage>? _sendQueue;
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
        /// Fired for every received frame (valid or CRC-failed). Check <c>frame.Valid</c>
        /// and <c>frame.Status</c> before acting on the payload.
        /// </summary>
        public event RawMessageHandler? FrameReceived;

        /// <summary>
        /// Fired when a valid frame arrives but no typed subscriber is registered for its message ID.
        /// </summary>
        public event RawMessageHandler? UnhandledMessage;

        /// <summary>
        /// Fired when the transport reports an error.
        /// </summary>
        public event EventHandler<Exception>? ErrorOccurred;

        /// <summary>
        /// Fired when the transport connection closes.
        /// </summary>
        public event EventHandler? ConnectionClosed;

        public StructFrameSdk(StructFrameSdkConfig config)
        {
            _transport = config.Transport;
            _profile = config.Profile;
            _getMessageInfo = config.GetMessageInfo;
            _debug = config.Debug;
            _messageHandlers = new Dictionary<ushort, IMessageHandler[]>();

            _encoder = new FrameEncoder(_profile);
            _reader = new AccumulatingReader(_profile, config.BufferSize, config.GetMessageInfo);
            _bufferSize = config.BufferSize;
            _strictOrdering = config.StrictOrdering;

            if (_transport is IBufferReceiveTransport bufferReceiveTransport)
            {
                _bufferReceiveTransport = bufferReceiveTransport;
                _onDataReceivedMemory = (_, data) => HandleIncomingData(data);
                _bufferReceiveTransport.DataReceivedMemory += _onDataReceivedMemory;
            }
            else
            {
                _onDataReceived = (_, data) => HandleIncomingData(data);
                _transport.DataReceived += _onDataReceived;
            }
            _onErrorOccurred = (_, error) => HandleError(error);
            _onConnectionClosed = (_, _) => HandleClose();

            _transport.ErrorOccurred += _onErrorOccurred;
            _transport.ConnectionClosed += _onConnectionClosed;
        }

        /// <summary>
        /// Get the profile configuration
        /// </summary>
        public ProfileConfig Profile => _profile;

        /// <summary>
        /// Connect to the transport. When strict ordering is enabled,
        /// starts the background send queue consumer.
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
        /// Disconnect from the transport. Stops the strict-ordering send queue (if active)
        /// before disconnecting so in-flight queued messages are cancelled cleanly.
        /// </summary>
        public async Task DisconnectAsync()
        {
            if (_strictOrdering) await StopSendQueueAsync();
            await _transport.DisconnectAsync();
            Log("Disconnected");
        }

        /// <summary>
        /// Subscribe to messages of a specific type.
        /// The message ID is automatically inferred from the message type.
        /// Returns an action that, when called, removes this subscription.
        /// </summary>
        public Action Subscribe<T>(MessageHandler<T> handler) where T : IStructFrameMessage<T>, new()
        {
            var temp = new T();
            ushort msgId = temp.GetMsgId();

            var typedHandler = new TypedMessageHandler<T>(handler);

            lock (_handlersLock)
            {
                _messageHandlers.TryGetValue(msgId, out var existing);
                int n = existing?.Length ?? 0;
                var updated = new IMessageHandler[n + 1];
                if (existing != null) Array.Copy(existing, updated, n);
                updated[n] = typedHandler;
                _messageHandlers[msgId] = updated;
            }
            Log($"Subscribed to message ID {msgId} ({typeof(T).Name})");

            return () =>
            {
                lock (_handlersLock)
                {
                    if (!_messageHandlers.TryGetValue(msgId, out var arr)) return;
                    int idx = Array.IndexOf(arr, typedHandler);
                    if (idx < 0) return;
                    if (arr.Length == 1)
                    {
                        _messageHandlers.Remove(msgId);
                    }
                    else
                    {
                        var updated = new IMessageHandler[arr.Length - 1];
                        Array.Copy(arr, 0, updated, 0, idx);
                        Array.Copy(arr, idx + 1, updated, idx, arr.Length - idx - 1);
                        _messageHandlers[msgId] = updated;
                    }
                }
            };
        }

        /// <summary>
        /// Send a request message and await a matching response.
        /// <para>
        /// Subscribes a one-shot handler for <typeparamref name="TResp"/> before sending
        /// <paramref name="request"/>, then waits up to <paramref name="timeoutSeconds"/>
        /// for a response that satisfies the optional <paramref name="match"/> predicate.
        /// The subscription is always removed in a finally block.
        /// </para>
        /// </summary>
        /// <typeparam name="TReq">Request message type.</typeparam>
        /// <typeparam name="TResp">Expected response message type.</typeparam>
        /// <param name="request">Message to send.</param>
        /// <param name="match">
        ///   Optional predicate applied to each received <typeparamref name="TResp"/>.
        ///   When null, the first response with the correct message ID is returned.
        /// </param>
        /// <param name="timeoutSeconds">Seconds before a <see cref="TimeoutException"/> is thrown.</param>
        /// <param name="ct">Cancellation token.</param>
        /// <returns>The first matching response.</returns>
        /// <exception cref="TimeoutException">
        ///   Thrown when no matching response arrives within <paramref name="timeoutSeconds"/> seconds.
        /// </exception>
        public async Task<TResp> RequestAsync<TReq, TResp>(
            TReq request,
            Func<TResp, bool>? match = null,
            float timeoutSeconds = 5f,
            CancellationToken ct = default)
            where TReq : IStructFrameMessage<TReq>
            where TResp : IStructFrameMessage<TResp>, new()
        {
            var tcs = new TaskCompletionSource<TResp>(TaskCreationOptions.RunContinuationsAsynchronously);

            Action? unsubscribe = Subscribe<TResp>(msg =>
            {
                if (!tcs.Task.IsCompleted && (match == null || match(msg)))
                    tcs.TrySetResult(msg);
            });

            try
            {
                await SendAsync(request).ConfigureAwait(false);
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                cts.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));
                return await tcs.Task.WaitAsync(cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                var respId = new TResp().GetMsgId();
                throw new TimeoutException(
                    $"No response (msg_id={respId}) within {timeoutSeconds}s");
            }
            finally
            {
                unsubscribe?.Invoke();
            }
        }

        /// <summary>
        /// Send a framed message through the transport.
        /// <para>
        /// When <c>StrictOrdering</c> is enabled the message is placed into an internal
        /// FIFO queue; the returned Task completes when the message has been sent.
        /// When disabled, the message is sent directly and concurrently.
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

            // buffer is a fresh, non-reused allocation; hand a view of the written bytes to
            // the transport directly. The strict-ordering queue makes its own owned copy.
            var result = await SendFramedBytesAsync(buffer.AsMemory(0, bytesWritten)).ConfigureAwait(false);

            Log($"Sent message ID {message.GetMsgId()}, {bytesWritten} bytes total");
            return result;
        }

        /// <summary>
        /// Send pre-serialized payload bytes as a framed message.
        /// Equivalent to Python's <c>send_raw(msg_id, data)</c> and TypeScript's <c>sendRaw(msgId, data)</c> —
        /// frames the given payload under the configured profile without requiring a message object.
        /// </summary>
        public async Task<SendResult> SendRawAsync(ushort msgId, ReadOnlyMemory<byte> payload, byte seq = 0, byte sysId = 0, byte compId = 0, byte pkgId = 0)
        {
            byte[] buffer = new byte[_profile.MaxPayload + _profile.Overhead];
            var info = _getMessageInfo(msgId);
            int bytesWritten = _encoder.EncodeRaw(buffer, 0, msgId, payload.Span, seq, sysId, compId, pkgId, info);
            if (bytesWritten == 0)
            {
                throw new InvalidOperationException("Failed to encode raw payload — buffer too small or payload exceeds max size");
            }
            var result = await SendFramedBytesAsync(buffer.AsMemory(0, bytesWritten)).ConfigureAwait(false);
            Log($"Sent raw message ID {msgId}, {bytesWritten} bytes total");
            return result;
        }

        /// <summary>
        /// Re-encode a parsed frame using the current profile and send it.
        /// </summary>
        public async Task<SendResult> ReencodeAsync(FrameMsgInfo frame)
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

            var result = await SendFramedBytesAsync(buffer.AsMemory(0, bytesWritten)).ConfigureAwait(false);
            Log($"Re-encoded and sent frame ID {frame.MsgId}, {bytesWritten} bytes total");
            return result;
        }

        /// <summary>
        /// Directly forward an already-framed message without re-encoding.
        /// Assumes the source and destination profiles are the same.
        /// </summary>
        public async Task<SendResult> ForwardAsync(FrameMsgInfo frame)
        {
            if (frame.FrameData.IsEmpty)
            {
                throw new InvalidOperationException("FrameData is required for direct forwarding");
            }

            var result = await SendFramedBytesAsync(frame.FrameData).ConfigureAwait(false);
            Log($"Forwarded frame ID {frame.MsgId}, {frame.FrameData.Length} bytes total");
            return result;
        }

        // Keep old names as thin wrappers so existing tests compile without changes.
        [Obsolete("Use ReencodeAsync")]
        public Task<SendResult> Send(FrameMsgInfo frame) => ReencodeAsync(frame);
        [Obsolete("Use ForwardAsync")]
        public Task<SendResult> SendDirect(FrameMsgInfo frame) => ForwardAsync(frame);

        /// <summary>
        /// Check if connected
        /// </summary>
        public bool IsConnected => _transport.IsConnected;

        private void HandleIncomingData(byte[] data)
            => HandleIncomingData(new ReadOnlyMemory<byte>(data));

        private void HandleIncomingData(ReadOnlyMemory<byte> data)
        {
            if (_disposed) return;
            if (MemoryMarshal.TryGetArray(data, out ArraySegment<byte> segment) && segment.Array != null)
            {
                _reader.AddData(segment.Array, segment.Offset, segment.Count);
            }
            else
            {
                _reader.AddData(data.ToArray());
            }
            // TryNext keeps draining past CRC-failed and resync events and stops only when no
            // further progress is possible. Dispatch only actual frames (valid or CRC-failed)
            // to ProcessFrame, mirroring the raw-tap semantics; pure resync events are skipped.
            while (_reader.TryNext(out var frame))
            {
                if (frame.Valid || frame.Status == FrameMsgStatus.CrcFailure)
                {
                    ProcessFrame(frame);
                }
            }
        }

        private void ProcessFrame(FrameMsgInfo frame)
        {
            Log($"Received message ID {frame.MsgId}, {frame.MsgLen} bytes payload, valid={frame.Valid}");

            // Clone frame bytes before dispatch so callback consumers never observe
            // transport buffer reuse from subsequent reads.
            FrameMsgInfo dispatchFrame = CloneFrameForDispatch(frame);

            // FrameReceived fires for all frames (raw tap) — valid and CRC-failed alike.
            FrameReceived?.Invoke(dispatchFrame);

            if (!dispatchFrame.Valid)
            {
                // Do not dispatch invalid (e.g. CRC-failed) frames to typed subscribers.
                return;
            }

            IMessageHandler[]? handlersCopy = null;
            lock (_handlersLock)
            {
                // COW array: safe to read the reference under the lock and iterate outside it
                // without copying — Subscribe/Unsubscribe never mutate an array in place.
                if (_messageHandlers.TryGetValue(dispatchFrame.MsgId, out var handlers) && handlers.Length > 0)
                    handlersCopy = handlers;
            }

            if (handlersCopy != null)
            {
                foreach (var handler in handlersCopy)
                {
                    try
                    {
                        handler.Invoke(dispatchFrame);
                    }
                    catch (Exception ex)
                    {
                        Log($"Handler error for message ID {dispatchFrame.MsgId}: {ex.Message}");
                    }
                }
            }
            else
            {
                UnhandledMessage?.Invoke(dispatchFrame);
            }
        }

        private static FrameMsgInfo CloneFrameForDispatch(FrameMsgInfo frame)
        {
            if (frame.FrameData.IsEmpty)
            {
                return frame;
            }

            byte[] ownedFrame = frame.FrameData.ToArray();
            var cloned = frame;
            cloned.FrameData = ownedFrame;
            cloned.MsgData = ownedFrame;

            int payloadOffset = frame.MsgDataOffset;
            if (MemoryMarshal.TryGetArray(frame.FrameData, out ArraySegment<byte> frameSegment) &&
                frameSegment.Array != null)
            {
                payloadOffset = frame.MsgDataOffset - frameSegment.Offset;
            }

            if (payloadOffset < 0 || payloadOffset + frame.MsgLen > ownedFrame.Length)
            {
                payloadOffset = 0;
            }

            cloned.MsgDataOffset = payloadOffset;
            return cloned;
        }

        private async Task<SendResult> SendFramedBytesAsync(ReadOnlyMemory<byte> framedData)
        {
            if (_strictOrdering)
            {
                Channel<QueuedMessage>? queue;
                lock (_handlersLock)
                {
                    queue = _sendQueue;
                }
                if (queue == null)
                {
                    throw new InvalidOperationException("Send queue is not running — call ConnectAsync first");
                }

                var tcs = new TaskCompletionSource<SendResult>(TaskCreationOptions.RunContinuationsAsynchronously);
                byte[] bytes = framedData.ToArray();
                if (!queue.Writer.TryWrite(new QueuedMessage(bytes, tcs)))
                {
                    throw new InvalidOperationException("Send queue is closed — transport may be disconnected");
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
            ErrorOccurred?.Invoke(this, error);
        }

        private void HandleClose()
        {
            Log("Transport closed");
            ConnectionClosed?.Invoke(this, EventArgs.Empty);
            if (_strictOrdering) _ = StopSendQueueAsync();
            _reader.Reset();
        }

        private void StartSendQueue()
        {
            var queue = Channel.CreateUnbounded<QueuedMessage>(new UnboundedChannelOptions
            {
                SingleReader = true
            });
            var cts = new CancellationTokenSource();
            lock (_handlersLock)
            {
                _sendQueue = queue;
                _sendQueueCts = cts;
                _sendQueueTask = SendQueueConsumerAsync(queue, cts.Token);
            }
        }

        private Task StopSendQueueAsync()
        {
            Channel<QueuedMessage>? queue;
            CancellationTokenSource? cts;
            Task? consumerTask;

            lock (_handlersLock)
            {
                queue = _sendQueue;
                cts = _sendQueueCts;
                consumerTask = _sendQueueTask;
                _sendQueue = null;
                _sendQueueCts = null;
                _sendQueueTask = null;
            }

            if (queue != null)
            {
                queue.Writer.TryComplete();
                // Drain remaining queued messages and cancel them.
                while (queue.Reader.TryRead(out var queued))
                {
                    queued.Completion.TrySetCanceled();
                }
            }

            cts?.Cancel();
            cts?.Dispose();

            // Do NOT await consumerTask: the consumer may be blocked inside an
            // in-flight transport.SendAsync that has no cancellation support.
            // We've completed the channel and cancelled the token, so the consumer
            // will exit on its own after the current send finishes or throws.
            _ = consumerTask; // suppress unused-variable warning
            return Task.CompletedTask;
        }

        private async Task SendQueueConsumerAsync(Channel<QueuedMessage> queue, CancellationToken ct)
        {
            try
            {
                await foreach (var queued in queue.Reader.ReadAllAsync(ct).ConfigureAwait(false))
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
                // Expected on disconnect/dispose.
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
        /// Call <see cref="DisconnectAsync"/> before Dispose to drain the send queue cleanly.
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
                    // Unsubscribe transport events first to prevent callbacks into a disposed SDK.
                    if (_bufferReceiveTransport != null && _onDataReceivedMemory != null)
                    {
                        _bufferReceiveTransport.DataReceivedMemory -= _onDataReceivedMemory;
                    }
                    if (_onDataReceived != null)
                    {
                        _transport.DataReceived -= _onDataReceived;
                    }
                    _transport.ErrorOccurred -= _onErrorOccurred;
                    _transport.ConnectionClosed -= _onConnectionClosed;

                    if (_strictOrdering)
                    {
                        // Best-effort synchronous teardown of the send queue.
                        Channel<QueuedMessage>? queue;
                        CancellationTokenSource? cts;
                        lock (_handlersLock)
                        {
                            queue = _sendQueue;
                            cts = _sendQueueCts;
                            _sendQueue = null;
                            _sendQueueCts = null;
                            _sendQueueTask = null;
                        }
                        queue?.Writer.TryComplete();
                        while (queue?.Reader.TryRead(out var queued) == true)
                            queued.Completion.TrySetCanceled();
                        cts?.Cancel();
                        cts?.Dispose();
                    }
                }
                _disposed = true;
            }
        }
    }
}
