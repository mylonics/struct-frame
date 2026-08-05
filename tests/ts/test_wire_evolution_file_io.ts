/**
 * Cross-language x cross-version wire-evolution file I/O (TypeScript).
 * See tests/cpp/test_wire_evolution_file_io.cpp for the full rationale.
 *
 * Usage:
 *   node test_wire_evolution_file_io.js encode v1 <file>
 *   node test_wire_evolution_file_io.js encode v2 <file>
 *   node test_wire_evolution_file_io.js decode v1 <file>
 *   node test_wire_evolution_file_io.js decode v2 <file>
 *
 * Canonical values must match every other language's file_io helper:
 * header=0x1234, seq=42, crcSeed=0xDEADBEEF.
 */
import * as fs from 'fs';

import { BaseExtensionMessage as V1BaseExtensionMessage } from '../generated/ts/wire-evolution-v1.structframe';
import { BaseExtensionMessage as V2BaseExtensionMessage } from '../generated/ts/wire-evolution-v2.structframe';

const HEADER = 0x1234;
const SEQ = 42;
const CRC_SEED = 0xdeadbeef;

function doEncode(version: string, path: string): number {
  let buf: Buffer;
  if (version === 'v1') {
    const msg = new V1BaseExtensionMessage();
    msg.header = HEADER;
    msg.seq = SEQ;
    buf = msg.serialize();
  } else if (version === 'v2') {
    const msg = new V2BaseExtensionMessage();
    msg.header = HEADER;
    msg.seq = SEQ;
    msg.crcSeed = CRC_SEED;
    buf = msg.serialize();
  } else {
    console.error(`[ENCODE] FAILED: unknown version '${version}'`);
    return 1;
  }
  fs.writeFileSync(path, buf);
  console.log(`[ENCODE] SUCCESS: wrote ${buf.length} bytes (${version}) to ${path}`);
  return 0;
}

function doDecode(version: string, path: string): number {
  const buf = fs.readFileSync(path);

  if (version === 'v1') {
    const msg = V1BaseExtensionMessage.deserialize(buf);
    if (msg.header !== HEADER || msg.seq !== SEQ) {
      console.error(`[DECODE] FAILED: header=0x${msg.header.toString(16).padStart(4, '0')} ` +
                    `(expected 0x${HEADER.toString(16).padStart(4, '0')}) seq=${msg.seq} (expected ${SEQ})`);
      return 1;
    }
    console.log(`[DECODE] SUCCESS: v1 header=0x${msg.header.toString(16).padStart(4, '0')} seq=${msg.seq}`);
    return 0;
  } else if (version === 'v2') {
    const msg = V2BaseExtensionMessage.deserialize(buf);
    if (msg.header !== HEADER || msg.seq !== SEQ) {
      console.error(`[DECODE] FAILED: header=0x${msg.header.toString(16).padStart(4, '0')} ` +
                    `(expected 0x${HEADER.toString(16).padStart(4, '0')}) seq=${msg.seq} (expected ${SEQ})`);
      return 1;
    }
    // A legacy (v1-sized, 3-byte) frame decoded as v2 must fill the extension
    // with its schema default (4242, not zero); a genuine v2-sized (7-byte)
    // frame must preserve the transmitted value.
    const expectedCrc = buf.length >= V2BaseExtensionMessage._baseSize + 4 ? CRC_SEED : 4242;
    if (msg.crcSeed !== expectedCrc) {
      console.error(`[DECODE] FAILED: crcSeed=0x${msg.crcSeed.toString(16).padStart(8, '0')} ` +
                    `(expected 0x${expectedCrc.toString(16).padStart(8, '0')} for ${buf.length}-byte input)`);
      return 1;
    }
    console.log(`[DECODE] SUCCESS: v2 header=0x${msg.header.toString(16).padStart(4, '0')} ` +
                `seq=${msg.seq} crcSeed=0x${msg.crcSeed.toString(16).padStart(8, '0')} (from ${buf.length} bytes)`);
    return 0;
  }
  console.error(`[DECODE] FAILED: unknown version '${version}'`);
  return 1;
}

function main(): number {
  const args = process.argv.slice(2);
  if (args.length !== 3) {
    console.error('Usage: test_wire_evolution_file_io <encode|decode> <v1|v2> <file>');
    return 2;
  }
  const [mode, version, path] = args;
  if (mode === 'encode') return doEncode(version, path);
  if (mode === 'decode') return doDecode(version, path);
  console.error(`Unknown mode: ${mode}`);
  return 2;
}

process.exit(main());
