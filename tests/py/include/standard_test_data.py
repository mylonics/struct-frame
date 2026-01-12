#!/usr/bin/env python3
"""
Test message data definitions (Python).
Hardcoded test messages for cross-platform compatibility testing.

This module follows the same pattern as C, C++, TypeScript, and JavaScript
test data files, providing:
1. Message count and order
2. Index tracking for encoding/validation
3. Helper functions for encoding and validation
4. Test configuration struct
"""

from enum import IntEnum


class MessageType(IntEnum):
    """Message type identifier."""
    SERIALIZATION_TEST = 0
    BASIC_TYPES = 1
    UNION_TEST = 2


# ============================================================================
# Message count and order
# ============================================================================

MESSAGE_COUNT = 11

# Index tracking for encoding/validation
_serial_idx = 0
_basic_idx = 0
_union_idx = 0


def get_test_message_count():
    """Get the total number of test messages."""
    return MESSAGE_COUNT


def reset_indices():
    """Reset all message indices (for encode/decode cycles)."""
    global _serial_idx, _basic_idx, _union_idx
    _serial_idx = 0
    _basic_idx = 0
    _union_idx = 0


# ============================================================================
# Test message data
# ============================================================================

_SERIALIZATION_TEST_MESSAGES = [
    # 0: basic_values
    {
        'magic_number': 0xDEADBEEF,
        'test_string': 'Cross-platform test!',
        'test_float': 3.14159,
        'test_bool': True,
        'test_array': [100, 200, 300]
    },
    # 1: zero_values
    {
        'magic_number': 0,
        'test_string': '',
        'test_float': 0.0,
        'test_bool': False,
        'test_array': []
    },
    # 2: max_values
    {
        'magic_number': 0xFFFFFFFF,
        'test_string': 'Maximum length test string for coverage!',
        'test_float': 999999.9,
        'test_bool': True,
        'test_array': [2147483647, -2147483648, 0, 1, -1]
    },
    # 3: negative_values
    {
        'magic_number': 0xAAAAAAAA,
        'test_string': 'Negative test',
        'test_float': -273.15,
        'test_bool': False,
        'test_array': [-100, -200, -300, -400]
    },
    # 4: special_chars
    {
        'magic_number': 1234567890,
        'test_string': 'Special: !@#$%^&*()',
        'test_float': 2.71828,
        'test_bool': True,
        'test_array': [0, 1, 1, 2, 3]
    },
]

_BASIC_TYPES_MESSAGES = [
    # 0: basic_values
    {
        'small_int': 42,
        'medium_int': 1000,
        'regular_int': 123456,
        'large_int': 9876543210,
        'small_uint': 200,
        'medium_uint': 50000,
        'regular_uint': 4000000000,
        'large_uint': 9223372036854775807,
        'single_precision': 3.14159,
        'double_precision': 2.718281828459045,
        'flag': True,
        'device_id': 'DEVICE-001',
        'description': 'Basic test values'
    },
    # 1: zero_values
    {
        'small_int': 0,
        'medium_int': 0,
        'regular_int': 0,
        'large_int': 0,
        'small_uint': 0,
        'medium_uint': 0,
        'regular_uint': 0,
        'large_uint': 0,
        'single_precision': 0.0,
        'double_precision': 0.0,
        'flag': False,
        'device_id': '',
        'description': ''
    },
    # 2: negative_values (also used as message #10)
    {
        'small_int': -128,
        'medium_int': -32768,
        'regular_int': -2147483648,
        'large_int': -9223372036854775807,
        'small_uint': 255,
        'medium_uint': 65535,
        'regular_uint': 4294967295,
        'large_uint': 9223372036854775807,
        'single_precision': -273.15,
        'double_precision': -9999.999999,
        'flag': False,
        'device_id': 'NEG-TEST',
        'description': 'Negative and max values'
    },
]

