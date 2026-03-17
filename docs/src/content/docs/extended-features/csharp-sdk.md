---
title: C# SDK
description: C# SDK with async/await-based transport layers for .NET applications.
---

The C# SDK provides async/await-based transport layers for .NET applications using C# 11+ static abstract interface members.

## Requirements

- .NET 7.0+ (required for static abstract interface members)
- For serial port support: `System.IO.Ports` NuGet package
- For network transports: `NetCoreServer` NuGet package

## Installation

Generate C# code (messages, framing, SDK core, and `.csproj`):

```bash
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/
```

Generate with transports (includes Serial, TCP, UDP, WebSocket transport implementations):

```bash
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --csharp_sdk
```

### Generation Options

```bash
# With custom namespace (default: StructFrame)
python -m struct_frame messages.proto --build_csharp --csharp_namespace MyApp.Protocol

# With custom target framework (default: net8.0)
python -m struct_frame messages.proto --build_csharp --target_framework net7.0

# With equality operators
python -m struct_frame messages.proto --build_csharp --equality

# With transports
python -m struct_frame messages.proto --build_csharp --csharp_sdk
```

### Generated Output Structure

```
Generated/
├── StructFrame.csproj              # Always generated
├── Framework/                      # Framing & SDK boilerplate
│   ├── Framing/                    # Frame encoders, parsers, readers, writers
│   ├── Profiles/                   # Frame profiles (Standard, Sensor, IPC, etc.)
│   ├── Sdk/                        # SDK core (StructFrameSdk, Transport base)
│   │   └── Transports/             # Only with --csharp_sdk
│   │       ├── SerialTransport.cs
│   │       ├── TcpTransport.cs
│   │       ├── UdpTransport.cs
│   │       └── WebSocketTransport.cs
│   └── Types/                      # Base types (FrameMsgInfo, IStructFrameMessage, etc.)
└── <PackageName>/                  # One folder per proto package (PascalCase)
    ├── Enums/                      # One file per enum
    ├── Messages/                   # One file per message
    ├── MessageDefinitions.cs       # Message registry
    └── SdkInterface.cs             # Always generated
```

### Transport Compilation

When `--csharp_sdk` is used, transport implementations are copied but excluded from compilation by default in the `.csproj`. Enable them at build time:

```bash
# Serial transport (System.IO.Ports)
dotnet build -p:IncludeSerialTransport=true

# Network transports: TCP, UDP, WebSocket (NetCoreServer)
dotnet build -p:IncludeNetCoreServer=true

# Both
dotnet build -p:IncludeSerialTransport=true -p:IncludeNetCoreServer=true
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

The serial transport uses `System.IO.Ports.SerialPort.BaseStream` for reliable async reading, which is more robust than the event-based `DataReceived` approach.

```csharp
using StructFrame.Sdk;

var config = new SerialTransportConfig
{
    PortName = "COM3",
    BaudRate = 115200,
    DataBits = 8,
    Parity = System.IO.Ports.Parity.None,
    StopBits = System.IO.Ports.StopBits.One
};

var transport = new SerialTransport(config);
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

## Envelope Message Support

When you have envelope messages (messages with `is_envelope = true`), the SDK generates convenient helper methods:

```csharp
using StructFrame.MyPackage.Sdk;

// Create the SDK interface
var sdk = new MyPackageSdkInterface(baseSdk);

// Send a payload wrapped in an envelope - multiple overloads available:

// Overload 1: Pass the message object plus envelope fields
var adcCmd = new ADCCommand { Channel = 1, SampleRate = 1000, Enable = true };
await sdk.SendADCCommandViaCommandEnvelope(adcCmd, sequenceNumber: 42, priority: 1, runImmediately: true);

// Overload 2: Pass all fields flat (payload fields + envelope fields)
await sdk.SendADCCommandViaCommandEnvelope(
    channel: 1,
    sampleRate: 1000,
    enable: true,
    sequenceNumber: 42,
    priority: 1,
    runImmediately: true
);
```

The naming convention is `Send{PayloadType}Via{EnvelopeName}`. This pattern:

- Automatically wraps the payload in the envelope message
- Sets the discriminator field correctly (msgid or field_order)
- Handles serialization and framing
- Works with both `msgid` and `field_order` discriminator types

## .NET Platform Support

The SDK requires .NET 7.0+ due to the use of C# 11 static abstract interface members:

- .NET 7.0+
- .NET 8.0+ (default target framework)
- .NET 9.0+

