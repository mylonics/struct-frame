#!/usr/bin/env python3
"""
Test codec (Python) - Encode/decode and test runner infrastructure.

This file provides:
1. Config-based encode/decode functions
2. Test runner utilities (file I/O, hex dump, CLI parsing)
3. A unified run_test_main() function for entry points

Usage:
Each test entry point (.py file) must provide a test_config with:
- MESSAGE_COUNT: number of messages
- BUFFER_SIZE: buffer size for encode/decode
- FORMATS_HELP: help text for supported formats
- TEST_NAME: name for logging
- supports_format(): function to check if format is supported
"""

import sys
import os


# ============================================================================
# Utility functions
# ============================================================================

def print_usage(config):
    """Print usage information."""
    print("Usage:")
    print(f"  test_runner.py encode <frame_format> <output_file>")
    print(f"  test_runner.py decode <frame_format> <input_file>")
    print(f"\nFrame formats: {config.FORMATS_HELP}")


def print_hex(data):
    """Print hex dump of data (up to 64 bytes)."""
    hex_str = data.hex() if len(data) <= 64 else data[:64].hex() + "..."
    print(f"  Hex ({len(data)} bytes): {hex_str}")


# ============================================================================
# Encoding functions
# ============================================================================

def encode_standard_messages(format_name):
    """Encode standard test messages using the specified frame format."""
    # Add generated code to path
    gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from serialization_test_sf import (
        SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
        SerializationTestUnionTestMessage, SerializationTestComprehensiveArrayMessage,
        SerializationTestSensor
    )
    
    from frame_profiles import (
        create_profile_standard_writer, create_profile_sensor_writer, create_profile_ipc_writer,
        create_profile_bulk_writer, create_profile_network_writer
    )
    
    from standard_test_data import (
        get_test_message_count, get_test_message, MessageType,
        create_message_from_data, create_basic_types_message_from_data,
        create_union_test_message_from_data
    )
    
    # Create the appropriate BufferWriter for this profile
    capacity = 4096
    writer_creators = {
        'profile_standard': lambda: create_profile_standard_writer(capacity),
        'profile_sensor': lambda: create_profile_sensor_writer(capacity),
        'profile_ipc': lambda: create_profile_ipc_writer(capacity),
        'profile_bulk': lambda: create_profile_bulk_writer(capacity),
        'profile_network': lambda: create_profile_network_writer(capacity),
    }
    
    creator = writer_creators.get(format_name)
    if not creator:
        raise ValueError(f"Unknown format: {format_name}")
    
    writer = creator()
    
    # Message classes mapping
    message_classes = {
        'SerializationTestMessage': SerializationTestSerializationTestMessage,
        'BasicTypesMessage': SerializationTestBasicTypesMessage,
        'UnionTestMessage': SerializationTestUnionTestMessage,
        'ComprehensiveArrayMessage': SerializationTestComprehensiveArrayMessage,
        'Sensor': SerializationTestSensor
    }
    
    # Encode all test messages
    for i in range(get_test_message_count()):
        msg_type, msg_data = get_test_message(i)
        
        if msg_type == MessageType.SERIALIZATION_TEST:
            msg = create_message_from_data(message_classes['SerializationTestMessage'], msg_data)
        elif msg_type == MessageType.BASIC_TYPES:
            msg = create_basic_types_message_from_data(message_classes['BasicTypesMessage'], msg_data)
        elif msg_type == MessageType.UNION_TEST:
            msg = create_union_test_message_from_data(
                message_classes['UnionTestMessage'],
                message_classes['ComprehensiveArrayMessage'],
                message_classes['SerializationTestMessage'],
                message_classes['Sensor'],
                msg_data
            )
        else:
            raise ValueError(f"Unknown message type: {msg_type}")
        
        msg_bytes = bytes(msg.pack())
        bytes_written = writer.write(msg.msg_id, msg_bytes)
        
        if bytes_written == 0:
            raise RuntimeError(f"Failed to encode message {i}: buffer full or encoding error")
    
    return writer.data()


