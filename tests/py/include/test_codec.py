#!/usr/bin/env python3
"""
Test codec (template-based) - Config-based encode/decode and test runner infrastructure.

This file provides:
1. Template encode/decode functions that work with any TestConfig
2. Test runner utilities (file I/O, hex dump, CLI parsing)
3. A unified run_test_main() function for entry points

Usage:
Each test entry point (.py file) must provide a TestConfig with:
- MESSAGE_COUNT: number of messages
- BUFFER_SIZE: buffer size for encode/decode
- FORMATS_HELP: help text for supported formats
- TEST_NAME: name for logging
- get_msg_id_order(): list of msg_ids in encode/decode order
- create_encoder(): factory function returning an Encoder object
- create_validator(): factory function returning a Validator object
- get_message_info(msg_id): unified function returning MessageInfo (size, magic1, magic2)
- supports_format(format): check if format is supported
"""

import sys
import os
from typing import Callable, Optional, List, Tuple, Any

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))


# ============================================================================
# Utility functions
# ============================================================================

def print_hex(data: bytes, max_bytes: int = 64) -> None:
    """Print hex dump of data (up to max_bytes)."""
    print(f"  Hex ({len(data)} bytes): ", end="")
    for i, b in enumerate(data[:max_bytes]):
        print(f"{b:02x}", end="")
    if len(data) > max_bytes:
        print("...", end="")
    print()


def print_usage(program_name: str, formats_help: str) -> None:
    """Print usage help."""
    print("Usage:")
    print(f"  {program_name} encode <frame_format> <output_file>")
    print(f"  {program_name} decode <frame_format> <input_file>")
    print(f"\nFrame formats: {formats_help}")


# ============================================================================
# Template encode function
# ============================================================================

def encode_messages(config, format_name: str, buffer: bytearray) -> Tuple[bool, int]:
    """
    Encode messages using the given config and format.
    
    Args:
        config: Config object with message data (must have MESSAGE_COUNT, get_msg_id_order, create_encoder)
        format_name: Frame format name (e.g., 'profile_standard')
        buffer: Buffer to encode into
        
    Returns:
        (success, encoded_size) tuple
    """
    from frame_profiles import (
        ProfileStandardWriter,
        ProfileSensorWriter,
        ProfileIPCWriter,
        ProfileBulkWriter,
        ProfileNetworkWriter,
    )
    
    if not config.supports_format(format_name):
        print(f"  Unsupported format: {format_name}")
        return False, 0
    
    msg_order = config.get_msg_id_order()
    encoder = config.create_encoder()
    
    # Writer classes for each format
    writer_classes = {
        'profile_standard': ProfileStandardWriter,
        'profile_sensor': ProfileSensorWriter,
        'profile_ipc': ProfileIPCWriter,
        'profile_bulk': ProfileBulkWriter,
        'profile_network': ProfileNetworkWriter,
    }
    
    writer_class = writer_classes.get(format_name)
    if not writer_class:
        print(f"  Unknown frame format: {format_name}")
        return False, 0
    
    writer = writer_class(len(buffer))
    
    for i in range(config.MESSAGE_COUNT):
        msg_id = msg_order[i]
        written = encoder.write_message(writer, msg_id)
        
        if written == 0:
            print(f"  Encoding failed for message {i} (ID {msg_id})")
            return False, 0
    
    # Copy data back to the provided buffer
    data = writer.data()
    buffer[:len(data)] = data
    
    if "Variable Flag" in config.TEST_NAME:
        print(f"Total: {writer.size()} bytes")
    
    return True, writer.size()


# ============================================================================
# Template decode function
# ============================================================================

