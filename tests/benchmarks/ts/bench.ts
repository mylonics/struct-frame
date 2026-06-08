import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { arch, cpus, platform } from 'node:os';
import { performance } from 'node:perf_hooks';

type Scenario = [string, string, number, number, boolean];

const scenarios: Scenario[] = [
  ['standard', 'standard', 0x71, 32, false],
  ['bulk',     'bulk',     0x74, 512, false],
  ['network',  'network',  0x78, 96,  true],
];

function fletcher(buf: Buffer): [number, number] {
  let a = 0, b = 0;
  for (const x of buf) {
    a = (a + x) & 0xff;
    b = (b + a) & 0xff;
  }
  return [a, b];
}

function verifyPayload(payload: Buffer): void {
  const payloadLen = payload.length;
  if (payloadLen === 0) return;
  const checks = new Set([0, Math.floor(payloadLen / 2), payloadLen - 1]);
  for (const i of checks) {
    const expected = (i * 31 + payloadLen) & 0xff;
    if (payload[i] !== expected) throw new Error('bad payload');
  }
}

function encode(profile: string, typeByte: number, payloadLen: number, network = false, seq = 1): Buffer {
  const payload = Buffer.alloc(payloadLen);
  for (let i = 0; i < payloadLen; i++) {
    payload[i] = (i * 31 + payloadLen) & 0xff;
  }
  const body: number[] = [];
  if (network) {
    body.push(seq & 0xff, 1, 42, payloadLen & 0xff, (payloadLen >> 8) & 0xff, 7, 3);
  } else if (profile === 'bulk') {
    body.push(payloadLen & 0xff, (payloadLen >> 8) & 0xff, 7, 3);
  } else {
    body.push(payloadLen & 0xff, 3);
  }
  const b = Buffer.concat([Buffer.from(body), payload]);
  const [c1, c2] = fletcher(b);
  return Buffer.concat([Buffer.from([0x90, typeByte]), b, Buffer.from([c1, c2])]);
}

function decode(frame: Buffer): Buffer {
  if (frame[0] !== 0x90) throw new Error('bad sync');
  let off = 2;
  const p = frame[1] - 0x70;
  let len = 0;
  if (p === 8) {
    off += 3;
    len = frame[off] | (frame[off + 1] << 8);
    off += 4;
  } else if (p === 4) {
    len = frame[off] | (frame[off + 1] << 8);
    off += 4;
  } else {
    len = frame[off];
    off += 2;
  }
  const end = off + len;
  const [c1, c2] = fletcher(frame.subarray(2, end));
  if (frame[end] !== c1 || frame[end + 1] !== c2) throw new Error('bad crc');
  const payload = frame.subarray(off, end);
  verifyPayload(payload);
  return payload;
}

function pct(v: number[], q: number): number {
  v.sort((a, b) => a - b);
  return v[Math.min(v.length - 1, Math.floor((v.length - 1) * q))];
}

function encScenario(s: Scenario, seq: number): Buffer {
  return encode(s[1], s[2], s[3], s[4], seq);
}

function runCase(name: string, profile: string, op: string, iterations: number) {
  const scenario = scenarios.find(s => s[0] === profile)!;
  const frames = Array.from({ length: 8 }, (_, i) => encScenario(scenario, i));
  const lat: number[] = [];
  let bytes = 0;
  const start = performance.now();
  for (let i = 0; i < iterations; i++) {
    const t0 = performance.now();
    if (op === 'encode') {
      const f = encScenario(scenario, i);
      bytes += f.length;
    } else {
      const f = frames[i % frames.length];
      decode(f);
      bytes += f.length;
    }
    lat.push(Math.round((performance.now() - t0) * 1e6));
  }
  const dur = Math.max((performance.now() - start) / 1000, 1e-9);
  return {
    name, profile, operation: op,
    msg_count: iterations, bytes_total: bytes, duration_s: dur,
    msg_per_sec: iterations / dur,
    mb_per_sec: bytes / dur / 1e6,
    latency_ns: {
      p50: pct(lat, 0.5), p95: pct(lat, 0.95),
      p99: pct(lat, 0.99), max: Math.max(...lat),
    },
  };
}

const args = process.argv.slice(2);
const iterations = Number(
  args[args.indexOf('--iterations') + 1] || process.env.BENCH_ITERATIONS || 50000,
);
const output = args.includes('--output')
  ? args[args.indexOf('--output') + 1]
  : 'tests/benchmarks/results/ts.json';

const out: any = {
  schema_version: '1',
  language: 'ts',
  runner_version: 'tier-d-1',
  timestamp: new Date().toISOString(),
  host: { os: platform(), arch: arch(), cpu: cpus()[0]?.model || 'unknown' },
  scenarios: [],
};
for (const [profile] of scenarios) {
  for (const op of ['encode', 'decode']) {
    out.scenarios.push(runCase(`${profile}_${op}`, profile, op, iterations));
  }
}
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(out, null, 2) + '\n');
