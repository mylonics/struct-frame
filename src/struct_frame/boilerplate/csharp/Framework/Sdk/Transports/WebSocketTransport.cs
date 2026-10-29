// WebSocket transport for C#
// Requires NetCoreServer package

#nullable enable

using System;
using System.Net;
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
        /// <summary>WebSocket endpoint URL (<c>ws://host:port/path</c>).</summary>
        public string Url { get; set; } = "ws://localhost:8080";
        /// <summary>Connection timeout in milliseconds, covering the TCP connect and the WebSocket handshake.</summary>
        public int TimeoutMs { get; set; } = 5000;
    }

#if NETCORESERVER_AVAILABLE
    /// <summary>
    /// WebSocket transport implementation backed by NetCoreServer.
    /// Requires the NetCoreServer package and the <c>NETCORESERVER_AVAILABLE</c> compilation symbol.
    /// Only plain <c>ws://</c> endpoints are supported.
    /// </summary>
    public class WebSocketTransport : WsClient, ITransport, IBufferReceiveTransport
    {
        private readonly WebSocketTransportConfig _wsConfig;
        private readonly string _path;
        private readonly string _hostHeader;
        private volatile bool _connected;
        private TaskCompletionSource<bool>? _handshake;

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
        /// <summary>Gets whether the WebSocket handshake has completed and the link is up.</summary>
        public new bool IsConnected => _connected;

        /// <summary>Creates a WebSocket transport for an IP address, port and request path.</summary>
        public WebSocketTransport(WebSocketTransportConfig config, string address, int port, string path = "/")
            : this(config, address, port, path, $"{address}:{port}")
        {
        }

        /// <summary>Creates a WebSocket transport for <see cref="WebSocketTransportConfig.Url"/>.</summary>
        public WebSocketTransport(WebSocketTransportConfig config)
            : this(config, ResolveAddress(ParseUrl(config.Url)), ParseUrl(config.Url).Port,
                   ParseUrl(config.Url).PathAndQuery, ParseUrl(config.Url).Authority)
        {
        }

        private WebSocketTransport(WebSocketTransportConfig config, string address, int port, string path, string hostHeader)
            : base(address, port)
        {
            _wsConfig = config;
            _path = string.IsNullOrEmpty(path) ? "/" : path;
            _hostHeader = hostHeader;
        }

        private static Uri ParseUrl(string url)
        {
            var uri = new Uri(url);
            if (uri.Scheme != "ws")
                throw new NotSupportedException($"WebSocketTransport supports ws:// URLs only, not '{uri.Scheme}://'");
            return uri;
        }

        private static string ResolveAddress(Uri uri)
        {
            if (IPAddress.TryParse(uri.Host, out _)) return uri.Host;
            return Dns.GetHostAddresses(uri.DnsSafeHost)[0].ToString();
        }

        // These three are `new` rather than `override`: the NetCoreServer base
        // methods differ only by return type (bool vs Task), which C# cannot override.
        /// <summary>
        /// Connects and completes the WebSocket handshake. Throws if the TCP connection fails or the
        /// handshake does not complete within <see cref="WebSocketTransportConfig.TimeoutMs"/>.
        /// </summary>
        public new async Task ConnectAsync()
        {
            var handshake = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            _handshake = handshake;
            // NetCoreServer only runs its receive loop for asynchronous connects; the synchronous
            // Connect() would never read the handshake response (or any later message).
            if (!base.ConnectAsync())
            {
                var error = new InvalidOperationException($"WebSocket: could not start connecting to {Address}:{Port}");
                ErrorOccurred?.Invoke(this, error);
                throw error;
            }
            var finished = await Task.WhenAny(handshake.Task, Task.Delay(_wsConfig.TimeoutMs));
            if (finished != handshake.Task || !handshake.Task.Result)
            {
                base.DisconnectAsync();
                var error = new TimeoutException($"WebSocket connection to {_hostHeader}{_path} failed or timed out");
                ErrorOccurred?.Invoke(this, error);
                throw error;
            }
        }

        /// <summary>Disconnects from the WebSocket endpoint.</summary>
        public new async Task DisconnectAsync()
        {
            _connected = false;
            base.DisconnectAsync();
            await Task.CompletedTask;
        }

        /// <summary>Reports socket errors (including a refused connection).</summary>
        protected override void OnError(System.Net.Sockets.SocketError error)
        {
            _handshake?.TrySetResult(false);
            ErrorOccurred?.Invoke(this, new System.Net.Sockets.SocketException((int)error));
        }

        /// <summary>Sends a byte-array message through the WebSocket.</summary>
        public new async Task<int> SendAsync(byte[] data)
        {
            if (!_connected)
                throw new InvalidOperationException("WebSocket not connected");
            SendBinary(data);
            await Task.CompletedTask;
            return data.Length;
        }

        /// <summary>Sends a memory message through the WebSocket.</summary>
        public async Task<int> SendAsync(ReadOnlyMemory<byte> data)
        {
            return await SendAsync(data.ToArray());
        }

        /// <summary>Builds the HTTP upgrade request NetCoreServer sends after the TCP connect.</summary>
        public override void OnWsConnecting(HttpRequest request)
        {
            request.SetBegin("GET", _path);
            request.SetHeader("Host", _hostHeader);
            request.SetHeader("Origin", "http://" + _hostHeader);
            request.SetHeader("Upgrade", "websocket");
            request.SetHeader("Connection", "Upgrade");
            request.SetHeader("Sec-WebSocket-Key", Convert.ToBase64String(WsNonce));
            request.SetHeader("Sec-WebSocket-Version", "13");
            request.SetBody();
        }

        /// <summary>Handles a successful WebSocket handshake.</summary>
        public override void OnWsConnected(HttpResponse response)
        {
            _connected = true;
            _handshake?.TrySetResult(true);
        }

        /// <summary>Handles WebSocket disconnection.</summary>
        public override void OnWsDisconnected()
        {
            bool wasConnected = _connected;
            _connected = false;
            _handshake?.TrySetResult(false);
            if (wasConnected)
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
