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


def load_mixed_messages():
    """Load mixed messages from test_messages.json following MixedMessages sequence"""
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
                
                # Get the MixedMessages array
                mixed_array = data.get('MixedMessages')
                if not mixed_array:
                    raise ValueError("MixedMessages array not found in test_messages.json")
                
                # Get message data arrays
                serial_msgs = data.get('SerializationTestMessage', [])
                basic_msgs = data.get('BasicTypesMessage', [])
                union_msgs = data.get('UnionTestMessage', [])
                
                # Build the mixed message list
                messages = []
                for item in mixed_array:
                    msg_type = item.get('type')
                    msg_name = item.get('name')
                    
                    # Find the message by name in the appropriate array
                    if msg_type == 'SerializationTestMessage':
                        msg_data = next((m for m in serial_msgs if m.get('name') == msg_name), None)
                        if msg_data:
                            messages.append({'type': 'SerializationTestMessage', 'data': msg_data})
                    elif msg_type == 'BasicTypesMessage':
                        msg_data = next((m for m in basic_msgs if m.get('name') == msg_name), None)
                        if msg_data:
                            messages.append({'type': 'BasicTypesMessage', 'data': msg_data})
                    elif msg_type == 'UnionTestMessage':
                        msg_data = next((m for m in union_msgs if m.get('name') == msg_name), None)
                        if msg_data:
                            messages.append({'type': 'UnionTestMessage', 'data': msg_data})
                
                return messages
    
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


def create_basic_types_message_from_data(msg_class, test_msg):
    """Create a BasicTypesMessage from test message data."""
    # large_int and large_uint may be stored as strings in JSON to preserve precision
    large_int = int(test_msg['large_int']) if isinstance(test_msg['large_int'], str) else test_msg['large_int']
    large_uint = int(test_msg['large_uint']) if isinstance(test_msg['large_uint'], str) else test_msg['large_uint']
    return msg_class(
        small_int=test_msg['small_int'],
        medium_int=test_msg['medium_int'],
        regular_int=test_msg['regular_int'],
        large_int=large_int,
        small_uint=test_msg['small_uint'],
        medium_uint=test_msg['medium_uint'],
        regular_uint=test_msg['regular_uint'],
        large_uint=large_uint,
        single_precision=test_msg['single_precision'],
        double_precision=test_msg['double_precision'],
        flag=test_msg['flag'],
        device_id=test_msg['device_id'].encode('utf-8'),
        description=test_msg['description'].encode('utf-8')
    )


