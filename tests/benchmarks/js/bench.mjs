// Tier D benchmark for JavaScript: runs the generated message classes and the real runtime
// (BufferWriter / BufferReader) from tests/benchmarks/generated/js, built by run_all.py from
// tests/benchmarks/schema/bench.sf. Emits results matching schema.json.
import { writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { arch, cpus, platform } from 'node:os';
import { performance } from 'node:perf_hooks';

const args = process.argv.slice(2);
const argValue = (flag, fallback) => (args.includes(flag) ? args[args.indexOf(flag) + 1] : fallback);
const iterations = Number(argValue('--iterations', process.env.BENCH_ITERATIONS || 50000));
const output = argValue('--output', 'tests/benchmarks/results/js.json');
const genDir = resolve(argValue('--gen-dir', 'tests/benchmarks/generated/js'));

const require = createRequire(import.meta.url);
const fp = require(`${genDir}/frame-profiles.js`);
const gen = require(`${genDir}/bench.structframe.js`);

const BATCH = 64;
const WARMUP_BATCHES = 20;
const SCENARIOS = [
  ['standard', fp.ProfileStandardConfig, gen.Small, false],
  ['bulk', fp.ProfileBulkConfig, gen.Large, false],
  ['network', fp.ProfileNetworkConfig, gen.Medium, true],
  ['sensor', fp.ProfileSensorConfig, gen.Small, false],
  ['ipc', fp.ProfileIPCConfig, gen.Small, false],
];
let sink = 0;

function pct(values, q) {
  const v = [...values].sort((a, b) => a - b);
  return v[Math.min(v.length - 1, Math.floor((v.length - 1) * q))];
}

function runCase(name, config, Msg, addressed, op) {
  const size = Msg._size;
  const msg = new Msg({ data: Array.from({ length: size }, (_, i) => (i * 31) & 0xff) });
  const writer = new fp.BufferWriter(config, 2048);
  const encodeOnce = (i) => {
    writer.reset();
    const n = writer.write(msg, addressed ? { seq: i & 0xff, sysId: 1, compId: 42 } : {});
    if (n === 0) throw new Error('encode failed');
    return n;
  };
  const frames = [];
  for (let i = 0; i < 8; i++) {
    encodeOnce(i);
    frames.push(writer.data());
  }
  const decodeOnce = (i) => {
    const frame = frames[i & 7];
    const info = new fp.BufferReader(config, frame, gen.getMessageInfo).next();
    if (!info.valid) throw new Error('decode failed');
    sink += Msg.deserialize(info).data[0];
    return frame.length;
  };
  const one = op === 'encode' ? encodeOnce : decodeOnce;

  for (let i = 0; i < WARMUP_BATCHES * BATCH; i++) sink += one(i);

  const batches = Math.max(1, Math.floor(iterations / BATCH));
  const lat = [];
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
  language: 'js',
  runner_version: 'tier-d-2-generated',
  timestamp: new Date().toISOString(),
  host: { os: platform(), arch: arch(), cpu: cpus()[0]?.model || 'unknown' },
  scenarios: [],
};
for (const [name, config, Msg, addressed] of SCENARIOS) {
  for (const op of ['encode', 'decode']) out.scenarios.push(runCase(name, config, Msg, addressed, op));
}
if (sink === -1) console.log(sink);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(out, null, 2) + '\n');