def decode_messages(config, format_name: str, buffer: bytes) -> Tuple[bool, int]:
    """
    Decode messages using the given config and format.
    
    Args:
        config: Config object with message data (must have MESSAGE_COUNT, get_msg_id_order, create_validator)
        format_name: Frame format name (e.g., 'profile_standard')
        buffer: Buffer containing encoded data
        
    Returns:
        (success, message_count) tuple
    """
    from frame_profiles import (
        ProfileStandardAccumulatingReader,
        ProfileSensorAccumulatingReader,
        ProfileIPCAccumulatingReader,
        ProfileBulkAccumulatingReader,
        ProfileNetworkAccumulatingReader,
    )
    
    if not config.supports_format(format_name):
        print(f"  Unsupported format: {format_name}")
        return False, 0
    
    msg_order = config.get_msg_id_order()
    validator = config.create_validator()
    message_count = 0
    
    # Split buffer into 3 chunks to test partial message handling
    buffer_size = len(buffer)
    chunk1_size = buffer_size // 3
    chunk2_size = buffer_size // 3
    chunk3_size = buffer_size - chunk1_size - chunk2_size
    
    chunks = [
        buffer[:chunk1_size],
        buffer[chunk1_size:chunk1_size + chunk2_size],
        buffer[chunk1_size + chunk2_size:]
    ]
    
    # Get unified message info function
    get_msg_info = config.get_message_info
    
    # Reader classes for each format
    reader_info = {
        'profile_standard': lambda: ProfileStandardAccumulatingReader(get_msg_info, config.BUFFER_SIZE),
        'profile_sensor': lambda: ProfileSensorAccumulatingReader(get_msg_info, config.BUFFER_SIZE),
        'profile_ipc': lambda: ProfileIPCAccumulatingReader(get_msg_info, config.BUFFER_SIZE),
        'profile_bulk': lambda: ProfileBulkAccumulatingReader(get_msg_info, config.BUFFER_SIZE),
        'profile_network': lambda: ProfileNetworkAccumulatingReader(get_msg_info, config.BUFFER_SIZE),
    }
    
    factory = reader_info.get(format_name)
    if not factory:
        print(f"  Unknown frame format: {format_name}")
        return False, 0
    
    reader = factory()
    
    # Process chunks
    for chunk in chunks:
        reader.add_data(chunk)
        
        while True:
            result = reader.next()
            if result is None or not result.valid:
                break
            
            if message_count >= config.MESSAGE_COUNT:
                print(f"  Too many messages decoded: {message_count}")
                return False, message_count
            
            expected_msg_id = msg_order[message_count]
            if result.msg_id != expected_msg_id:
                print(f"  Message {message_count} ID mismatch: expected {expected_msg_id}, got {result.msg_id}")
                return False, message_count
            
            # Use validate_with_equals to compare using __eq__ operator
            # Pass the FrameMsgInfo directly - it contains msg_id
            if not validator.validate_with_equals(result):
                print(f"  Message {message_count} content mismatch (equality check failed)")
                return False, message_count
            
            message_count += 1
    
    if message_count != config.MESSAGE_COUNT:
        print(f"  Expected {config.MESSAGE_COUNT} messages, decoded {message_count}")
        return False, message_count
    
    if reader.has_partial():
        print(f"  Incomplete partial message: {reader.partial_size()} bytes")
        return False, message_count
    
    return True, message_count


# ============================================================================
# Test runner functions
# ============================================================================

def run_encode(config, format_name: str, output_file: str) -> int:
    """Run encode test."""
    buffer = bytearray(config.BUFFER_SIZE)
    
    print(f"[ENCODE] Format: {format_name}")
    
    success, encoded_size = encode_messages(config, format_name, buffer)
    
    if not success:
        print("[ENCODE] FAILED: Encoding error")
        return 1
    
    try:
        with open(output_file, 'wb') as f:
            f.write(buffer[:encoded_size])
    except IOError as e:
        print(f"[ENCODE] FAILED: Cannot create output file: {output_file} ({e})")
        return 1
    
    print(f"[ENCODE] SUCCESS: Wrote {encoded_size} bytes to {output_file}")
    return 0


def run_decode(config, format_name: str, input_file: str) -> int:
    """Run decode test."""
    print(f"[DECODE] Format: {format_name}, File: {input_file}")
    
    try:
        with open(input_file, 'rb') as f:
            buffer = f.read()
    except IOError as e:
        print(f"[DECODE] FAILED: Cannot open input file: {input_file} ({e})")
        return 1
    
    if len(buffer) == 0:
        print("[DECODE] FAILED: Empty file")
        return 1
    
    success, message_count = decode_messages(config, format_name, buffer)
    
    if not success:
        print(f"[DECODE] FAILED: {message_count} messages validated before error")
        print_hex(buffer)
        return 1
    
    print(f"[DECODE] SUCCESS: {message_count} messages validated correctly")
    return 0


def run_test_main(config) -> int:
    """
    Main entry point for test programs.
    Parses command line arguments and runs encode or decode.
    """
    if len(sys.argv) != 4:
        print_usage(sys.argv[0], config.FORMATS_HELP)
        return 1
    
    mode = sys.argv[1]
    format_name = sys.argv[2]
    file_path = sys.argv[3]
    
    print(f"\n[TEST START] {config.TEST_NAME} {format_name} {mode}")
    
    if mode == "encode":
        result = run_encode(config, format_name, file_path)
    elif mode == "decode":
        result = run_decode(config, format_name, file_path)
    else:
        print(f"Unknown mode: {mode}")
        result = 1
    
    status = "PASS" if result == 0 else "FAIL"
    print(f"[TEST END] {config.TEST_NAME} {format_name} {mode}: {status}\n")
    
    return result
