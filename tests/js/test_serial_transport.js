#!/usr/bin/env node
// Tests for the TypeScript/JavaScript SDK's SerialTransport. The transport is written against the
// `serialport` package; a small fake with the same event API (open/data/error/close, write, drain,
// close) is substituted through Node's module loader, so no device or native package is needed.
// It runs the compiled SDK in src/struct_frame/boilerplate/js (built from the TypeScript source).
'use strict';

const path = require('path');
const Module = require('module');
const { EventEmitter } = require('events');

const ports = [];
class FakeSerialPort extends EventEmitter {
  constructor(options) {
    super();
    this.options = options;
    this.isOpen = false;
    this.written = [];
    ports.push(this);
    setImmediate(() => {
      if (options.path === 'MISSING') {
        this.emit('error', new Error('Opening MISSING: File not found'));
      } else {
        this.isOpen = true;
        this.emit('open');
      }
    });
  }
  write(buf, cb) { this.written.push(...buf); setImmediate(() => cb && cb(null)); return true; }
  drain(cb) { setImmediate(() => cb && cb(null)); }
  close(cb) {
    this.isOpen = false;
    setImmediate(() => { this.emit('close'); if (cb) cb(null); });
  }
  // test helpers
  receive(bytes) { this.emit('data', Buffer.from(bytes)); }
  unplug() { this.isOpen = false; this.emit('close'); }
}

const realLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === 'serialport') return { SerialPort: FakeSerialPort };
  return realLoad.apply(this, arguments);
};

const sdk = path.join(__dirname, '..', '..', 'src', 'struct_frame', 'boilerplate', 'js', 'struct-frame-sdk');
const { SerialTransport } = require(path.join(sdk, 'serial-transport.js'));

let run = 0;
let failed = 0;
function check(name, ok) {
  run++;
  if (!ok) failed++;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(p, ms = 2000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { if (p()) return true; await sleep(5); }
  return p();
}

(async () => {
  console.log('Serial transport');
  const t = new SerialTransport({ path: 'COM7', baudRate: 115200 });
  const got = [];
  let closed = 0;
  t.onData((d) => got.push(...d));
  t.onClose(() => closed++);

  await t.connect();
  const port = ports[ports.length - 1];
  check('connect opens the port with the configured settings',
    t.isConnected() && port.options.path === 'COM7' && port.options.baudRate === 115200 && port.options.dataBits === 8);
  check('send resolves with the byte count after drain', (await t.send(new Uint8Array([1, 2, 3]))) === 3);
  check('the bytes reach the port', port.written.join(',') === '1,2,3');
  port.receive([9, 8, 7]);
  check('onData delivers received bytes', await until(() => got.join(',') === '9,8,7'));
  await t.disconnect();
  check('disconnect clears isConnected', !t.isConnected());
  let rejected = false;
  try { await t.send(new Uint8Array([1])); } catch (_) { rejected = true; }
  check('send after disconnect rejects', rejected);

  const bad = new SerialTransport({ path: 'MISSING', baudRate: 9600 });
  let errored = false;
  try { await bad.connect(); } catch (_) { errored = true; }
  check('connect rejects when the port cannot be opened', errored && !bad.isConnected());

  // Unplugging the device fires onClose; an intentional disconnect must not trigger a reconnect.
  const r = new SerialTransport({ path: 'COM8', baudRate: 9600, autoReconnect: true, reconnectDelay: 20 });
  let rClosed = 0;
  r.onClose(() => rClosed++);
  await r.connect();
  const before = ports.length;
  ports[ports.length - 1].unplug();
  check('unplugging fires onClose', await until(() => rClosed === 1));
  check('autoReconnect reopens the port after it is unplugged', await until(() => ports.length === before + 1 && r.isConnected()));
  await r.disconnect();
  const opened = ports.length;
  await sleep(150);
  check('an intentional disconnect does not reconnect', ports.length === opened && !r.isConnected());

  console.log(`\n${run - failed}/${run} transport checks passed`);
  process.exit(failed === 0 ? 0 : 1);
})().catch((e) => { console.log('FAIL  unexpected exception', e); process.exit(1); });
