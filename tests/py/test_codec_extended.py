#!/usr/bin/env python3
"""
Test codec - Extended message ID and payload tests (Python).
Uses the new Parser with header + payload architecture.
Streaming interface - no JSON dependency.
"""

import os


def encode_extended_messages(format_name):
    """Encode multiple extended test messages using the specified frame format."""
    import sys
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
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
    
    from test_messages_data_extended import write_extended_test_messages
    
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
    capacity = 8192  # Larger for extended payloads
    writer_creators = {
        'profile_bulk': lambda: create_profile_bulk_writer(capacity),
        'profile_network': lambda: create_profile_network_writer(capacity),
    }
    
    creator = writer_creators.get(format_name)
    if not creator:
        raise ValueError(f"Format not supported for extended messages: {format_name}. Use profile_bulk or profile_network.")
    
    writer = creator()
    
    # Use streaming interface - messages are written directly to the writer
    write_extended_test_messages(writer, msg_classes)
    
    return writer.data()


def decode_extended_messages(format_name, data):
    """Decode and validate multiple extended test messages."""
    import sys
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
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
    
    from test_messages_data_extended import get_extended_test_message_count, get_extended_test_message
    
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
        # Full msg_id = (pkg_id << 8) | msg_id
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
