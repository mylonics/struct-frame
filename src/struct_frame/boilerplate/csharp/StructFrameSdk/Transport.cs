// Transport interface for C# struct-frame SDK
// Provides abstraction for various communication channels

#nullable enable

using System;
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
        /// Send data through the transport
        /// </summary>
        Task SendAsync(byte[] data);

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
    /// Base transport with common functionality
    /// </summary>
    public abstract class BaseTransport : ITransport
    {
        protected bool _connected;
        protected TransportConfig _config;
        protected int _reconnectAttempts;

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
        public abstract Task SendAsync(byte[] data);

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
    }
}
