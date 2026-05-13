/**
 * Tests for the StrictOrdering=true send-queue path of StructFrameSdk.
 *
 * Real-world consumer (Magnum.Services.SerialAsync.Detector) constructs the
 * SDK with StrictOrdering=true so that many concurrent SendXxxCommand calls
 * are serialized onto the wire in FIFO order. None of the existing C# tests
 * exercise this code path (the queue, background consumer, completion-task
 * wiring, cancel-on-disconnect, exception propagation, or restart after
 * reconnect).
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using StructFrame;
using StructFrame.Sdk;
using StructFrame.SerializationTest;

static class TestSdkStrictOrdering
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
               MessageDefinitions.GetMessageInfo,
               StructFrame.Profiles.Profiles.Standard,
               bufferSize: 1024,
               debug: false,
               strictOrdering: true);

    // -------------------------------------------------------------------------
    // A1. SendAsync completes only after the transport actually receives bytes.
    // -------------------------------------------------------------------------
    static async Task TestSendCompletesAfterTransportReceives()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        await sdk.ConnectAsync();

        // Gate the transport so the queue consumer cannot complete the send.
        var gate = new ManualResetEventSlim(false);
        transport.SendGate = gate;

        var send = sdk.SendAsync(new BasicTypesMessage { RegularInt = 1 });

        // Give the consumer a moment to dequeue and block on the gate.
        await Task.Delay(50);
        Assert("strict: SendAsync awaits until transport completes", !send.IsCompleted);
        Assert("strict: transport has not received bytes yet (gated)",
               transport.SentData.Count == 0);

        gate.Set();
        await send.WaitAsync(TimeSpan.FromSeconds(2));

        Assert("strict: SendAsync completes after gate releases", send.IsCompletedSuccessfully);
        Assert("strict: transport recorded 1 send", transport.SentData.Count == 1);

        await sdk.DisconnectAsync();
    }

    // -------------------------------------------------------------------------
    // A2. Order is preserved when many sends are queued before the consumer
    //     drains. We enqueue sequentially (so the *channel write order* is
    //     deterministic) but hold the consumer with the gate so all writes
    //     land in the channel before any drain happens. This isolates the
    //     SDK's FIFO contract: items written to the queue must be sent in
    //     the same order. (The contract does NOT promise to reorder concurrent
    //     callers — that is up to the caller, per the SDK's own docs.)
    // -------------------------------------------------------------------------
    static async Task TestFifoUnderConcurrency()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        await sdk.ConnectAsync();

        var gate = new ManualResetEventSlim(false);
        transport.SendGate = gate;

        const int N = 32;
        var sends = new List<Task>(N);
        for (int i = 0; i < N; i++)
        {
            // Sequential enqueue: each SendAsync call returns after the item
            // has been written to the channel (no awaiting transport here).
            sends.Add(sdk.SendAsync(new BasicTypesMessage { RegularInt = i }));
        }

        gate.Set();
        await Task.WhenAll(sends).WaitAsync(TimeSpan.FromSeconds(5));

        Assert("strict-fifo: all sends recorded", transport.SentData.Count == N);

        // Decode each frame's RegularInt by parsing it back out via the SDK
        // on the receiving side so we can assert FIFO without hand-parsing.
        var rxTransport = new MockTransport();
        using var rxSdk = new StructFrameSdk(SdkTestHelpers.MakeConfig(rxTransport));
        var received = new List<int>();
        rxSdk.Subscribe<BasicTypesMessage>(m => received.Add(m.RegularInt));
        foreach (var frame in transport.SentData)
        {
            rxTransport.InjectData(frame);
        }

        bool inOrder = received.Count == N;
        for (int i = 0; inOrder && i < N; i++)
        {
            if (received[i] != i) inOrder = false;
        }
        Assert("strict-fifo: payloads observed in enqueue order", inOrder);

        await sdk.DisconnectAsync();
    }

    // -------------------------------------------------------------------------
    // A3. DisconnectAsync cancels in-flight queued sends.
    // -------------------------------------------------------------------------
    static async Task TestDisconnectCancelsQueuedSends()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        await sdk.ConnectAsync();

        // Hold the consumer indefinitely so subsequent items pile up.
        var gate = new ManualResetEventSlim(false);
        transport.SendGate = gate;

        // First send: will be dequeued and block on the gate.
        var first = sdk.SendAsync(new BasicTypesMessage { RegularInt = 1 });

        // Two more sends: will sit in the queue (consumer is blocked).
        var second = sdk.SendAsync(new BasicTypesMessage { RegularInt = 2 });
        var third = sdk.SendAsync(new BasicTypesMessage { RegularInt = 3 });

        await Task.Delay(50); // let everything land in the channel/consumer
        await sdk.DisconnectAsync();

        // The two queued tasks should be cancelled. The first one was already
        // dequeued and is blocked inside transport.SendAsync — release it so
        // the consumer can finish its loop cleanly.
        gate.Set();

        bool secondCancelled = false;
        try { await second.WaitAsync(TimeSpan.FromSeconds(1)); }
        catch (TaskCanceledException) { secondCancelled = true; }
        catch (OperationCanceledException) { secondCancelled = true; }

        bool thirdCancelled = false;
        try { await third.WaitAsync(TimeSpan.FromSeconds(1)); }
        catch (TaskCanceledException) { thirdCancelled = true; }
        catch (OperationCanceledException) { thirdCancelled = true; }

        Assert("strict-cancel: queued send #2 was cancelled on disconnect", secondCancelled);
        Assert("strict-cancel: queued send #3 was cancelled on disconnect", thirdCancelled);

        // Drain any completion of `first` so we don't leak the task.
        try { await first.WaitAsync(TimeSpan.FromSeconds(1)); } catch { /* may also be cancelled */ }
    }

    // -------------------------------------------------------------------------
    // A4. Disconnect → Connect cycle restarts the queue cleanly.
    // -------------------------------------------------------------------------
    static async Task TestQueueRestartsAfterReconnect()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));

        await sdk.ConnectAsync();
        await sdk.SendAsync(new BasicTypesMessage { RegularInt = 1 });
        Assert("strict-reconnect: first cycle delivered", transport.SentData.Count == 1);

        await sdk.DisconnectAsync();
        // Reconnect (transport.ConnectAsync will toggle IsConnected back on).
        await sdk.ConnectAsync();
        await sdk.SendAsync(new BasicTypesMessage { RegularInt = 2 });

        Assert("strict-reconnect: second cycle delivered after reconnect",
               transport.SentData.Count == 2);

        await sdk.DisconnectAsync();
    }

    // -------------------------------------------------------------------------
    // A5. Exception thrown by transport.SendAsync flows through to the awaiter.
    // -------------------------------------------------------------------------
    static async Task TestExceptionPropagatesFromQueueConsumer()
    {
        var transport = new MockTransport();
        using var sdk = new StructFrameSdk(MakeConfig(transport));
        await sdk.ConnectAsync();

        transport.NextSendThrows = new InvalidOperationException("boom");

        bool gotException = false;
        try
        {
            await sdk.SendAsync(new BasicTypesMessage { RegularInt = 99 })
                     .WaitAsync(TimeSpan.FromSeconds(2));
        }
        catch (InvalidOperationException ex) when (ex.Message == "boom")
        {
            gotException = true;
        }

        Assert("strict-exn: SendAsync awaiter receives the transport exception",
               gotException);

        // Subsequent sends should still work (consumer is resilient).
        await sdk.SendAsync(new BasicTypesMessage { RegularInt = 1 })
                 .WaitAsync(TimeSpan.FromSeconds(2));
        Assert("strict-exn: subsequent send succeeds after error",
               transport.SentData.Count == 1);

        await sdk.DisconnectAsync();
    }

    // -------------------------------------------------------------------------
    // A6. Dispose with pending items cancels them safely; double Dispose ok.
    // -------------------------------------------------------------------------
    static async Task TestDisposeCancelsPendingAndIsIdempotent()
    {
        var transport = new MockTransport();
        var sdk = new StructFrameSdk(MakeConfig(transport));
        await sdk.ConnectAsync();

        var gate = new ManualResetEventSlim(false);
        transport.SendGate = gate;

        var first = sdk.SendAsync(new BasicTypesMessage { RegularInt = 1 });
        var second = sdk.SendAsync(new BasicTypesMessage { RegularInt = 2 });
        await Task.Delay(50);

        // Dispose without an explicit DisconnectAsync — must not throw and
        // must cancel queued items.
        sdk.Dispose();
        gate.Set();

        bool secondCancelled = false;
        try { await second.WaitAsync(TimeSpan.FromSeconds(1)); }
        catch (OperationCanceledException) { secondCancelled = true; }
        Assert("strict-dispose: queued send cancelled on Dispose", secondCancelled);

        bool doubleDisposeOk = true;
        try { sdk.Dispose(); } catch { doubleDisposeOk = false; }
        Assert("strict-dispose: Dispose is idempotent", doubleDisposeOk);

        try { await first.WaitAsync(TimeSpan.FromSeconds(1)); } catch { /* ignore */ }
    }

    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("SDK STRICT-ORDERING TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestSendCompletesAfterTransportReceives().GetAwaiter().GetResult();
        TestFifoUnderConcurrency().GetAwaiter().GetResult();
        TestDisconnectCancelsQueuedSends().GetAwaiter().GetResult();
        TestQueueRestartsAfterReconnect().GetAwaiter().GetResult();
        TestExceptionPropagatesFromQueueConsumer().GetAwaiter().GetResult();
        TestDisposeCancelsPendingAndIsIdempotent().GetAwaiter().GetResult();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}
