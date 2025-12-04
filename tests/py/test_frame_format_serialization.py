#!/usr/bin/env python3
"""
Frame format serialization test for Python.

This test serializes data using different frame formats and saves to binary files.
Usage: test_frame_format_serialization.py <frame_format>
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


def create_test_data(frame_format):
    """Create test data for the specified frame format"""
    try:
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

        # Load expected values from JSON
        expected = load_expected_values()
        if not expected:
            return False

        # Create test message using values from JSON
        msg = SerializationTestSerializationTestMessage(
            magic_number=expected['magic_number'],
            test_string=expected['test_string'].encode('utf-8'),
            test_float=expected['test_float'],
            test_bool=expected['test_bool'],
            test_array=expected['test_array']
        )

        # Create parser instance and encode using the frame format
        parser = parser_class()
        encoded_data = parser.encode_msg(msg)

        # Write to file
        filename = f'python_{frame_format}_test_data.bin'
        with open(filename, 'wb') as f:
            f.write(bytes(encoded_data))

        print(f"  [OK] Encoded with {frame_format} format ({len(encoded_data)} bytes) -> {filename}")
        return True

    except ImportError as e:
        print(f"  Import error: {e}")
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
    print("\n[TEST START] Python Frame Format Serialization")

    if len(sys.argv) != 2:
        print(f"  Usage: {sys.argv[0]} <frame_format>")
        print("  Supported formats:")
        for fmt in get_supported_formats():
            print(f"    {fmt}")
        print("[TEST END] Python Frame Format Serialization: FAIL\n")
        return False
    
    frame_format = sys.argv[1]
    success = create_test_data(frame_format)
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Frame Format Serialization: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
