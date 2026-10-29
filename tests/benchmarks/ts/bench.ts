// Tier D benchmark for TypeScript: runs the generated TypeScript message classes and runtime
// (BufferWriter / BufferReader) from tests/benchmarks/generated/ts, built by run_all.py from
// tests/benchmarks/schema/bench.sf and compiled with tsc. Emits results matching schema.json.
import { writeFileSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { arch, cpus, platform } from 'os';
import { performance } from 'perf_hooks';
import {
  BufferReader, BufferWriter, FrameProfileConfig,
  ProfileBulkConfig, ProfileIPCConfig, ProfileNetworkConfig, ProfileSensorConfig, ProfileStandardConfig,
} from '../generated/ts/frame-profiles';
import { Large, Medium, Small, getMessageInfo } from '../generated/ts/bench.structframe';

type MsgClass = typeof Small | typeof Medium | typeof Large;

const args = process.argv.slice(2);
const argValue = (flag: string, fallback: string): string =>
  args.includes(flag) ? args[args.indexOf(flag) + 1] : fallback;
const iterations = Number(argValue('--iterations', process.env.BENCH_ITERATIONS || '50000'));
const output = argValue('--output', 'tests/benchmarks/results/ts.json');

const BATCH = 64;
const WARMUP_BATCHES = 20;
const SCENARIOS: Array<[string, FrameProfileConfig, MsgClass, boolean]> = [
  ['standard', ProfileStandardConfig, Small, false],
  ['bulk', ProfileBulkConfig, Large, false],
  ['network', ProfileNetworkConfig, Medium, true],
  ['sensor', ProfileSensorConfig, Small, false],
  ['ipc', ProfileIPCConfig, Small, false],
];
let sink = 0;

function pct(values: number[], q: number): number {
  const v = [...values].sort((a, b) => a - b);
  return v[Math.min(v.length - 1, Math.floor((v.length - 1) * q))];
}

function runCase(name: string, config: FrameProfileConfig, Msg: MsgClass, addressed: boolean, op: string) {
  const msg = new Msg({ data: Array.from({ length: Msg._size }, (_, i) => (i * 31) & 0xff) });
  const writer = new BufferWriter(config, 2048);
  const encodeOnce = (i: number): number => {
    writer.reset();
    const n = writer.write(msg, addressed ? { seq: i & 0xff, sysId: 1, compId: 42 } : {});
    if (n === 0) throw new Error('encode failed');
    return n;
  };
  const frames: Uint8Array[] = [];
  for (let i = 0; i < 8; i++) {
    encodeOnce(i);
    frames.push(writer.data());
  }
  const decodeOnce = (i: number): number => {
    const frame = frames[i & 7];
    const info = new BufferReader(config, frame, getMessageInfo).next();
    if (!info.valid) throw new Error('decode failed');
    sink += Msg.deserialize(info).data[0];
    return frame.length;
  };
  const one = op === 'encode' ? encodeOnce : decodeOnce;

  for (let i = 0; i < WARMUP_BATCHES * BATCH; i++) sink += one(i);

  const batches = Math.max(1, Math.floor(iterations / BATCH));
  const lat: number[] = [];
  let bytes = 0;
  const start = performance.now();
  for (let b = 0; b < batches; b++) {
    const t0 = performance.now();
    for (let j = 0; j < BATCH; j++) bytes += one(b * BATCH + j);
    lat.push(Math.round(((performance.now() - t0) * 1e6) / BATCH));
  }
  const dur = Math.max((performance.now() - start) / 1000, 1e-9);
  const count = batches * BATCH;
  return {
    name: `${name}_${op}`, profile: name, operation: op,
    msg_count: count, bytes_total: bytes, duration_s: dur,
    msg_per_sec: count / dur, mb_per_sec: bytes / dur / 1e6,
    latency_ns: { p50: pct(lat, 0.5), p95: pct(lat, 0.95), p99: pct(lat, 0.99), max: Math.max(...lat) },
  };
}

const out = {
  schema_version: '1',
  language: 'ts',
  runner_version: 'tier-d-2-generated',
  timestamp: new Date().toISOString(),
  host: { os: platform(), arch: arch(), cpu: cpus()[0]?.model || 'unknown' },
  scenarios: [] as object[],
};
for (const [name, config, Msg, addressed] of SCENARIOS) {
  for (const op of ['encode', 'decode']) out.scenarios.push(runCase(name, config, Msg, addressed, op));
}
if (sink === -1) console.log(sink);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(out, null, 2) + '\n');
