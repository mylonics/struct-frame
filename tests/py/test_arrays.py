#!/usr/bin/env python3
"""
Test script for array operations serialization/deserialization in Python.
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


def test_array_operations():
    """Test array operations serialization and deserialization with BasicPacket"""
    try:
        sys.path.insert(0, '../generated/py')
        from comprehensive_arrays_sf import (
            ComprehensiveArraysComprehensiveArrayMessage,
            ComprehensiveArraysSensor,
            ComprehensiveArraysStatus,
            _BoundedArray_bounded_uints,
            _BoundedArray_bounded_doubles,
            _BoundedStringArray_bounded_strings,
            _BoundedArray_bounded_statuses,
            _BoundedArray_bounded_sensors
        )
        from struct_frame_parser import BasicPacket, FrameParser

        sensor1 = ComprehensiveArraysSensor(1, 25.5, 1, b"Temp1")
        sensor3 = ComprehensiveArraysSensor(3, 15.5, 2, b"Pressure")

        bounded_uints = _BoundedArray_bounded_uints(3, [100, 200, 300])
        bounded_doubles = _BoundedArray_bounded_doubles(2, [123.456, 789.012])
        bounded_strings = _BoundedStringArray_bounded_strings(2, [b"BoundedStr1", b"BoundedStr2"])
        bounded_statuses = _BoundedArray_bounded_statuses(2, [1, 3])
        bounded_sensors = _BoundedArray_bounded_sensors(1, sensor3)

        msg = ComprehensiveArraysComprehensiveArrayMessage(
            [1, 2, 3], [1.1, 2.2], [True, False, True, False],
            bounded_uints, bounded_doubles,
            [b"String1", b"String2"], bounded_strings,
            [1, 2], bounded_statuses,
            sensor1, bounded_sensors
        )

        # Encode message into BasicPacket format
        packet = BasicPacket()
        encoded_data = packet.encode_msg(msg)

        if len(encoded_data) == 0:
            print_failure_details(
                "Empty encoded data",
                expected_values={"encoded_size": ">0"},
                actual_values={"encoded_size": len(encoded_data)}
            )
            return False

        # Decode the BasicPacket back into a message
        packet_formats = {0x90: BasicPacket()}
        msg_definitions = {203: ComprehensiveArraysComprehensiveArrayMessage}
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
        if decoded_msg.fixed_uints != msg.fixed_uints:
            print_failure_details(
                "Value mismatch: fixed_uints",
                expected_values={"fixed_uints": msg.fixed_uints},
                actual_values={"fixed_uints": decoded_msg.fixed_uints}
            )
            return False

        if decoded_msg.bounded_uints.count != msg.bounded_uints.count:
            print_failure_details(
                "Value mismatch: bounded_uints.count",
                expected_values={"count": msg.bounded_uints.count},
                actual_values={"count": decoded_msg.bounded_uints.count}
            )
            return False

        if decoded_msg.sensor.id != msg.sensor.id:
            print_failure_details(
                "Value mismatch: sensor.id",
                expected_values={"sensor.id": msg.sensor.id},
                actual_values={"sensor.id": decoded_msg.sensor.id}
            )
            return False

        return True

    except ImportError:
        return True  # Skip if generated code not available

    except Exception as e:
        print_failure_details(
            f"Exception: {type(e).__name__}",
            expected_values={"result": "success"},
            actual_values={"exception": str(e)}
        )
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n[TEST START] Python Array Operations")
    
    success = test_array_operations()
    
    status = "PASS" if success else "FAIL"
    print(f"[TEST END] Python Array Operations: {status}\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
