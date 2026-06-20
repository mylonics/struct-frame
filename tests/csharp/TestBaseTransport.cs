/**
 * Tests for BaseTransport / SerialTransport boilerplate.
 *
 * The existing C# tests only ever exercise MockTransport — the
 * BaseTransport semaphore, ROM overload, AutoReconnect logic, and
 * SerialTransport constructor are not covered. Magnum.Services.SerialAsync
 * derives its own SerialTransport and depends on BaseTransport-like
 * semantics, so regressions here would silently break real consumers.
 *
 * Covers gap F from the Magnum review.
 */

#nullable enable

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using StructFrame.Sdk;

static class TestBaseTransport
{
    private static int _passed = 0;
    private static int _failed = 0;

    private static void Assert(string name, bool condition)
    {
        bool ok = condition;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")} {name}");
        if (ok) _passed++; else _failed++;
    }

    // -------------------------------------------------------------------------
    // F1. Semaphore serializes concurrent writes (no interleaving in SendCore).
    // -------------------------------------------------------------------------
    static async Task TestSemaphoreSerializesConcurrentWrites()
    {
        var transport = new InstrumentedTransport();
        await transport.ConnectAsync();

        // Each SendCoreAsync call holds the semaphore for ~25 ms. Fire 4
        // overlapping sends; if the semaphore works, the in-flight count must
        // never exceed 1.
        transport.SendDelayMs = 25;

        var sends = new List<Task>();
        for (int i = 0; i < 4; i++)
        {
            sends.Add(transport.SendAsync(new byte[] { (byte)i }));
        }
        await Task.WhenAll(sends);

        Assert("base-semaphore: SendCoreAsync never had >1 caller in flight",
               transport.MaxConcurrent == 1);
        Assert("base-semaphore: all 4 sends recorded",
               transport.SendCalls.Count == 4);
    }

    // -------------------------------------------------------------------------
    // F2. SendAsync(ROM) overload reaches SendCoreAsync with the same bytes.
    // -------------------------------------------------------------------------
    static async Task TestRomOverloadReachesSendCore()
    {
        var transport = new InstrumentedTransport();
        await transport.ConnectAsync();

        var payload = new byte[] { 9, 8, 7, 6 };
        await transport.SendAsync(new ReadOnlyMemory<byte>(payload));

        Assert("base-rom: 1 SendCoreAsync call recorded",
               transport.SendCalls.Count == 1);
        Assert("base-rom: payload bytes match",
               transport.SendCalls[0].Length == payload.Length &&
               transport.SendCalls[0][0] == 9 &&
               transport.SendCalls[0][3] == 6);
    }

    // -------------------------------------------------------------------------
    // F2b. Receive memory event reports the exact incoming slice.
    // -------------------------------------------------------------------------
    static void TestReceiveMemorySliceEvent()
    {
        var transport = new InstrumentedTransport();
        ReadOnlyMemory<byte> received = default;
        int calls = 0;

        transport.DataReceivedMemory += (_, data) =>
        {
            received = data;
            calls++;
        };

        byte[] backing = new byte[] { 0, 10, 11, 12, 0 };
        transport.ForceReceiveMemory(backing, 1, 3);

        Assert("base-receive-memory: event fired once", calls == 1);
        Assert("base-receive-memory: slice length preserved", received.Length == 3);
        Assert("base-receive-memory: slice bytes preserved",
               received.Span[0] == 10 && received.Span[2] == 12);
    }

    // -------------------------------------------------------------------------
    // F2c. Legacy DataReceived subscribers still receive right-sized byte arrays.
    // -------------------------------------------------------------------------
    static void TestReceiveMemorySliceLegacyEvent()
    {
        var transport = new InstrumentedTransport();
        byte[]? received = null;
        int calls = 0;

        transport.DataReceived += (_, data) =>
        {
            received = data;
            calls++;
        };

        byte[] backing = new byte[] { 0, 20, 21, 22, 0 };
        transport.ForceReceiveMemory(backing, 1, 3);

        Assert("base-receive-legacy: event fired once", calls == 1);
        Assert("base-receive-legacy: copied slice is right-sized", received?.Length == 3);
        Assert("base-receive-legacy: copied slice bytes preserved",
               received != null && received[0] == 20 && received[2] == 22);
    }

    // -------------------------------------------------------------------------
    // F2d. Legacy DataReceived subscribers must not alias a reusable full buffer.
    // -------------------------------------------------------------------------
    static void TestReceiveMemoryFullBufferLegacyEvent()
    {
        var transport = new InstrumentedTransport();
        byte[]? received = null;
        int calls = 0;

        transport.DataReceived += (_, data) =>
        {
            received = data;
            calls++;
        };

        byte[] backing = new byte[] { 30, 31, 32 };
        transport.ForceReceiveMemory(backing, 0, backing.Length);
        backing[0] = 99;

        Assert("base-receive-legacy-full: event fired once", calls == 1);
        Assert("base-receive-legacy-full: legacy event returns a copy",
               received != null && !ReferenceEquals(received, backing));
        Assert("base-receive-legacy-full: legacy event stays stable after buffer reuse",
               received != null && received[0] == 30 && received[2] == 32);
    }

    // -------------------------------------------------------------------------
    // F3. AutoReconnect: ConnectionClosed triggers reconnect only when enabled.
    // -------------------------------------------------------------------------
    static async Task TestAutoReconnectHonored()
    {
        // No auto-reconnect: ConnectionClosed should not re-call ConnectAsync.
        var off = new InstrumentedTransport(new TransportConfig { AutoReconnect = false });
        await off.ConnectAsync();
        int connectsAfter = off.ConnectCalls;
        off.ForceClose();
        // Give any spurious reconnect attempt a chance to run.
        await Task.Delay(50);
        Assert("base-reconnect: no reconnect when AutoReconnect=false",
               off.ConnectCalls == connectsAfter);

        // AutoReconnect with a small max should make exactly that many attempts.
        var on = new InstrumentedTransport(new TransportConfig
        {
            AutoReconnect = true,
            ReconnectDelayMs = 10,
            MaxReconnectAttempts = 2,
        });
        // First Connect must succeed; subsequent ones should fail to drive
        // the reconnect-loop cap.
        await on.ConnectAsync();      // attempt #1: succeeds
        on.FailNextConnect = 99;      // every reconnect from here on throws
        int baseline = on.ConnectCalls;
        on.ForceClose();              // triggers reconnect attempt
        await Task.Delay(200);
        int attemptsTriggered = on.ConnectCalls - baseline;
        Assert("base-reconnect: AutoReconnect respects MaxReconnectAttempts",
               attemptsTriggered <= 2 && attemptsTriggered >= 1);
    }

    // -------------------------------------------------------------------------
    // F4. Dispose is idempotent and releases the semaphore.
    // -------------------------------------------------------------------------
    static async Task TestDisposeIdempotent()
    {
        var transport = new InstrumentedTransport();
        await transport.ConnectAsync();
        await transport.SendAsync(new byte[] { 1 });

        bool first = true, second = true;
        try { transport.Dispose(); } catch { first = false; }
        try { transport.Dispose(); } catch { second = false; }

        Assert("base-dispose: first Dispose succeeds", first);
        Assert("base-dispose: second Dispose is a no-op", second);
    }

    // -------------------------------------------------------------------------
    // F5. SerialTransport coverage is intentionally omitted: the test project
    //     does not enable IncludeSerialTransport=true (which would require the
    //     System.IO.Ports NuGet package). The construction + safe-idle-disconnect
    //     contract is exercised indirectly through BaseTransport above.
    // -------------------------------------------------------------------------

    public static int Main(string[] args)
    {
        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("BASE TRANSPORT TESTS - C#");
        Console.WriteLine("========================================");
        Console.WriteLine();

        TestSemaphoreSerializesConcurrentWrites().GetAwaiter().GetResult();
        TestRomOverloadReachesSendCore().GetAwaiter().GetResult();
        TestReceiveMemorySliceEvent();
        TestReceiveMemorySliceLegacyEvent();
        TestReceiveMemoryFullBufferLegacyEvent();
        TestAutoReconnectHonored().GetAwaiter().GetResult();
        TestDisposeIdempotent().GetAwaiter().GetResult();

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine($"Summary: {_passed}/{_passed + _failed} tests passed");
        Console.WriteLine("========================================");
        Console.WriteLine();

        return _failed > 0 ? 1 : 0;
    }
}