_UNION_TEST_MESSAGES = [
    # 0: with_array_payload
    {
        'payload_type': 1,
        'array_payload': {
            'fixed_ints': [10, 20, 30],
            'fixed_floats': [1.1, 2.2],
            'fixed_bools': [True, False, True, False],
            'bounded_uints': [100, 200, 300],
            'bounded_doubles': [3.14, 2.71, 1.41],
            'fixed_strings': ['str1', 'str2'],
            'bounded_strings': ['bounded1', 'bounded2'],
            'fixed_statuses': [1, 2],
            'bounded_statuses': [10, 20, 30],
            'fixed_sensors': [
                {'id': 1, 'value': 1.1, 'status': 1, 'name': 'sensor1'}
            ],
            'bounded_sensors': [
                {'id': 2, 'value': 2.2, 'status': 2, 'name': 'sensor2'},
                {'id': 3, 'value': 3.3, 'status': 3, 'name': 'sensor3'}
            ]
        }
    },
    # 1: with_test_payload
    {
        'payload_type': 2,
        'test_payload': {
            'magic_number': 0xCAFEBABE,
            'test_string': 'Union payload',
            'test_float': 42.42,
            'test_bool': False,
            'test_array': [7, 8, 9]
        }
    },
]

# Message ID order array - defines the sequence of messages for encoding/decoding
# Total: 11 messages
_MSG_TYPE_ORDER = [
    MessageType.SERIALIZATION_TEST,  # 0: SerializationTest[0]
    MessageType.SERIALIZATION_TEST,  # 1: SerializationTest[1]
    MessageType.SERIALIZATION_TEST,  # 2: SerializationTest[2]
    MessageType.SERIALIZATION_TEST,  # 3: SerializationTest[3]
    MessageType.SERIALIZATION_TEST,  # 4: SerializationTest[4]
    MessageType.BASIC_TYPES,         # 5: BasicTypes[0]
    MessageType.BASIC_TYPES,         # 6: BasicTypes[1]
    MessageType.BASIC_TYPES,         # 7: BasicTypes[2]
    MessageType.UNION_TEST,          # 8: UnionTest[0]
    MessageType.UNION_TEST,          # 9: UnionTest[1]
    MessageType.BASIC_TYPES,         # 10: BasicTypes[2] (repeated)
]


def get_msg_type_order():
    """Get the message type order array."""
    return _MSG_TYPE_ORDER


def get_test_message(index):
    """
    Get a test message by index.
    
    Args:
        index: Message index (0-based)
    
    Returns:
        tuple: (message_type, message_data) or (None, None) if invalid index
    """
    if index < 0 or index >= MESSAGE_COUNT:
        return None, None
    
    msg_type = _MSG_TYPE_ORDER[index]
    
    if msg_type == MessageType.SERIALIZATION_TEST:
        msg_index = sum(1 for i in range(index) if _MSG_TYPE_ORDER[i] == MessageType.SERIALIZATION_TEST)
        return MessageType.SERIALIZATION_TEST, _SERIALIZATION_TEST_MESSAGES[msg_index]
    elif msg_type == MessageType.BASIC_TYPES:
        msg_index = sum(1 for i in range(index) if _MSG_TYPE_ORDER[i] == MessageType.BASIC_TYPES)
        if msg_index >= len(_BASIC_TYPES_MESSAGES):
            msg_index = len(_BASIC_TYPES_MESSAGES) - 1  # Reuse last message
        return MessageType.BASIC_TYPES, _BASIC_TYPES_MESSAGES[msg_index]
    elif msg_type == MessageType.UNION_TEST:
        msg_index = sum(1 for i in range(index) if _MSG_TYPE_ORDER[i] == MessageType.UNION_TEST)
        return MessageType.UNION_TEST, _UNION_TEST_MESSAGES[msg_index]
    
    return None, None


# ============================================================================
# Message encoding helpers
# ============================================================================

