#!/usr/bin/env python3
"""
Validate the generated test packets match expected frame format.

This script reads the generated binary files and verifies they have
the correct structure according to the struct-frame protocol.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def fletcher16(data):
    """Calculate Fletcher-16 checksum."""
    sum1 = 0
    sum2 = 0
    for byte in data:
        sum1 = (sum1 + byte) % 256
        sum2 = (sum2 + sum1) % 256
    return sum1, sum2


def validate_basic_default_packet(packet):
    """Validate a BasicDefault packet structure."""
    print(f"\nValidating BasicDefault packet ({len(packet)} bytes):")
    print(f"  Packet: {packet.hex(' ')}")
    
    # Check minimum length
    if len(packet) < 6:
        print("  ✗ FAIL: Packet too short")
        return False
    
    # Check start bytes
    if packet[0] != 0x90:
        print(f"  ✗ FAIL: Start byte 1 should be 0x90, got 0x{packet[0]:02X}")
        return False
    if packet[1] != 0x71:
        print(f"  ✗ FAIL: Start byte 2 should be 0x71, got 0x{packet[1]:02X}")
        return False
    
    print("  ✓ Start bytes: 0x90 0x71")
    
    # Get length
    payload_length = packet[2]
    print(f"  ✓ Payload length: {payload_length}")
    
    # Get message ID
    msg_id = packet[3]
    print(f"  ✓ Message ID: {msg_id}")
    
    # Check total length
    expected_total = 4 + payload_length + 2  # header + payload + CRC
    if len(packet) != expected_total:
        print(f"  ✗ FAIL: Expected {expected_total} bytes, got {len(packet)}")
        return False
    
    # Validate CRC
    crc_data = packet[2:4+payload_length]  # length + msg_id + payload
    crc1, crc2 = fletcher16(bytes(crc_data))
    
    received_crc1 = packet[4 + payload_length]
    received_crc2 = packet[4 + payload_length + 1]
    
    if received_crc1 == crc1 and received_crc2 == crc2:
        print(f"  ✓ CRC: 0x{crc1:02X} 0x{crc2:02X} (valid)")
        return True
    else:
        print(f"  ✗ FAIL: CRC mismatch - expected 0x{crc1:02X} 0x{crc2:02X}, got 0x{received_crc1:02X} 0x{received_crc2:02X}")
        return False


def validate_tiny_minimal_packet(packet):
    """Validate a TinyMinimal packet structure."""
    print(f"\nValidating TinyMinimal packet ({len(packet)} bytes):")
    print(f"  Packet: {packet.hex(' ')}")
    
    # Check minimum length
    if len(packet) < 2:
        print("  ✗ FAIL: Packet too short")
        return False
    
    # Check start byte
    if packet[0] != 0x70:
        print(f"  ✗ FAIL: Start byte should be 0x70, got 0x{packet[0]:02X}")
        return False
    
    print("  ✓ Start byte: 0x70")
    
    # Get message ID
    msg_id = packet[1]
    print(f"  ✓ Message ID: {msg_id}")
    
    # Minimal format has no CRC or length field
    payload_length = len(packet) - 2
    print(f"  ✓ Payload length: {payload_length} (inferred)")
    
    return True


def validate_basic_extended_packet(packet):
    """Validate a BasicExtended packet structure."""
    print(f"\nValidating BasicExtended packet ({len(packet)} bytes):")
    print(f"  Packet: {packet.hex(' ')}")
    
    # Check minimum length
    if len(packet) < 8:
        print("  ✗ FAIL: Packet too short")
        return False
    
    # Check start bytes
    if packet[0] != 0x90:
        print(f"  ✗ FAIL: Start byte 1 should be 0x90, got 0x{packet[0]:02X}")
        return False
    if packet[1] != 0x74:
        print(f"  ✗ FAIL: Start byte 2 should be 0x74, got 0x{packet[1]:02X}")
        return False
    
    print("  ✓ Start bytes: 0x90 0x74")
    
    # Get length (16-bit, little endian)
    payload_length = packet[2] + (packet[3] << 8)
    print(f"  ✓ Payload length: {payload_length}")
    
    # Get package ID
    pkg_id = packet[4]
    print(f"  ✓ Package ID: {pkg_id}")
    
    # Get message ID
    msg_id = packet[5]
    print(f"  ✓ Message ID: {msg_id}")
    
    # Check total length
    expected_total = 6 + payload_length + 2  # header + payload + CRC
    if len(packet) != expected_total:
        print(f"  ✗ FAIL: Expected {expected_total} bytes, got {len(packet)}")
        return False
    
    # Validate CRC
    crc_data = packet[2:6+payload_length]  # len_lo, len_hi, pkg_id, msg_id, payload
    crc1, crc2 = fletcher16(bytes(crc_data))
    
    received_crc1 = packet[6 + payload_length]
    received_crc2 = packet[6 + payload_length + 1]
    
    if received_crc1 == crc1 and received_crc2 == crc2:
        print(f"  ✓ CRC: 0x{crc1:02X} 0x{crc2:02X} (valid)")
        return True
    else:
        print(f"  ✗ FAIL: CRC mismatch - expected 0x{crc1:02X} 0x{crc2:02X}, got 0x{received_crc1:02X} 0x{received_crc2:02X}")
        return False


def validate_basic_extended_multi_system_stream_packet(packet):
    """Validate a BasicExtendedMultiSystemStream packet structure."""
    print(f"\nValidating BasicExtendedMultiSystemStream packet ({len(packet)} bytes):")
    print(f"  Packet: {packet.hex(' ')}")
    
    # Check minimum length
    if len(packet) < 11:
        print("  ✗ FAIL: Packet too short")
        return False
    
    # Check start bytes
    if packet[0] != 0x90:
        print(f"  ✗ FAIL: Start byte 1 should be 0x90, got 0x{packet[0]:02X}")
        return False
    if packet[1] != 0x78:
        print(f"  ✗ FAIL: Start byte 2 should be 0x78, got 0x{packet[1]:02X}")
        return False
    
    print("  ✓ Start bytes: 0x90 0x78")
    
    # Get sequence
    seq = packet[2]
    print(f"  ✓ Sequence: {seq}")
    
    # Get system and component IDs
    sys_id = packet[3]
    comp_id = packet[4]
    print(f"  ✓ System ID: {sys_id}, Component ID: {comp_id}")
    
    # Get length (16-bit, little endian)
    payload_length = packet[5] + (packet[6] << 8)
    print(f"  ✓ Payload length: {payload_length}")
    
    # Get package ID
    pkg_id = packet[7]
    print(f"  ✓ Package ID: {pkg_id}")
    
    # Get message ID
    msg_id = packet[8]
    print(f"  ✓ Message ID: {msg_id}")
    
    # Check total length
    expected_total = 9 + payload_length + 2  # header + payload + CRC
    if len(packet) != expected_total:
        print(f"  ✗ FAIL: Expected {expected_total} bytes, got {len(packet)}")
        return False
    
    # Validate CRC
    crc_data = packet[2:9+payload_length]  # seq, sys, comp, len_lo, len_hi, pkg_id, msg_id, payload
    crc1, crc2 = fletcher16(bytes(crc_data))
    
    received_crc1 = packet[9 + payload_length]
    received_crc2 = packet[9 + payload_length + 1]
    
    if received_crc1 == crc1 and received_crc2 == crc2:
        print(f"  ✓ CRC: 0x{crc1:02X} 0x{crc2:02X} (valid)")
        return True
    else:
        print(f"  ✗ FAIL: CRC mismatch - expected 0x{crc1:02X} 0x{crc2:02X}, got 0x{received_crc1:02X} 0x{received_crc2:02X}")
        return False


def main():
    """Validate all generated test packets."""
    
    sample_dir = os.path.join(os.path.dirname(__file__), 'sample_packets')
    
    if not os.path.exists(sample_dir):
        print(f"Error: {sample_dir} does not exist")
        print("Run generate_test_packets.py first")
        return 1
    
    print("=" * 60)
    print("Validating Struct Frame Test Packets")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Standard Profile (BasicDefault)
    try:
        with open(os.path.join(sample_dir, 'standard.bin'), 'rb') as f:
            packet = f.read()
        if not validate_basic_default_packet(packet):
            all_passed = False
    except Exception as e:
        print(f"\n✗ FAIL: Could not validate standard.bin: {e}")
        all_passed = False
    
    # Test 2: Sensor Profile (TinyMinimal)
    try:
        with open(os.path.join(sample_dir, 'sensor.bin'), 'rb') as f:
            packet = f.read()
        if not validate_tiny_minimal_packet(packet):
            all_passed = False
    except Exception as e:
        print(f"\n✗ FAIL: Could not validate sensor.bin: {e}")
        all_passed = False
    
    # Test 3: Bulk Profile (BasicExtended)
    try:
        with open(os.path.join(sample_dir, 'bulk.bin'), 'rb') as f:
            packet = f.read()
        if not validate_basic_extended_packet(packet):
            all_passed = False
    except Exception as e:
        print(f"\n✗ FAIL: Could not validate bulk.bin: {e}")
        all_passed = False
    
    # Test 4: Network Profile (BasicExtendedMultiSystemStream)
    try:
        with open(os.path.join(sample_dir, 'network.bin'), 'rb') as f:
            packet = f.read()
        if not validate_basic_extended_multi_system_stream_packet(packet):
            all_passed = False
    except Exception as e:
        print(f"\n✗ FAIL: Could not validate network.bin: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
