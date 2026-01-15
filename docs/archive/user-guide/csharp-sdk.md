# C# SDK

The C# SDK provides an async/await-based interface for structured message communication using .NET Standard 2.0+.

## Features

- **Async/await**: Modern C# asynchronous patterns
- **Event-based**: Standard .NET event model for messages
- **Cross-platform**: Works on .NET Core, .NET 5+, Xamarin, MAUI
- **Mobile-friendly**: Generic serial interface for mobile apps

## Installation

Generate C# code with SDK:

```bash
python -m struct_frame your_messages.proto --build_csharp --csharp_path generated/csharp --sdk
```

**Note**: The SDK is not included by default. Use the `--sdk` flag to generate SDK files.

## Available Transports

### UDP Transport

Uses standard `UdpClient`:

```csharp
using StructFrame.Sdk;

var transport = new UdpTransport(new UdpTransportConfig
{
    RemoteHost = "192.168.1.100",
    RemotePort = 5000,
    LocalPort = 5001,
    LocalAddress = "0.0.0.0",
    EnableBroadcast = false,
    AutoReconnect = true,
    ReconnectDelayMs = 1000,
    MaxReconnectAttempts = 5,
});
```

### TCP Transport

Uses standard `TcpClient`:

```csharp
var transport = new TcpTransport(new TcpTransportConfig
{
    Host = "192.168.1.100",
    Port = 5000,
    TimeoutMs = 5000,
    AutoReconnect = true,
});
```

### WebSocket Transport

Requires `NetCoreServer` NuGet package:

```csharp
var transport = new WebSocketTransport(new WebSocketTransportConfig
{
    Url = "ws://localhost:8080",
    TimeoutMs = 5000,
});
```

### Serial Transport

Uses `System.IO.Ports.SerialPort`:

```csharp
var transport = new SerialTransport(new SerialTransportConfig
{
    PortName = "COM3",  // or "/dev/ttyUSB0" on Linux
    BaudRate = 115200,
    DataBits = 8,
    Parity = System.IO.Ports.Parity.None,
    StopBits = System.IO.Ports.StopBits.One,
});
```

### Generic Serial Transport (Mobile)

For Xamarin/MAUI applications, implement `IGenericSerialPort`:

```csharp
// Your platform-specific implementation
public class XamarinSerialPort : IGenericSerialPort
{
    // Implement serial I/O for your platform
}

var serialPort = new XamarinSerialPort();
var transport = new GenericSerialTransport(serialPort);
```

## SDK Usage

### Using Parsers

The generated frame parsers handle the low-level framing and message extraction:

```csharp
using StructFrame;

// Basic frame parser (includes length and CRC)
var parser = new BasicDefaultParser();

// Parse incoming bytes
foreach (byte b in incomingData)
{
    var result = parser.ParseByte(b);
    if (result.Valid)
    {
        Console.WriteLine($"Received msg_id={result.MsgId}, len={result.MsgLen}");
        // Process result.MsgData
    }
}

// Encode a message
var msgData = new byte[] {1, 2, 3, 4, 5};
var frame = parser.Encode(42, msgData);
```

### Parsing Minimal Frames

Minimal frames don't include a length field or CRC. To parse them, provide a callback function that returns the expected message length for each message ID:

**Note**: Verify the exact API signature in your generated parser code. The callback parameter may vary.

```csharp
using StructFrame;

// Define message size lookup
int? GetMsgLength(int msgId)
{
    return msgId switch
    {
        1 => 10,  // Status message is 10 bytes
        2 => 20,  // Command message is 20 bytes
        3 => 5,   // Sensor reading is 5 bytes
        _ => null
    };
}

// Create parser with callback
// The exact constructor signature depends on generated code
var parser = new TinyMinimalParser(GetMsgLength);

// Parse bytes
foreach (byte b in incomingData)
{
    var result = parser.ParseByte(b);
    if (result.Valid)
    {
        Console.WriteLine($"Minimal frame: msg_id={result.MsgId}, len={result.MsgLen}");
    }
}

// Encode minimal frame
var data = new byte[] {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
var frame = parser.Encode(1, data);
// Result: [0x70] [0x01] [0x01 0x02 ... 0x0A]
```

