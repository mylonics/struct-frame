#!/usr/bin/env python3
"""
Test codec - Encode/decode functions for all frame formats (Python).
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


def get_parser_class(format_name):
    """Get the parser class for a frame format."""
    format_map = {
        'basic_default': 'BasicDefault',
        'basic_minimal': 'BasicMinimal',
        'tiny_default': 'TinyDefault',
        'tiny_minimal': 'TinyMinimal',
    }

    class_name = format_map.get(format_name)
    if not class_name:
        raise ValueError(f"Unknown frame format: {format_name}")

    module_name = format_name
    try:
        import importlib
        # Try importing from py package first
        try:
            module = importlib.import_module(f'py.{module_name}')
        except ImportError:
            module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except Exception as e:
        raise ImportError(f"Cannot import parser for {format_name}: {e}")


def get_message_class():
    """Get the message class."""
    try:
        import importlib
        try:
            module = importlib.import_module('py.serialization_test_sf')
        except ImportError:
            module = importlib.import_module('serialization_test_sf')
        return module.SerializationTestSerializationTestMessage
    except Exception as e:
        raise ImportError(f"Cannot import message class: {e}")


def encode_test_message(format_name):
    """Encode a test message using the specified frame format."""
    parser_class = get_parser_class(format_name)
    msg_class = get_message_class()

    msg = create_test_message(msg_class)
    parser = parser_class()
    return bytes(parser.encode_msg(msg))


def decode_test_message(format_name, data):
    """Decode a test message using the specified frame format."""
    parser_class = get_parser_class(format_name)
    msg_class = get_message_class()

    parser = parser_class()
    result = parser.validate_packet(data)

    if result is None or not result.valid:
        return None

    # Convert raw bytes to message object
    return msg_class.create_unpack(result.msg_data)
