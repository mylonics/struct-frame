#!/usr/bin/env python3
"""
Test script for the new frame formats architecture.

This tests the language-agnostic frame format definitions and profiles.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from struct_frame.frame_formats import (
    Profile,
    get_profile,
    list_profiles,
    HeaderType,
    PayloadType,
    create_custom_profile,
)


def test_standard_profiles():
    """Test all 5 standard profiles"""
    print("Testing Standard Profiles")
    print("=" * 80)
    
    for profile in Profile:
        definition = get_profile(profile)
        print(f"\nProfile: {profile.name}")
        print(f"  Frame Format: {definition.name}")
        print(f"  Header: {definition.header.name} ({definition.header.num_start_bytes} bytes)")
        print(f"  Payload: {definition.payload.name}")
        print(f"  Total Overhead: {definition.total_overhead} bytes")
        print(f"  Description: {definition.description[:100]}...")
        
        # Verify expected combinations
        if profile == Profile.STANDARD:
            assert definition.header.header_type == HeaderType.BASIC
            assert definition.payload.payload_type == PayloadType.DEFAULT
            assert definition.name == "BasicDefault"
            assert definition.total_overhead == 6
            
        elif profile == Profile.SENSOR:
            assert definition.header.header_type == HeaderType.TINY
            assert definition.payload.payload_type == PayloadType.MINIMAL
            assert definition.name == "TinyMinimal"
            assert definition.total_overhead == 2
            
        elif profile == Profile.IPC:
            assert definition.header.header_type == HeaderType.NONE
            assert definition.payload.payload_type == PayloadType.MINIMAL
            assert definition.name == "NoneMinimal"
            assert definition.total_overhead == 1
            
        elif profile == Profile.BULK:
            assert definition.header.header_type == HeaderType.BASIC
            assert definition.payload.payload_type == PayloadType.EXTENDED
            assert definition.name == "BasicExtended"
            assert definition.total_overhead == 8
            
        elif profile == Profile.NETWORK:
            assert definition.header.header_type == HeaderType.BASIC
            assert definition.payload.payload_type == PayloadType.EXTENDED_MULTI_SYSTEM_STREAM
            assert definition.name == "BasicExtendedMultiSystemStream"
            assert definition.total_overhead == 11
    
    print("\n✓ All standard profiles verified")


def test_custom_profiles():
    """Test custom profile creation"""
    print("\n\nTesting Custom Profiles")
    print("=" * 80)
    
    # Create TinyDefault profile
    tiny_default = create_custom_profile(
        "TinyDefault",
        HeaderType.TINY,
        PayloadType.DEFAULT,
        "Tiny header with default payload"
    )
    print(f"\nCustom Profile: {tiny_default.name}")
    print(f"  Overhead: {tiny_default.total_overhead} bytes")
    assert tiny_default.total_overhead == 5  # 1 (tiny) + 1 (len) + 1 (msg_id) + 2 (crc)
    
    # Create BasicSeq profile
    basic_seq = create_custom_profile(
        "BasicSeq",
        HeaderType.BASIC,
        PayloadType.SEQ,
        "Basic header with sequence payload"
    )
    print(f"\nCustom Profile: {basic_seq.name}")
    print(f"  Overhead: {basic_seq.total_overhead} bytes")
    assert basic_seq.total_overhead == 7  # 2 (basic) + 1 (seq) + 1 (len) + 1 (msg_id) + 2 (crc)
    
    print("\n✓ Custom profiles work correctly")


def test_profile_list():
    """Test profile listing"""
    print("\n\nProfile List")
    print("=" * 80)
    
    profiles = list_profiles()
    print(f"\n{'Profile':<15} {'Format':<35} {'Overhead':<10} {'Description'}")
    print("-" * 100)
    
    for name, format_name, overhead, description in profiles:
        desc_short = description[:60] + "..." if len(description) > 60 else description
        print(f"{name:<15} {format_name:<35} {overhead:<10} {desc_short}")
    
    assert len(profiles) == 5
    print("\n✓ Profile listing works")


def test_payload_structure():
    """Test payload structure details"""
    print("\n\nPayload Structure Analysis")
    print("=" * 80)
    
    # Test Default payload structure
    default_profile = get_profile(Profile.STANDARD)
    payload = default_profile.payload
    
    print(f"\n{payload.name} Payload:")
    print(f"  Has CRC: {payload.has_crc} ({payload.crc_bytes} bytes)")
    print(f"  Has Length: {payload.has_length} ({payload.length_bytes} bytes)")
    print(f"  Has Sequence: {payload.has_sequence}")
    print(f"  Has System ID: {payload.has_system_id}")
    print(f"  Has Component ID: {payload.has_component_id}")
    print(f"  Has Package ID: {payload.has_package_id}")
    print(f"  Field order: {payload.get_field_order()}")
    
    assert payload.has_crc == True
    assert payload.crc_bytes == 2
    assert payload.has_length == True
    assert payload.length_bytes == 1
    
    # Test Network payload structure
    network_profile = get_profile(Profile.NETWORK)
    payload = network_profile.payload
    
    print(f"\n{payload.name} Payload:")
    print(f"  Has CRC: {payload.has_crc} ({payload.crc_bytes} bytes)")
    print(f"  Has Length: {payload.has_length} ({payload.length_bytes} bytes)")
    print(f"  Has Sequence: {payload.has_sequence}")
    print(f"  Has System ID: {payload.has_system_id}")
    print(f"  Has Component ID: {payload.has_component_id}")
    print(f"  Has Package ID: {payload.has_package_id}")
    print(f"  Field order: {payload.get_field_order()}")
    
    assert payload.has_sequence == True
    assert payload.has_system_id == True
    assert payload.has_component_id == True
    assert payload.has_package_id == True
    assert payload.length_bytes == 2
    
    print("\n✓ Payload structures verified")


def test_start_bytes():
    """Test start byte calculation"""
    print("\n\nStart Byte Calculation")
    print("=" * 80)
    
    # Test Basic profiles
    standard = get_profile(Profile.STANDARD)
    print(f"\n{standard.name}:")
    print(f"  Start bytes: {standard.header.start_bytes}")
    print(f"  Encodes payload type: {standard.header.encodes_payload_type}")
    if standard.start_byte_value:
        print(f"  Second start byte: 0x{standard.start_byte_value:02X}")
    
    # Verify start byte calculation (0x70 + PayloadType.DEFAULT = 0x70 + 1 = 0x71)
    assert standard.start_byte_value == 0x71
    
    # Test Sensor profile
    sensor = get_profile(Profile.SENSOR)
    print(f"\n{sensor.name}:")
    print(f"  Start bytes: {sensor.header.start_bytes}")
    print(f"  Encodes payload type: {sensor.header.encodes_payload_type}")
    if sensor.start_byte_value:
        print(f"  Start byte: 0x{sensor.start_byte_value:02X}")
    
    # Verify start byte calculation (0x70 + PayloadType.MINIMAL = 0x70 + 0 = 0x70)
    assert sensor.start_byte_value == 0x70
    
    # Test IPC profile (no start bytes)
    ipc = get_profile(Profile.IPC)
    print(f"\n{ipc.name}:")
    print(f"  Start bytes: {ipc.header.start_bytes}")
    print(f"  Num start bytes: {ipc.header.num_start_bytes}")
    assert ipc.start_byte_value is None
    
    print("\n✓ Start byte calculation verified")


if __name__ == '__main__':
    print("Frame Formats Architecture Test")
    print("=" * 80)
    
    try:
        test_standard_profiles()
        test_custom_profiles()
        test_profile_list()
        test_payload_structure()
        test_start_bytes()
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