**When to use minimal frames:**
- ✅ Fixed-size messages on trusted links
- ✅ Bandwidth-constrained (LoRa, RF)
- ✅ Minimal overhead (1-3 bytes)
- ❌ No error detection (no CRC)

See the [Minimal Frames Guide](minimal-frames.md) for complete details.

## Profile-Based Parsing API

The C# SDK provides high-performance parsing classes that match the C++ gold standard implementation. These are optimized for specific frame profiles and provide convenient factory methods.

### Available Profiles

| Profile | Header | Payload | Use Case |
|---------|--------|---------|----------|
| `ProfileStandard` | Basic | Default | General serial/UART communication |
| `ProfileSensor` | Tiny | Minimal | Low-bandwidth sensors, radio links |
| `ProfileIPC` | None | Minimal | Trusted inter-process communication |
| `ProfileBulk` | Basic | Extended | Firmware/file transfers |
| `ProfileNetwork` | Basic | ExtendedMultiSystemStream | Multi-node mesh networks |

### BufferReader - Parse Multiple Frames from a Buffer

`BufferReader` iterates through a buffer containing one or more frames, automatically tracking the offset:

```csharp
using StructFrame;

// Parse a buffer containing multiple ProfileStandard frames
var reader = FrameProfiles.CreateProfileStandardReader(bufferData);
while (reader.HasMore())
{
    var result = reader.Next();
    if (!result.Valid) break;
    Console.WriteLine($"Message ID: {result.MsgId}, Length: {result.MsgLen}");
    ProcessMessage(result.MsgData);
}

Console.WriteLine($"Processed {reader.Offset} bytes, {reader.Remaining} remaining");
```

For minimal profiles (no length field), provide a message length callback:

```csharp
// Parse ProfileSensor frames (minimal payload)
var reader = FrameProfiles.CreateProfileSensorReader(bufferData, GetMessageLength);
while (reader.HasMore())
{
    var result = reader.Next();
    if (result.Valid)
    {
        ProcessMessage(result.MsgId, result.MsgData);
    }
}

int? GetMessageLength(int msgId)
{
    return msgId switch
    {
        1 => 10,  // Status message
        2 => 20,  // Command message
        _ => null
    };
}
```

### BufferWriter - Encode Multiple Frames

`BufferWriter` encodes multiple frames into a buffer with automatic offset tracking:

```csharp
using StructFrame;

// Create writer with capacity
var writer = FrameProfiles.CreateProfileStandardWriter(4096);

// Write multiple messages
writer.Write(1, msg1Data);
writer.Write(2, msg2Data);
writer.Write(3, msg3Data);

// Get the encoded data
var encodedBuffer = writer.Data();
Console.WriteLine($"Encoded {writer.Size} bytes with {writer.Count} messages");
```

For network profiles with extra header fields:

```csharp
var writer = FrameProfiles.CreateProfileNetworkWriter(4096);
writer.Write(1, data, seq: 1, sysId: 10, compId: 1);
```

### AccumulatingReader - Unified Buffer and Streaming Parser

`AccumulatingReader` handles both buffer mode and byte-by-byte streaming, with support for partial messages across buffer boundaries:

**Buffer Mode** - Processing chunks of data:

```csharp
using StructFrame;

var reader = FrameProfiles.CreateProfileStandardAccumulatingReader();

// Process incoming chunks (e.g., from network or file)
reader.AddData(chunk1);
while (true)
{
    var result = reader.Next();
    if (!result.Valid) break;
    ProcessMessage(result.MsgId, result.MsgData);
}

// Add more data (handles partial messages automatically)
reader.AddData(chunk2);
while (true)
{
    var result = reader.Next();
    if (!result.Valid) break;
    ProcessMessage(result.MsgId, result.MsgData);
}
```

**Stream Mode** - Byte-by-byte processing (UART/serial):

```csharp
using StructFrame;

var reader = FrameProfiles.CreateProfileSensorAccumulatingReader(GetMessageLength);

// Process incoming bytes one at a time
serialPort.DataReceived += (sender, e) =>
{
    while (serialPort.BytesToRead > 0)
    {
        var b = (byte)serialPort.ReadByte();
        var result = reader.PushByte(b);
        if (result.Valid)
        {
            // Complete message received
            ProcessMessage(result.MsgId, result.MsgData);
        }
    }
};
```

