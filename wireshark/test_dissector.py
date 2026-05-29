#!/usr/bin/env python3
import json, os, shutil, struct, subprocess, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'wireshark' / 'struct_frame.lua'
OUT = ROOT / 'wireshark' / '_test_packets'
LINKTYPE_USER0 = 147

def fletcher(data):
    a = b = 0
    for x in data:
        a = (a + x) & 0xff; b = (b + a) & 0xff
    return bytes([a, b])

def frame_standard(payload=b'abc', msg_id=3):
    body = bytes([len(payload), msg_id]) + payload
    return bytes([0x90, 0x71]) + body + fletcher(body)

def frame_bulk(payload=bytes(range(64)), package_id=7, msg_id=3):
    body = bytes([len(payload) & 0xff, len(payload) >> 8, package_id, msg_id]) + payload
    return bytes([0x90, 0x74]) + body + fletcher(body)

def frame_network(payload=bytes(range(32)), package_id=7, msg_id=3):
    body = bytes([9, 1, 42, len(payload) & 0xff, len(payload) >> 8, package_id, msg_id]) + payload
    return bytes([0x90, 0x78]) + body + fletcher(body)

def write_pcap(path, packet):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as f:
        f.write(struct.pack('<IHHIIII', 0xA1B2C3D4, 2, 4, 0, 0, 65535, LINKTYPE_USER0))
        f.write(struct.pack('<IIII', 0, 0, len(packet), len(packet)))
        f.write(packet)

def find_field(obj, name):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == name:
                return v
            found = find_field(v, name)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_field(item, name)
            if found is not None:
                return found
    return None

@unittest.skipUnless(shutil.which('tshark'), 'tshark is not installed')
class StructFrameDissectorTest(unittest.TestCase):
    def dissect(self, name, packet):
        pcap = OUT / f'{name}.pcap'
        write_pcap(pcap, packet)
        cmd = ['tshark', '-r', str(pcap), '-T', 'json', '-X', f'lua_script:{SCRIPT}']
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        stdout = proc.stdout.strip()
        json_start = stdout.find('[')
        self.assertGreaterEqual(json_start, 0, f'no JSON output from tshark\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}')
        data = json.loads(stdout[json_start:])
        self.assertTrue(data, 'no packets returned')
        return data[0]
    def assert_common(self, pkt, msg_id, length):
        self.assertEqual(str(find_field(pkt, 'struct_frame.start1')), '0x90')
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.message_id')), 0), msg_id)
        crc_status = find_field(pkt, 'struct_frame.crc_status')
        if crc_status is not None:
            self.assertIn('Valid', str(crc_status))
        else:
            self.assertIsNotNone(find_field(pkt, 'struct_frame.crc1'))
            self.assertIsNotNone(find_field(pkt, 'struct_frame.crc2'))
        got_len = find_field(pkt, 'struct_frame.length')
        if isinstance(got_len, list): got_len = got_len[-1]
        self.assertEqual(int(str(got_len), 0), length)
    def test_standard(self):
        pkt = self.dissect('standard', frame_standard(b'abc', 3))
        self.assert_common(pkt, 3, 3)
        self.assertIn('Default', str(find_field(pkt, 'struct_frame.payload_type')))
    def test_bulk_extended(self):
        payload = bytes(range(64))
        pkt = self.dissect('bulk', frame_bulk(payload, 7, 3))
        self.assert_common(pkt, 3, len(payload))
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.package_id')), 0), 7)
    def test_network(self):
        payload = bytes(range(32))
        pkt = self.dissect('network', frame_network(payload, 7, 3))
        self.assert_common(pkt, 3, len(payload))
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.system_id')), 0), 1)
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.component_id')), 0), 42)

if __name__ == '__main__':
    unittest.main()
