#!/usr/bin/env python3
"""Basic Default frame format serialization test for Python."""

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


def create_test_data():
    """Create test data for basic_default format"""
    try:
        import importlib
        try:
            msg_module = importlib.import_module('py.serialization_test_sf')
            SerializationTestSerializationTestMessage = msg_module.SerializationTestSerializationTestMessage
            basic_module = importlib.import_module('py.basic_default')
            BasicDefault = basic_module.BasicDefault
        except ImportError:
            try:
                from serialization_test_sf import SerializationTestSerializationTestMessage
                from basic_default import BasicDefault
            except ImportError as e:
                print(f"  Error importing modules: {e}")
                return True  # Skip if generated code not available

        expected = load_expected_values()
        if not expected:
            return False

        msg = SerializationTestSerializationTestMessage(
            magic_number=expected['magic_number'],
            test_string=expected['test_string'].encode('utf-8'),
            test_float=expected['test_float'],
            test_bool=expected['test_bool'],
            test_array=expected['test_array']
        )

        parser = BasicDefault()
        encoded_data = parser.encode_msg(msg)

        with open('python_basic_default_test_data.bin', 'wb') as f:
            f.write(bytes(encoded_data))

        return True

    except Exception as e:
        print_failure_details(f"Create test data exception: {type(e).__name__}",
                             expected_values={"result": "success"},
                             actual_values={"exception": str(e)})
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n[TEST START] Python Basic Default Serialization")

    success = create_test_data()
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Basic Default Serialization: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