### Factory Methods

All profiles have factory methods for creating readers and writers:

```csharp
using StructFrame;

// BufferReader factories
var reader = FrameProfiles.CreateProfileStandardReader(buffer);
var reader = FrameProfiles.CreateProfileSensorReader(buffer, getMsgLength);
var reader = FrameProfiles.CreateProfileIPCReader(buffer, getMsgLength);
var reader = FrameProfiles.CreateProfileBulkReader(buffer);
var reader = FrameProfiles.CreateProfileNetworkReader(buffer);

// BufferWriter factories
var writer = FrameProfiles.CreateProfileStandardWriter(capacity);
var writer = FrameProfiles.CreateProfileSensorWriter(capacity);
var writer = FrameProfiles.CreateProfileIPCWriter(capacity);
var writer = FrameProfiles.CreateProfileBulkWriter(capacity);
var writer = FrameProfiles.CreateProfileNetworkWriter(capacity);

// AccumulatingReader factories
var reader = FrameProfiles.CreateProfileStandardAccumulatingReader();
var reader = FrameProfiles.CreateProfileSensorAccumulatingReader(getMsgLength);
var reader = FrameProfiles.CreateProfileIPCAccumulatingReader(getMsgLength);
var reader = FrameProfiles.CreateProfileBulkAccumulatingReader();
var reader = FrameProfiles.CreateProfileNetworkAccumulatingReader();
```

### Creating the SDK

```csharp

### Generated SDK Interface

When using the `--sdk` or `--sdk_embedded` flag, struct-frame generates a high-level SDK interface for each package that provides type-safe methods for sending messages. This interface eliminates boilerplate code and provides two convenient ways to send each message type.

#### Features

- **Type-safe send methods**: One method per message type
- **Two overloads**: Send with individual fields or with a complete struct
- **Automatic framing**: Messages are automatically serialized and framed
- **Frame parser integration**: Works with any generated frame parser

#### Example

For a message defined as:

```proto
package robot_messages;

message RobotCommand {
  option msgid = 1;
  uint8 command_type = 1;
  float speed = 2;
  float direction = 3;
}
```

The generated SDK interface provides:

```csharp
using StructFrame.RobotMessages;
using StructFrame.RobotMessages.Sdk;

// Create SDK interface with a frame parser and send function
var frameParser = new BasicDefault();
var sdkInterface = new RobotMessagesSdkInterface(
    frameParser,
    transport.SendAsync  // or any Func<byte[], Task>
);

// Option 1: Send with individual field values
await sdkInterface.SendRobotCommand(
    commandType: 1,
    speed: 5.0f,
    direction: 90.0f
);

// Option 2: Send with complete struct
var cmd = new RobotMessagesRobotCommand
{
    CommandType = 1,
    Speed = 5.0f,
    Direction = 90.0f,
};
await sdkInterface.SendRobotCommand(cmd);
```

#### Integration with StructFrameSdk

The SDK interface works seamlessly with the main `StructFrameSdk`:

```csharp
using StructFrame.Sdk;
using StructFrame.RobotMessages.Sdk;

// Create and configure SDK
var sdk = new StructFrameSdk(new StructFrameSdkConfig
{
    Transport = transport,
    FrameParser = new BasicDefault(),
    Debug = true,
});

await sdk.ConnectAsync();

// Create SDK interface using the same frame parser and transport
var sdkInterface = new RobotMessagesSdkInterface(
    new BasicDefault(),  // Same frame parser
    async (bytes) => await transport.SendAsync(bytes)
);

// Send using SDK interface
await sdkInterface.SendRobotCommand(1, 5.0f, 90.0f);

// Receive using standard SDK subscription
sdk.Subscribe<RobotCommand>(RobotCommand.MsgId, (msg, id) =>
{
    Console.WriteLine($"Command: {msg.CommandType}, Speed: {msg.Speed}");
});
```

### Creating the SDK

```csharp
using StructFrame.Sdk;

var sdk = new StructFrameSdk(new StructFrameSdkConfig
{
    Transport = transport,
    FrameParser = new BasicDefault(),
    Debug = true,
});
```

### Connecting and Disconnecting

```csharp
// Connect
await sdk.ConnectAsync();

