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
        public int LocalPort { get; set; } = 0;
        public string LocalAddress { get; set; } = "0.0.0.0";
        public string RemoteHost { get; set; } = "127.0.0.1";
        public int RemotePort { get; set; }
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

        public UdpTransport(UdpTransportConfig config) : base(config)
        {
            _udpConfig = config;
        }

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

                // Start receiving
                _ = ReceiveAsync();

                await Task.CompletedTask;
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
            _client?.Close();
            _client?.Dispose();
            _client = null;
            await Task.CompletedTask;
        }

        public override async Task SendAsync(byte[] data)
        {
            if (_client == null || !_connected)
            {
                throw new InvalidOperationException("UDP socket not connected");
            }

            try
            {
                await _client.SendAsync(data, data.Length, _remoteEndpoint);
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        private async Task ReceiveAsync()
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
                    {
                        OnErrorOccurred(ex);
                    }
                    break;
                }
            }
        }
    }
}