def create_message_from_data(msg_class, test_msg):
    """Create a SerializationTestMessage from test message data."""
    return msg_class(
        magic_number=test_msg['magic_number'],
        test_string=test_msg['test_string'].encode('utf-8'),
        test_float=test_msg['test_float'],
        test_bool=test_msg['test_bool'],
        test_array=test_msg['test_array']
    )


def create_basic_types_message_from_data(msg_class, test_msg):
    """Create a BasicTypesMessage from test message data."""
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


def create_union_test_message_from_data(union_class, array_class, serial_class, sensor_class, test_msg):
    """Create a UnionTestMessage from test message data."""
    payload_dict = {}
    payload_which = None
    payload_discriminator = None
    
    # Create array_payload if present
    array_data = test_msg.get('array_payload')
    if array_data:
        fixed_sensors = []
        for sensor_data in array_data.get('fixed_sensors', []):
            sensor = sensor_class(
                id=sensor_data.get('id', 0),
                value=sensor_data.get('value', 0.0),
                status=sensor_data.get('status', 0),
                name=sensor_data.get('name', '').encode('utf-8')
            )
            fixed_sensors.append(sensor)
        
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


# ============================================================================
# Message validation helpers
# ============================================================================

def validate_message(msg, test_msg):
    """Validate that a decoded SerializationTestMessage matches expected data."""
    errors = []

    if msg.magic_number != test_msg['magic_number']:
        errors.append(f"magic_number: expected {test_msg['magic_number']}, got {msg.magic_number}")

    test_string = msg.test_string
    if isinstance(test_string, bytes):
        test_string = test_string.decode('utf-8', errors='replace').rstrip('\x00')
    expected_string = test_msg['test_string']
    if test_string != expected_string:
        errors.append(f"test_string: expected '{expected_string}', got '{test_string}'")

    expected_float = test_msg['test_float']
    tolerance = max(abs(expected_float) * 1e-4, 1e-4)
    if abs(msg.test_float - expected_float) > tolerance:
        errors.append(f"test_float: expected {expected_float}, got {msg.test_float}")

    if msg.test_bool != test_msg['test_bool']:
        errors.append(f"test_bool: expected {test_msg['test_bool']}, got {msg.test_bool}")

    test_array = msg.test_array
    if hasattr(test_array, 'count') and hasattr(test_array, 'data'):
        array_list = list(test_array.data[:test_array.count])
    else:
        array_list = list(test_array) if test_array else []

    expected_array = test_msg['test_array']
    if array_list != expected_array:
        errors.append(f"test_array: expected {expected_array}, got {array_list}")

    if errors:
        for error in errors:
            print(f"  Value mismatch: {error}")
        return False

    return True


def validate_basic_types_message(msg, test_msg):
    """Validate BasicTypesMessage against expected data."""
    errors = []
    
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
    
    if abs(msg.single_precision - test_msg['single_precision']) > 0.01:
        errors.append(f"single_precision: expected {test_msg['single_precision']}, got {msg.single_precision}")
    if abs(msg.double_precision - test_msg['double_precision']) > 0.000001:
        errors.append(f"double_precision: expected {test_msg['double_precision']}, got {msg.double_precision}")
    
    if msg.flag != test_msg['flag']:
        errors.append(f"flag: expected {test_msg['flag']}, got {msg.flag}")
    
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


# ============================================================================
# Test configuration
# ============================================================================

class StdTestConfig:
    """Test configuration for standard messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 4096
    FORMATS_HELP = "profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network"
    TEST_NAME = "standard"
    
    @staticmethod
    def get_msg_type_order():
        return _MSG_TYPE_ORDER
    
    @staticmethod
    def supports_format(format_name):
        """Check if the given format is supported."""
        return format_name in [
            'profile_standard', 'profile_sensor', 'profile_ipc',
            'profile_bulk', 'profile_network'
        ]


# Export config instance
std_test_config = StdTestConfig()
