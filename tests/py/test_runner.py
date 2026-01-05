#!/usr/bin/env python3
"""
Test runner entry point for Python.

Usage:
    test_runner.py encode <frame_format> <output_file>
    test_runner.py decode <frame_format> <input_file>

Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
"""

import sys
import os

# Add the generated code directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
gen_dir = os.path.join(script_dir, '..', 'generated', 'py')
if gen_dir not in sys.path:
    sys.path.insert(0, gen_dir)


def print_usage():
    print("Usage:")
    print("  test_runner.py encode <frame_format> <output_file>")
    print("  test_runner.py decode <frame_format> <input_file>")
    print("\nFrame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network")


def print_hex(data):
    hex_str = data.hex() if len(data) <= 64 else data[:64].hex() + "..."
    print(f"  Hex ({len(data)} bytes): {hex_str}")


def run_encode(format_name, output_file):
    from test_codec import encode_test_message

    print(f"[ENCODE] Format: {format_name}")

    try:
        encoded_data = encode_test_message(format_name)
    except Exception as e:
        print(f"[ENCODE] FAILED: Encoding error - {e}")
        import traceback
        traceback.print_exc()
        return 1

    try:
        with open(output_file, 'wb') as f:
            f.write(encoded_data)
    except Exception as e:
        print(
            f"[ENCODE] FAILED: Cannot create output file: {output_file} - {e}")
        return 1

    print(
        f"[ENCODE] SUCCESS: Wrote {len(encoded_data)} bytes to {output_file}")
    return 0


def run_decode(format_name, input_file):
    from test_codec import decode_test_messages

    print(f"[DECODE] Format: {format_name}, File: {input_file}")

    try:
        with open(input_file, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"[DECODE] FAILED: Cannot open input file: {input_file} - {e}")
        return 1

    if len(data) == 0:
        print("[DECODE] FAILED: Empty file")
        return 1

    try:
        success, message_count = decode_test_messages(format_name, data)
    except Exception as e:
        print(f"[DECODE] FAILED: Decoding error - {e}")
        print_hex(data)
        import traceback
        traceback.print_exc()
        return 1

    if not success:
        print("[DECODE] FAILED: Validation error")
        print_hex(data)
        return 1

    print(f"[DECODE] SUCCESS: {message_count} messages validated correctly")
    return 0


def main():
    if len(sys.argv) != 4:
        print_usage()
        return 1

    mode = sys.argv[1]
    format_name = sys.argv[2]
    file_path = sys.argv[3]

    print(f"\n[TEST START] Python {format_name} {mode}")

    if mode == "encode":
        result = run_encode(format_name, file_path)
    elif mode == "decode":
        result = run_decode(format_name, file_path)
    else:
        print(f"Unknown mode: {mode}")
        print_usage()
        result = 1

    status = "PASS" if result == 0 else "FAIL"
    print(f"[TEST END] Python {format_name} {mode}: {status}\n")

    return result


if __name__ == "__main__":
    sys.exit(main())
