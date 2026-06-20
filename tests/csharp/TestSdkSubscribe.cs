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
using System.Linq;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;
using StructFrame.Sdk;
using StructFrame.SerializationTest;

// MockTransport is defined in MockTransport.cs (shared across test files).

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

    /// <summary>Creates a StructFrameSdkConfig backed by the given transport.</summary>
    public static StructFrameSdkConfig MakeConfig(ITransport transport)
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
    // Test 1b: Basic subscribe + dispatch through length-aware receive slice
    // -------------------------------------------------------------------------
    static void TestSubscribeAndDispatchMemorySlice()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        BasicTypesMessage? received = null;
        sdk.Subscribe<BasicTypesMessage>(msg => received = msg);

        var outgoing = new BasicTypesMessage { RegularInt = 99, Flag = true };
        byte[] frame = SdkTestHelpers.EncodeStandard(outgoing);
        byte[] padded = new byte[frame.Length + 4];
        Buffer.BlockCopy(frame, 0, padded, 2, frame.Length);

        transport.InjectDataMemory(padded, 2, frame.Length);

        Assert("subscribe-memory: handler invoked from sliced receive buffer", received != null);
        Assert("subscribe-memory: RegularInt value correct", received?.RegularInt == 99);
        Assert("subscribe-memory: Flag value correct", received?.Flag == true);
    }

    // -------------------------------------------------------------------------
    // Test 1c: FrameReceived gets stable frame memory across buffer reuse
    // -------------------------------------------------------------------------
    static void TestFrameReceivedMemoryIsStableAcrossBufferReuse()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        FrameMsgInfo? firstFrame = null;
        int seen = 0;
        sdk.FrameReceived += frame =>
        {
            seen++;
            if (seen == 1)
            {
                firstFrame = frame;
            }
        };

        byte[] first = SdkTestHelpers.EncodeStandard(new BasicTypesMessage { RegularInt = 1234, Flag = true });
        byte[] second = SdkTestHelpers.EncodeStandard(new BasicTypesMessage { RegularInt = 5678, Flag = false });
        int n = Math.Max(first.Length, second.Length);
        byte[] shared = new byte[n + 4];

        Buffer.BlockCopy(first, 0, shared, 2, first.Length);
        transport.InjectDataMemory(shared, 2, first.Length);

        Buffer.BlockCopy(second, 0, shared, 2, second.Length);
        transport.InjectDataMemory(shared, 2, second.Length);

        byte[] expectedFirst = new byte[first.Length];
        Buffer.BlockCopy(first, 0, expectedFirst, 0, first.Length);

        Assert("frame-memory-stable: received two frames", seen == 2);
        Assert("frame-memory-stable: first frame captured", firstFrame.HasValue);
        Assert("frame-memory-stable: first frame bytes preserved after buffer reuse",
               firstFrame.HasValue && firstFrame.Value.FrameData.ToArray().SequenceEqual(expectedFirst));
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
    // Test 5: FrameReceived fires for all complete frames, including CRC failure.
    // -------------------------------------------------------------------------
    static void TestFrameReceivedIncludesCrcFailure()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        int frameCount = 0;
        bool sawCrcFailure = false;
        sdk.FrameReceived += frame =>
        {
            frameCount++;
            sawCrcFailure = !frame.Valid && frame.Status == FrameMsgStatus.CrcFailure && frame.FrameData.Length > 0;
        };

        var outgoing = new BasicTypesMessage { RegularInt = 77, Flag = true };
        byte[] frame = SdkTestHelpers.EncodeStandard(outgoing);
        frame[frame.Length - 1] ^= 0xFF;
        transport.InjectData(frame);

        Assert("frame-received: callback fires for checksum failure", frameCount == 1);
        Assert("frame-received: invalid complete frame is preserved", sawCrcFailure);
    }

    // -------------------------------------------------------------------------
    // Test 6: SendDirect forwards raw bytes without re-encoding.
    // -------------------------------------------------------------------------
    static void TestSendDirectForwardsRawFrame()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        int frameCount = 0;
        sdk.FrameReceived += frame =>
        {
            frameCount++;
            sdk.SendDirect(frame).GetAwaiter().GetResult();
        };

        var outgoing = new BasicTypesMessage { RegularInt = 123, Flag = true };
        byte[] rawFrame = SdkTestHelpers.EncodeStandard(outgoing);
        transport.InjectData(rawFrame);

        Assert("send-direct: frame callback fired once", frameCount == 1);
        Assert("send-direct: transport received forwarded frame", transport.SentData.Count == 1);
        Assert("send-direct: forwarded bytes match original raw bytes",
               transport.SentData[0].SequenceEqual(rawFrame));
    }

    // -------------------------------------------------------------------------
    // Test 7: Send(FrameMsgInfo) re-encodes using payload metadata.
    // -------------------------------------------------------------------------
    static async Task TestSendFrameInfoReencodes()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        var outgoing = new BasicTypesMessage { RegularInt = 456, Flag = true };
        byte[] rawFrame = SdkTestHelpers.EncodeStandard(outgoing);
        var parser = new BufferParser(StructFrame.Profiles.Profiles.Standard,
                                       StructFrame.SerializationTest.MessageDefinitions.GetMessageInfo);
        var parsed = parser.Parse(rawFrame, 0, rawFrame.Length);
        parsed.FrameData = default;

        await sdk.Send(parsed);

        Assert("send-frameinfo: transport received one frame", transport.SentData.Count == 1);
        Assert("send-frameinfo: re-encoded frame parses valid",
               new BufferParser(StructFrame.Profiles.Profiles.Standard,
                                StructFrame.SerializationTest.MessageDefinitions.GetMessageInfo)
                   .Parse(transport.SentData[0], 0, transport.SentData[0].Length).Valid);
        Assert("send-frameinfo: re-encoded bytes match same-profile source",
               transport.SentData[0].SequenceEqual(rawFrame));
    }

    // -------------------------------------------------------------------------
    // Test 8: Two distinct message types are dispatched independently
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
    // Test 9: SendAsync frames and emits through the transport
    // -------------------------------------------------------------------------
    static async Task TestSendAsync()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(transport));

        var msg = new BasicTypesMessage { MediumInt = 1234 };
        await sdk.SendAsync(msg);

        Assert("SendAsync: transport received data", transport.SentData.Count == 1);
        Assert("SendAsync: frame is non-empty", transport.SentData[0].Length > 0);

        var parser = new BufferParser(StructFrame.Profiles.Profiles.Standard, MessageDefinitions.GetMessageInfo);
        var frame = parser.Parse(transport.SentData[0], 0, transport.SentData[0].Length);

        Assert("SendAsync: emitted frame parses as valid", frame.Valid);
        Assert("SendAsync: emitted frame msg_id preserved", frame.MsgId == BasicTypesMessage.MsgId);

        var expectedPayload = msg.Serialize();
        var actualPayload = frame.ExtractPayload();
        Assert("SendAsync: emitted frame payload preserved",
             Enumerable.SequenceEqual(actualPayload, expectedPayload));

        var decoded = BasicTypesMessage.Deserialize(frame);
        Assert("SendAsync: decoded payload round-trips MediumInt", decoded.MediumInt == msg.MediumInt);
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
        TestSubscribeAndDispatchMemorySlice();
        TestFrameReceivedMemoryIsStableAcrossBufferReuse();
        TestMultipleHandlers();
        TestUnsubscribe();
        TestUnhandledMessage();
        TestFrameReceivedIncludesCrcFailure();
        TestSendDirectForwardsRawFrame();
        TestSendFrameInfoReencodes().GetAwaiter().GetResult();
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
