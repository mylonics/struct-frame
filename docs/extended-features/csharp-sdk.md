# C# SDK

The C# SDK provides async/await-based transport layers for .NET applications using C# 11+ static abstract interface members.

## Requirements

- .NET 7.0+ (required for static abstract interface members)
- For serial port support: `System.IO.Ports` NuGet package

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --sdk
```

Generate with auto-generated `.csproj` file for immediate building:

```bash
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --generate_csproj
```

### .csproj Generation Options

The generator can create a `.csproj` file that allows immediate `dotnet build`:

```bash
# Basic .csproj generation (excludes SDK, no dependencies needed)
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --generate_csproj

# With custom namespace
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --generate_csproj --csharp_namespace MyApp.Protocol

# With custom target framework
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --generate_csproj --target_framework net7.0

# Full SDK with .csproj (includes System.IO.Ports dependency)
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --sdk --generate_csproj
```

## Basic Usage

The SDK client uses the unified `FrameProfiles` infrastructure for encoding and parsing:

```csharp
using StructFrame;
using StructFrame.Sdk;

// Configure the SDK with required parameters
var config = new StructFrameSdkConfig(
    transport: new TcpTransport("192.168.1.100", 8080),
    getMessageInfo: MessageDefinitions.GetMessageInfo,
    profile: Profiles.Standard,  // optional, default is Standard
    debug: true                  // optional, default is false
);

var sdk = new StructFrameSdk(config);
await sdk.ConnectAsync();

// Subscribe to messages - type-safe with compile-time dispatch
sdk.Subscribe<SensorDataMessage>(msg => {
    Console.WriteLine($"Sensor value: {msg.Value}, ID: {msg.GetMsgId()}");
});

// Send messages (uses IStructFrameMessage interface)
var command = new CommandMessage { Action = 1 };
await sdk.SendAsync(command);

// Handle unregistered message types
sdk.UnhandledMessage += frame => {
    Console.WriteLine($"Unknown message ID: {frame.MsgId}");
};
```

## Generated SDK Interface

When you generate with `--sdk`, a type-safe `SdkInterface` class is generated for each package. This provides convenience methods for sending and subscribing to specific message types:

```csharp
using StructFrame;
using StructFrame.Sdk;
using StructFrame.MyPackage.Sdk;

// Create the base SDK
var config = new StructFrameSdkConfig(
    transport: new TcpTransport("192.168.1.100", 8080),
    getMessageInfo: MessageDefinitions.GetMessageInfo
);
var sdk = new StructFrameSdk(config);

// Create the package-specific interface
var myPackageSdk = new MyPackageSdkInterface(sdk);

// Type-safe subscribe methods for each message
myPackageSdk.SubscribeSensorData(msg => {
    Console.WriteLine($"Sensor: {msg.Value}");
});

myPackageSdk.SubscribeStatusUpdate(msg => {
    Console.WriteLine($"Status: {msg.Code}");
});

// Type-safe send methods for each message
await myPackageSdk.SendCommand(new MyPackageCommand { Action = 1 });

// Or send with individual field values
await myPackageSdk.SendCommand(action: 1);

// Access underlying SDK for advanced usage
await myPackageSdk.Sdk.ConnectAsync();
```

## Message Interface

Generated messages implement `IStructFrameMessage<T>` which provides:

```csharp
public interface IStructFrameMessage<TSelf> : IStructFrameMessage 
    where TSelf : IStructFrameMessage<TSelf>
{
    /// <summary>
    /// Deserialize a message from frame info (static abstract)
    /// </summary>
    static abstract TSelf Deserialize(FrameMsgInfo frame);
}

public interface IStructFrameMessage
{
    ushort GetMsgId();
    int GetSize();
    byte[] Serialize();
    (byte Magic1, byte Magic2) GetMagicNumbers();
}
```

This enables compile-time dispatch for deserialization without reflection:

```csharp
// The SDK internally calls T.Deserialize(frame) directly
sdk.Subscribe<SensorDataMessage>(msg => {
    // msg is already deserialized - no reflection needed
});
```

## Message Registry

The generated code includes a `MessageDefinitions` class that provides:

### Message Lookup by ID

```csharp
using StructFrame.MyPackage;

// Get message info by ID (required for SDK configuration)
var info = MessageDefinitions.GetMessageInfo(SensorDataMessage.MsgId);
Console.WriteLine($"Size: {info?.Size}, Magic: {info?.Magic1:X2}{info?.Magic2:X2}");
```

### Enumerate All Messages

```csharp
// Get all registered message types
foreach (var entry in MessageDefinitions.GetAllMessages())
{
    Console.WriteLine($"Message: {entry.Name} (ID: {entry.Id}, Size: {entry.MaxSize})");
}
```

## Transports

### TCP

```csharp
using StructFrame.Sdk;

var transport = new TcpTransport("192.168.1.100", 8080);
await transport.ConnectAsync();
await transport.SendAsync(data);
```

### UDP

```csharp
using StructFrame.Sdk;

var transport = new UdpTransport("192.168.1.100", 8080);
await transport.ConnectAsync();
await transport.SendAsync(data);
```

### Serial

```csharp
using StructFrame.Sdk;

var transport = new SerialTransport("COM3", 115200);
await transport.ConnectAsync();
await transport.SendAsync(data);
```

## Async/Await Patterns

```csharp
public async Task RunAsync()
{
    var config = new StructFrameSdkConfig(
        transport: new TcpTransport("localhost", 8080),
        getMessageInfo: MessageDefinitions.GetMessageInfo
    );
    
    var sdk = new StructFrameSdk(config);
    
    sdk.Subscribe<StatusMessage>(HandleStatus);
    
    await sdk.ConnectAsync();
    
    // SDK handles incoming data automatically via transport events
    // Send messages as needed
    await sdk.SendAsync(new CommandMessage { Action = 1 });
}

void HandleStatus(StatusMessage msg)
{
    Console.WriteLine($"Received status: {msg.Code}");
}
```

## .NET Platform Support

The SDK requires .NET 7.0+ due to the use of C# 11 static abstract interface members:

- .NET 7.0+
- .NET 8.0+
- .NET 9.0+

