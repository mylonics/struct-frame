// Stream driver: node stream_driver.js <profile> <stream.bin> <chunk>
// Runs the compiled runtime (boilerplate/js is built from the TypeScript source), so this
// covers TypeScript too. The message table matches tests/fuzz/corpus.py.
const fs = require('fs');
const path = require('path');
const fp = require(path.join(__dirname, '..', '..', '..', 'src', 'struct_frame', 'boilerplate', 'js', 'frame-profiles.js'));

const TABLE = { 1: [8, 11, 22], 2: [32, 33, 44], 3: [100, 55, 66], 4: [1, 77, 88], 5: [200, 99, 111] };
const CONFIGS = {
  standard: fp.ProfileStandardConfig, sensor: fp.ProfileSensorConfig, ipc: fp.ProfileIPCConfig,
  bulk: fp.ProfileBulkConfig, network: fp.ProfileNetworkConfig,
};

function getInfo(id) {
  const e = TABLE[id];
  return e ? { size: e[0], minSize: e[0], magic1: e[1], magic2: e[2] } : undefined;
}

function fnv1a(d) {
  let h = 0x811c9dc5;
  for (const b of d) h = Math.imul(h ^ b, 0x01000193) >>> 0;
  return h;
}

const [profile, file, chunkArg] = process.argv.slice(2);
const chunk = Number(chunkArg);
const data = fs.readFileSync(file);
const reader = new fp.AccumulatingReader(CONFIGS[profile], getInfo, 1024);
const out = [];
for (let pos = 0; pos < data.length; pos += chunk) {
  reader.addData(new Uint8Array(data.subarray(pos, Math.min(pos + chunk, data.length))));
  for (let guard = 0; guard < 1000000; guard++) {
    const r = reader.tryNext();
    if (r === null) break;
    if (r.valid) out.push(`${r.msgId} ${r.msgLen} ${fnv1a(r.msgData.subarray(0, r.msgLen))}`);
  }
}
process.stdout.write(out.map((l) => l + '\n').join(''));
