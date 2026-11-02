// Tier D benchmark for C#: runs the generated message classes and the real runtime
// (BufferWriter / BufferReader) from tests/benchmarks/generated/csharp, built by run_all.py from
// tests/benchmarks/schema/bench.sf. Emits results matching schema.json.
using System.Diagnostics;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;
using StructFrame;
using StructFrame.Bench;
using StructFrame.Framing;
using StructFrame.Profiles;

const int Batch = 64;
const int WarmupBatches = 20;

int iterations = int.TryParse(Environment.GetEnvironmentVariable("BENCH_ITERATIONS"), out var envIters) ? envIters : 50000;
string output = "tests/benchmarks/results/csharp.json";
for (int i = 0; i < args.Length - 1; i++)
{
    if (args[i] == "--iterations") iterations = int.Parse(args[i + 1]);
    if (args[i] == "--output") output = args[i + 1];
}

long sink = 0;
var scenarios = new List<string>();

void Both(string name, ProfileConfig cfg, IStructFrameMessage msg, Func<FrameMsgInfo, byte> decode, bool addressed)
{
    foreach (var op in new[] { "encode", "decode" })
        scenarios.Add(Run(name, cfg, msg, decode, addressed, op));
}

string Run(string name, ProfileConfig cfg, IStructFrameMessage msg, Func<FrameMsgInfo, byte> decode, bool addressed, string op)
{
    var writer = new BufferWriter(cfg);
    var frameBuf = new byte[2048];
    int EncodeOnce(int i)
    {
        writer.SetBuffer(frameBuf);
        int n = addressed ? writer.Write(msg, (byte)i, 1, 42) : writer.Write(msg);
        if (n == 0) throw new InvalidOperationException("encode failed");
        return n;
    }
    int len = EncodeOnce(0);
    var frame = frameBuf.AsSpan(0, len).ToArray();
    var reader = new BufferReader(cfg, MessageDefinitions.GetMessageInfo);
    int DecodeOnce()
    {
        reader.SetBuffer(frame);
        var info = reader.Next();
        if (!info.Valid) throw new InvalidOperationException("decode failed");
        sink += decode(info);
        return frame.Length;
    }
    Func<int, int> one = op == "encode" ? EncodeOnce : _ => DecodeOnce();

    for (int i = 0; i < WarmupBatches * Batch; i++) sink += one(i);

    int batches = Math.Max(1, iterations / Batch);
    var lat = new long[batches];
    long bytes = 0;
    double tickNs = 1e9 / Stopwatch.Frequency;
    var total = Stopwatch.StartNew();
    for (int b = 0; b < batches; b++)
    {
        long t0 = Stopwatch.GetTimestamp();
        for (int j = 0; j < Batch; j++) bytes += one(b * Batch + j);
        lat[b] = (long)((Stopwatch.GetTimestamp() - t0) * tickNs / Batch);
    }
    double dur = Math.Max(total.Elapsed.TotalSeconds, 1e-9);
    int count = batches * Batch;
    Array.Sort(lat);
    long P(double q) => lat[Math.Min(lat.Length - 1, (int)((lat.Length - 1) * q))];
    return string.Create(CultureInfo.InvariantCulture,
        $"{{\"name\":\"{name}_{op}\",\"profile\":\"{name}\",\"operation\":\"{op}\",\"msg_count\":{count}," +
        $"\"bytes_total\":{bytes},\"duration_s\":{dur:F9},\"msg_per_sec\":{count / dur:F3},\"mb_per_sec\":{bytes / dur / 1e6:F3}," +
        $"\"latency_ns\":{{\"p50\":{P(0.5)},\"p95\":{P(0.95)},\"p99\":{P(0.99)},\"max\":{lat[^1]}}}}}");
}

static byte[] Pattern(int n) => Enumerable.Range(0, n).Select(i => (byte)(i * 31)).ToArray();

Both("standard", Profiles.Standard, new Small { Data = Pattern(32) }, info => Small.Deserialize(info).Data[0], false);
Both("bulk", Profiles.Bulk, new Large { Data = Pattern(512) }, info => Large.Deserialize(info).Data[0], false);
Both("network", Profiles.Network, new Medium { Data = Pattern(96) }, info => Medium.Deserialize(info).Data[0], true);
Both("sensor", Profiles.Sensor, new Small { Data = Pattern(32) }, info => Small.Deserialize(info).Data[0], false);
Both("ipc", Profiles.IPC, new Small { Data = Pattern(32) }, info => Small.Deserialize(info).Data[0], false);

var json = new StringBuilder();
json.Append("{\"schema_version\":\"1\",\"language\":\"csharp\",\"runner_version\":\"tier-d-2-generated\",");
json.Append($"\"timestamp\":\"{DateTime.UtcNow:yyyy-MM-ddTHH:mm:ssZ}\",");
json.Append($"\"host\":{{\"os\":\"{RuntimeInformation.OSDescription.Replace("\"", "'")}\",\"arch\":\"{RuntimeInformation.OSArchitecture}\",\"cpu\":\"unknown\"}},");
json.Append("\"scenarios\":[").Append(string.Join(",", scenarios)).Append("]}\n");
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, json.ToString());
if (sink == long.MinValue) Console.WriteLine(sink);
