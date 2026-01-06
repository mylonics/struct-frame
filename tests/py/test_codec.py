#!/usr/bin/env python3
"""
Test codec - Encode/decode functions for all frame formats (Python).
Uses the new Parser with header + payload architecture.
"""

import json
import os


def load_test_messages():
    """Load test messages from test_messages.json"""
    # Try different paths to find the JSON file
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'test_messages.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'test_messages.json'),
        'test_messages.json',
        '../test_messages.json',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                # Return SerializationTestMessage data for backwards compatibility
                return data.get('SerializationTestMessage', data.get('messages', []))
    
    raise FileNotFoundError("Could not find test_messages.json")


def create_message_from_data(msg_class, test_msg):
    """Create a message from test message data."""
    return msg_class(
        magic_number=test_msg['magic_number'],
        test_string=test_msg['test_string'].encode('utf-8'),
        test_float=test_msg['test_float'],
        test_bool=test_msg['test_bool'],
        test_array=test_msg['test_array']
    )


def validate_message(msg, test_msg):
    """Validate that a decoded message matches expected test message data."""
    errors = []

    if msg.magic_number != test_msg['magic_number']:
        errors.append(
            f"magic_number: expected {test_msg['magic_number']}, got {msg.magic_number}")

    # Handle string comparison (may be bytes or str)
    test_string = msg.test_string
    if isinstance(test_string, bytes):
        test_string = test_string.decode('utf-8', errors='replace').rstrip('\x00')
    expected_string = test_msg['test_string']
    if test_string != expected_string:
        errors.append(
            f"test_string: expected '{expected_string}', got '{test_string}'")

    # Use relative tolerance for float comparison to handle precision issues
    expected_float = test_msg['test_float']
    tolerance = max(abs(expected_float) * 1e-4, 1e-4)  # 0.01% or 0.0001, whichever is larger
    if abs(msg.test_float - expected_float) > tolerance:
        errors.append(
            f"test_float: expected {expected_float}, got {msg.test_float}")

    if msg.test_bool != test_msg['test_bool']:
        errors.append(
            f"test_bool: expected {test_msg['test_bool']}, got {msg.test_bool}")

    # Handle array comparison (may be list or have .count/.data)
    test_array = msg.test_array
    if hasattr(test_array, 'count') and hasattr(test_array, 'data'):
        array_list = list(test_array.data[:test_array.count])
    else:
        array_list = list(test_array) if test_array else []

    expected_array = test_msg['test_array']
    if array_list != expected_array:
        errors.append(
            f"test_array: expected {expected_array}, got {array_list}")

    if errors:
        for error in errors:
            print(f"  Value mismatch: {error}")
        return False

    return True


# Backwards compatibility - keep old function names
# EXPECTED_VALUES is derived from the first message in the JSON
try:
    _loaded_messages = load_test_messages()
    EXPECTED_VALUES = _loaded_messages[0] if _loaded_messages else {
        'magic_number': 0,
        'test_string': '',
        'test_float': 0.0,
        'test_bool': False,
        'test_array': [],
    }
except Exception:
    # If JSON loading fails during import, use empty values
    EXPECTED_VALUES = {
        'magic_number': 0,
        'test_string': '',
        'test_float': 0.0,
        'test_bool': False,
        'test_array': [],
    }


def create_test_message(msg_class):
    """Create and populate a test message with expected values (backwards compat)."""
    return create_message_from_data(msg_class, EXPECTED_VALUES)


def validate_test_message(msg):
    """Validate that a decoded message matches expected values (backwards compat)."""
    return validate_message(msg, EXPECTED_VALUES)


