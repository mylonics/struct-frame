// Test for the C# SerialTransport over a real serial device: one end of a pseudo-terminal pair
// (made by `socat pty,raw,echo=0 pty,raw,echo=0`). The transport opens the first end; the test
// talks to the second end with a plain FileStream.
//
//   dotnet run -- /dev/pts/3 /dev/pts/4
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using StructFrame.Sdk;

internal static class Program
{
    private static int _run, _failed;

    private static void Check(string name, bool ok)
    {
        _run++;
        if (!ok) _failed++;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")}  {name}");
    }

    private static async Task<bool> Until(Func<bool> p, int ms = 3000)
    {
        var end = DateTime.UtcNow.AddMilliseconds(ms);
        while (DateTime.UtcNow < end) { if (p()) return true; await Task.Delay(10); }
        return p();
    }

    private static async Task<int> Main(string[] args)
    {
        if (args.Length != 2)
        {
            Console.WriteLine("usage: SerialTransportTests <transport-port> <peer-port>");
            return 64;
        }
        using var watchdog = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        watchdog.Token.Register(() => { Console.WriteLine("FAIL  transport tests timed out"); Environment.Exit(2); });
        Console.WriteLine("Serial transport (System.IO.Ports)");

        using var peer = new FileStream(args[1], FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite, 1, false);
        var peerGot = new List<byte>();
        var reader = Task.Run(() =>
        {
            var buf = new byte[64];
            try
            {
                int n;
                while ((n = peer.Read(buf, 0, buf.Length)) > 0)
                    lock (peerGot) for (int i = 0; i < n; i++) peerGot.Add(buf[i]);
            }
            catch (Exception) { }
        });

        var t = new SerialTransport(new SerialTransportConfig { PortName = args[0], BaudRate = 115200 });
        var got = new List<byte>();
        t.DataReceived += (_, d) => { lock (got) got.AddRange(d); };
        try
        {
            await t.ConnectAsync();
            Check("ConnectAsync opens the port", t.IsConnected);

            int n = await t.SendAsync(new byte[] { 0x90, 0x71, 0x01, 0x02 });
            Check("SendAsync returns the byte count", n == 4);
            Check("the peer receives the bytes",
                  await Until(() => { lock (peerGot) return peerGot.Count == 4 && peerGot[0] == 0x90 && peerGot[3] == 0x02; }));

            peer.Write(new byte[] { 7, 8, 9 }, 0, 3);
            peer.Flush();
            Check("DataReceived delivers bytes from the peer",
                  await Until(() => { lock (got) return got.Count == 3 && got[0] == 7 && got[2] == 9; }));

            await t.DisconnectAsync();
            Check("DisconnectAsync clears IsConnected", !t.IsConnected);
            bool threw = false;
            try { await t.SendAsync(new byte[] { 1 }); } catch (InvalidOperationException) { threw = true; }
            Check("SendAsync after DisconnectAsync throws", threw);
        }
        catch (Exception e)
        {
            Check("no unexpected exception: " + e.Message, false);
        }

        var missing = new SerialTransport(new SerialTransportConfig { PortName = "/dev/does-not-exist-sf" });
        bool failed = false;
        try { await missing.ConnectAsync(); } catch (Exception) { failed = true; }
        Check("ConnectAsync to a missing port throws", failed && !missing.IsConnected);

        Console.WriteLine($"\n{_run - _failed}/{_run} transport checks passed");
        return _failed == 0 ? 0 : 1;
    }
}
