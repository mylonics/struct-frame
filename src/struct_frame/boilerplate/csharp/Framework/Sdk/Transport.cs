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
        public bool AutoReconnect { get; set; } = false;
        public int ReconnectDelayMs { get; set; } = 1000;
        public int MaxReconnectAttempts { get; set; } = 0; // 0 = infinite
    }

    /// <summary>
    /// Verbose send result returned by SDK send methods.
    /// </summary>
    public readonly struct SendResult
    {
        public bool Success { get; }
        public int AttemptedBytes { get; }
        public int BytesWritten { get; }

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
    /// Base transport with common functionality.
    /// Implements IDisposable to clean up the internal send semaphore.
    /// </summary>
    public abstract class BaseTransport : ITransport, IDisposable
    {
        protected bool _connected;
        protected TransportConfig _config;
        protected int _reconnectAttempts;
        private readonly SemaphoreSlim _sendSemaphore = new SemaphoreSlim(1, 1);
        private bool _disposed;

        public event EventHandler<byte[]>? DataReceived;
        public event EventHandler<Exception>? ErrorOccurred;
        public event EventHandler? ConnectionClosed;

        public bool IsConnected => _connected;

        protected BaseTransport(TransportConfig? config = null)
        {
            _config = config ?? new TransportConfig();
        }

        public abstract Task ConnectAsync();
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
                return await SendCoreAsync(data).ConfigureAwait(false);
            }
            finally
            {
                _sendSemaphore.Release();
            }
        }

        /// <summary>
        /// Send data through the transport (memory-efficient overload).
        /// Serialized with a SemaphoreSlim to prevent concurrent writes.
        /// Default implementation converts to array - subclasses should override SendCoreAsync for zero-copy.
        /// </summary>
        public async Task<int> SendAsync(ReadOnlyMemory<byte> data)
        {
            await _sendSemaphore.WaitAsync().ConfigureAwait(false);
            try
            {
                return await SendCoreAsync(data.ToArray()).ConfigureAwait(false);
            }
            finally
            {
                _sendSemaphore.Release();
            }
        }

        /// <summary>
        /// Implement the actual send logic in subclasses.
        /// Called under the send semaphore — only one call executes at a time.
        /// </summary>
        protected abstract Task<int> SendCoreAsync(byte[] data);

        protected void OnDataReceived(byte[] data)
        {
            DataReceived?.Invoke(this, data);
        }

        protected void OnErrorOccurred(Exception error)
        {
            ErrorOccurred?.Invoke(this, error);
            if (_config.AutoReconnect && _connected)
            {
                _ = AttemptReconnectAsync();
            }
        }

        protected void OnConnectionClosed()
        {
            _connected = false;
            ConnectionClosed?.Invoke(this, EventArgs.Empty);
            if (_config.AutoReconnect)
            {
                _ = AttemptReconnectAsync();
            }
        }

        protected async Task AttemptReconnectAsync()
        {
            if (_config.MaxReconnectAttempts > 0 &&
                _reconnectAttempts >= _config.MaxReconnectAttempts)
            {
                return;
            }

            _reconnectAttempts++;
            await Task.Delay(_config.ReconnectDelayMs);

            try
            {
                await ConnectAsync();
                _reconnectAttempts = 0;
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
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
