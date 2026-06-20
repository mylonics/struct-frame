// Serial transports for C#
// Uses System.IO.Ports

#nullable enable

using System;
using System.Threading.Tasks;

namespace StructFrame.Sdk
{
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
                    ReadTimeout = 100,
                    // Set write timeout to prevent indefinite blocking
                    WriteTimeout = 500
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

        protected override async Task<int> SendCoreAsync(byte[] data)
        {
            if (_serialPort == null || !_connected || !_serialPort.IsOpen)
            {
                throw new InvalidOperationException("Serial port not connected");
            }

            try
            {
                // Use synchronous Write in Task.Run — BaseStream.WriteAsync is known to
                // stall on Windows due to unreliable overlapped I/O completion on serial ports.
                await Task.Run(() =>
                {
                    _serialPort.Write(data, 0, data.Length);
                }).ConfigureAwait(false);
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
                if (_readCts != null)
                    await ReadLoopAsync(_readCts.Token);
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

        private async Task ReadLoopAsync(System.Threading.CancellationToken cancellationToken)
        {
            byte[] buffer = new byte[4096];

            // Use synchronous Read on a dedicated thread — BaseStream.ReadAsync
            // uses overlapped I/O that can stall or ignore cancellation on Windows
            // serial ports. LongRunning creates a dedicated thread (not a thread-pool
            // thread) since this loop runs for the entire connection lifetime.
            // The ReadTimeout (100 ms) causes Read to throw TimeoutException
            // periodically, giving us a natural cancellation check.
            await Task.Factory.StartNew(() =>
            {
                while (!cancellationToken.IsCancellationRequested && _serialPort != null && _serialPort.IsOpen)
                {
                    try
                    {
                        int bytesRead = _serialPort.Read(buffer, 0, buffer.Length);

                        if (bytesRead > 0)
                        {
                            // Pass only the valid receive slice; BaseTransport handles legacy
                            // byte[] subscribers by materializing a right-sized copy only when needed.
                            OnDataReceived(new ReadOnlyMemory<byte>(buffer, 0, bytesRead));
                        }
                    }
                    catch (TimeoutException)
                    {
                        // ReadTimeout expired — loop back to check cancellation
                        continue;
                    }
                    catch (OperationCanceledException)
                    {
                        // Expected during disconnect
                        break;
                    }
                    catch (System.IO.IOException)
                    {
                        // Port closed or disconnected
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
            }, cancellationToken, TaskCreationOptions.LongRunning, TaskScheduler.Default).ConfigureAwait(false);
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

                // Start receive loop; route any unhandled exception through OnErrorOccurred.
                _ = RunGenericReceiveLoopAsync();
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

        protected override async Task<int> SendCoreAsync(byte[] data)
        {
            if (!_connected || !_serialPort.IsOpen)
            {
                throw new InvalidOperationException("Serial port not connected");
            }

            try
            {
                await _serialPort.WriteAsync(data);
                return data.Length;
            }
            catch (Exception ex)
            {
                OnErrorOccurred(ex);
                throw;
            }
        }

        private async Task RunGenericReceiveLoopAsync()
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
