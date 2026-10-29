// Stream driver: StreamDriver <profile> <stream.bin> <chunk>
// The message table matches tests/fuzz/corpus.py.
using System;
using System.IO;
using System.Text;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;

internal static class Program
{
    private static MessageInfo? GetInfo(int id) => id switch
    {
        1 => new MessageInfo(8, 11, 22),
        2 => new MessageInfo(32, 33, 44),
        3 => new MessageInfo(100, 55, 66),
        4 => new MessageInfo(1, 77, 88),
        5 => new MessageInfo(200, 99, 111),
        _ => null,
    };

    private static uint Fnv1a(byte[] d, int off, int n)
    {
        uint h = 0x811C9DC5u;
        for (int i = 0; i < n; i++) h = (h ^ d[off + i]) * 0x01000193u;
        return h;
    }

    private static int Main(string[] args)
    {
        if (args.Length != 3) return 64;
        ProfileConfig cfg = args[0] switch
        {
            "standard" => Profiles.Standard,
            "sensor" => Profiles.Sensor,
            "ipc" => Profiles.IPC,
            "bulk" => Profiles.Bulk,
            "network" => Profiles.Network,
            _ => throw new ArgumentException(args[0]),
        };
        int chunk = int.Parse(args[2]);
        byte[] data = File.ReadAllBytes(args[1]);
        var reader = new AccumulatingReader(cfg, 1024, GetInfo);
        var sb = new StringBuilder();
        for (int pos = 0; pos < data.Length; pos += chunk)
        {
            int len = Math.Min(chunk, data.Length - pos);
            var slice = new byte[len];
            Array.Copy(data, pos, slice, 0, len);
            reader.AddData(slice);
            for (int guard = 0; guard < 1000000 && reader.TryNext(out FrameMsgInfo f); guard++)
            {
                if (f.Valid && f.MsgData != null)
                    sb.Append(f.MsgId).Append(' ').Append(f.MsgLen).Append(' ')
                      .Append(Fnv1a(f.MsgData, f.MsgDataOffset, f.MsgLen)).Append('\n');
            }
        }
        Console.Out.Write(sb.ToString());
        return 0;
    }
}