def encode_extended_messages(format_name):
    """Encode extended test messages using the specified frame format."""
    # Add generated code to path
    gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from extended_test_sf import (
        ExtendedTestExtendedIdMessage1, ExtendedTestExtendedIdMessage2,
        ExtendedTestExtendedIdMessage3, ExtendedTestExtendedIdMessage4,
        ExtendedTestExtendedIdMessage5, ExtendedTestExtendedIdMessage6,
        ExtendedTestExtendedIdMessage7, ExtendedTestExtendedIdMessage8,
        ExtendedTestExtendedIdMessage9, ExtendedTestExtendedIdMessage10,
        ExtendedTestLargePayloadMessage1, ExtendedTestLargePayloadMessage2
    )
    
    from frame_profiles import (
        create_profile_bulk_writer, create_profile_network_writer
    )
    
    from extended_test_data import get_extended_test_message_count, get_extended_test_message
    
    # Map message types to classes
    msg_classes = {
        'ExtendedIdMessage1': ExtendedTestExtendedIdMessage1,
        'ExtendedIdMessage2': ExtendedTestExtendedIdMessage2,
        'ExtendedIdMessage3': ExtendedTestExtendedIdMessage3,
        'ExtendedIdMessage4': ExtendedTestExtendedIdMessage4,
        'ExtendedIdMessage5': ExtendedTestExtendedIdMessage5,
        'ExtendedIdMessage6': ExtendedTestExtendedIdMessage6,
        'ExtendedIdMessage7': ExtendedTestExtendedIdMessage7,
        'ExtendedIdMessage8': ExtendedTestExtendedIdMessage8,
        'ExtendedIdMessage9': ExtendedTestExtendedIdMessage9,
        'ExtendedIdMessage10': ExtendedTestExtendedIdMessage10,
        'LargePayloadMessage1': ExtendedTestLargePayloadMessage1,
        'LargePayloadMessage2': ExtendedTestLargePayloadMessage2,
    }
    
    # Only extended profiles support msg_id > 255
    capacity = 8192
    writer_creators = {
        'profile_bulk': lambda: create_profile_bulk_writer(capacity),
        'profile_network': lambda: create_profile_network_writer(capacity),
    }
    
    creator = writer_creators.get(format_name)
    if not creator:
        raise ValueError(f"Format not supported for extended messages: {format_name}. Use profile_bulk or profile_network.")
    
    writer = creator()
    
    # Encode all extended test messages
    for i in range(get_extended_test_message_count()):
        msg_instance, msg_type_name = get_extended_test_message(i, msg_classes)
        msg_bytes = bytes(msg_instance.pack())
        bytes_written = writer.write(msg_instance.msg_id, msg_bytes)
        
        if bytes_written == 0:
            raise RuntimeError(f"Failed to encode extended message {i}: buffer full or encoding error")
    
    return writer.data()


# ============================================================================
# Decoding functions
# ============================================================================