def validate_basic_types_message(msg, test_msg):
    """Validate BasicTypesMessage against expected data."""
    errors = []
    
    # large_int and large_uint may be stored as strings in JSON to preserve precision
    expected_large_int = int(test_msg['large_int']) if isinstance(test_msg['large_int'], str) else test_msg['large_int']
    expected_large_uint = int(test_msg['large_uint']) if isinstance(test_msg['large_uint'], str) else test_msg['large_uint']
    
    if msg.small_int != test_msg['small_int']:
        errors.append(f"small_int: expected {test_msg['small_int']}, got {msg.small_int}")
    if msg.medium_int != test_msg['medium_int']:
        errors.append(f"medium_int: expected {test_msg['medium_int']}, got {msg.medium_int}")
    if msg.regular_int != test_msg['regular_int']:
        errors.append(f"regular_int: expected {test_msg['regular_int']}, got {msg.regular_int}")
    if msg.large_int != expected_large_int:
        errors.append(f"large_int: expected {expected_large_int}, got {msg.large_int}")
    if msg.small_uint != test_msg['small_uint']:
        errors.append(f"small_uint: expected {test_msg['small_uint']}, got {msg.small_uint}")
    if msg.medium_uint != test_msg['medium_uint']:
        errors.append(f"medium_uint: expected {test_msg['medium_uint']}, got {msg.medium_uint}")
    if msg.regular_uint != test_msg['regular_uint']:
        errors.append(f"regular_uint: expected {test_msg['regular_uint']}, got {msg.regular_uint}")
    if msg.large_uint != expected_large_uint:
        errors.append(f"large_uint: expected {expected_large_uint}, got {msg.large_uint}")
    
    # Float tolerance
    if abs(msg.single_precision - test_msg['single_precision']) > 0.01:
        errors.append(f"single_precision: expected {test_msg['single_precision']}, got {msg.single_precision}")
    if abs(msg.double_precision - test_msg['double_precision']) > 0.000001:
        errors.append(f"double_precision: expected {test_msg['double_precision']}, got {msg.double_precision}")
    
    if msg.flag != test_msg['flag']:
        errors.append(f"flag: expected {test_msg['flag']}, got {msg.flag}")
    
    # String comparison
    device_id = msg.device_id
    if isinstance(device_id, bytes):
        device_id = device_id.decode('utf-8', errors='replace').rstrip('\x00')
    if device_id != test_msg['device_id']:
        errors.append(f"device_id: expected '{test_msg['device_id']}', got '{device_id}'")
    
    description = msg.description
    if isinstance(description, bytes):
        description = description.decode('utf-8', errors='replace').rstrip('\x00')
    if description != test_msg['description']:
        errors.append(f"description: expected '{test_msg['description']}', got '{description}'")
    
    if errors:
        for error in errors:
            print(f"  Value mismatch: {error}")
        return False
    
    return True


