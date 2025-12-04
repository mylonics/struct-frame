#!/usr/bin/env python3
"""
Frame format deserialization test for Python.

This test reads binary files and deserializes using different frame formats.
Usage: test_frame_format_deserialization.py <frame_format> <binary_file>
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
    json_path = os.path.join(os.path.dirname(__file__), '..', 'expected_values.json')
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


def get_frame_parser_class(frame_format):
    """Get the frame parser class for a given frame format name"""
    import importlib
    
    # Map frame format names to class names
    format_class_map = {
        'basic_default': 'BasicDefault',
        'basic_minimal': 'BasicMinimal',
        'basic_seq': 'BasicSeq',
        'basic_sys_comp': 'BasicSysComp',
        'basic_extended_msg_ids': 'BasicExtendedMsgIds',
        'basic_extended_length': 'BasicExtendedLength',
        'basic_extended': 'BasicExtended',
        'basic_multi_system_stream': 'BasicMultiSystemStream',
        'basic_extended_multi_system_stream': 'BasicExtendedMultiSystemStream',
        'tiny_default': 'TinyDefault',
        'tiny_minimal': 'TinyMinimal',
        'tiny_seq': 'TinySeq',
        'tiny_sys_comp': 'TinySysComp',
        'tiny_extended_msg_ids': 'TinyExtendedMsgIds',
        'tiny_extended_length': 'TinyExtendedLength',
        'tiny_extended': 'TinyExtended',
        'tiny_multi_system_stream': 'TinyMultiSystemStream',
        'tiny_extended_multi_system_stream': 'TinyExtendedMultiSystemStream',
    }
    
    class_name = format_class_map.get(frame_format)
    if not class_name:
        return None, None
    
    # Import the module dynamically using importlib
    # The generated code uses relative imports, so import through the package
    # The PYTHONPATH should be set to tests/generated (not tests/generated/py)
    try:
        # First try importing from py package
        module = importlib.import_module(f"py.{frame_format}")
        parser_class = getattr(module, class_name)
        return parser_class, class_name
    except (ImportError, AttributeError):
        pass
    
    # Fallback: try direct import (if PYTHONPATH includes generated/py directly)
    try:
        module = importlib.import_module(frame_format)
        parser_class = getattr(module, class_name)
        return parser_class, class_name
    except (ImportError, AttributeError) as e:
        print(f"  Error loading frame format {frame_format}: {e}")
        return None, None


def read_and_validate_test_data(frame_format, filename):
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

        # Import the message class (works with PYTHONPATH including generated parent)
        import importlib
        try:
            msg_module = importlib.import_module('py.serialization_test_sf')
            SerializationTestSerializationTestMessage = msg_module.SerializationTestSerializationTestMessage
        except ImportError:
            try:
                from serialization_test_sf import SerializationTestSerializationTestMessage
            except ImportError as e:
                print(f"  Error importing serialization_test_sf: {e}")
                return False

        # Get frame parser class
        parser_class, class_name = get_frame_parser_class(frame_format)
        if parser_class is None:
            print(f"  Unknown frame format: {frame_format}")
            return False

        # Validate and decode using the frame parser
        result = parser_class.validate_packet(list(binary_data))
        
        if not result.valid:
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

        print(f"  [OK] Data validated successfully with {frame_format} format")
        return True

    except ImportError as e:
        print(f"  Error: Generated code not available: {e}")
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


def get_supported_formats():
    """Return list of supported frame formats"""
    return [
        'basic_default', 'basic_minimal', 'basic_seq', 'basic_sys_comp',
        'basic_extended_msg_ids', 'basic_extended_length', 'basic_extended',
        'basic_multi_system_stream', 'basic_extended_multi_system_stream',
        'tiny_default', 'tiny_minimal', 'tiny_seq', 'tiny_sys_comp',
        'tiny_extended_msg_ids', 'tiny_extended_length', 'tiny_extended',
        'tiny_multi_system_stream', 'tiny_extended_multi_system_stream',
    ]


def main():
    """Main test function"""
    print("\n[TEST START] Python Frame Format Deserialization")

    if len(sys.argv) != 3:
        print(f"  Usage: {sys.argv[0]} <frame_format> <binary_file>")
        print("  Supported formats:")
        for fmt in get_supported_formats():
            print(f"    {fmt}")
        print("[TEST END] Python Frame Format Deserialization: FAIL\n")
        return False

    frame_format = sys.argv[1]
    filename = sys.argv[2]
    
    success = read_and_validate_test_data(frame_format, filename)

    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Frame Format Deserialization: {status}\n")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