def decode_standard_messages(format_name, data):
    """Decode and validate standard test messages."""
    # Add generated code to path
    gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from serialization_test_sf import (
        SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
        SerializationTestUnionTestMessage
    )
    
    from frame_profiles import (
        create_profile_standard_reader, create_profile_sensor_reader, create_profile_ipc_reader,
        create_profile_bulk_reader, create_profile_network_reader
    )
    
    from standard_test_data import (
        get_test_message_count, get_test_message, MessageType,
        validate_message, validate_basic_types_message
    )
    
    # Get message length callback for minimal profiles
    def get_msg_length(msg_id):
        if msg_id == SerializationTestSerializationTestMessage.msg_id:
            return SerializationTestSerializationTestMessage.msg_size
        elif msg_id == SerializationTestBasicTypesMessage.msg_id:
            return SerializationTestBasicTypesMessage.msg_size
        elif msg_id == SerializationTestUnionTestMessage.msg_id:
            return SerializationTestUnionTestMessage.msg_size
        return None
    
    # Create the appropriate BufferReader for this profile
    reader_creators = {
        'profile_standard': lambda: create_profile_standard_reader(data),
        'profile_sensor': lambda: create_profile_sensor_reader(data, get_msg_length),
        'profile_ipc': lambda: create_profile_ipc_reader(data, get_msg_length),
        'profile_bulk': lambda: create_profile_bulk_reader(data),
        'profile_network': lambda: create_profile_network_reader(data),
    }
    
    creator = reader_creators.get(format_name)
    if not creator:
        raise ValueError(f"Unknown format: {format_name}")
    
    reader = creator()
    message_count = 0
    expected_count = get_test_message_count()
    
    # Decode and validate all messages
    while reader.has_more() and message_count < expected_count:
        result = reader.next()
        
        if not result or not result.valid:
            print(f"  Decoding failed for message {message_count}")
            return False, message_count
        
        # Get expected message
        msg_type, test_msg = get_test_message(message_count)
        
        # Validate msg_id matches expected type
        if msg_type == MessageType.SERIALIZATION_TEST:
            expected_msg_id = SerializationTestSerializationTestMessage.msg_id
        elif msg_type == MessageType.BASIC_TYPES:
            expected_msg_id = SerializationTestBasicTypesMessage.msg_id
        elif msg_type == MessageType.UNION_TEST:
            expected_msg_id = SerializationTestUnionTestMessage.msg_id
        else:
            print(f"  Unknown message type: {msg_type}")
            return False, message_count
        
        if result.msg_id != expected_msg_id:
            print(f"  Message ID mismatch for message {message_count}: expected {expected_msg_id}, got {result.msg_id}")
            return False, message_count
        
        # Decode and validate the message
        msg_data = result.msg_data
        if msg_type == MessageType.SERIALIZATION_TEST:
            msg = SerializationTestSerializationTestMessage.create_unpack(msg_data)
            if not validate_message(msg, test_msg):
                print(f"  Validation failed for message {message_count}")
                return False, message_count
        elif msg_type == MessageType.BASIC_TYPES:
            msg = SerializationTestBasicTypesMessage.create_unpack(msg_data)
            if not validate_basic_types_message(msg, test_msg):
                print(f"  Validation failed for message {message_count}")
                return False, message_count
        elif msg_type == MessageType.UNION_TEST:
            msg = SerializationTestUnionTestMessage.create_unpack(msg_data)
            # For UnionTestMessage, just validate it decoded without error
        
        message_count += 1
    
    # Ensure all messages were decoded
    if message_count != expected_count:
        print(f"  Expected {expected_count} messages, but decoded {message_count}")
        return False, message_count
    
    # Ensure all data was consumed
    if reader.remaining != 0:
        print(f"  Extra data after messages: {reader.remaining} bytes remaining")
        return False, message_count
    
    return True, message_count