// Check connection status
if (sdk.IsConnected)
{
    Console.WriteLine("Connected!");
}

// Disconnect
await sdk.DisconnectAsync();
```

### Subscribing to Messages

```csharp
using RobotMessages;

// Subscribe to messages
Action unsubscribe = sdk.Subscribe<StatusMessage>(
    StatusMessage.MsgId,
    (message, msgId) =>
    {
        Console.WriteLine($"Temperature: {message.Temperature}°C");
        Console.WriteLine($"Battery: {message.Battery}%");
    }
);

// Unsubscribe when done
unsubscribe();
```

### Sending Messages

```csharp
using RobotMessages;

// Create and send message
var cmd = new CommandMessage
{
    Command = "MOVE_FORWARD",
    Speed = 50,
};

await sdk.SendAsync(cmd);

// Or send raw bytes
byte[] rawData = new byte[] { 1, 2, 3, 4 };
await sdk.SendRawAsync(CommandMessage.MsgId, rawData);
```

### Automatic Message Deserialization

Register codecs for automatic deserialization:

```csharp
// Create a codec wrapper
public class StatusMessageCodec : IMessageCodec<StatusMessage>
{
    public byte MsgId => StatusMessage.MsgId;
    
    public StatusMessage Deserialize(byte[] data)
    {
        return StatusMessage.CreateUnpack(data);
    }
}

sdk.RegisterCodec(new StatusMessageCodec());

// Now messages are automatically deserialized
sdk.Subscribe<StatusMessage>(StatusMessage.MsgId, (message, msgId) =>
{
    // message is already a StatusMessage instance
    Console.WriteLine(message);
});
```

## Complete Example

```csharp
using System;
using System.Threading.Tasks;
using StructFrame.Sdk;
using RobotMessages;

public class RobotClient
{
    public static async Task Main(string[] args)
    {
        // Create transport
        var transport = new TcpTransport(new TcpTransportConfig
        {
            Host = "localhost",
            Port = 8080,
            AutoReconnect = true,
            ReconnectDelayMs = 2000,
            MaxReconnectAttempts = 10,
        });

        // Create SDK
        var sdk = new StructFrameSdk(new StructFrameSdkConfig
        {
            Transport = transport,
            FrameParser = new BasicDefault(),
            Debug = true,
        });

        // Subscribe to status messages
        sdk.Subscribe<StatusMessage>(StatusMessage.MsgId, (msg, id) =>
        {
            Console.WriteLine($"[Status] Temp: {msg.Temperature}°C, Battery: {msg.Battery}%");
        });

        // Connect
        await sdk.ConnectAsync();
        Console.WriteLine("Connected to robot");

        // Send command
        var cmd = new CommandMessage
        {
            Command = "MOVE_FORWARD",
            Speed = 50,
        };
        await sdk.SendAsync(cmd);

        // Handle errors
        transport.ErrorOccurred += (sender, error) =>
        {
            Console.WriteLine($"Transport error: {error.Message}");
        };

        // Handle close
        transport.ConnectionClosed += (sender, args) =>
        {
            Console.WriteLine("Connection closed");
        };

        // Keep alive
        Console.WriteLine("Press Ctrl+C to exit");
        await Task.Delay(-1);
    }
}
```

## ASP.NET Core Integration

Integrate with ASP.NET Core dependency injection:

```csharp
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

public class Startup
{
    public void ConfigureServices(IServiceCollection services)
    {
        // Register transport
        services.AddSingleton<ITransport>(sp =>
        {
            return new TcpTransport(new TcpTransportConfig
            {
                Host = "localhost",
                Port = 8080,
            });
        });

        // Register SDK
        services.AddSingleton<StructFrameSdk>(sp =>
        {
            var transport = sp.GetRequiredService<ITransport>();
            return new StructFrameSdk(new StructFrameSdkConfig
            {
                Transport = transport,
                FrameParser = new BasicDefault(),
            });
        });

        // Register as hosted service
        services.AddHostedService<RobotService>();
    }
}

public class RobotService : BackgroundService
{
    private readonly StructFrameSdk _sdk;

