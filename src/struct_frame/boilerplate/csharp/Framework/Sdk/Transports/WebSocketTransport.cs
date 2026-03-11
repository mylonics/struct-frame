// WebSocket transport for C#
// Requires NetCoreServer package

#nullable enable

using System;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
    /// <summary>
    /// WebSocket transport configuration
    /// </summary>
    public class WebSocketTransportConfig : TransportConfig
    {
        public string Url { get; set; } = "ws://localhost:8080";
        public int TimeoutMs { get; set; } = 5000;
    }

#if NETCORESERVER_AVAILABLE
    // WebSocket Transport implementation
    // This code is only compiled when NetCoreServer package is available
    // To use: Install NetCoreServer NuGet package and define NETCORESERVER_AVAILABLE
    using NetCoreServer;

    public class WebSocketTransport : WsClient, ITransport
    {
        private readonly WebSocketTransportConfig _wsConfig;
        private bool _connected;

        public event EventHandler<byte[]> DataReceived;
        public event EventHandler<Exception> ErrorOccurred;
        public event EventHandler ConnectionClosed;

        public bool IsConnected => _connected;

        public WebSocketTransport(WebSocketTransportConfig config, string address, int port, string path = "/")
            : base(address, port)
        {
            _wsConfig = config;
        }

        public async Task ConnectAsync()
        {
            await Task.Run(() => Connect());
            _connected = IsConnected;
        }

        public async Task DisconnectAsync()
        {
            Disconnect();
            _connected = false;
            await Task.CompletedTask;
        }

        public async Task SendAsync(byte[] data)
        {
            SendBinary(data);
            await Task.CompletedTask;
        }

        protected override void OnWsConnected(HttpResponse response)
        {
            _connected = true;
        }

        protected override void OnWsDisconnected()
        {
            _connected = false;
            ConnectionClosed?.Invoke(this, EventArgs.Empty);
        }

        protected override void OnWsReceived(byte[] buffer, long offset, long size)
        {
            byte[] data = new byte[size];
            Array.Copy(buffer, offset, data, 0, size);
            DataReceived?.Invoke(this, data);
        }

        protected override void OnWsError(string error)
        {
            ErrorOccurred?.Invoke(this, new Exception(error));
        }
    }
#endif
}
