#!/usr/bin/env python3
"""
Test script for cross-platform deserialization - reads and validates test data from files.
This test reads a binary file and validates it against expected_values.json.
"""

import sys
import os
import json


def print_failure_details(label, expected_values=None, actual_values=None, raw_data=None):
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


def load_expected_values():
    """Load expected values from JSON file"""
    json_path = os.path.join(os.path.dirname(
        __file__), '..', 'expected_values.json')
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data['serialization_test']
    except Exception as e:
        print(f"Error loading expected values: {e}")
        return None


def validate_message(msg, expected):
    """Validate a decoded message against expected values"""
    if msg.magic_number != expected['magic_number']:
        print_failure_details(
            "Value mismatch: magic_number",
            expected_values={"magic_number": expected['magic_number']},
            actual_values={"magic_number": msg.magic_number}
        )
        return False

    # Compare string (bytes vs string)
    test_string = msg.test_string.decode('utf-8').rstrip('\x00') if isinstance(
        msg.test_string, bytes) else str(msg.test_string).rstrip('\x00')
    if test_string != expected['test_string']:
        print_failure_details(
            "Value mismatch: test_string",
            expected_values={"test_string": expected['test_string']},
            actual_values={"test_string": test_string}
        )
        return False

    # Compare float with tolerance
    if abs(msg.test_float - expected['test_float']) > 0.0001:
        print_failure_details(
            "Value mismatch: test_float",
            expected_values={"test_float": expected['test_float']},
            actual_values={"test_float": msg.test_float}
        )
        return False

    if msg.test_bool != expected['test_bool']:
        print_failure_details(
            "Value mismatch: test_bool",
            expected_values={"test_bool": expected['test_bool']},
            actual_values={"test_bool": msg.test_bool}
        )
        return False

    # Compare array
    if list(msg.test_array) != expected['test_array']:
        print_failure_details(
            "Value mismatch: test_array",
            expected_values={"test_array": expected['test_array']},
            actual_values={"test_array": list(msg.test_array)}
        )
        return False

    return True


def read_and_validate_test_data(filename):
    """Read and validate test data from a binary file"""
    try:
        if not os.path.exists(filename):
            print(f"  Error: file not found: {filename}")
            return False

        with open(filename, 'rb') as f:
            binary_data = f.read()

        if len(binary_data) == 0:
            print_failure_details(
                "Empty file",
                expected_values={"data_size": ">0"},
                actual_values={"data_size": 0},
                raw_data=binary_data
            )
            return False

        sys.path.insert(0, '../generated/py')
        from serialization_test_sf import SerializationTestSerializationTestMessage
        from frame_parsers_gen import BasicFrame

        # Validate and decode using BasicFrame
        result = BasicFrame.validate_packet(list(binary_data))
        
        if not result or not result.valid:
            print_failure_details(
                "Failed to decode data",
                expected_values={"decoded_message": "valid"},
                actual_values={"decoded_message": None},
                raw_data=binary_data
            )
            return False

        # Decode the message data
        msg_data = bytes(result.msg_data)
        decoded_msg = SerializationTestSerializationTestMessage.create_unpack(msg_data)

        # Load expected values and validate
        expected = load_expected_values()
        if not expected:
            return False

        if not validate_message(decoded_msg, expected):
            print("  Validation failed")
            return False

        print("  [OK] Data validated successfully")
        return True

    except ImportError:
        print("  Error: Generated code not available")
        return False

    except Exception as e:
        print_failure_details(
            f"Read data exception: {type(e).__name__}",
            expected_values={"result": "success"},
            actual_values={"exception": str(e)}
        )
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n[TEST START] Python Cross-Platform Deserialization")

    if len(sys.argv) != 2:
        print(f"  Usage: {sys.argv[0]} <binary_file>")
        print("[TEST END] Python Cross-Platform Deserialization: FAIL\n")
        return False

    success = read_and_validate_test_data(sys.argv[1])

    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Cross-Platform Deserialization: {status}\n")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
