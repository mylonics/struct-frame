// WebSocket transport for C#
// Requires NetCoreServer package

#nullable enable

using System;
using System.Threading.Tasks;
#if NETCORESERVER_AVAILABLE
// Must sit with the other using directives: C# rejects a using that follows a
// type declaration inside a namespace (CS1529).
using NetCoreServer;
#endif

namespace StructFrame.Sdk
{
    /// <summary>
    /// WebSocket transport configuration
    /// </summary>
    public class WebSocketTransportConfig : TransportConfig
    {
        /// <summary>WebSocket endpoint URL.</summary>
        public string Url { get; set; } = "ws://localhost:8080";
        /// <summary>Connection timeout in milliseconds.</summary>
        public int TimeoutMs { get; set; } = 5000;
    }

#if NETCORESERVER_AVAILABLE
    /// <summary>
    /// WebSocket transport implementation backed by NetCoreServer.
    /// Requires the NetCoreServer package and the <c>NETCORESERVER_AVAILABLE</c> compilation symbol.
    /// </summary>
    public class WebSocketTransport : WsClient, ITransport, IBufferReceiveTransport
    {
        private readonly WebSocketTransportConfig _wsConfig;
        private bool _connected;

        // Nullable to match BaseTransport in Transport.cs; this class cannot inherit
        // it because it already extends NetCoreServer's WsClient.
        /// <summary>Raised when byte-array data is received.</summary>
        public event EventHandler<byte[]>? DataReceived;
        /// <summary>Raised when memory data is received.</summary>
        public event EventHandler<ReadOnlyMemory<byte>>? DataReceivedMemory;
        /// <summary>Raised when a WebSocket error occurs.</summary>
        public event EventHandler<Exception>? ErrorOccurred;
        /// <summary>Raised when the WebSocket connection closes.</summary>
        public event EventHandler? ConnectionClosed;

        // `new`, not `override`: this tracks the WebSocket handshake, which is a
        // narrower notion than the inherited TcpClient.IsConnected socket state.
        /// <summary>Gets whether the WebSocket handshake is connected.</summary>
        public new bool IsConnected => _connected;

        /// <summary>Creates a WebSocket transport for the supplied endpoint.</summary>
        public WebSocketTransport(WebSocketTransportConfig config, string address, int port, string path = "/")
            : base(address, port)
        {
            _wsConfig = config;
        }

        // These three are `new` rather than `override`: the NetCoreServer base
        // methods differ only by return type (bool vs Task), which C# cannot override.
        /// <summary>Connects to the WebSocket endpoint.</summary>
        public new async Task ConnectAsync()
        {
            await Task.Run(() => Connect());
            _connected = base.IsConnected;
        }

        /// <summary>Disconnects from the WebSocket endpoint.</summary>
        public new async Task DisconnectAsync()
        {
            Disconnect();
            _connected = false;
            await Task.CompletedTask;
        }

        /// <summary>Sends a byte-array message through the WebSocket.</summary>
        public new async Task<int> SendAsync(byte[] data)
        {
            SendBinary(data);
            await Task.CompletedTask;
            return data.Length;
        }

        /// <summary>Sends a memory message through the WebSocket.</summary>
        public async Task<int> SendAsync(ReadOnlyMemory<byte> data)
        {
            byte[] bytes = data.ToArray();
            SendBinary(bytes);
            await Task.CompletedTask;
            return bytes.Length;
        }

        /// <summary>Handles a successful WebSocket connection.</summary>
        public override void OnWsConnected(HttpResponse response)
        {
            _connected = true;
        }

        /// <summary>Handles WebSocket disconnection.</summary>
        public override void OnWsDisconnected()
        {
            _connected = false;
            ConnectionClosed?.Invoke(this, EventArgs.Empty);
        }

        /// <summary>Handles a received WebSocket message.</summary>
        public override void OnWsReceived(byte[] buffer, long offset, long size)
        {
            var memory = new ReadOnlyMemory<byte>(buffer, checked((int)offset), checked((int)size));
            DataReceivedMemory?.Invoke(this, memory);
            if (DataReceived != null)
            {
                DataReceived.Invoke(this, memory.ToArray());
            }
        }

        /// <summary>Handles a WebSocket error.</summary>
        public override void OnWsError(string error)
        {
            ErrorOccurred?.Invoke(this, new Exception(error));
        }
    }
#endif
}
