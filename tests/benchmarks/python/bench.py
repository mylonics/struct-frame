#!/usr/bin/env python3
import argparse, json, os, platform, socket, time
from datetime import datetime, timezone
from pathlib import Path

SCENARIOS = [
    ("standard", "standard", 0x71, 32, False),
    ("bulk", "bulk", 0x74, 512, False),
    ("network", "network", 0x78, 96, True),
]

def fletcher(data):
    a = b = 0
    for x in data:
        a = (a + x) & 0xff; b = (b + a) & 0xff
    return a, b

def encode(profile, type_byte, payload_len, network=False, seq=1):
    payload = bytes((i * 31 + payload_len) & 0xff for i in range(payload_len))
    body = bytearray()
    if network:
        body += bytes([seq & 0xff, 1, 42, payload_len & 0xff, (payload_len >> 8) & 0xff, 7, 3])
    elif profile == "bulk":
        body += bytes([payload_len & 0xff, (payload_len >> 8) & 0xff, 7, 3])
    else:
        body += bytes([payload_len & 0xff, 3])
    body += payload
    c1, c2 = fletcher(body)
    return bytes([0x90, type_byte]) + bytes(body) + bytes([c1, c2])

def decode(frame):
    if frame[0] != 0x90 or not (0x70 <= frame[1] <= 0x78):
        raise ValueError("bad sync")
    off = 2; ptype = frame[1] - 0x70
    if ptype == 8:
        off += 3; length = frame[off] | (frame[off+1] << 8); off += 3; off += 1
    elif ptype == 4:
        length = frame[off] | (frame[off+1] << 8); off += 4
    else:
        length = frame[off]; off += 2
    end = off + length
    c1, c2 = fletcher(frame[2:end])
    if frame[end] != c1 or frame[end+1] != c2:
        raise ValueError("bad crc")
    return frame[off:end]

def pct(values, q):
    values.sort(); return values[min(len(values)-1, int((len(values)-1) * q))]

def run_case(name, profile, op, iterations):
    scenario = next(s for s in SCENARIOS if s[0] == profile)
    _, *encode_args = scenario
    frames = [encode(*encode_args, seq=i) for i in range(8)]
    lat = []; total_bytes = 0; start = time.perf_counter_ns()
    for i in range(iterations):
        t0 = time.perf_counter_ns()
        if op == "encode":
            frame = encode(*encode_args, seq=i); total_bytes += len(frame)
        elif op == "decode":
            frame = frames[i % len(frames)]
            decode(frame)
            total_bytes += len(frame)
        else:
            frame = encode(*encode_args, seq=i); decode(frame); total_bytes += len(frame)
        lat.append(time.perf_counter_ns() - t0)
    duration = max((time.perf_counter_ns() - start) / 1e9, 1e-9)
    return {"name": name, "profile": profile, "operation": op, "msg_count": iterations, "bytes_total": total_bytes,
            "duration_s": duration, "msg_per_sec": iterations / duration, "mb_per_sec": total_bytes / duration / 1_000_000,
            "latency_ns": {"p50": pct(lat, .50), "p95": pct(lat, .95), "p99": pct(lat, .99), "max": max(lat)}}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--iterations", type=int, default=int(os.getenv("BENCH_ITERATIONS", "50000"))); ap.add_argument("--output", default="tests/benchmarks/results/python.json")
    args = ap.parse_args(); scenarios=[]
    for profile, *_ in SCENARIOS:
        for op in ("encode", "decode"):
            scenarios.append(run_case(f"{profile}_{op}", profile, op, args.iterations))
    result = {"schema_version":"1", "language":"python", "runner_version":"tier-d-1", "timestamp":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
              "host":{"os":platform.system(), "arch":platform.machine(), "cpu":platform.processor() or socket.gethostname()}, "scenarios":scenarios}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True); Path(args.output).write_text(json.dumps(result, indent=2)+"\n")
if __name__ == "__main__": main()
