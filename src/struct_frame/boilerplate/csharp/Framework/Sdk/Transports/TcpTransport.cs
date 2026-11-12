// TCP Transport implementation using NetCoreServer
// Requires: NetCoreServer NuGet package

#nullable enable

using System;
using System.Net.Sockets;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// TCP transport configuration
    /// </summary>
    public class TcpTransportConfig : TransportConfig
    {
        /// <summary>Remote host name or IP address.</summary>
        public string Host { get; set; } = "localhost";
        /// <summary>Remote TCP port.</summary>
        public int Port { get; set; }
        /// <summary>Connection timeout in milliseconds.</summary>
        public int TimeoutMs { get; set; } = 5000;
        /// <summary>
        /// Size of the pre-allocated receive buffer. Larger buffers reduce allocation
        /// frequency but use more memory. Default is 4096 bytes.
        /// </summary>
        public int ReceiveBufferSize { get; set; } = 4096;
    }

    /// <summary>
    /// TCP Transport using NetCoreServer
    /// NOTE: This is a stub implementation. Full implementation requires NetCoreServer package.
    ///
    /// To implement:
    /// 1. Install NetCoreServer NuGet package
    /// 2. Inherit from NetCoreServer.TcpClient
    /// 3. Override OnConnected, OnDisconnected, OnReceived, OnError methods
    ///
    /// Example:
    /// using NetCoreServer;
    ///
    /// public class TcpTransport : TcpClient, ITransport
    /// {
    ///     protected override void OnReceived(byte[] buffer, long offset, long size)
    ///     {
    ///         byte[] data = new byte[size];
    ///         Array.Copy(buffer, offset, data, 0, size);
    ///         OnDataReceived(data);
    ///     }
    /// }
    /// </summary>
    public class TcpTransport : BaseTransport
    {
        private readonly TcpTransportConfig _tcpConfig;
        private TcpClient? _client;
        private NetworkStream? _stream;
        // Pre-allocated receive buffer to reduce allocation in receive loop
        private readonly byte[] _receiveBuffer;

        /// <summary>Creates a TCP transport with the supplied configuration.</summary>
        public TcpTransport(TcpTransportConfig config) : base(config)
        {
            _tcpConfig = config;
            _receiveBuffer = new byte[config.ReceiveBufferSize];
        }

        /// <summary>Connects to the configured TCP endpoint and starts receiving data.</summary>
        public override async Task ConnectAsync()
        {
            _disconnectRequested = false;
            try
            {
                _client = new TcpClient();
                await _client.ConnectAsync(_tcpConfig.Host, _tcpConfig.Port);
                _stream = _client.GetStream();
                _connected = true;

                // Start receive loop; route any unhandled exception through OnErrorOccurred.
                _ = RunReceiveLoopAsync(_stream);
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        /// <summary>Stops receiving data and closes the TCP connection.</summary>
        public override async Task DisconnectAsync()
        {
            // Set before closing: on Linux the pending read then completes with 0 bytes,
            // which must not be mistaken for the peer closing the connection.
            _disconnectRequested = true;
            _connected = false;
            _stream?.Close();
            _client?.Close();
            _stream = null;
            _client = null;
            await Task.CompletedTask;
        }

        // Override the ReadOnlyMemory overload for zero-copy sends via NetworkStream.
        /// <summary>Sends framed data through the TCP connection.</summary>
        protected override async Task<int> SendCoreAsync(ReadOnlyMemory<byte> data)
        {
            if (_stream == null || !_connected)
            {
                throw new InvalidOperationException("TCP socket not connected");
            }

            try
            {
                await _stream.WriteAsync(data);
                await _stream.FlushAsync();
                return data.Length;
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        // A receive loop belongs to one connection: it only reports a close or an error while
        // its stream is still the current one and no disconnect was requested. Otherwise a
        // local DisconnectAsync, or a loop left over from a previous connection, would be
        // reported as the peer dropping the link (and trigger AutoReconnect).
        private bool IsCurrent(NetworkStream stream)
            => _connected && !_disconnectRequested && ReferenceEquals(_stream, stream);

        private async Task RunReceiveLoopAsync(NetworkStream stream)
        {
            try
            {
                await ReceiveLoopAsync(stream);
            }
            catch (Exception ex)
            {
                if (IsCurrent(stream))
                {
                    OnErrorOccurred(ex);
                    OnConnectionClosed();
                }
            }
        }

        private async Task ReceiveLoopAsync(NetworkStream stream)
        {
            while (IsCurrent(stream))
            {
                int bytesRead;
                try
                {
                    bytesRead = await stream.ReadAsync(_receiveBuffer, 0, _receiveBuffer.Length);
                }
                catch (Exception ex)
                {
                    // A read error (e.g. connection reset) ends the connection too.
                    if (IsCurrent(stream))
                    {
                        OnErrorOccurred(ex);
                        OnConnectionClosed();
                    }
                    break;
                }

                if (bytesRead == 0)
                {
                    if (IsCurrent(stream))
                        OnConnectionClosed();
                    break;
                }

                // Pass only the valid receive slice; BaseTransport handles legacy
                // byte[] subscribers by materializing a right-sized copy only when needed.
                OnDataReceived(new ReadOnlyMemory<byte>(_receiveBuffer, 0, bytesRead));
            }
        }
    }
}
