#!/usr/bin/env python3
"""
Test message data definitions.
Hardcoded test messages for cross-platform compatibility testing.
Replaces JSON-based test data loading.
"""

from enum import IntEnum


class MessageType(IntEnum):
    """Message type identifier."""
    SERIALIZATION_TEST = 0
    BASIC_TYPES = 1
    UNION_TEST = 2


def get_test_message_count():
    """Get the total number of test messages."""
    return 11


def get_test_message(index):
    """
    Get a test message by index.
    
    Args:
        index: Message index (0-based)
    
    Returns:
        tuple: (message_type, message_data) or (None, None) if invalid index
    """
    if index < 0 or index >= get_test_message_count():
        return None, None
    
    messages = [
        # 0: SerializationTestMessage - basic_values
        (MessageType.SERIALIZATION_TEST, {
            'magic_number': 0xDEADBEEF,
            'test_string': 'Cross-platform test!',
            'test_float': 3.14159,
            'test_bool': True,
            'test_array': [100, 200, 300]
        }),
        
        # 1: SerializationTestMessage - zero_values
        (MessageType.SERIALIZATION_TEST, {
            'magic_number': 0,
            'test_string': '',
            'test_float': 0.0,
            'test_bool': False,
            'test_array': []
        }),
        
        # 2: SerializationTestMessage - max_values
        (MessageType.SERIALIZATION_TEST, {
            'magic_number': 0xFFFFFFFF,
            'test_string': 'Maximum length test string for coverage!',
            'test_float': 999999.9,
            'test_bool': True,
            'test_array': [2147483647, -2147483648, 0, 1, -1]
        }),
        
        # 3: SerializationTestMessage - negative_values
        (MessageType.SERIALIZATION_TEST, {
            'magic_number': 0xAAAAAAAA,
            'test_string': 'Negative test',
            'test_float': -273.15,
            'test_bool': False,
            'test_array': [-100, -200, -300, -400]
        }),
        
        # 4: SerializationTestMessage - special_chars
        (MessageType.SERIALIZATION_TEST, {
            'magic_number': 1234567890,
            'test_string': 'Special: !@#$%^&*()',
            'test_float': 2.71828,
            'test_bool': True,
            'test_array': [0, 1, 1, 2, 3]
        }),
        
        # 5: BasicTypesMessage - basic_values
        (MessageType.BASIC_TYPES, {
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
        }),
        
        # 6: BasicTypesMessage - zero_values
        (MessageType.BASIC_TYPES, {
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
        }),
        
        # 7: BasicTypesMessage - negative_values
        (MessageType.BASIC_TYPES, {
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
        }),
        
        # 8: UnionTestMessage - with_array_payload
        (MessageType.UNION_TEST, {
            'payload_type': 1,  # UNION_PAYLOAD_COMPREHENSIVE_ARRAY
            'payload_type_name': 'UNION_PAYLOAD_COMPREHENSIVE_ARRAY',
            'array_payload': {
                'fixed_ints': [10, 20, 30],
                'fixed_floats': [1.5, 2.5],
                'fixed_bools': [True, False, True, False],
                'bounded_uints': [100, 200],
                'bounded_doubles': [3.14159],
                'fixed_strings': ['Hello', 'World'],
                'bounded_strings': ['Test'],
                'fixed_statuses': [1, 2],  # ACTIVE, ERROR
                'bounded_statuses': [0],   # INACTIVE
                'fixed_sensors': [{'id': 1, 'value': 25.5, 'status': 1, 'name': 'TempSensor'}],
                'bounded_sensors': []
            },
            'test_payload': None
        }),
        
        # 9: UnionTestMessage - with_test_payload
        (MessageType.UNION_TEST, {
            'payload_type': 2,  # UNION_PAYLOAD_SERIALIZATION_TEST
            'payload_type_name': 'UNION_PAYLOAD_SERIALIZATION_TEST',
            'array_payload': None,
            'test_payload': {
                'magic_number': 0x12345678,
                'test_string': 'Union test message',
                'test_float': 99.99,
                'test_bool': True,
                'test_array': [1, 2, 3, 4, 5]
            }
        }),
        
        # 10: BasicTypesMessage - negative_values (duplicate)
        (MessageType.BASIC_TYPES, {
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
        }),
    ]
    
    return messages[index]
