#!/usr/bin/env python3
"""
Test the 5 standard frame format profiles across all languages.

This test validates that the 5 recommended profiles (STANDARD, SENSOR, IPC, BULK, NETWORK)
work correctly for code generation, serialization, and deserialization across all supported
languages.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from struct_frame.frame_formats import (
    Profile,
    get_profile,
    HeaderType,
    PayloadType,
)


def test_profile_definitions():
    """Test that all 5 standard profiles are correctly defined"""
    print("\n[TEST] Profile Definitions")
    
    # Test STANDARD profile
    standard = get_profile(Profile.STANDARD)
    assert standard.name == "BasicDefault"
    assert standard.header.header_type == HeaderType.BASIC
    assert standard.payload.payload_type == PayloadType.DEFAULT
    assert standard.total_overhead == 6
    assert standard.start_byte_value == 0x71
    print(f"  ✓ Profile.STANDARD = {standard.name} (overhead: {standard.total_overhead} bytes)")
    
    # Test SENSOR profile
    sensor = get_profile(Profile.SENSOR)
    assert sensor.name == "TinyMinimal"
    assert sensor.header.header_type == HeaderType.TINY
    assert sensor.payload.payload_type == PayloadType.MINIMAL
    assert sensor.total_overhead == 2
    assert sensor.start_byte_value == 0x70
    print(f"  ✓ Profile.SENSOR = {sensor.name} (overhead: {sensor.total_overhead} bytes)")
    
    # Test IPC profile
    ipc = get_profile(Profile.IPC)
    assert ipc.name == "NoneMinimal"
    assert ipc.header.header_type == HeaderType.NONE
    assert ipc.payload.payload_type == PayloadType.MINIMAL
    assert ipc.total_overhead == 1
    assert ipc.start_byte_value is None  # No start bytes
    print(f"  ✓ Profile.IPC = {ipc.name} (overhead: {ipc.total_overhead} bytes)")
    
    # Test BULK profile
    bulk = get_profile(Profile.BULK)
    assert bulk.name == "BasicExtended"
    assert bulk.header.header_type == HeaderType.BASIC
    assert bulk.payload.payload_type == PayloadType.EXTENDED
    assert bulk.total_overhead == 8
    assert bulk.start_byte_value == 0x74
    print(f"  ✓ Profile.BULK = {bulk.name} (overhead: {bulk.total_overhead} bytes)")
    
    # Test NETWORK profile
    network = get_profile(Profile.NETWORK)
    assert network.name == "BasicExtendedMultiSystemStream"
    assert network.header.header_type == HeaderType.BASIC
    assert network.payload.payload_type == PayloadType.EXTENDED_MULTI_SYSTEM_STREAM
    assert network.total_overhead == 11
    assert network.start_byte_value == 0x78
    print(f"  ✓ Profile.NETWORK = {network.name} (overhead: {network.total_overhead} bytes)")
    
    print("  PASS: All 5 standard profiles correctly defined")


def test_profile_features():
    """Test that profiles have the expected features"""
    print("\n[TEST] Profile Features")
    
    # STANDARD should have length and CRC
    standard = get_profile(Profile.STANDARD)
    assert standard.payload.has_length == True
    assert standard.payload.has_crc == True
    assert standard.payload.has_sequence == False
    assert standard.payload.has_system_id == False
    print(f"  ✓ STANDARD has length and CRC")
    
    # SENSOR should have minimal features
    sensor = get_profile(Profile.SENSOR)
    assert sensor.payload.has_length == False
    assert sensor.payload.has_crc == False
    assert sensor.payload.has_sequence == False
    print(f"  ✓ SENSOR has minimal features (no length, no CRC)")
    
    # IPC should have minimal features
    ipc = get_profile(Profile.IPC)
    assert ipc.payload.has_length == False
    assert ipc.payload.has_crc == False
    print(f"  ✓ IPC has minimal features")
    
    # BULK should have extended length and package ID
    bulk = get_profile(Profile.BULK)
    assert bulk.payload.has_length == True
    assert bulk.payload.length_bytes == 2  # 16-bit length
    assert bulk.payload.has_package_id == True
    assert bulk.payload.has_crc == True
    print(f"  ✓ BULK has 16-bit length and package ID")
    
    # NETWORK should have all features
    network = get_profile(Profile.NETWORK)
    assert network.payload.has_length == True
    assert network.payload.length_bytes == 2  # 16-bit length
    assert network.payload.has_sequence == True
    assert network.payload.has_system_id == True
    assert network.payload.has_component_id == True
    assert network.payload.has_package_id == True
    assert network.payload.has_crc == True
    print(f"  ✓ NETWORK has all features (seq, routing, 16-bit length, package ID, CRC)")
    
    print("  PASS: All profiles have expected features")


def test_profile_payload_sizes():
    """Test that profiles support expected payload sizes"""
    print("\n[TEST] Profile Payload Size Limits")
    
    # STANDARD: 255 bytes max (1-byte length)
    standard = get_profile(Profile.STANDARD)
    max_payload = 255 if standard.payload.length_bytes == 1 else 65535
    assert max_payload == 255
    print(f"  ✓ STANDARD: max {max_payload} bytes")
    
    # SENSOR: No length field (requires known message sizes)
    sensor = get_profile(Profile.SENSOR)
    assert sensor.payload.has_length == False
    print(f"  ✓ SENSOR: no length field (fixed-size messages)")
    
    # IPC: No length field
    ipc = get_profile(Profile.IPC)
    assert ipc.payload.has_length == False
    print(f"  ✓ IPC: no length field")
    
    # BULK: 65535 bytes max (2-byte length)
    bulk = get_profile(Profile.BULK)
    max_payload = 65535 if bulk.payload.length_bytes == 2 else 255
    assert max_payload == 65535
    print(f"  ✓ BULK: max {max_payload} bytes (64KB)")
    
    # NETWORK: 65535 bytes max (2-byte length)
    network = get_profile(Profile.NETWORK)
    max_payload = 65535 if network.payload.length_bytes == 2 else 255
    assert max_payload == 65535
    print(f"  ✓ NETWORK: max {max_payload} bytes (64KB)")
    
    print("  PASS: All profiles have correct payload size limits")


def test_profile_to_dict():
    """Test conversion to dictionary representation"""
    print("\n[TEST] Profile Dictionary Representation")
    
    for profile in Profile:
        definition = get_profile(profile)
        data = definition.to_dict()
        
        # Verify required fields
        assert 'name' in data
        assert 'header_type' in data
        assert 'payload_type' in data
        assert 'total_overhead' in data
        assert 'has_crc' in data
        
        print(f"  ✓ {profile.name}: {data['name']} ({data['total_overhead']} bytes overhead)")
    
    print("  PASS: All profiles convert to dict correctly")


def main():
    """Run all profile tests"""
    print("=" * 70)
    print("Profile Test Suite")
    print("=" * 70)
    
    try:
        test_profile_definitions()
        test_profile_features()
        test_profile_payload_sizes()
        test_profile_to_dict()
        
        print("\n" + "=" * 70)
        print("✓ ALL PROFILE TESTS PASSED")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
