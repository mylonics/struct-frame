#!/usr/bin/env python3
"""
Test codec - Encode/decode functions for all frame formats (Python).
Uses the new Parser with header + payload architecture.
"""

from test_messages_data import MessageType, get_test_message_count, get_test_message


def load_test_messages():
    """Load test messages - now uses hardcoded data instead of JSON"""
    messages = []
    for i in range(get_test_message_count()):
        msg_type, msg_data = get_test_message(i)
        if msg_type == MessageType.SERIALIZATION_TEST:
            messages.append(msg_data)
    return messages


def load_mixed_messages():
    """Load mixed messages - now uses hardcoded data instead of JSON"""
    messages = []
    for i in range(get_test_message_count()):
        msg_type, msg_data = get_test_message(i)
        if msg_type == MessageType.SERIALIZATION_TEST:
            messages.append({'type': 'SerializationTestMessage', 'data': msg_data})
        elif msg_type == MessageType.BASIC_TYPES:
            messages.append({'type': 'BasicTypesMessage', 'data': msg_data})
        elif msg_type == MessageType.UNION_TEST:
            messages.append({'type': 'UnionTestMessage', 'data': msg_data})
    return messages


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


def encode_test_message(format_name):
    """Encode multiple test messages using the specified frame format."""
    return encode_test_messages(format_name)


def encode_test_messages(format_name):
    """Encode multiple test messages using the specified frame format.
    Uses BufferWriter for efficient multi-frame encoding.
    """
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
    
    # Import generated frame profiles - use BufferWriter for multi-frame encoding
    from frame_profiles import (
        create_profile_standard_writer, create_profile_sensor_writer, create_profile_ipc_writer,
        create_profile_bulk_writer, create_profile_network_writer
    )
    
    mixed_messages = load_mixed_messages()
    
    # Create the appropriate BufferWriter for this profile (with enough capacity)
    capacity = 4096  # Should be enough for test messages
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
        
        # Use BufferWriter to encode and append frame - it tracks offset automatically
        bytes_written = writer.write(msg.msg_id, msg_data)
        if bytes_written == 0:
            raise RuntimeError(f"Failed to encode message: buffer full or encoding error")
    
    return writer.data()


def decode_test_message(format_name, data):
    """Decode multiple test messages using the specified frame format."""
    return decode_test_messages(format_name, data)


def decode_test_messages(format_name, data):
    """Decode and validate multiple test messages using the specified frame format.
    Uses BufferReader for efficient multi-frame parsing.
    """
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
    
    # Import generated frame profiles - use BufferReader for multi-frame parsing
    from frame_profiles import (
        create_profile_standard_reader, create_profile_sensor_reader, create_profile_ipc_reader,
        create_profile_bulk_reader, create_profile_network_reader
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
    mixed_messages = load_mixed_messages()
    message_count = 0
    
    # Use BufferReader to iterate through frames - it handles offset tracking automatically
    while reader.has_more() and message_count < len(mixed_messages):
        result = reader.next()
        
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
        
        message_count += 1
    
    # Ensure all messages were decoded
    if message_count != len(mixed_messages):
        print(f"  Expected {len(mixed_messages)} messages, but decoded {message_count}")
        return False, message_count
    
    # Ensure all data was consumed (BufferReader tracks remaining bytes)
    if reader.remaining != 0:
        print(f"  Extra data after messages: {reader.remaining} bytes remaining")
        return False, message_count
    
    return True, message_count