def create_union_test_message_from_data(union_class, array_class, serial_class, sensor_class, test_msg):
    """Create a UnionTestMessage from test message data."""
    # Determine which payload to use based on what's present in the test data
    payload_dict = {}
    payload_which = None
    payload_discriminator = None
    
    # Create array_payload if present
    array_data = test_msg.get('array_payload')
    if array_data:
        # Create sensors for fixed_sensors
        fixed_sensors = []
        for sensor_data in array_data.get('fixed_sensors', []):
            sensor = sensor_class(
                id=sensor_data.get('id', 0),
                value=sensor_data.get('value', 0.0),
                status=sensor_data.get('status', 0),
                name=sensor_data.get('name', '').encode('utf-8')
            )
            fixed_sensors.append(sensor)
        
        # Create sensors for bounded_sensors
        bounded_sensors = []
        for sensor_data in array_data.get('bounded_sensors', []):
            sensor = sensor_class(
                id=sensor_data.get('id', 0),
                value=sensor_data.get('value', 0.0),
                status=sensor_data.get('status', 0),
                name=sensor_data.get('name', '').encode('utf-8')
            )
            bounded_sensors.append(sensor)
        
        array_payload = array_class(
            fixed_ints=array_data.get('fixed_ints', [0, 0, 0]),
            fixed_floats=array_data.get('fixed_floats', [0.0, 0.0]),
            fixed_bools=array_data.get('fixed_bools', [False, False, False, False]),
            bounded_uints=array_data.get('bounded_uints', []),
            bounded_doubles=array_data.get('bounded_doubles', []),
            fixed_strings=[s.encode('utf-8') if isinstance(s, str) else s for s in array_data.get('fixed_strings', ['', ''])],
            bounded_strings=[s.encode('utf-8') if isinstance(s, str) else s for s in array_data.get('bounded_strings', [])],
            fixed_statuses=array_data.get('fixed_statuses', [0, 0]),
            bounded_statuses=array_data.get('bounded_statuses', []),
            fixed_sensors=fixed_sensors if fixed_sensors else [sensor_class()],
            bounded_sensors=bounded_sensors
        )
        payload_dict['array_payload'] = array_payload
        payload_which = 'array_payload'
        payload_discriminator = array_class.msg_id
    
    # Create test_payload if present
    test_data = test_msg.get('test_payload')
    if test_data:
        test_payload = serial_class(
            magic_number=test_data.get('magic_number', 0),
            test_string=test_data.get('test_string', '').encode('utf-8'),
            test_float=test_data.get('test_float', 0.0),
            test_bool=test_data.get('test_bool', False),
            test_array=test_data.get('test_array', [])
        )
        payload_dict['test_payload'] = test_payload
        payload_which = 'test_payload'
        payload_discriminator = serial_class.msg_id
    
    return union_class(
        payload=payload_dict,
        payload_which=payload_which,
        payload_discriminator=payload_discriminator
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

    from parser import Parser, PayloadType, HeaderType
    from serialization_test_sf import (
        SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
        SerializationTestUnionTestMessage
    )

    # Check if this format uses MINIMAL payload (which has no length field)
    get_msg_length = None
    enable_none = False
    default_payload_type = PayloadType.DEFAULT
    
    if format_name:
        header_type, payload_type = get_frame_config(format_name)
        
        # Enable NONE header type for profile_ipc
        if header_type == HeaderType.NONE:
            enable_none = True
            default_payload_type = payload_type
        
        if payload_type == PayloadType.MINIMAL:
            # MINIMAL payload has no length field, need callback
            def get_length_by_id(msg_id):
                if msg_id == SerializationTestSerializationTestMessage.msg_id:
                    return SerializationTestSerializationTestMessage.msg_size
                elif msg_id == SerializationTestBasicTypesMessage.msg_id:
                    return SerializationTestBasicTypesMessage.msg_size
                return 0
            get_msg_length = get_length_by_id

    return Parser(get_msg_length=get_msg_length, enable_none=enable_none, default_payload_type=default_payload_type)


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
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from serialization_test_sf import (
        SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
        SerializationTestUnionTestMessage, SerializationTestComprehensiveArrayMessage,
        SerializationTestSensor
    )
    
    # Import generated frame profiles
    from frame_profiles import (
        encode_profile_standard, encode_profile_sensor, encode_profile_ipc,
        encode_profile_bulk, encode_profile_network
    )
    
    mixed_messages = load_mixed_messages()
    encoded_data = bytearray()
    
    # Get the appropriate encode function for this profile
    encode_funcs = {
        'profile_standard': encode_profile_standard,
        'profile_sensor': encode_profile_sensor,
        'profile_ipc': encode_profile_ipc,
        'profile_bulk': encode_profile_bulk,
        'profile_network': encode_profile_network,
    }
    encode_func = encode_funcs.get(format_name)
    if not encode_func:
        raise ValueError(f"Unknown format: {format_name}")
    
    for item in mixed_messages:
        msg_type = item['type']
        test_msg = item['data']
        
        if msg_type == 'SerializationTestMessage':
            msg = create_message_from_data(SerializationTestSerializationTestMessage, test_msg)
        elif msg_type == 'BasicTypesMessage':
            msg = create_basic_types_message_from_data(SerializationTestBasicTypesMessage, test_msg)
        elif msg_type == 'UnionTestMessage':
            msg = create_union_test_message_from_data(
                SerializationTestUnionTestMessage,
                SerializationTestComprehensiveArrayMessage,
                SerializationTestSerializationTestMessage,
                SerializationTestSensor,
                test_msg
            )
        else:
            raise ValueError(f"Unknown message type: {msg_type}")
        
        msg_data = bytes(msg.pack())
        
        # Use the generated profile encode function
        frame_data = encode_func(msg.msg_id, msg_data)
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
    
    from serialization_test_sf import (
        SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
        SerializationTestUnionTestMessage
    )
    
    # Import generated frame profiles
    from frame_profiles import (
        parse_profile_standard_buffer, parse_profile_sensor_buffer, parse_profile_ipc_buffer,
        parse_profile_bulk_buffer, parse_profile_network_buffer,
        PROFILE_STANDARD_CONFIG, PROFILE_SENSOR_CONFIG, PROFILE_IPC_CONFIG,
        PROFILE_BULK_CONFIG, PROFILE_NETWORK_CONFIG
    )
    
    # Get message length callback for minimal profiles
    def get_msg_length(msg_id):
        if msg_id == SerializationTestSerializationTestMessage.msg_id:
            return SerializationTestSerializationTestMessage.msg_size
        elif msg_id == SerializationTestBasicTypesMessage.msg_id:
            return SerializationTestBasicTypesMessage.msg_size
        elif msg_id == SerializationTestUnionTestMessage.msg_id:
            return SerializationTestUnionTestMessage.msg_size
        return 0
    
    # Get the appropriate parse function and config for this profile
    parse_configs = {
        'profile_standard': (parse_profile_standard_buffer, PROFILE_STANDARD_CONFIG, False),
        'profile_sensor': (parse_profile_sensor_buffer, PROFILE_SENSOR_CONFIG, True),
        'profile_ipc': (parse_profile_ipc_buffer, PROFILE_IPC_CONFIG, True),
        'profile_bulk': (parse_profile_bulk_buffer, PROFILE_BULK_CONFIG, False),
        'profile_network': (parse_profile_network_buffer, PROFILE_NETWORK_CONFIG, False),
    }
    
    parse_info = parse_configs.get(format_name)
    if not parse_info:
        raise ValueError(f"Unknown format: {format_name}")
    
    parse_func, config, needs_callback = parse_info
    
    mixed_messages = load_mixed_messages()
    message_count = 0
    data_index = 0
    
    while data_index < len(data) and message_count < len(mixed_messages):
        # Parse the frame from current position
        remaining = data[data_index:]
        
        if needs_callback:
            result = parse_func(remaining, get_msg_length)
        else:
            result = parse_func(remaining)
        
        if not result or not result.valid:
            print(f"  Decoding failed for message {message_count}")
            return False, message_count
        
        # Get expected message type
        item = mixed_messages[message_count]
        msg_type = item['type']
        test_msg = item['data']
        
        # Validate msg_id matches expected type
        if msg_type == 'SerializationTestMessage':
            expected_msg_id = SerializationTestSerializationTestMessage.msg_id
        elif msg_type == 'BasicTypesMessage':
            expected_msg_id = SerializationTestBasicTypesMessage.msg_id
        elif msg_type == 'UnionTestMessage':
            expected_msg_id = SerializationTestUnionTestMessage.msg_id
        else:
            print(f"  Unknown message type: {msg_type}")
            return False, message_count
        
        if result.msg_id != expected_msg_id:
            print(f"  Message ID mismatch for message {message_count}: expected {expected_msg_id}, got {result.msg_id}")
            return False, message_count
        
        # Decode the message based on type
        msg_data = result.msg_data
        if msg_type == 'SerializationTestMessage':
            msg = SerializationTestSerializationTestMessage.create_unpack(msg_data)
            if not validate_message(msg, test_msg):
                print(f"  Validation failed for message {message_count}")
                return False, message_count
        elif msg_type == 'BasicTypesMessage':
            msg = SerializationTestBasicTypesMessage.create_unpack(msg_data)
            if not validate_basic_types_message(msg, test_msg):
                print(f"  Validation failed for message {message_count}")
                return False, message_count
        elif msg_type == 'UnionTestMessage':
            msg = SerializationTestUnionTestMessage.create_unpack(msg_data)
            # For UnionTestMessage, we just validate it decoded without error
            # Full validation would require comparing nested structures
        
        # Calculate frame size based on config
        frame_size = config.header_size + result.msg_len + config.footer_size
        data_index += frame_size
        message_count += 1
    
    # Ensure all messages were decoded
    if message_count != len(mixed_messages):
        print(f"  Expected {len(mixed_messages)} messages, but decoded {message_count}")
        return False, message_count
    
    # Ensure all data was consumed
    if data_index != len(data):
        print(f"  Extra data after messages: processed {data_index} bytes, got {len(data)} bytes")
        return False, message_count
    
    return True, message_count