def decode_extended_messages(format_name, data):
    """Decode and validate extended test messages."""
    # Add generated code to path
    gen_path = os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from extended_test_sf import (
        ExtendedTestExtendedIdMessage1, ExtendedTestExtendedIdMessage2,
        ExtendedTestExtendedIdMessage3, ExtendedTestExtendedIdMessage4,
        ExtendedTestExtendedIdMessage5, ExtendedTestExtendedIdMessage6,
        ExtendedTestExtendedIdMessage7, ExtendedTestExtendedIdMessage8,
        ExtendedTestExtendedIdMessage9, ExtendedTestExtendedIdMessage10,
        ExtendedTestLargePayloadMessage1, ExtendedTestLargePayloadMessage2
    )
    
    from frame_profiles import (
        create_profile_bulk_reader, create_profile_network_reader
    )
    
    from extended_test_data import get_extended_test_message_count, get_extended_test_message
    
    # Map message types to classes
    msg_classes = {
        'ExtendedIdMessage1': ExtendedTestExtendedIdMessage1,
        'ExtendedIdMessage2': ExtendedTestExtendedIdMessage2,
        'ExtendedIdMessage3': ExtendedTestExtendedIdMessage3,
        'ExtendedIdMessage4': ExtendedTestExtendedIdMessage4,
        'ExtendedIdMessage5': ExtendedTestExtendedIdMessage5,
        'ExtendedIdMessage6': ExtendedTestExtendedIdMessage6,
        'ExtendedIdMessage7': ExtendedTestExtendedIdMessage7,
        'ExtendedIdMessage8': ExtendedTestExtendedIdMessage8,
        'ExtendedIdMessage9': ExtendedTestExtendedIdMessage9,
        'ExtendedIdMessage10': ExtendedTestExtendedIdMessage10,
        'LargePayloadMessage1': ExtendedTestLargePayloadMessage1,
        'LargePayloadMessage2': ExtendedTestLargePayloadMessage2,
    }
    
    # Only extended profiles support msg_id > 255
    reader_creators = {
        'profile_bulk': lambda: create_profile_bulk_reader(data),
        'profile_network': lambda: create_profile_network_reader(data),
    }
    
    creator = reader_creators.get(format_name)
    if not creator:
        raise ValueError(f"Format not supported for extended messages: {format_name}. Use profile_bulk or profile_network.")
    
    reader = creator()
    expected_count = get_extended_test_message_count()
    message_count = 0
    
    while reader.has_more() and message_count < expected_count:
        result = reader.next()
        
        if not result or not result.valid:
            print(f"  Decoding failed for message {message_count}")
            return False, message_count
        
        # Get expected message
        expected_msg, msg_type_name = get_extended_test_message(message_count, msg_classes)
        expected_msg_id = expected_msg.msg_id
        
        # For extended profiles, combine pkg_id and msg_id to get full message ID
        decoded_msg_id = (result.package_id << 8) | result.msg_id
        
        if decoded_msg_id != expected_msg_id:
            print(f"  Message ID mismatch for message {message_count}: expected {expected_msg_id}, got {decoded_msg_id} (pkg_id={result.package_id}, msg_id={result.msg_id})")
            return False, message_count
        
        # Decode and validate (just verify it decodes without error)
        msg_class = msg_classes.get(msg_type_name)
        if not msg_class:
            print(f"  Unknown message type: {msg_type_name}")
            return False, message_count
        
        msg = msg_class.create_unpack(result.msg_data)
        
        message_count += 1
    
    if message_count != expected_count:
        print(f"  Expected {expected_count} messages, but decoded {message_count}")
        return False, message_count
    
    if reader.remaining != 0:
        print(f"  Extra data after messages: {reader.remaining} bytes remaining")
        return False, message_count
    
    return True, message_count


# ============================================================================
# Test runner main
# ============================================================================

def run_encode(config, encode_func, format_name, output_file):
    """Run encode test."""
    print(f"[ENCODE] Format: {format_name}")
    
    try:
        encoded_data = encode_func(format_name)
    except Exception as e:
        print(f"[ENCODE] FAILED: Encoding error - {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    try:
        with open(output_file, 'wb') as f:
            f.write(encoded_data)
    except Exception as e:
        print(f"[ENCODE] FAILED: Cannot create output file: {output_file} - {e}")
        return 1
    
    print(f"[ENCODE] SUCCESS: Wrote {len(encoded_data)} bytes to {output_file}")
    return 0


def run_decode(config, decode_func, format_name, input_file):
    """Run decode test."""
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
        success, message_count = decode_func(format_name, data)
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


def run_test_main(config, encode_func, decode_func):
    """
    Main test runner function.
    
    Args:
        config: Test configuration object
        encode_func: Function to encode messages (format_name) -> bytes
        decode_func: Function to decode messages (format_name, data) -> (success, count)
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) != 4:
        print_usage(config)
        return 1
    
    mode = sys.argv[1]
    format_name = sys.argv[2]
    file_path = sys.argv[3]
    
    # Validate format
    if not config.supports_format(format_name):
        print(f"Error: Unsupported format '{format_name}' for {config.TEST_NAME} tests")
        print(f"Supported formats: {config.FORMATS_HELP}")
        return 1
    
    print(f"\n[TEST START] Python {format_name} {mode} ({config.TEST_NAME})")
    
    if mode == "encode":
        result = run_encode(config, encode_func, format_name, file_path)
    elif mode == "decode":
        result = run_decode(config, decode_func, format_name, file_path)
    else:
        print(f"Unknown mode: {mode}")
        print_usage(config)
        result = 1
    
    status = "PASS" if result == 0 else "FAIL"
    print(f"[TEST END] Python {format_name} {mode}: {status}\n")
    
    return result
