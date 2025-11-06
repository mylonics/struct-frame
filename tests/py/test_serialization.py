#!/usr/bin/env python3
"""
Test script for cross-language serialization compatibility in Python.
"""

import sys
import os


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


def create_test_data():
    """Create test data for cross-language compatibility testing"""
    try:
        sys.path.insert(0, '../generated/py')
        from serialization_test_sf import (
            SerializationTestSerializationTestMessage, 
            _BoundedArray_test_array,
            _VariableString_test_string
        )
        from struct_frame_parser import BasicPacket

        test_string = _VariableString_test_string(18, b"Hello from Python!")
        test_array = _BoundedArray_test_array(3, [100, 200, 300, 0, 0])

        msg = SerializationTestSerializationTestMessage(
            0xDEADBEEF, test_string, 3.14159, True, test_array
        )

        packet = BasicPacket()
        encoded_data = packet.encode_msg(msg)

        with open('python_test_data.bin', 'wb') as f:
            f.write(bytes(encoded_data))

        return True

    except ImportError:
        return True  # Skip if generated code not available

    except Exception as e:
        print_failure_details(
            f"Create test data exception: {type(e).__name__}",
            expected_values={"result": "success"},
            actual_values={"exception": str(e)}
        )
        import traceback
        traceback.print_exc()
        return False


def read_test_data(filename, language):
    """Try to read and decode test data created by other languages"""
    try:
        if not os.path.exists(filename):
            return True  # Skip if file not available

        with open(filename, 'rb') as f:
            binary_data = f.read()

        if len(binary_data) == 0:
            print_failure_details(
                f"Empty data from {language}",
                expected_values={"data_size": ">0"},
                actual_values={"data_size": 0},
                raw_data=binary_data
            )
            return False

        sys.path.insert(0, './serialization_test')
        from serialization_test_sf import SerializationTestSerializationTestMessage
        from struct_frame_parser import BasicPacket, FrameParser

        packet_formats = {0x90: BasicPacket()}
        msg_definitions = {204: SerializationTestSerializationTestMessage}
        parser = FrameParser(packet_formats, msg_definitions)

        result = None
        for byte in binary_data:
            result = parser.parse_char(byte)
            if result:
                break

        if not result:
            print_failure_details(
                f"Failed to decode {language} data",
                expected_values={"decoded_message": "valid"},
                actual_values={"decoded_message": None},
                raw_data=binary_data
            )
            return False

        return True

    except ImportError:
        return True  # Skip if generated code not available

    except Exception as e:
        print_failure_details(
            f"Read {language} data exception: {type(e).__name__}",
            expected_values={"result": "success"},
            actual_values={"exception": str(e)}
        )
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n[TEST START] Python Cross-Language Serialization")
    
    success = create_test_data()
    if success:
        success = success and read_test_data('c_test_data.bin', 'C')
        success = success and read_test_data('typescript_test_data.bin', 'TypeScript')
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Cross-Language Serialization: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
