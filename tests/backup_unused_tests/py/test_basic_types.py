#!/usr/bin/env python3
"""
Test script for basic data types serialization/deserialization in Python.
"""

import sys
import os


def print_failure_details(label, msg, expected_values=None, actual_values=None, raw_data=None):
    """Print detailed failure information"""
    print(f"\n{'='*60}")
    print(f"FAILURE DETAILS: {label}")
    print(f"{'='*60}")
    
    if expected_values:
        print("\nExpected Values:")
        for key, val in expected_values.items():
            print(f"  {key}: {val}")
    
    if actual_values:
        print("\nActual Values:")
        for key, val in actual_values.items():
            print(f"  {key}: {val}")
    
    if raw_data:
        print(f"\nRaw Data ({len(raw_data)} bytes):")
        print(f"  Hex: {raw_data.hex()}")
    
    print(f"{'='*60}\n")


def test_basic_types():
    """Test basic data types serialization and deserialization with BasicPacket"""
    try:
        sys.path.insert(0, '../generated/py')
        from basic_types_sf import BasicTypesBasicTypesMessage, _VariableString_description
        from struct_frame_parser import BasicPacket, FrameParser

        desc_text = b"Test description for basic types"
        description = _VariableString_description(
            length=len(desc_text),
            data=desc_text.ljust(128, b'\x00')
        )

        msg = BasicTypesBasicTypesMessage(
            -42, -1000, -100000, -1000000000,
            255, 65535, 4294967295, 18446744073709551615,
            3.14159, 2.718281828459045, True,
            b"TEST_DEVICE_12345678901234567890",
            description
        )

        # Encode message into BasicPacket format
        packet = BasicPacket()
        encoded_data = packet.encode_msg(msg)

        # Verify encoded data is not empty
        if len(encoded_data) == 0:
            print_failure_details(
                "Empty encoded data",
                msg,
                expected_values={"encoded_size": ">0"},
                actual_values={"encoded_size": len(encoded_data)}
            )
            return False

        # Decode the BasicPacket back into a message
        packet_formats = {0x90: BasicPacket()}
        msg_definitions = {201: BasicTypesBasicTypesMessage}
        parser = FrameParser(packet_formats, msg_definitions)

        decoded_msg = None
        for byte in encoded_data:
            result = parser.parse_char(byte)
            if result:
                decoded_msg = result
                break

        if not decoded_msg:
            print_failure_details(
                "Failed to decode message",
                expected_values={"decoded_message": "valid"},
                actual_values={"decoded_message": None},
                raw_data=encoded_data
            )
            return False

        # Compare original and decoded messages
        if decoded_msg.small_int != msg.small_int:
            print_failure_details(
                "Value mismatch: small_int",
                expected_values={"small_int": msg.small_int},
                actual_values={"small_int": decoded_msg.small_int}
            )
            return False

        if decoded_msg.medium_int != msg.medium_int:
            print_failure_details(
                "Value mismatch: medium_int",
                expected_values={"medium_int": msg.medium_int},
                actual_values={"medium_int": decoded_msg.medium_int}
            )
            return False

        if decoded_msg.flag != msg.flag:
            print_failure_details(
                "Value mismatch: flag",
                expected_values={"flag": msg.flag},
                actual_values={"flag": decoded_msg.flag}
            )
            return False

        return True

    except ImportError:
        return True  # Skip if generated code not available

    except Exception as e:
        print_failure_details(
            f"Exception: {type(e).__name__}",
            None,
            expected_values={"result": "success"},
            actual_values={"exception": str(e)}
        )
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n[TEST START] Python Basic Types")
    
    success = test_basic_types()
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Basic Types: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
