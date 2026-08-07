// Transport interface for C# struct-frame SDK
// Provides abstraction for various communication channels

#nullable enable

using System;
using System.Threading;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// Transport configuration
    /// </summary>
    public class TransportConfig
    {
        /// <summary>Whether to reconnect automatically after a failure.</summary>
        public bool AutoReconnect { get; set; } = false;
        /// <summary>Delay between reconnect attempts in milliseconds.</summary>
        public int ReconnectDelayMs { get; set; } = 1000;
        /// <summary>Maximum reconnect attempts; zero means unlimited.</summary>
        public int MaxReconnectAttempts { get; set; } = 0; // 0 = infinite
    }

    /// <summary>
    /// Verbose send result returned by SDK send methods.
    /// </summary>
    public readonly struct SendResult
    {
        /// <summary>Whether the send completed successfully.</summary>
        public bool Success { get; }
        /// <summary>Number of bytes attempted.</summary>
        public int AttemptedBytes { get; }
        /// <summary>Number of bytes written.</summary>
        public int BytesWritten { get; }

        /// <summary>Creates a send result.</summary>
        public SendResult(bool success, int attemptedBytes, int bytesWritten)
        {
            Success = success;
            AttemptedBytes = attemptedBytes;
            BytesWritten = bytesWritten;
        }
    }

    /// <summary>
    /// Transport interface for sending and receiving data
    /// </summary>
    public interface ITransport
    {
        /// <summary>
        /// Connect to the transport endpoint
        /// </summary>
        Task ConnectAsync();

        /// <summary>
        /// Disconnect from the transport endpoint
        /// </summary>
        Task DisconnectAsync();

        /// <summary>
        /// Send data through the transport.
        /// Thread-safe: concurrent calls are serialized to prevent data corruption.
        /// Note: message ordering is NOT guaranteed when multiple callers invoke
        /// SendAsync concurrently. If message order matters, the caller must
        /// await each SendAsync call sequentially.
        /// </summary>
        Task<int> SendAsync(byte[] data);

        /// <summary>
        /// Send data through the transport (memory-efficient overload).
        /// See <see cref="SendAsync(byte[])"/> for thread-safety and ordering notes.
        /// </summary>
        Task<int> SendAsync(ReadOnlyMemory<byte> data);

        /// <summary>
        /// Event fired when data is received
        /// </summary>
        event EventHandler<byte[]> DataReceived;

        /// <summary>
        /// Event fired when an error occurs
        /// </summary>
        event EventHandler<Exception> ErrorOccurred;

        /// <summary>
        /// Event fired when connection closes
        /// </summary>
        event EventHandler ConnectionClosed;

        /// <summary>
        /// Check if transport is connected
        /// </summary>
        bool IsConnected { get; }
    }

    /// <summary>
    /// Optional receive-side extension for transports that can report a valid
    /// buffer slice without first allocating a right-sized byte array.
    /// The memory is only guaranteed to remain valid for the duration of the callback.
    /// </summary>
    public interface IBufferReceiveTransport
    {
        /// <summary>
        /// Event fired when data is received as a length-aware memory slice.
        /// </summary>
        event EventHandler<ReadOnlyMemory<byte>> DataReceivedMemory;
    }

    /// <summary>
    /// Base transport with common functionality.
    /// Implements IDisposable to clean up the internal send semaphore.
    /// </summary>
    public abstract class BaseTransport : ITransport, IBufferReceiveTransport, IDisposable
    {
        // Volatile: written on connect/disconnect paths and read from receive threads.
        /// <summary>Connection state shared across transport threads.</summary>
        protected volatile bool _connected;
        /// <summary>Transport reconnect configuration.</summary>
        protected TransportConfig _config;
        /// <summary>Number of reconnect attempts made.</summary>
        protected int _reconnectAttempts;
        private readonly SemaphoreSlim _sendSemaphore = new SemaphoreSlim(1, 1);
        private int _reconnectInProgress;
        private bool _disposed;

        /// <summary>Raised when byte-array data is received.</summary>
        public event EventHandler<byte[]>? DataReceived;
        /// <summary>Raised when memory data is received.</summary>
        public event EventHandler<ReadOnlyMemory<byte>>? DataReceivedMemory;
        /// <summary>Raised when a transport error occurs.</summary>
        public event EventHandler<Exception>? ErrorOccurred;
        /// <summary>Raised when the connection closes.</summary>
        public event EventHandler? ConnectionClosed;

        /// <summary>Gets whether the transport is connected.</summary>
        public bool IsConnected => _connected;

        /// <summary>Creates a base transport with optional configuration.</summary>
        protected BaseTransport(TransportConfig? config = null)
        {
            _config = config ?? new TransportConfig();
        }

        /// <summary>Connects to the transport endpoint.</summary>
        public abstract Task ConnectAsync();
        /// <summary>Disconnects from the transport endpoint.</summary>
        public abstract Task DisconnectAsync();

        /// <summary>
        /// Send data through the transport.
        /// Serialized with a SemaphoreSlim to prevent concurrent writes
        /// from corrupting the underlying stream.
        /// <para>
        /// Thread-safe: multiple callers may invoke SendAsync concurrently;
        /// each write completes atomically (no interleaving). However, the
        /// order in which queued writes execute is not guaranteed. If message
        /// order matters, callers must await each SendAsync sequentially:
        /// <code>
        /// await transport.SendAsync(msg1);  // completes first
        /// await transport.SendAsync(msg2);  // guaranteed after msg1
        /// </code>
        /// </para>
        /// </summary>
        public async Task<int> SendAsync(byte[] data)
        {
            await _sendSemaphore.WaitAsync().ConfigureAwait(false);
            try
            {
                return await SendCoreAsync(new ReadOnlyMemory<byte>(data)).ConfigureAwait(false);
            }
            finally
            {
                _sendSemaphore.Release();
            }
        }

        /// <summary>
        /// Send data through the transport (memory-efficient overload).
        /// Serialized with a SemaphoreSlim to prevent concurrent writes.
        /// </summary>
        public async Task<int> SendAsync(ReadOnlyMemory<byte> data)
        {
            await _sendSemaphore.WaitAsync().ConfigureAwait(false);
            try
            {
                return await SendCoreAsync(data).ConfigureAwait(false);
            }
            finally
            {
                _sendSemaphore.Release();
            }
        }

        /// <summary>
        /// Implement the actual send logic in subclasses.
        /// Called under the send semaphore — only one call executes at a time.
        /// Subclasses that can write directly from a ReadOnlyMemory span avoid a ToArray() copy.
        /// The default overload for byte[] is provided for convenience; prefer overriding this one.
        /// </summary>
        protected virtual Task<int> SendCoreAsync(ReadOnlyMemory<byte> data)
            => SendCoreAsync(data.ToArray());

        /// <summary>
        /// Convenience overload for subclasses that only handle byte[].
        /// Override <see cref="SendCoreAsync(ReadOnlyMemory{byte})"/> to avoid the ToArray allocation.
        /// </summary>
        protected virtual Task<int> SendCoreAsync(byte[] data)
            => throw new NotImplementedException("Override SendCoreAsync(ReadOnlyMemory<byte>) or SendCoreAsync(byte[])");

        /// <summary>Raises data-received events for a byte array.</summary>
        protected void OnDataReceived(byte[] data)
        {
            DataReceivedMemory?.Invoke(this, data);
            DataReceived?.Invoke(this, data);
        }

        /// <summary>Raises data-received events for a memory slice.</summary>
        protected void OnDataReceived(ReadOnlyMemory<byte> data)
        {
            DataReceivedMemory?.Invoke(this, data);
            if (DataReceived != null)
            {
                DataReceived.Invoke(this, ToByteArrayForLegacyEvent(data));
            }
        }

        private static byte[] ToByteArrayForLegacyEvent(ReadOnlyMemory<byte> data)
            => data.ToArray();

        /// <summary>Raises an error event and starts reconnect handling when enabled.</summary>
        protected void OnErrorOccurred(Exception error)
        {
            ErrorOccurred?.Invoke(this, error);
            if (_config.AutoReconnect && _connected)
            {
                _ = AttemptReconnectAsync();
            }
        }

        /// <summary>Raises the connection-closed event and starts reconnect handling when enabled.</summary>
        protected void OnConnectionClosed()
        {
            _connected = false;
            ConnectionClosed?.Invoke(this, EventArgs.Empty);
            if (_config.AutoReconnect)
            {
                _ = AttemptReconnectAsync();
            }
        }

        /// <summary>
        /// Reconnect loop: keeps retrying (honouring ReconnectDelayMs and
        /// MaxReconnectAttempts, 0 = infinite) until the transport reconnects.
        /// Retries are driven by this loop directly — the previous implementation
        /// relied on OnErrorOccurred to re-trigger the next attempt, which never
        /// fired after a close because its gate requires <c>_connected</c>, so
        /// "infinite" reconnects actually stopped after a single attempt.
        /// Guarded so concurrent error/close events start at most one loop.
        /// </summary>
        protected async Task AttemptReconnectAsync()
        {
            if (Interlocked.Exchange(ref _reconnectInProgress, 1) == 1)
            {
                return;
            }

            try
            {
                while (!_connected && !_disposed &&
                       (_config.MaxReconnectAttempts == 0 ||
                        _reconnectAttempts < _config.MaxReconnectAttempts))
                {
                    _reconnectAttempts++;
                    await Task.Delay(_config.ReconnectDelayMs).ConfigureAwait(false);

                    try
                    {
                        await ConnectAsync().ConfigureAwait(false);
                        _reconnectAttempts = 0;
                        return;
                    }
                    catch (Exception ex)
                    {
                        // Report the failed attempt without re-triggering another
                        // reconnect loop through OnErrorOccurred.
                        ErrorOccurred?.Invoke(this, ex);
                    }
                }
            }
            finally
            {
                Interlocked.Exchange(ref _reconnectInProgress, 0);
            }
        }

        /// <summary>
        /// Releases resources used by this transport.
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
                    _sendSemaphore.Dispose();
                }
                _disposed = true;
            }
        }
    }
}
