# C# SDK

The C# SDK provides async/await-based transport layers for .NET applications.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_csharp --csharp_path Generated/ --sdk
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
- .NET Framework 4.7.2+
- Xamarin
- .NET MAUI

