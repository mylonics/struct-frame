// UDP Transport implementation using NetCoreServer
// Requires: NetCoreServer NuGet package

#nullable enable

using System;
using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// UDP transport configuration
    /// </summary>
    public class UdpTransportConfig : TransportConfig
    {
        /// <summary>Local UDP port to bind.</summary>
        public int LocalPort { get; set; } = 0;
        /// <summary>Local address to bind.</summary>
        public string LocalAddress { get; set; } = "0.0.0.0";
        /// <summary>Remote host name or IP address.</summary>
        public string RemoteHost { get; set; } = "127.0.0.1";
        /// <summary>Remote UDP port.</summary>
        public int RemotePort { get; set; }
        /// <summary>Whether broadcast datagrams are enabled.</summary>
        public bool EnableBroadcast { get; set; } = false;
    }

    /// <summary>
    /// UDP Transport using NetCoreServer
    /// NOTE: This is a stub implementation. Full implementation requires NetCoreServer package.
    ///
    /// To implement:
    /// 1. Install NetCoreServer NuGet package
    /// 2. Inherit from NetCoreServer.UdpClient
    /// 3. Override OnReceived, OnSent, OnError methods
    ///
    /// Example:
    /// using NetCoreServer;
    ///
    /// public class UdpTransport : UdpClient, ITransport
    /// {
    ///     // Implement transport interface
    ///     protected override void OnReceived(EndPoint endpoint, byte[] buffer, long offset, long size)
    ///     {
    ///         byte[] data = new byte[size];
    ///         Array.Copy(buffer, offset, data, 0, size);
    ///         OnDataReceived(data);
    ///     }
    /// }
    /// </summary>
    public class UdpTransport : BaseTransport
    {
        private readonly UdpTransportConfig _udpConfig;
        private UdpClient? _client;
        private IPEndPoint? _remoteEndpoint;

        /// <summary>Creates a UDP transport with the supplied configuration.</summary>
        public UdpTransport(UdpTransportConfig config) : base(config)
        {
            _udpConfig = config;
        }

        /// <summary>Opens the UDP socket and starts receiving datagrams.</summary>
        public override async Task ConnectAsync()
        {
            try
            {
                _client = new UdpClient(_udpConfig.LocalPort);

                if (_udpConfig.EnableBroadcast)
                {
                    _client.EnableBroadcast = true;
                }

                _remoteEndpoint = new IPEndPoint(
                    IPAddress.Parse(_udpConfig.RemoteHost),
                    _udpConfig.RemotePort
                );

                _connected = true;

                // Start receive loop; route any unhandled exception through OnErrorOccurred.
                _ = RunReceiveLoopAsync();

                await Task.CompletedTask;
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        /// <summary>Stops receiving datagrams and closes the UDP socket.</summary>
        public override async Task DisconnectAsync()
        {
            _connected = false;
            _client?.Close();
            _client?.Dispose();
            _client = null;
            await Task.CompletedTask;
        }

        // UdpClient.SendAsync accepts byte[], so no zero-copy opportunity here.
        /// <summary>Sends framed data as a UDP datagram.</summary>
        protected override async Task<int> SendCoreAsync(ReadOnlyMemory<byte> data)
        {
            if (_client == null || !_connected)
            {
                throw new InvalidOperationException("UDP socket not connected");
            }

            try
            {
                byte[] bytes = data.ToArray();
                await _client.SendAsync(bytes, bytes.Length, _remoteEndpoint);
                return bytes.Length;
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
            while (_connected && _client != null)
            {
                try
                {
                    var result = await _client.ReceiveAsync();
                    OnDataReceived(result.Buffer);
                }
                catch (Exception ex)
                {
                    if (_connected)
                        OnErrorOccurred(ex);
                    break;
                }
            }
        }
    }
}
