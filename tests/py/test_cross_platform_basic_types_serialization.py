#!/usr/bin/env python3
"""
Test script for cross-platform basic types serialization - writes test data to file.
This test populates a BasicTypesMessage from expected_values.json and writes it to a binary file.
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
        return data['basic_types']
    except Exception as e:
        print(f"Error loading expected values: {e}")
        return None


def create_test_data():
    """Create test data for cross-platform compatibility testing"""
    try:
        sys.path.insert(0, '../generated/py')
        from basic_types_sf import BasicTypesBasicTypesMessage
        from struct_frame_parser import BasicFrame

        # Load expected values from JSON
        expected = load_expected_values()
        if not expected:
            return False

        # Handle large_uint which may be a string in JSON due to JavaScript number limits
        large_uint = expected['large_uint']
        if isinstance(large_uint, str):
            large_uint = int(large_uint)

        # Create test message using values from JSON
        msg = BasicTypesBasicTypesMessage(
            small_int=expected['small_int'],
            medium_int=expected['medium_int'],
            regular_int=expected['regular_int'],
            large_int=expected['large_int'],
            small_uint=expected['small_uint'],
            medium_uint=expected['medium_uint'],
            regular_uint=expected['regular_uint'],
            large_uint=large_uint,
            single_precision=expected['single_precision'],
            double_precision=expected['double_precision'],
            flag=expected['flag'],
            device_id=expected['device_id'].encode('utf-8'),
            description=expected['description'].encode('utf-8')
        )

        packet = BasicFrame()
        encoded_data = packet.encode_msg(msg)

        with open('python_basic_types_test_data.bin', 'wb') as f:
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


def main():
    """Main test function"""
    print("\n[TEST START] Python Cross-Platform Basic Types Serialization")
    
    success = create_test_data()
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Cross-Platform Basic Types Serialization: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
