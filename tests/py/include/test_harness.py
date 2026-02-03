#!/usr/bin/env python3
"""
Test harness (Python).
High-level test setup, CLI parsing, file I/O, and test execution.

This file matches the C++ test_harness.hpp structure.
"""

import sys
from typing import Callable

from profile_runner import encode, parse, BUFFER_SIZE


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


def run_encode(message_count: int, get_message: Callable, profile: str, output_file: str) -> int:
    """Run encode operation."""
    buffer = bytearray(BUFFER_SIZE)
    bytes_written = encode(message_count, get_message, profile, buffer)
    
    if bytes_written == 0 or not write_file(output_file, bytes(buffer[:bytes_written])):
        print("[ENCODE] FAILED")
        return 1
    
    print(f"[ENCODE] SUCCESS: Wrote {bytes_written} bytes to {output_file}")
    return 0


def run_decode(message_count: int, check_message: Callable, get_message_info: Callable, profile: str, input_file: str) -> int:
    """Run decode operation."""
    buffer = read_file(input_file)
    if len(buffer) == 0:
        print("[DECODE] FAILED: Cannot read file")
        return 1
    
    count = parse(message_count, check_message, get_message_info, profile, buffer)
    if count != message_count:
        print(f"[DECODE] FAILED: {count} of {message_count} messages validated")
        return 1
    
    print(f"[DECODE] SUCCESS: {count} messages validated")
    return 0


def run_both(message_count: int, get_message: Callable, check_message: Callable, get_message_info: Callable, profile: str) -> int:
    """Run encode then decode (round-trip test)."""
    buffer = bytearray(BUFFER_SIZE)
    bytes_written = encode(message_count, get_message, profile, buffer)
    
    if bytes_written == 0:
        print("[BOTH] FAILED: Encoding error")
        return 1
    
    print(f"[BOTH] Encoded {bytes_written} bytes")
    
    count = parse(message_count, check_message, get_message_info, profile, bytes(buffer[:bytes_written]))
    if count != message_count:
        print(f"[BOTH] FAILED: {count} of {message_count} messages validated")
        return 1
    
    print(f"[BOTH] SUCCESS: {count} messages round-trip validated")
    return 0


def run(message_count: int, get_message: Callable, check_message: Callable, get_message_info: Callable, test_name: str, profile_help: str) -> int:
    """
    Main entry point for test programs.
    
    Args:
        message_count: Number of messages
        get_message: Function(index) -> message for encoding
        check_message: Function(index, frame_info) -> bool for validation
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
    
    print(f"\n[TEST START] {test_name} {profile} {mode}")
    
    if mode == "encode":
        result = run_encode(message_count, get_message, profile, file_path)
    elif mode == "decode":
        result = run_decode(message_count, check_message, get_message_info, profile, file_path)
    else:  # both
        result = run_both(message_count, get_message, check_message, get_message_info, profile)
    
    status = "PASS" if result == 0 else "FAIL"
    print(f"[TEST END] {test_name} {profile} {mode}: {status}\n")
    
    return result
