"""
Example: Using Frame Format Profiles

This example demonstrates how to use the 5 standard frame format profiles
and how to create custom profile combinations.
"""

import sys
import os

# Add src to path for the example
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from struct_frame.frame_formats import (
    Profile,
    get_profile,
    list_profiles,
    create_custom_profile,
    HeaderType,
    PayloadType,
)


def example_standard_profiles():
    """Show how to use standard profiles"""
    print("=" * 70)
    print("STANDARD PROFILES")
    print("=" * 70)
    
    print("\nUse these 5 profiles for most applications:\n")
    
    for profile in Profile:
        definition = get_profile(profile)
        print(f"{profile.name:15} → {definition.name:35} ({definition.total_overhead:2} bytes)")
        print(f"                Use case: {definition.description[:60]}...")
        print()


def example_profile_details():
    """Show detailed information about a profile"""
    print("=" * 70)
    print("PROFILE DETAILS: NETWORK")
    print("=" * 70)
    
    network = get_profile(Profile.NETWORK)
    
    print(f"\nFrame Format: {network.name}")
    print(f"Description: {network.description}")
    print()
    
    print(f"Header: {network.header.name}")
    print(f"  Start bytes: {network.header.num_start_bytes}")
    print(f"  Encodes payload type: {network.header.encodes_payload_type}")
    if network.start_byte_value:
        print(f"  Start byte value: 0x{network.start_byte_value:02X}")
    print()
    
    print(f"Payload: {network.payload.name}")
    print(f"  Has CRC: {network.payload.has_crc} ({network.payload.crc_bytes} bytes)")
    print(f"  Has Length: {network.payload.has_length} ({network.payload.length_bytes} bytes)")
    print(f"  Has Sequence: {network.payload.has_sequence}")
    print(f"  Has System ID: {network.payload.has_system_id}")
    print(f"  Has Component ID: {network.payload.has_component_id}")
    print(f"  Has Package ID: {network.payload.has_package_id}")
    print(f"  Field order: {network.payload.get_field_order()}")
    print()
    
    print(f"Total Overhead: {network.total_overhead} bytes")
    max_payload = 65535 if network.payload.length_bytes == 2 else 255 if network.payload.has_length else "No limit (fixed size)"
    print(f"Max Payload Size: {max_payload} bytes")


def example_custom_profiles():
    """Show how to create custom profile combinations"""
    print("\n" + "=" * 70)
    print("CUSTOM PROFILES")
    print("=" * 70)
    
    print("\nCreate custom combinations when the standard profiles don't fit:\n")
    
    # Example 1: TinyDefault - Lower overhead than Standard
    tiny_default = create_custom_profile(
        "TinyDefault",
        HeaderType.TINY,
        PayloadType.DEFAULT,
        "Lower overhead alternative to Standard profile"
    )
    print(f"1. {tiny_default.name}")
    print(f"   Header: {tiny_default.header.name} (1 byte)")
    print(f"   Payload: {tiny_default.payload.name} (4 bytes)")
    print(f"   Total overhead: {tiny_default.total_overhead} bytes")
    print(f"   Start byte: 0x{tiny_default.start_byte_value:02X}")
    print(f"   Use case: {tiny_default.description}")
    print()
    
    # Example 2: BasicSeq - Standard with packet loss detection
    basic_seq = create_custom_profile(
        "BasicSeq",
        HeaderType.BASIC,
        PayloadType.SEQ,
        "Standard profile with packet loss detection"
    )
    print(f"2. {basic_seq.name}")
    print(f"   Header: {basic_seq.header.name} (2 bytes)")
    print(f"   Payload: {basic_seq.payload.name} (5 bytes)")
    print(f"   Total overhead: {basic_seq.total_overhead} bytes")
    print(f"   Has sequence: {basic_seq.payload.has_sequence}")
    print(f"   Use case: {basic_seq.description}")
    print()
    
    # Example 3: NoneDefault - IPC with error detection
    none_default = create_custom_profile(
        "NoneDefault",
        HeaderType.NONE,
        PayloadType.DEFAULT,
        "Trusted IPC with CRC error detection"
    )
    print(f"3. {none_default.name}")
    print(f"   Header: {none_default.header.name} (0 bytes)")
    print(f"   Payload: {none_default.payload.name} (4 bytes)")
    print(f"   Total overhead: {none_default.total_overhead} bytes")
    print(f"   Use case: {none_default.description}")


