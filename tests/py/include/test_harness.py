#!/usr/bin/env python3
"""
Test harness (Python).
High-level test setup, CLI parsing, file I/O, and test execution.

This file matches the C++ test_harness.hpp structure.
"""

import sys
from typing import Callable

from profile_runner import get_profile_ops, BUFFER_SIZE


def print_usage(program_name: str, profile_help: str) -> None:
    """Print usage help."""
    print("Usage:")
    print(f"  {program_name} encode <profile> <output_file>")
    print(f"  {program_name} decode <profile> <input_file>")
    print(f"  {program_name} both <profile>")
    print(f"\nProfiles: {profile_help}")


def write_file(path: str, data: bytes) -> bool:
    """Write data to file."""
    try:
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except IOError:
        return False


def read_file(path: str) -> bytes:
    """Read data from file."""
    try:
        with open(path, 'rb') as f:
            return f.read()
    except IOError:
        return b''


def run_encode(encode_fn: Callable, output_file: str, message_count: int) -> int:
    """Run encode operation."""
    buffer = bytearray(BUFFER_SIZE)
    bytes_written = encode_fn(buffer)
    
    if bytes_written == 0 or not write_file(output_file, bytes(buffer[:bytes_written])):
        print("[ENCODE] FAILED")
        return 1
    
    print(f"[ENCODE] SUCCESS: Wrote {bytes_written} bytes to {output_file}")
    return 0


def run_decode(parse_fn: Callable, input_file: str, message_count: int) -> int:
    """Run decode operation."""
    buffer = read_file(input_file)
    if len(buffer) == 0:
        print("[DECODE] FAILED: Cannot read file")
        return 1
    
    count = parse_fn(buffer)
    if count != message_count:
        print(f"[DECODE] FAILED: {count} of {message_count} messages validated")
        return 1
    
    print(f"[DECODE] SUCCESS: {count} messages validated")
    return 0


def run_both(encode_fn: Callable, parse_fn: Callable, message_count: int) -> int:
    """Run encode then decode (round-trip test)."""
    buffer = bytearray(BUFFER_SIZE)
    bytes_written = encode_fn(buffer)
    
    if bytes_written == 0:
        print("[BOTH] FAILED: Encoding error")
        return 1
    
    print(f"[BOTH] Encoded {bytes_written} bytes")
    
    count = parse_fn(bytes(buffer[:bytes_written]))
    if count != message_count:
        print(f"[BOTH] FAILED: {count} of {message_count} messages validated")
        return 1
    
    print(f"[BOTH] SUCCESS: {count} messages round-trip validated")
    return 0


def run(message_provider, get_message_info: Callable, test_name: str, profile_help: str) -> int:
    """
    Main entry point for test programs.
    
    Args:
        message_provider: Module with MESSAGE_COUNT and get_message(index)
        get_message_info: Function to get message info by msg_id
        test_name: Name for test output labeling
        profile_help: Help text listing available profiles
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) < 3:
        print_usage(sys.argv[0], profile_help)
        return 1
    
    mode = sys.argv[1]
    profile = sys.argv[2]
    file_path = sys.argv[3] if len(sys.argv) > 3 else ""
    
    if mode not in ("encode", "decode", "both"):
        print(f"Unknown mode: {mode}")
        print_usage(sys.argv[0], profile_help)
        return 1
    
    if mode in ("encode", "decode") and not file_path:
        print(f"Mode '{mode}' requires a file argument")
        print_usage(sys.argv[0], profile_help)
        return 1
    
    encode_fn, parse_fn = get_profile_ops(message_provider, get_message_info, profile)
    
    # Verify profile is supported by checking if encode returns > 0 for a small test
    test_buffer = bytearray(64)
    # Can't easily test without encoding, so we rely on profile_runner to return 0 for invalid profiles
    
    print(f"\n[TEST START] {test_name} {profile} {mode}")
    
    message_count = message_provider.MESSAGE_COUNT
    
    if mode == "encode":
        result = run_encode(encode_fn, file_path, message_count)
    elif mode == "decode":
        result = run_decode(parse_fn, file_path, message_count)
    else:  # both
        result = run_both(encode_fn, parse_fn, message_count)
    
    status = "PASS" if result == 0 else "FAIL"
    print(f"[TEST END] {test_name} {profile} {mode}: {status}\n")
    
    return result