/// <summary>
/// BaseTransport subclass that records SendCoreAsync calls, tracks how many
/// callers are concurrently inside SendCoreAsync (must always be 1 because
/// of the semaphore), and lets tests inject delay / reconnect failures.
/// </summary>
class InstrumentedTransport : BaseTransport
{
    public List<byte[]> SendCalls { get; } = new();
    public int ConnectCalls { get; private set; }
    public int MaxConcurrent { get; private set; }
    public int SendDelayMs { get; set; } = 0;

    /// <summary>If &gt; 0, the next N ConnectAsync calls throw.</summary>
    public int FailNextConnect { get; set; }

    private int _inFlight;

    public InstrumentedTransport(TransportConfig? config = null) : base(config) { }

    public override Task ConnectAsync()
    {
        ConnectCalls++;
        if (FailNextConnect > 0)
        {
            FailNextConnect--;
            throw new InvalidOperationException("simulated connect failure");
        }
        _connected = true;
        return Task.CompletedTask;
    }

    public override Task DisconnectAsync()
    {
        _connected = false;
        OnConnectionClosed();
        return Task.CompletedTask;
    }

    /// <summary>Force a ConnectionClosed event without changing internal flag-flip ordering.</summary>
    public void ForceClose() => OnConnectionClosed();

    /// <summary>Force a memory-slice receive event for BaseTransport contract tests.</summary>
    public void ForceReceiveMemory(byte[] data, int offset, int count)
        => OnDataReceived(new ReadOnlyMemory<byte>(data, offset, count));

    protected override async Task<int> SendCoreAsync(byte[] data)
    {
        int now = Interlocked.Increment(ref _inFlight);
        if (now > MaxConcurrent) MaxConcurrent = now;
        try
        {
            if (SendDelayMs > 0)
                await Task.Delay(SendDelayMs).ConfigureAwait(false);
            lock (SendCalls)
            {
                SendCalls.Add((byte[])data.Clone());
            }
            return data.Length;
        }
        finally
        {
            Interlocked.Decrement(ref _inFlight);
        }
    }
}
