/**
 * Subscribe / dispatch tests for the C# StructFrameSdk (section 6.3)
 *
 * Uses a MockTransport to inject encoded frames and verifies that subscribed
 * handlers are invoked with correctly deserialized messages.
 *
 * Test matrix:
 *   - Subscribe + DataReceived dispatches to handler
 *   - Multiple handlers for the same message type all fire
 *   - Unsubscribe action removes the handler
 *   - Unknown message ID triggers UnhandledMessage event
 *   - SubscribeRaw receives any message without deserialization
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;
using StructFrame.Sdk;
using StructFrame.SerializationTest;

// ============================================================================
// Mock Transport
// ============================================================================

/// <summary>
/// A minimal ITransport implementation that allows test code to inject data
/// directly by raising DataReceived, and records all outgoing Send calls.
/// </summary>
class MockTransport : ITransport
{
    public bool IsConnected { get; private set; }

    public event EventHandler<byte[]>? DataReceived;
    public event EventHandler<Exception>? ErrorOccurred;
    public event EventHandler? ConnectionClosed;

    public List<byte[]> SentData { get; } = new();

    public Task ConnectAsync()
    {
        IsConnected = true;
        return Task.CompletedTask;
    }

    public Task DisconnectAsync()
    {
        IsConnected = false;
        ConnectionClosed?.Invoke(this, EventArgs.Empty);
        return Task.CompletedTask;
    }

    public Task SendAsync(byte[] data)
    {
        SentData.Add((byte[])data.Clone());
        return Task.CompletedTask;
    }

    public Task SendAsync(ReadOnlyMemory<byte> data)
    {
        SentData.Add(data.ToArray());
        return Task.CompletedTask;
    }

    /// <summary>Simulates arriving data (e.g., received over the network).</summary>
    public void InjectData(byte[] data) => DataReceived?.Invoke(this, data);

    public void InjectError(Exception ex) => ErrorOccurred?.Invoke(this, ex);
}

// ============================================================================
// Helpers
// ============================================================================

static class SdkTestHelpers
{
    /// <summary>
    /// Builds a Standard-profile encoded frame for a given message and returns the bytes.
    /// </summary>
    public static byte[] EncodeStandard(IStructFrameMessage message)
    {
        var encoder = new FrameEncoder(StructFrame.Profiles.Profiles.Standard);
        byte[] buf = new byte[512];
        int len = encoder.Encode(buf, 0, message);
        byte[] frame = new byte[len];
        Buffer.BlockCopy(buf, 0, frame, 0, len);
        return frame;
    }

    /// <summary>Creates a StructFrameSdkConfig backed by the given mock transport.</summary>
    public static StructFrameSdkConfig MakeConfig(MockTransport transport)
        => new StructFrameSdkConfig(
               transport,
               MessageDefinitions.GetMessageInfo,
               StructFrame.Profiles.Profiles.Standard);
}

// ============================================================================
// Test class
// ============================================================================

static class TestSdkSubscribe
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static bool Assert(string name, bool condition)
    {
        bool ok = condition;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")} {name}");
        if (ok) _passed++; else _failed++;
        return ok;
    }

    // -------------------------------------------------------------------------
    // Test 1: Basic subscribe + dispatch
    // -------------------------------------------------------------------------
    static void TestSubscribeAndDispatch()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        BasicTypesMessage? received = null;
        sdk.Subscribe<BasicTypesMessage>(msg => received = msg);

        // Build and inject a valid frame
        var outgoing = new BasicTypesMessage { RegularInt = 42, Flag = true };
        transport.InjectData(SdkTestHelpers.EncodeStandard(outgoing));

        Assert("subscribe: handler invoked on DataReceived", received != null);
        Assert("subscribe: RegularInt value correct", received?.RegularInt == 42);
        Assert("subscribe: Flag value correct", received?.Flag == true);
    }

    // -------------------------------------------------------------------------
    // Test 2: Multiple handlers for the same message type
    // -------------------------------------------------------------------------
    static void TestMultipleHandlers()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        int countA = 0, countB = 0;
        sdk.Subscribe<BasicTypesMessage>(_ => countA++);
        sdk.Subscribe<BasicTypesMessage>(_ => countB++);

        var outgoing = new BasicTypesMessage { SmallInt = 7 };
        transport.InjectData(SdkTestHelpers.EncodeStandard(outgoing));

        Assert("multiple handlers: first handler fires", countA == 1);
        Assert("multiple handlers: second handler fires", countB == 1);
    }

    // -------------------------------------------------------------------------
    // Test 3: Unsubscribe action removes the handler
    // -------------------------------------------------------------------------
    static void TestUnsubscribe()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        int count = 0;
        Action unsub = sdk.Subscribe<BasicTypesMessage>(_ => count++);

        var outgoing = new BasicTypesMessage { SmallInt = 1 };
        transport.InjectData(SdkTestHelpers.EncodeStandard(outgoing));
        Assert("unsubscribe: handler fires before unsubscribe", count == 1);

        unsub();  // remove the handler

        transport.InjectData(SdkTestHelpers.EncodeStandard(outgoing));
        Assert("unsubscribe: handler does not fire after unsubscribe", count == 1);
    }

    // -------------------------------------------------------------------------
    // Test 4: Unhandled message fires UnhandledMessage event
    // -------------------------------------------------------------------------
    static void TestUnhandledMessage()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        // Subscribe to a DIFFERENT type so BasicTypesMessage is unhandled
        int unhandledCount = 0;
        sdk.UnhandledMessage += frame => unhandledCount++;

        var outgoing = new BasicTypesMessage { SmallInt = 99 };
        transport.InjectData(SdkTestHelpers.EncodeStandard(outgoing));

        Assert("unhandled: UnhandledMessage event fires for no-subscriber message",
               unhandledCount == 1);
    }

    // -------------------------------------------------------------------------
    // Test 5: Two distinct message types are dispatched independently
    // -------------------------------------------------------------------------
    static void TestTwoMessageTypes()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        BasicTypesMessage? gotBasic = null;
        SerializationTestMessage? gotSt = null;

        sdk.Subscribe<BasicTypesMessage>(m => gotBasic = m);
        sdk.Subscribe<SerializationTestMessage>(m => gotSt = m);

        // Inject BasicTypesMessage frame
        transport.InjectData(SdkTestHelpers.EncodeStandard(
            new BasicTypesMessage { RegularInt = 10 }));

        Assert("two types: BasicTypesMessage handler fires", gotBasic != null);
        Assert("two types: SerializationTestMessage handler has not fired yet", gotSt == null);

        // Inject SerializationTestMessage frame
        var stMsg = new SerializationTestMessage
        {
            MagicNumber = 0xCAFE,
            TestFloat = 1.5f,
            TestBool = true
        };
        transport.InjectData(SdkTestHelpers.EncodeStandard(stMsg));

        Assert("two types: SerializationTestMessage handler fires", gotSt != null);
        Assert("two types: MagicNumber correct", gotSt?.MagicNumber == 0xCAFE);
    }

    // -------------------------------------------------------------------------
    // Test 6: SendAsync frames and emits through the transport
    // -------------------------------------------------------------------------
    static async Task TestSendAsync()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        var msg = new BasicTypesMessage { MediumInt = 1234 };
        await sdk.SendAsync(msg);

        Assert("SendAsync: transport received data", transport.SentData.Count == 1);
        Assert("SendAsync: frame is non-empty", transport.SentData[0].Length > 0);
    }

    // -------------------------------------------------------------------------
    // Entry point
    // -------------------------------------------------------------------------
    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("SDK SUBSCRIBE/DISPATCH TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestSubscribeAndDispatch();
        TestMultipleHandlers();
        TestUnsubscribe();
        TestUnhandledMessage();
        TestTwoMessageTypes();
        TestSendAsync().GetAwaiter().GetResult();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}