    public RobotService(StructFrameSdk sdk)
    {
        _sdk = sdk;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await _sdk.ConnectAsync();

        // Subscribe to messages
        _sdk.Subscribe<StatusMessage>(StatusMessage.MsgId, HandleStatus);

        // Wait for cancellation
        await Task.Delay(-1, stoppingToken);
        
        await _sdk.DisconnectAsync();
    }

    private void HandleStatus(StatusMessage msg, byte msgId)
    {
        // Handle status
    }
}
```

## Xamarin/MAUI Example

```csharp
using Xamarin.Forms;
using StructFrame.Sdk;

public class RobotPage : ContentPage
{
    private StructFrameSdk _sdk;

    public RobotPage()
    {
        InitializeComponent();
        InitializeSdk();
    }

    private async void InitializeSdk()
    {
        // Platform-specific serial port
        var serialPort = DependencyService.Get<IGenericSerialPort>();
        var transport = new GenericSerialTransport(serialPort);

        _sdk = new StructFrameSdk(new StructFrameSdkConfig
        {
            Transport = transport,
            FrameParser = new BasicDefault(),
        });

        // Subscribe
        _sdk.Subscribe<StatusMessage>(StatusMessage.MsgId, (msg, id) =>
        {
            Device.BeginInvokeOnMainThread(() =>
            {
                // Update UI
                TempLabel.Text = $"{msg.Temperature}°C";
                BatteryLabel.Text = $"{msg.Battery}%";
            });
        });

        await _sdk.ConnectAsync();
    }

    private async void SendCommand_Clicked(object sender, EventArgs e)
    {
        var cmd = new CommandMessage { Command = "START" };
        await _sdk.SendAsync(cmd);
    }
}
```

## Error Handling

```csharp
try
{
    await sdk.ConnectAsync();
}
catch (Exception ex)
{
    Console.WriteLine($"Failed to connect: {ex.Message}");
}

// Event-based error handling
transport.ErrorOccurred += (sender, error) =>
{
    Console.WriteLine($"Transport error: {error.Message}");
};

transport.ConnectionClosed += (sender, args) =>
{
    Console.WriteLine("Connection closed");
};
```

## NuGet Dependencies

### Required
- .NET Standard 2.0+
- System.IO.Ports (for SerialTransport)

### Optional
- NetCoreServer (for WebSocket and enhanced TCP/UDP)

```bash
# Install via NuGet
dotnet add package System.IO.Ports
dotnet add package NetCoreServer
```

## Best Practices

1. **Use async/await consistently**:
   ```csharp
   await sdk.ConnectAsync();
   await sdk.SendAsync(message);
   ```

2. **Dispose properly**:
   ```csharp
   try
   {
       await sdk.ConnectAsync();
       // Use SDK
   }
   finally
   {
       await sdk.DisconnectAsync();
   }
   ```

3. **Handle UI thread marshalling** (Xamarin/WPF/WinForms):
   ```csharp
   sdk.Subscribe<StatusMessage>(StatusMessage.MsgId, (msg, id) =>
   {
       // Xamarin
       Device.BeginInvokeOnMainThread(() => UpdateUI(msg));
       
       // WPF
       Dispatcher.Invoke(() => UpdateUI(msg));
       
       // WinForms
       BeginInvoke(new Action(() => UpdateUI(msg)));
   });
   ```

4. **Use CancellationToken**:
   ```csharp
   public async Task RunAsync(CancellationToken ct)
   {
       await sdk.ConnectAsync();
       
       while (!ct.IsCancellationRequested)
       {
           await Task.Delay(100, ct);
       }
       
       await sdk.DisconnectAsync();
   }
   ```

## Platform-Specific Notes

### .NET Framework
- Requires .NET Framework 4.7.2+ for .NET Standard 2.0 support
- Use `System.IO.Ports` for serial communication

### .NET Core / .NET 5+
- Full support for all features
- Cross-platform serial port support

### Xamarin
- Implement `IGenericSerialPort` for platform-specific serial I/O
- Use `Device.BeginInvokeOnMainThread` for UI updates

### MAUI
- Similar to Xamarin, use platform-specific implementations
- Use `MainThread.BeginInvokeOnMainThread` for UI updates

### UWP
- Serial port access requires capabilities in Package.appxmanifest
- Limited network socket support (use UWP-specific APIs)
