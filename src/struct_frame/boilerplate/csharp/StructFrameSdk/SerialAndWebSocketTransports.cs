// WebSocket and Serial transports for C#
// WebSocket requires NetCoreServer package, Serial uses System.IO.Ports

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

    /// <summary>
    /// Serial transport configuration
    /// </summary>
    public class SerialTransportConfig : TransportConfig
    {
        public string PortName { get; set; } = "COM1";
        public int BaudRate { get; set; } = 9600;
        public int DataBits { get; set; } = 8;
        public System.IO.Ports.Parity Parity { get; set; } = System.IO.Ports.Parity.None;
        public System.IO.Ports.StopBits StopBits { get; set; } = System.IO.Ports.StopBits.One;
    }

    /// <summary>
    /// Serial Transport using System.IO.Ports with BaseStream for reliable async reading.
    /// Uses BaseStream.ReadAsync instead of the DataReceived event which is known to be
    /// unreliable with threading issues, missed data, and platform inconsistencies.
    /// </summary>
    public class SerialTransport : BaseTransport
    {
        private readonly SerialTransportConfig _serialConfig;
        private System.IO.Ports.SerialPort? _serialPort;
        private System.Threading.CancellationTokenSource? _readCts;
        private Task? _readTask;

        public SerialTransport(SerialTransportConfig config) : base(config)
        {
            _serialConfig = config;
        }

        public override async Task ConnectAsync()
        {
            try
            {
                _serialPort = new System.IO.Ports.SerialPort
                {
                    PortName = _serialConfig.PortName,
                    BaudRate = _serialConfig.BaudRate,
                    DataBits = _serialConfig.DataBits,
                    Parity = _serialConfig.Parity,
                    StopBits = _serialConfig.StopBits,
                    // Set read timeout to allow cancellation checks
                    ReadTimeout = 100
                };

                _serialPort.Open();
                _connected = true;

                // Start the async read loop using BaseStream
                _readCts = new System.Threading.CancellationTokenSource();
                _readTask = ReadLoopAsync(_readCts.Token);

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

            // Cancel the read loop
            if (_readCts != null)
            {
                _readCts.Cancel();
                try
                {
                    if (_readTask != null)
                    {
                        await _readTask.ConfigureAwait(false);
                    }
                }
                catch (OperationCanceledException)
                {
                    // Expected when cancelling
                }
                _readCts.Dispose();
                _readCts = null;
                _readTask = null;
            }

            if (_serialPort != null)
            {
                if (_serialPort.IsOpen)
                {
                    _serialPort.Close();
                }
                _serialPort.Dispose();
                _serialPort = null;
            }
        }

        public override async Task SendAsync(byte[] data)
        {
            if (_serialPort == null || !_connected || !_serialPort.IsOpen)
            {
                throw new InvalidOperationException("Serial port not connected");
            }

            try
            {
                // Use BaseStream for async write
                await _serialPort.BaseStream.WriteAsync(data, 0, data.Length).ConfigureAwait(false);
                await _serialPort.BaseStream.FlushAsync().ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        private async Task ReadLoopAsync(System.Threading.CancellationToken cancellationToken)
        {
            byte[] buffer = new byte[4096];

            while (!cancellationToken.IsCancellationRequested && _serialPort != null && _serialPort.IsOpen)
            {
                try
                {
                    // Use BaseStream.ReadAsync for reliable async reading
                    int bytesRead = await _serialPort.BaseStream.ReadAsync(buffer, 0, buffer.Length, cancellationToken).ConfigureAwait(false);

                    if (bytesRead > 0)
                    {
                        byte[] data = new byte[bytesRead];
                        Array.Copy(buffer, data, bytesRead);
                        OnDataReceived(data);
                    }
                }
                catch (OperationCanceledException)
                {
                    // Expected during disconnect
                    break;
                }
                catch (System.IO.IOException ex) when (ex.InnerException is OperationCanceledException)
                {
                    // Also expected during disconnect on some platforms
                    break;
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

    /// <summary>
    /// Generic serial interface for mobile applications
    /// Provides abstraction for platform-specific serial implementations (e.g., Xamarin, MAUI)
    /// </summary>
    public interface IGenericSerialPort
    {
        Task<bool> OpenAsync();
        Task CloseAsync();
        Task<int> WriteAsync(byte[] data);
        Task<byte[]> ReadAsync();
        bool IsOpen { get; }
    }

    /// <summary>
    /// Generic Serial Transport for mobile/cross-platform scenarios
    /// </summary>
    public class GenericSerialTransport : BaseTransport
    {
        private readonly IGenericSerialPort _serialPort;

        public GenericSerialTransport(IGenericSerialPort serialPort, TransportConfig? config = null)
            : base(config)
        {
            _serialPort = serialPort;
        }

        public override async Task ConnectAsync()
        {
            try
            {
                bool success = await _serialPort.OpenAsync();
                if (!success)
                {
                    throw new Exception("Failed to open serial port");
                }
                _connected = true;

                // Start receive loop
                _ = ReceiveLoopAsync();
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
            if (_serialPort.IsOpen)
            {
                await _serialPort.CloseAsync();
            }
        }

        public override async Task SendAsync(byte[] data)
        {
            if (!_connected || !_serialPort.IsOpen)
            {
                throw new InvalidOperationException("Serial port not connected");
            }

            try
            {
                await _serialPort.WriteAsync(data);
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        private async Task ReceiveLoopAsync()
        {
            while (_connected && _serialPort.IsOpen)
            {
                try
                {
                    byte[] data = await _serialPort.ReadAsync();
                    if (data != null && data.Length > 0)
                    {
                        OnDataReceived(data);
                    }
                    await Task.Delay(10); // Small delay to prevent tight loop
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
