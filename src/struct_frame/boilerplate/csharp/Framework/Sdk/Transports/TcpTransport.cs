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
        public string Host { get; set; } = "localhost";
        public int Port { get; set; }
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

        public TcpTransport(TcpTransportConfig config) : base(config)
        {
            _tcpConfig = config;
            _receiveBuffer = new byte[config.ReceiveBufferSize];
        }

        public override async Task ConnectAsync()
        {
            try
            {
                _client = new TcpClient();
                await _client.ConnectAsync(_tcpConfig.Host, _tcpConfig.Port);
                _stream = _client.GetStream();
                _connected = true;

                // Start receive loop; route any unhandled exception through OnErrorOccurred.
                _ = RunReceiveLoopAsync();
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        public override async Task DisconnectAsync()
        {
            _connected = false;
            _stream?.Close();
            _client?.Close();
            _stream = null;
            _client = null;
            await Task.CompletedTask;
        }

        // Override the ReadOnlyMemory overload for zero-copy sends via NetworkStream.
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

        private async Task RunReceiveLoopAsync()
        {
            try
            {
                await ReceiveLoopAsync();
            }
            catch (Exception ex)
            {
                if (_connected)
                {
                    OnErrorOccurred(ex);
                    OnConnectionClosed();
                }
            }
        }

        private async Task ReceiveLoopAsync()
        {
            while (_connected && _stream != null)
            {
                int bytesRead;
                try
                {
                    bytesRead = await _stream.ReadAsync(_receiveBuffer, 0, _receiveBuffer.Length);
                }
                catch (Exception ex)
                {
                    if (_connected)
                        OnErrorOccurred(ex);
                    break;
                }

                if (bytesRead == 0)
                {
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
