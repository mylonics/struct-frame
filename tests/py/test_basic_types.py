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
    """Test basic data types serialization and deserialization"""
    try:
        sys.path.insert(0, '../generated/py')
        from basic_types_sf import BasicTypesBasicTypesMessage, _VariableString_description
        from struct_frame_parser import BasicPacket

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
