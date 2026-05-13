/**
 * Tests for the generated package-specific Client wrapper (SdkInterface.cs).
 *
 * Magnum.Services.SerialAsync uses StructFrame.Biostream.Sdk.Client
 * extensively (Subscribe* / Send* / SendXxxViaCommandEnvelope / Sdk accessor).
 * Existing test suites construct StructFrameSdk directly and bypass the
 * generated wrapper; this file exercises that wrapper end-to-end.
 *
 * Covers gap C from the Magnum review:
 *   C1. Subscribe<X> via Client returns an unsubscribe Action that removes
 *       only that subscription.
 *   C2. Send<X> via Client produces wire bytes equivalent to _sdk.SendAsync.
 *   C3. Client.Sdk accessor exposes the underlying StructFrameSdk (Magnum
 *       relies on this for `client.Sdk.DisconnectAsync()`).
 *   C4. SendXxxViaCommandEnvelope wraps the inner message into the envelope
 *       and the receiver-side wrapper subscription dispatches it correctly.
 */

#nullable enable

using System;
using System.Linq;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Sdk;
using StructFrame.SerializationTest;
using StructFrame.SerializationTest.Sdk;
using StructFrame.EnvelopeTest;
using EnvelopeClient = StructFrame.EnvelopeTest.Sdk.Client;

static class TestSdkClientWrapper
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static void Assert(string name, bool condition)
    {
        bool ok = condition;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")} {name}");
        if (ok) _passed++; else _failed++;
    }

    private static StructFrameSdkConfig MakeConfig(MockTransport transport)
        => new StructFrameSdkConfig(
               transport,
               StructFrame.SerializationTest.MessageDefinitions.GetMessageInfo,
               StructFrame.Profiles.Profiles.Standard);

    // -------------------------------------------------------------------------
    // C3. Client.Sdk accessor returns the same instance handed to ctor.
    // -------------------------------------------------------------------------
    static void TestSdkAccessor()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        var client = new Client(sdk);

        Assert("client.Sdk: accessor returns the same SDK instance",
               object.ReferenceEquals(client.Sdk, sdk));
    }

    // -------------------------------------------------------------------------
    // C2. Send<X> via Client produces wire bytes equal to direct _sdk.SendAsync.
    // -------------------------------------------------------------------------
    static async Task TestSendParityWithDirectSdk()
    {
        var direct = new MockTransport();
        using var directSdk = new StructFrameSdk(MakeConfig(direct));
        await directSdk.SendAsync(new BasicTypesMessage { RegularInt = 42, Flag = true });

        var viaClient = new MockTransport();
        using var viaClientSdk = new StructFrameSdk(MakeConfig(viaClient));
        var client = new Client(viaClientSdk);
        await client.SendBasicTypesMessage(new BasicTypesMessage { RegularInt = 42, Flag = true });

        Assert("client-send: both paths produced 1 frame",
               direct.SentData.Count == 1 && viaClient.SentData.Count == 1);
        Assert("client-send: wire bytes are byte-identical",
               direct.SentData[0].SequenceEqual(viaClient.SentData[0]));
    }

    // -------------------------------------------------------------------------
    // C1. Client.SubscribeXxx returns an unsubscribe Action that removes
    //     only that subscription.
    // -------------------------------------------------------------------------
    static void TestSubscribeReturnsUnsubscribe()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        var client = new Client(sdk);

        int viaClientCalls = 0;
        int directCalls = 0;

        // One subscriber via the wrapper, one via the raw SDK on the same type.
        Action unsubClient = client.SubscribeBasicTypesMessage(_ => viaClientCalls++);
        sdk.Subscribe<BasicTypesMessage>(_ => directCalls++);

        var frame = SdkTestHelpers.EncodeStandard(new BasicTypesMessage { RegularInt = 1 });
        transport.InjectData(frame);
        Assert("client-sub: both subscribers fire on first message",
               viaClientCalls == 1 && directCalls == 1);

        unsubClient();
        transport.InjectData(frame);
        Assert("client-sub: only direct subscriber fires after wrapper unsub",
               viaClientCalls == 1 && directCalls == 2);
    }

    // -------------------------------------------------------------------------
    // C4. Envelope wrapping: SendXxxViaCommandEnvelope sets envelope fields and
    //     receiver-side SubscribeCommandEnvelope dispatches the inner payload.
    // -------------------------------------------------------------------------
    static async Task TestEnvelopeRoundTripViaClient()
    {
        // TX side: encode an ADCCommand inside a CommandEnvelope.
        var txTransport = new MockTransport();
        using var txSdk = new StructFrameSdk(new StructFrameSdkConfig(
            txTransport,
            StructFrame.EnvelopeTest.MessageDefinitions.GetMessageInfo,
            StructFrame.Profiles.Profiles.Standard));
        var txClient = new EnvelopeClient(txSdk);

        var inner = new ADCCommand { Channel = 4, SampleRate = 1000, Enable = true };
        await txClient.SendADCCommandViaCommandEnvelope(
            inner,
            sequence_number: 11,
            priority: 2,
            run_immediately: true);

        Assert("envelope: TX produced exactly one frame",
               txTransport.SentData.Count == 1);

        // Same bytes again with run_immediately=false should differ on wire.
        await txClient.SendADCCommandViaCommandEnvelope(
            inner,
            sequence_number: 11,
            priority: 2,
            run_immediately: false);
        Assert("envelope: run_immediately flag changes wire bytes",
               !txTransport.SentData[0].SequenceEqual(txTransport.SentData[1]));

        // RX side: decode the first frame and confirm the envelope dispatches.
        var rxTransport = new MockTransport();
        using var rxSdk = new StructFrameSdk(new StructFrameSdkConfig(
            rxTransport,
            StructFrame.EnvelopeTest.MessageDefinitions.GetMessageInfo,
            StructFrame.Profiles.Profiles.Standard));
        var rxClient = new EnvelopeClient(rxSdk);

        CommandEnvelope? gotEnvelope = null;
        rxClient.SubscribeCommandEnvelope(env => gotEnvelope = env);

        rxTransport.InjectData(txTransport.SentData[0]);

        Assert("envelope: RX received the envelope", gotEnvelope != null);
        if (gotEnvelope != null)
        {
            Assert("envelope: SequenceNumber preserved", gotEnvelope.SequenceNumber == 11);
            Assert("envelope: Priority preserved", gotEnvelope.Priority == 2);
            Assert("envelope: RunImmediately preserved", gotEnvelope.RunImmediately == true);
            Assert("envelope: inner Adc is populated", gotEnvelope.Adc != null);
            if (gotEnvelope.Adc != null)
            {
                Assert("envelope: inner Adc.Channel preserved", gotEnvelope.Adc.Channel == 4);
                Assert("envelope: inner Adc.SampleRate preserved",
                       gotEnvelope.Adc.SampleRate == 1000);
                Assert("envelope: inner Adc.Enable preserved", gotEnvelope.Adc.Enable);
            }
        }
    }

    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("SDK CLIENT WRAPPER TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestSdkAccessor();
        TestSendParityWithDirectSdk().GetAwaiter().GetResult();
        TestSubscribeReturnsUnsubscribe();
        TestEnvelopeRoundTripViaClient().GetAwaiter().GetResult();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}
