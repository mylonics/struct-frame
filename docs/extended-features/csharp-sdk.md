# C# SDK

The C# SDK provides async/await-based transport layers for .NET applications.

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
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --generate_csproj --target_framework net6.0

# Full SDK with .csproj (includes System.IO.Ports dependency)
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --sdk --generate_csproj
```

## Basic Usage

```csharp
using StructFrame;
using StructFrame.SDK;

var router = new MessageRouter();

// Subscribe to messages
router.Subscribe<Status>(msg => {
    Console.WriteLine($"Status: {msg.Value}");
});

// Process incoming data
router.ProcessByte(byte);
```

## Message Registry and Deserialization

The generated code includes a `MessageDefinitions` class that provides:

### Message Lookup by ID

```csharp
using StructFrame.MyPackage;

// Get message info by ID
var info = MessageDefinitions.GetMessageInfo(SensorDataMessage.MsgId);
Console.WriteLine($"Size: {info?.MaxSize}, Magic: {info?.Magic1:X2}{info?.Magic2:X2}");

// Get full message entry (includes deserializer)
var entry = MessageDefinitions.GetMessageEntry(SensorDataMessage.MsgId);
Console.WriteLine($"Name: {entry?.Name}, Type: {entry?.PayloadType}");
```

### Message Lookup by Name

```csharp
// Get message entry by name (case-insensitive)
var entry = MessageDefinitions.GetMessageEntry("SensorDataMessage");
Console.WriteLine($"ID: {entry?.Id}, MaxSize: {entry?.MaxSize}");
```

### Automatic Deserialization Dispatch

Instead of writing manual switch statements, use the automatic deserializer:

```csharp
// Parse a frame and get the message
var reader = Profiles.CreateReader("ProfileStandard", MessageDefinitions.GetMessageInfo);
reader.SetBuffer(frameData);

while (reader.TryNext(out var frame))
{
    // Automatic deserialization - no switch needed!
    var message = MessageDefinitions.Deserialize(frame);
    
    if (message is SensorDataMessage sensor)
    {
        Console.WriteLine($"Sensor: {sensor.Value}");
    }
    else if (message is StatusMessage status)
    {
        Console.WriteLine($"Status: {status.Code}");
    }
}
```

### Type-Safe Deserialization

```csharp
// Deserialize to a specific type
byte[] payload = GetPayload();
var sensor = MessageDefinitions.Deserialize<SensorDataMessage>(payload);
if (sensor != null)
{
    Console.WriteLine($"Value: {sensor.Value}");
}
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

### UDP

```csharp
using StructFrame.SDK.Transports;

var transport = new UdpTransport("192.168.1.100", 8080);
await transport.ConnectAsync();
await transport.SendAsync(msgId, data);
```

### TCP

```csharp
using StructFrame.SDK.Transports;

var transport = new TcpTransport("192.168.1.100", 8080);
await transport.ConnectAsync();
await transport.SendAsync(msgId, data);
```

### Serial

```csharp
using StructFrame.SDK.Transports;

var transport = new SerialTransport("COM3", 115200);
await transport.ConnectAsync();
await transport.SendAsync(msgId, data);
```

## Async/Await Patterns

```csharp
public async Task HandleMessagesAsync()
{
    var transport = new TcpTransport("localhost", 8080);
    await transport.ConnectAsync();
    
    var router = new MessageRouter();
    router.Subscribe<Status>(HandleStatus);
    
    while (await transport.ReceiveAsync() is byte[] data)
    {
        foreach (var b in data)
        {
            router.ProcessByte(b);
        }
    }
}

void HandleStatus(Status msg)
{
    Console.WriteLine($"Received status: {msg.Value}");
}
```

## .NET Platform Support

The SDK works on:
- .NET Core 3.1+
- .NET 5.0+
- .NET 6.0+
- .NET 7.0+
- .NET 8.0+
- .NET Framework 4.7.2+
- Xamarin
- .NET MAUI

