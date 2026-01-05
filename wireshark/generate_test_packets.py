#!/usr/bin/env python3
"""
Generate sample Struct Frame packets for testing the Wireshark dissector.

This script creates example packets for each standard profile and saves them
as raw binary files and PCAP files that can be opened in Wireshark.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from struct_frame.frame_formats import Profile, get_profile


def fletcher16(data):
    """Calculate Fletcher-16 checksum."""
    sum1 = 0
    sum2 = 0
    for byte in data:
        sum1 = (sum1 + byte) % 256
        sum2 = (sum2 + sum1) % 256
    return sum1, sum2


def create_basic_default_packet(msg_id=42, payload=b'\x01\x02\x03\x04'):
    """
    Create a BasicDefault (Standard) profile packet.
    Format: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
    """
    # Start bytes
    frame = bytearray([0x90, 0x71])
    
    # Length (payload only, not including header/crc)
    frame.append(len(payload))
    
    # Message ID
    frame.append(msg_id)
    
    # Add payload
    frame.extend(payload)
    
    # Calculate Fletcher-16 over length, msg_id, and payload
    crc_data = bytes([len(payload), msg_id]) + payload
    crc1, crc2 = fletcher16(crc_data)
    
    # Add CRC
    frame.extend([crc1, crc2])
    
    return bytes(frame)


def create_tiny_minimal_packet(msg_id=42, payload=b'\x01\x02\x03\x04'):
    """
    Create a TinyMinimal (Sensor) profile packet.
    Format: [0x70] [MSG_ID] [PAYLOAD]
    """
    frame = bytearray([0x70])
    frame.append(msg_id)
    frame.extend(payload)
    return bytes(frame)


def create_basic_extended_packet(msg_id=42, pkg_id=1, payload=b'\x01\x02\x03\x04'):
    """
    Create a BasicExtended (Bulk) profile packet.
    Format: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
    """
    # Start bytes
    frame = bytearray([0x90, 0x74])
    
    # Length (16-bit, little endian)
    length = len(payload)
    len_lo = length & 0xFF
    len_hi = (length >> 8) & 0xFF
    frame.extend([len_lo, len_hi])
    
    # Package ID
    frame.append(pkg_id)
    
    # Message ID
    frame.append(msg_id)
    
    # Add payload
    frame.extend(payload)
    
    # Calculate Fletcher-16 over length, pkg_id, msg_id, and payload
    crc_data = bytes([len_lo, len_hi, pkg_id, msg_id]) + payload
    crc1, crc2 = fletcher16(crc_data)
    
    # Add CRC
    frame.extend([crc1, crc2])
    
    return bytes(frame)


def create_basic_extended_multi_system_stream_packet(
    msg_id=42, pkg_id=1, sys_id=1, comp_id=2, seq=5, payload=b'\x01\x02\x03\x04'
):
    """
    Create a BasicExtendedMultiSystemStream (Network) profile packet.
    Format: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
    """
    # Start bytes
    frame = bytearray([0x90, 0x78])
    
    # Sequence number
    frame.append(seq)
    
    # System ID and Component ID
    frame.extend([sys_id, comp_id])
    
    # Length (16-bit, little endian)
    length = len(payload)
    len_lo = length & 0xFF
    len_hi = (length >> 8) & 0xFF
    frame.extend([len_lo, len_hi])
    
    # Package ID
    frame.append(pkg_id)
    
    # Message ID
    frame.append(msg_id)
    
    # Add payload
    frame.extend(payload)
    
    # Calculate Fletcher-16 over everything after start bytes
    crc_data = bytes([seq, sys_id, comp_id, len_lo, len_hi, pkg_id, msg_id]) + payload
    crc1, crc2 = fletcher16(crc_data)
    
    # Add CRC
    frame.extend([crc1, crc2])
    
    return bytes(frame)


def create_pcap_file(packets, filename):
    """
    Create a PCAP file with UDP packets containing the given payloads.
    
    This creates a minimal PCAP file that can be opened in Wireshark.
    Uses User DLT 147 for struct-frame packets.
    """
    import struct
    import time
    
    # PCAP Global Header
    # Magic number, version, timezone, accuracy, snaplen, network (User DLT 147)
    pcap_header = struct.pack('<IHHIIII', 
        0xa1b2c3d4,  # Magic number
        2, 4,        # Version 2.4
        0,           # Timezone (GMT)
        0,           # Timestamp accuracy
        65535,       # Snaplen
        147          # Network type (User DLT 0 = 147)
    )
    
    pcap_data = bytearray(pcap_header)
    
    # Add each packet
    timestamp = int(time.time())
    for i, packet in enumerate(packets):
        # Packet header
        ts_sec = timestamp
        ts_usec = i * 1000  # Increment by 1ms per packet
        incl_len = len(packet)
        orig_len = len(packet)
        
        packet_header = struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len)
        pcap_data.extend(packet_header)
        pcap_data.extend(packet)
    
    # Write to file
    with open(filename, 'wb') as f:
        f.write(pcap_data)
    
    print(f"Created PCAP file: {filename} ({len(packets)} packets)")


def main():
    """Generate sample packets and save them."""
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), 'sample_packets')
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating sample Struct Frame packets...")
    print()
    
    # Generate sample packets
    samples = []
    
    # 1. Standard Profile (BasicDefault)
    print("1. Standard Profile (BasicDefault)")
    packet = create_basic_default_packet(msg_id=42, payload=b'\x01\x02\x03\x04')
    print(f"   Packet: {packet.hex(' ')}")
    print(f"   Length: {len(packet)} bytes")
    samples.append(("standard", packet))
    print()
    
    # 2. Sensor Profile (TinyMinimal)
    print("2. Sensor Profile (TinyMinimal)")
    packet = create_tiny_minimal_packet(msg_id=42, payload=b'\x01\x02\x03\x04')
    print(f"   Packet: {packet.hex(' ')}")
    print(f"   Length: {len(packet)} bytes")
    samples.append(("sensor", packet))
    print()
    
    # 3. Bulk Profile (BasicExtended)
    print("3. Bulk Profile (BasicExtended)")
    packet = create_basic_extended_packet(msg_id=42, pkg_id=1, payload=b'\x01\x02\x03\x04')
    print(f"   Packet: {packet.hex(' ')}")
    print(f"   Length: {len(packet)} bytes")
    samples.append(("bulk", packet))
    print()
    
    # 4. Network Profile (BasicExtendedMultiSystemStream)
    print("4. Network Profile (BasicExtendedMultiSystemStream)")
    packet = create_basic_extended_multi_system_stream_packet(
        msg_id=42, pkg_id=1, sys_id=1, comp_id=2, seq=5, payload=b'\x01\x02\x03\x04'
    )
    print(f"   Packet: {packet.hex(' ')}")
    print(f"   Length: {len(packet)} bytes")
    samples.append(("network", packet))
    print()
    
    # 5. Additional samples with different payloads
    print("5. Standard Profile with longer payload")
    long_payload = bytes(range(32))  # 32 bytes
    packet = create_basic_default_packet(msg_id=100, payload=long_payload)
    print(f"   Packet length: {len(packet)} bytes")
    samples.append(("standard_long", packet))
    print()
    
    # Save individual binary files
    print("Saving individual binary files...")
    for name, packet in samples:
        filename = os.path.join(output_dir, f"{name}.bin")
        with open(filename, 'wb') as f:
            f.write(packet)
        print(f"  - {filename}")
    print()
    
    # Create combined PCAP file with all samples
    print("Creating PCAP file...")
    all_packets = [packet for _, packet in samples]
    pcap_file = os.path.join(output_dir, "struct_frame_samples.pcap")
    create_pcap_file(all_packets, pcap_file)
    print()
    
    print("Done! Test the dissector by:")
    print(f"1. Opening {pcap_file} in Wireshark")
    print("2. The packets should be automatically decoded as 'STRUCT_FRAME' protocol")
    print("3. Expand the protocol tree to see all fields")
    print()
    print("Or test with individual binary files:")
    print("  wireshark -X lua_script:struct_frame.lua -i lo")
    print("  Then send packets using netcat or similar tools")


if __name__ == '__main__':
    main()