def example_profile_comparison():
    """Compare overhead across different profiles"""
    print("\n" + "=" * 70)
    print("PROFILE COMPARISON")
    print("=" * 70)
    
    print("\nOverhead comparison for different use cases:\n")
    print(f"{'Profile':<20} {'Frame Format':<35} {'Overhead':>10} {'Max Payload':>15}")
    print("-" * 80)
    
    for profile in Profile:
        definition = get_profile(profile)
        max_payload = (
            f"{65535} bytes" if definition.payload.length_bytes == 2
            else f"{255} bytes" if definition.payload.has_length
            else "Fixed size"
        )
        print(f"{profile.name:<20} {definition.name:<35} {definition.total_overhead:>10} {max_payload:>15}")
    
    # Add some custom examples
    print()
    print("Custom examples:")
    tiny_default = create_custom_profile("TinyDefault", HeaderType.TINY, PayloadType.DEFAULT, "")
    print(f"{'TinyDefault':<20} {tiny_default.name:<35} {tiny_default.total_overhead:>10} {'255 bytes':>15}")
    
    basic_seq = create_custom_profile("BasicSeq", HeaderType.BASIC, PayloadType.SEQ, "")
    print(f"{'BasicSeq':<20} {basic_seq.name:<35} {basic_seq.total_overhead:>10} {'255 bytes':>15}")


def example_frame_structure():
    """Show the byte-level structure of different profiles"""
    print("\n" + "=" * 70)
    print("FRAME STRUCTURE")
    print("=" * 70)
    
    # STANDARD profile
    standard = get_profile(Profile.STANDARD)
    print(f"\n{Profile.STANDARD.name} ({standard.name}):")
    print("  [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]")
    print("   └─┬──┘ └─┬──┘  └┬──┘ └──┬──┘    │      └────┬────┘")
    print("     │      │      │       │        │           │")
    print("   Start  Start  1-byte Message  Message   CRC-16")
    print("   byte1  byte2  length    ID     data   checksum")
    
    # SENSOR profile
    sensor = get_profile(Profile.SENSOR)
    print(f"\n{Profile.SENSOR.name} ({sensor.name}):")
    print("  [0x70] [MSG_ID] [PAYLOAD]")
    print("   └─┬─┘ └──┬──┘     │")
    print("     │      │        │")
    print("   Start Message  Message")
    print("   byte    ID     data (fixed size)")
    
    # NETWORK profile
    network = get_profile(Profile.NETWORK)
    print(f"\n{Profile.NETWORK.name} ({network.name}):")
    print("  [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]")
    print("   └─┬──┘ └─┬──┘  │     │     │       └──────┬──────┘   │     │         │      └────┬────┘")
    print("     │      │     │     │     │              │          │     │         │           │")
    print("   Start  Start  Seq  System Component  16-bit      Package Message  Message    CRC-16")
    print("   byte1  byte2  num    ID      ID      length        ID      ID     data    checksum")


def main():
    """Run all examples"""
    example_standard_profiles()
    example_profile_details()
    example_custom_profiles()
    example_profile_comparison()
    example_frame_structure()
    
    print("\n" + "=" * 70)
    print("For more information, see:")
    print("  - docs/user-guide/framing.md")
    print("  - docs/user-guide/framing-calculator.md")
    print("  - docs/user-guide/framing-architecture.md")
    print("=" * 70)


if __name__ == '__main__':
    main()
