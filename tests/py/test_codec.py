#!/usr/bin/env python3
"""
Test codec - Encode/decode functions for all frame formats (Python).
Uses the new PolyglotParser with header + payload architecture.
"""

# Expected test values (from expected_values.json)
EXPECTED_VALUES = {
    'magic_number': 3735928559,  # 0xDEADBEEF
    'test_string': 'Cross-platform test!',
    'test_float': 3.14159,
    'test_bool': True,
    'test_array': [100, 200, 300],
}


def create_test_message(msg_class):
    """Create and populate a test message with expected values."""
    return msg_class(
        magic_number=EXPECTED_VALUES['magic_number'],
        test_string=EXPECTED_VALUES['test_string'].encode('utf-8'),
        test_float=EXPECTED_VALUES['test_float'],
        test_bool=EXPECTED_VALUES['test_bool'],
        test_array=EXPECTED_VALUES['test_array']
    )


def validate_test_message(msg):
    """Validate that a decoded message matches expected values."""
    errors = []

    if msg.magic_number != EXPECTED_VALUES['magic_number']:
        errors.append(
            f"magic_number: expected {EXPECTED_VALUES['magic_number']}, got {msg.magic_number}")

    # Handle string comparison (may be bytes or str)
    test_string = msg.test_string
    if isinstance(test_string, bytes):
        test_string = test_string.decode('utf-8', errors='replace')
    expected_string = EXPECTED_VALUES['test_string']
    if not test_string.startswith(expected_string):
        errors.append(
            f"test_string: expected '{expected_string}', got '{test_string}'")

    if abs(msg.test_float - EXPECTED_VALUES['test_float']) > 0.0001:
        errors.append(
            f"test_float: expected {EXPECTED_VALUES['test_float']}, got {msg.test_float}")

    if msg.test_bool != EXPECTED_VALUES['test_bool']:
        errors.append(
            f"test_bool: expected {EXPECTED_VALUES['test_bool']}, got {msg.test_bool}")

    # Handle array comparison (may be list or have .count/.data)
    test_array = msg.test_array
    if hasattr(test_array, 'count') and hasattr(test_array, 'data'):
        array_list = list(test_array.data[:test_array.count])
    else:
        array_list = list(test_array) if test_array else []

    expected_array = EXPECTED_VALUES['test_array']
    if array_list != expected_array:
        errors.append(
            f"test_array: expected {expected_array}, got {array_list}")

    if errors:
        for error in errors:
            print(f"  Value mismatch: {error}")
        return False

    return True


def get_frame_config(format_name):
    """Get the header_type and payload_type for a frame format or profile."""
    # Import from generated py package
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from polyglot_parser import HeaderType, PayloadType
    
    # Map format names to (header_type, payload_type)
    format_map = {
        # Profile names (preferred)
        'profile_standard': (HeaderType.BASIC, PayloadType.DEFAULT),
        'profile_sensor': (HeaderType.TINY, PayloadType.MINIMAL),
        'profile_bulk': (HeaderType.BASIC, PayloadType.EXTENDED),
        'profile_network': (HeaderType.BASIC, PayloadType.EXTENDED_MULTI_SYSTEM_STREAM),
        # Legacy direct format names (for backward compatibility)
        'basic_default': (HeaderType.BASIC, PayloadType.DEFAULT),
        'basic_minimal': (HeaderType.BASIC, PayloadType.MINIMAL),
        'tiny_default': (HeaderType.TINY, PayloadType.DEFAULT),
        'tiny_minimal': (HeaderType.TINY, PayloadType.MINIMAL),
        'basic_extended': (HeaderType.BASIC, PayloadType.EXTENDED),
        'basic_extended_multi_system_stream': (HeaderType.BASIC, PayloadType.EXTENDED_MULTI_SYSTEM_STREAM),
    }

    config = format_map.get(format_name)
    if not config:
        raise ValueError(f"Unknown frame format: {format_name}")
    
    return config


def get_parser(format_name=None):
    """Get the PolyglotParser instance, with proper callbacks for MINIMAL payloads."""
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from polyglot_parser import PolyglotParser, PayloadType
    
    # Check if this format uses MINIMAL payload (which has no length field)
    get_msg_length = None
    if format_name:
        _, payload_type = get_frame_config(format_name)
        if payload_type == PayloadType.MINIMAL:
            # MINIMAL payload has no length field, need callback
            msg_class = get_message_class()
            msg_size = msg_class.msg_size
            get_msg_length = lambda msg_id: msg_size
    
    return PolyglotParser(get_msg_length=get_msg_length)


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
    """Encode a test message using the specified frame format."""
    header_type, payload_type = get_frame_config(format_name)
    msg_class = get_message_class()
    parser = get_parser()

    msg = create_test_message(msg_class)
    msg_data = bytes(msg.pack())
    
    return parser.encode(
        msg_id=msg.msg_id,
        msg=msg_data,
        header_type=header_type,
        payload_type=payload_type
    )


def decode_test_message(format_name, data):
    """Decode a test message using the specified frame format."""
    header_type, payload_type = get_frame_config(format_name)
    msg_class = get_message_class()
    parser = get_parser(format_name)

    # Parse byte by byte
    result = None
    for byte in data:
        result = parser.parse_byte(byte)
        if result.valid:
            break

    if result is None or not result.valid:
        return None

    # Convert raw bytes to message object
    return msg_class.create_unpack(result.msg_data)
