// Loopback tests for the concrete C# TcpTransport and UdpTransport. Every wait is bounded.
using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using StructFrame.Sdk;

internal static class Program
{
    private static int _run, _failed;

    private static void Check(string name, bool ok, string detail = "")
    {
        _run++;
        if (!ok) _failed++;
        Console.WriteLine($"  {(ok ? "PASS" : "FAIL")}  {name}{(ok || detail == "" ? "" : " -- " + detail)}");
    }

    private static async Task<bool> Until(Func<bool> p, int timeoutMs = 2000)
    {
        var end = DateTime.UtcNow.AddMilliseconds(timeoutMs);
        while (DateTime.UtcNow < end)
        {
            if (p()) return true;
            await Task.Delay(5);
        }
        return p();
    }

    private static bool Same(List<byte> a, params byte[] b)
    {
        if (a.Count != b.Length) return false;
        for (int i = 0; i < b.Length; i++) if (a[i] != b[i]) return false;
        return true;
    }

    private static async Task TestTcp()
    {
        Console.WriteLine("TCP transport");
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        int port = ((IPEndPoint)listener.LocalEndpoint).Port;
        TcpClient? server = null;
        var received = new List<byte>();
        _ = Task.Run(async () =>
        {
            server = await listener.AcceptTcpClientAsync();
            var buf = new byte[256];
            var s = server.GetStream();
            try
            {
                int n;
                while ((n = await s.ReadAsync(buf, 0, buf.Length)) > 0)
                    lock (received) received.AddRange(new ArraySegment<byte>(buf, 0, n));
            }
            catch (Exception) { }
        });

        var t = new TcpTransport(new TcpTransportConfig { Host = "127.0.0.1", Port = port });
        var got = new List<byte>();
        int closed = 0;
        t.DataReceived += (_, d) => { lock (got) got.AddRange(d); };
        t.ConnectionClosed += (_, __) => Interlocked.Increment(ref closed);

        Check("IsConnected false before connect", !t.IsConnected);
        await t.ConnectAsync();
        Check("IsConnected true after connect", t.IsConnected);

        int n = await t.SendAsync(new byte[] { 1, 2, 3, 4 });
        Check("SendAsync returns the byte count", n == 4);
        Check("server receives the bytes sent", await Until(() => { lock (received) return received.Count == 4; }) && Same(received, 1, 2, 3, 4));

        await Until(() => server != null);
        await server!.GetStream().WriteAsync(new byte[] { 9, 8, 7 });
        Check("DataReceived delivers bytes sent by the peer", await Until(() => { lock (got) return got.Count == 3; }) && Same(got, 9, 8, 7));

        server.Close();
        Check("peer close raises ConnectionClosed", await Until(() => closed == 1));
        Check("IsConnected false after peer close", !t.IsConnected);
        bool rejected = false;
        try { await t.SendAsync(new byte[] { 1 }); } catch (Exception) { rejected = true; }
        Check("SendAsync on a closed transport throws", rejected);

        var t2 = new TcpTransport(new TcpTransportConfig { Host = "127.0.0.1", Port = port });
        var accept2 = listener.AcceptTcpClientAsync();
        await t2.ConnectAsync();
        await accept2;
        await t2.DisconnectAsync();
        Check("DisconnectAsync clears IsConnected", !t2.IsConnected);
        // Whether a local DisconnectAsync also raises ConnectionClosed differs between SDKs
        // (the TypeScript transport does, this one only reports peer-initiated closes), so
        // only the peer-close behaviour above is asserted.

        // With AutoReconnect on, an intentional DisconnectAsync must not reconnect.
        int accepted = 0;
        var acceptLoop = Task.Run(async () =>
        {
            try { while (true) { var c = await listener.AcceptTcpClientAsync(); Interlocked.Increment(ref accepted); } }
            catch (Exception) { }
        });
        var t4 = new TcpTransport(new TcpTransportConfig { Host = "127.0.0.1", Port = port, AutoReconnect = true, ReconnectDelayMs = 30 });
        await t4.ConnectAsync();
        await Until(() => accepted == 1);
        await t4.DisconnectAsync();
        await Task.Delay(300);
        Check("an intentional DisconnectAsync does not reconnect (AutoReconnect)", accepted == 1 && !t4.IsConnected);

        listener.Stop();
        var t3 = new TcpTransport(new TcpTransportConfig { Host = "127.0.0.1", Port = port, TimeoutMs = 1000 });
        bool refused = false;
        try { await t3.ConnectAsync(); } catch (Exception) { refused = true; }
        Check("ConnectAsync to a closed port throws", refused);
        Check("IsConnected stays false after a failed connect", !t3.IsConnected);
    }

    private static async Task TestUdp()
    {
        Console.WriteLine("UDP transport");
        var peer = new UdpClient(new IPEndPoint(IPAddress.Loopback, 0));
        int peerPort = ((IPEndPoint)peer.Client.LocalEndPoint!).Port;
        var t = new UdpTransport(new UdpTransportConfig { LocalAddress = "127.0.0.1", RemoteHost = "127.0.0.1", RemotePort = peerPort });
        var got = new List<byte>();
        t.DataReceived += (_, d) => { lock (got) got.AddRange(d); };
        await t.ConnectAsync();
        Check("IsConnected true after connect", t.IsConnected);

        int n = await t.SendAsync(new byte[] { 5, 6, 7 });
        Check("SendAsync returns the byte count", n == 3);
        var recv = peer.ReceiveAsync();
        var done = await Task.WhenAny(recv, Task.Delay(2000));
        Check("peer receives the datagram", done == recv);
        UdpReceiveResult r = await recv;
        Check("datagram payload matches", r.Buffer.Length == 3 && r.Buffer[0] == 5 && r.Buffer[2] == 7);

        await peer.SendAsync(new byte[] { 40, 41 }, 2, r.RemoteEndPoint);
        Check("DataReceived delivers a datagram from the peer", await Until(() => { lock (got) return got.Count == 2; }) && Same(got, 40, 41));

        await t.DisconnectAsync();
        Check("DisconnectAsync clears IsConnected", !t.IsConnected);
        peer.Close();
    }

    private static async Task<int> Main()
    {
        using var watchdog = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        watchdog.Token.Register(() => { Console.WriteLine("FAIL  transport tests timed out"); Environment.Exit(2); });
        try
        {
            await TestTcp();
            await TestUdp();
        }
        catch (Exception e)
        {
            Check("no unexpected exception", false, e.ToString());
        }
        Console.WriteLine($"\n{_run - _failed}/{_run} transport checks passed");
        return _failed == 0 ? 0 : 1;
    }
}
