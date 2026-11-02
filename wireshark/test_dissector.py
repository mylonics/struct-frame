#!/usr/bin/env python3
"""Tests for the Wireshark dissector and its magic-byte table.

Frames are produced by the *real struct-frame Python runtime* from a real schema
(``examples/package_ids/fleet.sf``), never hand-assembled, so the expected
checksum comes from the implementation and not from a second copy of the
algorithm. The struct-frame checksum is Fletcher-16 over the frame plus two
schema-derived magic bytes, which is why the dissector needs the
``magic_table`` preference to verify a frame.

The tshark end-to-end tests are skipped when tshark is not installed; the
checksum/table contract tests always run.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
SCRIPT = ROOT / 'wireshark' / 'struct_frame.lua'
SCHEMA = ROOT / 'examples' / 'package_ids' / 'fleet.sf'
LINKTYPE_USER0 = 147

sys.path.insert(0, str(ROOT / 'wireshark'))
import magic_table  # noqa: E402


def find_tshark():
    found = shutil.which('tshark')
    if found:
        return found
    for candidate in (r'C:\Program Files\Wireshark\tshark.exe',
                      r'C:\Program Files (x86)\Wireshark\tshark.exe'):
        if os.path.exists(candidate):
            return candidate
    return None


def fletcher_with_magic(data, magic1, magic2):
    a = b = 0
    for x in bytes(data) + bytes([magic1, magic2]):
        a = (a + x) & 0xFF
        b = (b + a) & 0xFF
    return bytes([a, b])


FRAME_SCRIPT = '''
import sys
from frame_profiles import (BufferWriter, PROFILE_STANDARD_CONFIG, PROFILE_BULK_CONFIG,
                            PROFILE_NETWORK_CONFIG)
from struct_frame.generated import sensor_data, actuator_control
reading = sensor_data.SensorReading(type=1, value=2.5, timestamp=123456, sensor_id=b"s-1")
command = actuator_control.ActuatorCommand(actuator_id=b"a-7", desired_state=1, target_value=3.0)
status = sensor_data.SensorStatus(sensor_id=b"s-1", online=1, battery_percent=50.0, error_count=2)
frames = {}
w = BufferWriter(PROFILE_BULK_CONFIG, 512); w.write(reading); frames["bulk"] = w.data().hex()
w = BufferWriter(PROFILE_NETWORK_CONFIG, 512); w.write(command, seq=9, sys_id=1, comp_id=42); frames["network"] = w.data().hex()
print(frames["bulk"]); print(frames["network"])
'''


class _Fixture:
    """Frames from the real runtime plus the magic table for their messages."""
    bulk = network = None
    table = ''
    entries = None

    @classmethod
    def build(cls):
        if cls.bulk is not None:
            return
        tmp = Path(tempfile.mkdtemp(prefix='sf_wireshark_'))
        env = dict(os.environ, PYTHONPATH=str(SRC))
        gen = subprocess.run([sys.executable, str(SRC / 'main.py'), str(SCHEMA), '--build_py',
                              '--py_path', str(tmp / 'py')], env=env, capture_output=True, text=True)
        assert gen.returncode == 0, gen.stdout + gen.stderr
        # Run with only the generated directory on the path: the generated package is
        # also called "struct_frame" and the generator must not shadow it.
        run = subprocess.run([sys.executable, '-c', FRAME_SCRIPT],
                             env=dict(os.environ, PYTHONPATH=str(tmp / 'py')),
                             capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        bulk_hex, network_hex = run.stdout.split()
        cls.bulk, cls.network = bytes.fromhex(bulk_hex), bytes.fromhex(network_hex)
        cls.entries = magic_table.magic_entries(str(SCHEMA))
        cls.table = magic_table.format_table(cls.entries)


def magic_for(pkg, msg):
    for p, m, m1, m2 in _Fixture.entries:
        if (p, m) == (pkg, msg):
            return m1, m2
    raise KeyError((pkg, msg))


class MagicTableContractTest(unittest.TestCase):
    """Run without tshark: pins the table format and the checksum the dissector must match."""

    @classmethod
    def setUpClass(cls):
        _Fixture.build()

    def test_table_format(self):
        self.assertRegex(_Fixture.table, r'^(\d+:\d+=\d+,\d+)(;\d+:\d+=\d+,\d+)*$')
        self.assertIn('1:1=', _Fixture.table)   # sensor_data.SensorReading
        self.assertIn('2:1=', _Fixture.table)   # actuator_control.ActuatorCommand

    def test_runtime_checksum_needs_the_magic_bytes(self):
        # Bulk: [0x90][0x74][LEN_LO][LEN_HI][PKG][MSG][payload][CRC1][CRC2]
        frame = _Fixture.bulk
        pkg, msg = frame[4], frame[5]
        m1, m2 = magic_for(pkg, msg)
        body, crc = frame[2:-2], frame[-2:]
        self.assertEqual(fletcher_with_magic(body, m1, m2), crc)
        # The unseeded Fletcher-16 the dissector used to compute does NOT match, which
        # is why every real frame was reported as "Invalid".
        a = b = 0
        for x in body:
            a = (a + x) & 0xFF
            b = (b + a) & 0xFF
        self.assertNotEqual(bytes([a, b]), crc)

    def test_network_frame_checksum(self):
        # Network: [0x90][0x78][SEQ][SYS][COMP][LEN_LO][LEN_HI][PKG][MSG][payload][CRC1][CRC2]
        frame = _Fixture.network
        pkg, msg = frame[7], frame[8]
        m1, m2 = magic_for(pkg, msg)
        self.assertEqual(fletcher_with_magic(frame[2:-2], m1, m2), frame[-2:])


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


@unittest.skipUnless(find_tshark(), 'tshark is not installed')
class StructFrameDissectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _Fixture.build()
        cls.out = Path(tempfile.mkdtemp(prefix='sf_pcap_'))

    def dissect(self, name, packet, table=None):
        pcap = self.out / f'{name}.pcap'
        write_pcap(pcap, packet)
        cmd = [find_tshark(), '-r', str(pcap), '-T', 'json', '-X', f'lua_script:{SCRIPT}']
        if table is not None:
            cmd += ['-o', f'struct_frame.magic_table:{table}']
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        stdout = proc.stdout.strip()
        start = stdout.find('[')
        self.assertGreaterEqual(start, 0, f'no JSON output\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}')
        data = json.loads(stdout[start:])
        self.assertTrue(data, 'no packets returned')
        return data[0]

    def crc_status(self, pkt):
        return str(find_field(pkt, 'struct_frame.crc_status'))

    def test_bulk_valid_with_magic_table(self):
        pkt = self.dissect('bulk', _Fixture.bulk, _Fixture.table)
        self.assertEqual(str(find_field(pkt, 'struct_frame.start1')), '0x90')
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.package_id')), 0), 1)
        self.assertEqual(self.crc_status(pkt), 'Valid')

    def test_network_valid_with_magic_table(self):
        pkt = self.dissect('network', _Fixture.network, _Fixture.table)
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.system_id')), 0), 1)
        self.assertEqual(int(str(find_field(pkt, 'struct_frame.component_id')), 0), 42)
        self.assertEqual(self.crc_status(pkt), 'Valid')

    def test_unverified_without_magic_table(self):
        # Without the table a mismatch proves nothing, so it must not say "Invalid".
        status = self.crc_status(self.dissect('bulk_no_table', _Fixture.bulk))
        self.assertTrue(status.startswith('Unverified'), status)

    def test_corrupted_payload_is_invalid_with_magic_table(self):
        frame = bytearray(_Fixture.bulk)
        frame[8] ^= 0xFF  # flip a payload byte
        status = self.crc_status(self.dissect('bulk_bad', bytes(frame), _Fixture.table))
        self.assertTrue(status.startswith('Invalid'), status)


if __name__ == '__main__':
    unittest.main()
