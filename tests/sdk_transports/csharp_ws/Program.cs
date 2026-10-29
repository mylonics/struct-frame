// Loopback test for the C# WebSocketTransport (NetCoreServer-based). The peer is a minimal
// hand-written WebSocket server on TcpListener, so the test does not share code with the
// library under test. Every wait is bounded.
using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using StructFrame.Sdk;

internal sealed class MiniWsServer : IDisposable
{
    private readonly TcpListener _listener = new TcpListener(IPAddress.Loopback, 0);
    private NetworkStream? _stream;
    public readonly List<byte> Received = new List<byte>();
    public string? RequestLine;
    public int Port => ((IPEndPoint)_listener.LocalEndpoint).Port;
    public bool Upgraded;

    public MiniWsServer()
    {
        _listener.Start();
        _ = Task.Run(AcceptAsync);
    }

    private async Task AcceptAsync()
    {
        try
        {
            var client = await _listener.AcceptTcpClientAsync();
            _stream = client.GetStream();
            var header = new StringBuilder();
            var one = new byte[1];
            while (!header.ToString().EndsWith("\r\n\r\n"))
            {
                if (await _stream.ReadAsync(one, 0, 1) == 0) return;
                header.Append((char)one[0]);
            }
            string text = header.ToString();
            RequestLine = text.Split("\r\n")[0];
            string key = "";
            foreach (var line in text.Split("\r\n"))
                if (line.StartsWith("Sec-WebSocket-Key:", StringComparison.OrdinalIgnoreCase))
                    key = line.Substring(line.IndexOf(':') + 1).Trim();
            string accept = Convert.ToBase64String(SHA1.HashData(
                Encoding.ASCII.GetBytes(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")));
            byte[] response = Encoding.ASCII.GetBytes(
                "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" +
                $"Sec-WebSocket-Accept: {accept}\r\n\r\n");
            await _stream.WriteAsync(response);
            Upgraded = true;
            while (true)
            {
                var head = new byte[2];
                if (!await ReadExactly(head)) return;
                int opcode = head[0] & 0x0F;
                int len = head[1] & 0x7F;      // test payloads are < 126 bytes
                var mask = new byte[4];
                if (!await ReadExactly(mask)) return;
                var payload = new byte[len];
                if (!await ReadExactly(payload)) return;
                for (int i = 0; i < len; i++) payload[i] ^= mask[i % 4];
                if (opcode == 2 || opcode == 1) lock (Received) Received.AddRange(payload);
                if (opcode == 8) return;
            }
        }
        catch (Exception) { }
    }

    private async Task<bool> ReadExactly(byte[] buf)
    {
        int got = 0;
        while (got < buf.Length)
        {
            int n = await _stream!.ReadAsync(buf, got, buf.Length - got);
            if (n == 0) return false;
            got += n;
        }
        return true;
    }

    public void SendBinary(params byte[] data)
    {
        var frame = new byte[2 + data.Length];
        frame[0] = 0x82;
        frame[1] = (byte)data.Length;
        Array.Copy(data, 0, frame, 2, data.Length);
        _stream!.Write(frame);
    }

    public void Close()
    {
        try { _stream?.Write(new byte[] { 0x88, 0x00 }); _stream?.Close(); } catch (Exception) { }
    }

    public void Dispose() { Close(); _listener.Stop(); }
}

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

    private static async Task<int> Main()
    {
        using var watchdog = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        watchdog.Token.Register(() => { Console.WriteLine("FAIL  transport tests timed out"); Environment.Exit(2); });
        Console.WriteLine("WebSocket transport (NetCoreServer)");
        using var server = new MiniWsServer();
        var t = new WebSocketTransport(new WebSocketTransportConfig { Url = $"ws://127.0.0.1:{server.Port}/stream" },
                                       "127.0.0.1", server.Port, "/stream");
        var got = new List<byte>();
        int closed = 0;
        t.DataReceived += (_, d) => { lock (got) got.AddRange(d); };
        t.ConnectionClosed += (_, __) => Interlocked.Increment(ref closed);
        try
        {
            await t.ConnectAsync();
            Check("the server receives a WebSocket upgrade request", await Until(() => server.Upgraded));
            Check("the upgrade request targets the configured path", server.RequestLine == "GET /stream HTTP/1.1");
            Check("IsConnected after the handshake", await Until(() => t.IsConnected));

            await t.SendAsync(new byte[] { 11, 12, 13 });
            Check("the server receives a binary message",
                  await Until(() => { lock (server.Received) return server.Received.Count == 3; }));

            server.SendBinary(21, 22, 23, 24);
            Check("DataReceived delivers a binary message from the server",
                  await Until(() => { lock (got) return got.Count == 4 && got[0] == 21 && got[3] == 24; }));

            server.Close();
            Check("a server close raises ConnectionClosed", await Until(() => closed >= 1));
            Check("IsConnected is false after the server closes", await Until(() => !t.IsConnected));
        }
        catch (Exception e)
        {
            Check("no unexpected exception: " + e.Message, false);
        }
        finally
        {
            try { await t.DisconnectAsync(); } catch (Exception) { }
        }

        // The Url-only constructor targets the URL's host, port and path.
        using (var server2 = new MiniWsServer())
        {
            var t2 = new WebSocketTransport(new WebSocketTransportConfig { Url = $"ws://127.0.0.1:{server2.Port}/feed?x=1" });
            try
            {
                await t2.ConnectAsync();
                Check("the Url constructor connects to the URL's path", t2.IsConnected && server2.RequestLine == "GET /feed?x=1 HTTP/1.1");
            }
            catch (Exception e) { Check("the Url constructor connects: " + e.Message, false); }
            finally { try { await t2.DisconnectAsync(); } catch (Exception) { } }
        }

        // Nothing listening: ConnectAsync must fail instead of reporting a connection.
        var probe = new TcpListener(IPAddress.Loopback, 0);
        probe.Start();
        int deadPort = ((IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();
        var t3 = new WebSocketTransport(new WebSocketTransportConfig { Url = $"ws://127.0.0.1:{deadPort}/", TimeoutMs = 2000 });
        bool threw = false;
        try { await t3.ConnectAsync(); } catch (Exception) { threw = true; }
        Check("ConnectAsync to a closed port throws", threw && !t3.IsConnected);
        bool sendThrew = false;
        try { await t3.SendAsync(new byte[] { 1 }); } catch (InvalidOperationException) { sendThrew = true; }
        Check("SendAsync when not connected throws", sendThrew);

        Console.WriteLine($"\n{_run - _failed}/{_run} transport checks passed");
        return _failed == 0 ? 0 : 1;
    }
}
