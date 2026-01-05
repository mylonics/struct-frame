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