def get_frame_config(format_name):
    """Get the header_type and payload_type for a frame format or profile."""
    # Import from generated py package
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from parser import HeaderType, PayloadType
    
    # Map format names to (header_type, payload_type)
    format_map = {
        # Profile names (preferred)
        'profile_standard': (HeaderType.BASIC, PayloadType.DEFAULT),
        'profile_sensor': (HeaderType.TINY, PayloadType.MINIMAL),
        'profile_ipc': (HeaderType.NONE, PayloadType.MINIMAL),
        'profile_bulk': (HeaderType.BASIC, PayloadType.EXTENDED),
        'profile_network': (HeaderType.BASIC, PayloadType.EXTENDED_MULTI_SYSTEM_STREAM),
    }

    config = format_map.get(format_name)
    if not config:
        raise ValueError(f"Unknown frame format: {format_name}")
    
    return config


def get_parser(format_name=None):
    """Get the Parser instance, with proper callbacks for MINIMAL payloads."""
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)

    from parser import Parser, PayloadType

    # Check if this format uses MINIMAL payload (which has no length field)
    get_msg_length = None
    if format_name:
        _, payload_type = get_frame_config(format_name)
        if payload_type == PayloadType.MINIMAL:
            # MINIMAL payload has no length field, need callback
            msg_class = get_message_class()
            msg_size = msg_class.msg_size
            get_msg_length = lambda msg_id: msg_size

    return Parser(get_msg_length=get_msg_length)


def get_message_class():
    """Get the message class."""
    try:
        import importlib
        try:
            module = importlib.import_module('py.serialization_test_sf')
        except ImportError:
            import sys
            import os
            gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
            if os.path.exists(gen_path) and gen_path not in sys.path:
                sys.path.insert(0, gen_path)
            module = importlib.import_module('serialization_test_sf')
        return module.SerializationTestSerializationTestMessage
    except Exception as e:
        raise ImportError(f"Cannot import message class: {e}")


def encode_test_message(format_name):
    """Encode multiple test messages using the specified frame format."""
    return encode_test_messages(format_name)


def encode_test_messages(format_name):
    """Encode multiple test messages using the specified frame format."""
    header_type, payload_type = get_frame_config(format_name)
    msg_class = get_message_class()
    parser = get_parser()
    
    test_messages = load_test_messages()
    encoded_data = bytearray()
    
    for test_msg in test_messages:
        msg = create_message_from_data(msg_class, test_msg)
        msg_data = bytes(msg.pack())
        
        frame_data = parser.encode(
            msg_id=msg.msg_id,
            msg=msg_data,
            header_type=header_type,
            payload_type=payload_type
        )
        encoded_data.extend(frame_data)
    
    return bytes(encoded_data)


def decode_test_message(format_name, data):
    """Decode multiple test messages using the specified frame format."""
    return decode_test_messages(format_name, data)


def decode_test_messages(format_name, data):
    """Decode and validate multiple test messages using the specified frame format."""
    # Import from generated py package
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from parser import HeaderType, PayloadType
    
    header_type, payload_type = get_frame_config(format_name)
    msg_class = get_message_class()
    parser = get_parser(format_name)
    test_messages = load_test_messages()
    
    message_count = 0
    data_index = 0
    
    while data_index < len(data) and message_count < len(test_messages):
        # Parse byte by byte until we get a valid message
        result = None
        start_index = data_index
        
        for byte_val in data[data_index:]:
            result = parser.parse_byte(byte_val)
            data_index += 1
            
            if result and result.valid:
                # Successfully decoded a message
                break
        
        if not result or not result.valid:
            print(f"  Decoding failed for message {message_count}")
            return False, message_count
        
        # Decode the message
        msg_data = result.msg_data
        msg = msg_class.create_unpack(msg_data)
        
        # Validate against expected test message
        if not validate_message(msg, test_messages[message_count]):
            print(f"  Validation failed for message {message_count}")
            return False, message_count
        
        message_count += 1
    
    # Ensure all messages were decoded
    if message_count != len(test_messages):
        print(f"  Expected {len(test_messages)} messages, but decoded {message_count}")
        return False, message_count
    
    # Ensure all data was consumed
    if data_index != len(data):
        print(f"  Extra data after messages: processed {data_index} bytes, got {len(data)} bytes")
        return False, message_count
    
    return True, message_count

