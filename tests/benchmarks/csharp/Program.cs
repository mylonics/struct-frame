using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;

record Scenario(string Name, string Profile, byte Type, int Len, bool Network);

class P
{
    static (byte, byte) Fletcher(byte[] d, int off, int len)
    {
        int a = 0, b = 0;
        for (int i = off; i < off + len; i++)
        {
            a = (a + d[i]) & 0xff;
            b = (b + a) & 0xff;
        }
        return ((byte)a, (byte)b);
    }

    static byte[] Encode(Scenario s, byte seq)
    {
        var body = new List<byte>();
        if (s.Network)
        {
            body.AddRange(new byte[] {
                seq, 1, 42,
                (byte)(s.Len & 0xff), (byte)(s.Len >> 8),
                7, 3,
            });
        }
        else if (s.Profile == "bulk")
        {
            body.AddRange(new byte[] {
                (byte)(s.Len & 0xff), (byte)(s.Len >> 8), 7, 3,
            });
        }
        else
        {
            body.AddRange(new byte[] { (byte)(s.Len & 0xff), 3 });
        }
        for (int i = 0; i < s.Len; i++)
        {
            body.Add((byte)((i * 31 + s.Len) & 0xff));
        }
        var bytes = body.ToArray();
        var (c1, c2) = Fletcher(bytes, 0, bytes.Length);
        return new byte[] { 0x90, s.Type }
            .Concat(bytes)
            .Concat(new byte[] { c1, c2 })
            .ToArray();
    }

    static int Decode(byte[] f)
    {
        int off = 2, len, p = f[1] - 0x70;
        if (p == 8)
        {
            off += 3;
            len = f[off] | (f[off + 1] << 8);
            off += 4;
        }
        else if (p == 4)
        {
            len = f[off] | (f[off + 1] << 8);
            off += 4;
        }
        else
        {
            len = f[off];
            off += 2;
        }
        var (c1, c2) = Fletcher(f, 2, off + len - 2);
        if (f[off + len] != c1 || f[off + len + 1] != c2)
        {
            throw new Exception("crc");
        }
        return len;
    }

    static long Pct(List<long> v, double q)
    {
        v.Sort();
        return v[(int)((v.Count - 1) * q)];
    }

    static object Run(Scenario s, string op, int iters)
    {
        var frames = Enumerable.Range(0, 8)
            .Select(i => Encode(s, (byte)i))
            .ToArray();
        var lat = new List<long>(iters);
        long bytes = 0;
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < iters; i++)
        {
            var t = Stopwatch.StartNew();
            if (op == "encode")
            {
                var f = Encode(s, (byte)i);
                bytes += f.Length;
            }
            else
            {
                var f = frames[i & 7];
                Decode(f);
                bytes += f.Length;
            }
            t.Stop();
            lat.Add((long)(t.Elapsed.TotalMilliseconds * 1_000_000));
        }
        sw.Stop();
        double dur = Math.Max(sw.Elapsed.TotalSeconds, 1e-9);
        return new
        {
            name = $"{s.Name}_{op}",
            profile = s.Profile,
            operation = op,
            msg_count = iters,
            bytes_total = bytes,
            duration_s = dur,
            msg_per_sec = iters / dur,
            mb_per_sec = bytes / dur / 1_000_000,
            latency_ns = new
            {
                p50 = Pct(new List<long>(lat), 0.50),
                p95 = Pct(new List<long>(lat), 0.95),
                p99 = Pct(new List<long>(lat), 0.99),
                max = lat.Max(),
            },
        };
    }

    static int Main(string[] args)
    {
        int iters = int.TryParse(
            Environment.GetEnvironmentVariable("BENCH_ITERATIONS"),
            out var e) ? e : 50_000;
        string output = "tests/benchmarks/results/csharp.json";
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--iterations" && i + 1 < args.Length)
            {
                iters = int.Parse(args[++i]);
            }
            else if (args[i] == "--output" && i + 1 < args.Length)
            {
                output = args[++i];
            }
        }
        var scens = new[]
        {
            new Scenario("standard", "standard", 0x71, 32,  false),
            new Scenario("bulk",     "bulk",     0x74, 512, false),
            new Scenario("network",  "network",  0x78, 96,  true),
        };
        var rows = new List<object>();
        foreach (var s in scens)
        {
            rows.Add(Run(s, "encode", iters));
            rows.Add(Run(s, "decode", iters));
        }
        var outObj = new
        {
            schema_version = "1",
            language = "csharp",
            runner_version = "tier-d-1",
            timestamp = DateTimeOffset.UtcNow.ToString("o"),
            host = new
            {
                os = RuntimeInformation.OSDescription,
                arch = RuntimeInformation.OSArchitecture.ToString(),
                cpu = "unknown",
            },
            scenarios = rows,
        };
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        File.WriteAllText(
            output,
            JsonSerializer.Serialize(
                outObj,
                new JsonSerializerOptions { WriteIndented = true }) + "\n");
        return 0;
    }
}
