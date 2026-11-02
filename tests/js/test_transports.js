#!/usr/bin/env node
// Loopback tests for the concrete TCP, UDP and WebSocket transports of the TypeScript/JavaScript
// SDK. They run the compiled SDK in src/struct_frame/boilerplate/js (built from the TypeScript
// source), so they cover both languages. Every wait is bounded, so a misbehaving socket fails the
// test instead of hanging it.
'use strict';

const net = require('net');
const dgram = require('dgram');
const crypto = require('crypto');
const path = require('path');

const sdk = path.join(__dirname, '..', '..', 'src', 'struct_frame', 'boilerplate', 'js', 'struct-frame-sdk');
const { TcpTransport } = require(path.join(sdk, 'tcp-transport.js'));
const { UdpTransport } = require(path.join(sdk, 'udp-transport.js'));
const { WebSocketTransport } = require(path.join(sdk, 'websocket-transport.js'));

let run = 0;
let failed = 0;
function check(name, ok, detail) {
  run++;
  if (!ok) failed++;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${ok || !detail ? '' : ' -- ' + detail}`);
}

function until(predicate, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const deadline = Date.now() + timeoutMs;
    const tick = () => {
      if (predicate()) return resolve(true);
      if (Date.now() > deadline) return resolve(false);
      setTimeout(tick, 5);
    };
    tick();
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const bytes = (...v) => new Uint8Array(v);
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

function listen(server) {
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));
}

// ---- TCP -------------------------------------------------------------------------------------
async function testTcp() {
  console.log('TCP transport');
  let serverSocket = null;
  const received = [];
  const server = net.createServer((s) => {
    serverSocket = s;
    s.on('data', (d) => received.push(...d));
  });
  const port = await listen(server);

  const t = new TcpTransport({ host: '127.0.0.1', port });
  const got = [];
  let closed = 0;
  let errors = 0;
  t.onData((d) => got.push(...d));
  t.onClose(() => closed++);
  t.onError(() => errors++);

  check('isConnected() false before connect', t.isConnected() === false);
  await t.connect();
  check('isConnected() true after connect', t.isConnected() === true);

  const n = await t.send(bytes(1, 2, 3, 4));
  check('send() resolves with the byte count', n === 4);
  check('server receives the bytes sent', await until(() => received.length === 4) && same(received, [1, 2, 3, 4]));

  await until(() => serverSocket !== null);
  serverSocket.write(Buffer.from([9, 8, 7]));
  check('onData delivers bytes sent by the peer', await until(() => got.length === 3) && same(got, [9, 8, 7]));

  serverSocket.write(Buffer.from([1]));
  serverSocket.write(Buffer.from([2]));
  serverSocket.write(Buffer.from([3]));
  check('back-to-back peer writes arrive in order', await until(() => got.length === 6) && same(got.slice(3), [1, 2, 3]));

  serverSocket.destroy();
  check('peer close fires onClose', await until(() => closed === 1));
  check('isConnected() false after peer close', t.isConnected() === false);
  let sendRejected = false;
  try { await t.send(bytes(1)); } catch (_) { sendRejected = true; }
  check('send() on a closed transport rejects', sendRejected);

  const t2 = new TcpTransport({ host: '127.0.0.1', port });
  await t2.connect();
  let closed2 = 0;
  t2.onClose(() => closed2++);
  await t2.disconnect();
  check('disconnect() clears isConnected()', t2.isConnected() === false);
  check('disconnect() fires onClose once', await until(() => closed2 === 1) && (await sleep(50), closed2 === 1));

  // Connection refused: grab a free port and close it again.
  const probe = net.createServer();
  const freePort = await listen(probe);
  await new Promise((r) => probe.close(r));
  const t3 = new TcpTransport({ host: '127.0.0.1', port: freePort, timeout: 1000 });
  let refused = false;
  try { await t3.connect(); } catch (_) { refused = true; }
  check('connect() to a closed port rejects', refused);
  check('isConnected() stays false after a failed connect', t3.isConnected() === false);

  // Auto-reconnect after a peer close.
  let conns = 0;
  const server2 = net.createServer((s) => { conns++; if (conns === 1) setTimeout(() => s.destroy(), 20); });
  const port2 = await listen(server2);
  const t4 = new TcpTransport({ host: '127.0.0.1', port: port2, autoReconnect: true, reconnectDelay: 50, maxReconnectAttempts: 5 });
  await t4.connect();
  check('autoReconnect reconnects after the peer closes', await until(() => conns >= 2 && t4.isConnected(), 3000));
  await t4.disconnect();
  const before = conns;
  await sleep(200);
  check('an intentional disconnect() does not reconnect', conns === before);

  server.close();
  server2.close();
}

// ---- UDP -------------------------------------------------------------------------------------
async function testUdp() {
  console.log('UDP transport');
  const peer = dgram.createSocket('udp4');
  const peerGot = [];
  let peerRemote = null;
  peer.on('message', (m, r) => { peerGot.push(...m); peerRemote = r; });
  await new Promise((r) => peer.bind(0, '127.0.0.1', r));
  const peerPort = peer.address().port;

  const t = new UdpTransport({ remoteHost: '127.0.0.1', remotePort: peerPort, localAddress: '127.0.0.1' });
  const got = [];
  t.onData((d) => got.push(...d));
  await t.connect();
  check('isConnected() true after connect', t.isConnected() === true);

  const n = await t.send(bytes(5, 6, 7));
  check('send() resolves with the byte count', n === 3);
  check('peer receives the datagram', await until(() => peerGot.length === 3) && same(peerGot, [5, 6, 7]));

  peer.send(Buffer.from([40, 41]), peerRemote.port, '127.0.0.1');
  check('onData delivers a datagram from the peer', await until(() => got.length === 2) && same(got, [40, 41]));

  await t.disconnect();
  check('disconnect() clears isConnected()', t.isConnected() === false);

  const r = new UdpTransport({ remoteHost: '127.0.0.1', remotePort: peerPort, localAddress: '127.0.0.1',
                               autoReconnect: true, reconnectDelay: 30 });
  await r.connect();
  await r.disconnect();
  await sleep(200);
  check('an intentional disconnect() does not rebind (autoReconnect)', r.isConnected() === false);
  peer.close();
}

// ---- WebSocket (minimal in-test server) ------------------------------------------------------
function wsServer(onConnection) {
  const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
  const server = net.createServer((sock) => {
    let buf = Buffer.alloc(0);
    let upgraded = false;
    const conn = {
      sock,
      received: [],
      sendBinary(data) {
        const payload = Buffer.from(data);
        sock.write(Buffer.concat([Buffer.from([0x82, payload.length]), payload]));
      },
      close() { sock.write(Buffer.from([0x88, 0x00])); sock.end(); },
    };
    sock.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      if (!upgraded) {
        const end = buf.indexOf('\r\n\r\n');
        if (end < 0) return;
        const key = /Sec-WebSocket-Key: (.+)\r\n/i.exec(buf.slice(0, end).toString())[1].trim();
        const accept = crypto.createHash('sha1').update(key + GUID).digest('base64');
        sock.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
        buf = buf.slice(end + 4);
        upgraded = true;
        onConnection(conn);
      }
      while (upgraded && buf.length >= 2) {
        const opcode = buf[0] & 0x0f;
        const len = buf[1] & 0x7f; // test payloads are < 126 bytes
        if (buf.length < 6 + len) return;
        const mask = buf.slice(2, 6);
        const payload = Buffer.from(buf.slice(6, 6 + len)).map((b, i) => b ^ mask[i % 4]);
        buf = buf.slice(6 + len);
        if (opcode === 2 || opcode === 1) conn.received.push(...payload);
      }
    });
    sock.on('error', () => {});
  });
  return server;
}

async function testWebSocket() {
  console.log('WebSocket transport');
  if (typeof WebSocket === 'undefined') {
    console.log('  SKIP  global WebSocket not available in this Node version');
    return;
  }
  let conn = null;
  const server = wsServer((c) => { conn = c; });
  const port = await listen(server);

  const t = new WebSocketTransport({ url: `ws://127.0.0.1:${port}` });
  const got = [];
  let closed = 0;
  t.onData((d) => got.push(...d));
  t.onClose(() => closed++);
  await t.connect();
  check('isConnected() true after connect', t.isConnected() === true);

  await t.send(bytes(11, 12, 13));
  await until(() => conn !== null);
  check('server receives a binary message', await until(() => conn.received.length === 3) && same(conn.received, [11, 12, 13]));

  conn.sendBinary([21, 22, 23, 24]);
  check('onData delivers a binary message from the peer', await until(() => got.length === 4) && same(got, [21, 22, 23, 24]));

  conn.close();
  check('server close fires onClose', await until(() => closed === 1, 3000));
  check('isConnected() false after server close', t.isConnected() === false);

  // With autoReconnect on, an intentional disconnect() must not reconnect.
  let connections = 0;
  const server2 = wsServer(() => { connections++; });
  const port2 = await listen(server2);
  const r = new WebSocketTransport({ url: `ws://127.0.0.1:${port2}`, autoReconnect: true, reconnectDelay: 30 });
  await r.connect();
  await until(() => connections === 1);
  await r.disconnect();
  await sleep(250);
  check('an intentional disconnect() does not reconnect', connections === 1 && !r.isConnected());
  server.close();
  server2.close();
}

(async () => {
  const watchdog = setTimeout(() => { console.log('FAIL  transport tests timed out'); process.exit(2); }, 60000);
  try {
    await testTcp();
    await testUdp();
    await testWebSocket();
  } catch (e) {
    check('no unexpected exception', false, e && e.stack);
  }
  clearTimeout(watchdog);
  console.log(`\n${run - failed}/${run} transport checks passed`);
  process.exit(failed === 0 ? 0 : 1);
})();
