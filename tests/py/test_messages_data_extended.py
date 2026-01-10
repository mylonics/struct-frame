#!/usr/bin/env python3
"""
Extended test message data definitions.
Hardcoded test messages for extended message ID and payload testing.
Replaces JSON-based test data loading.

This module provides a streaming interface where messages are directly
encoded to a buffer using a writer object, eliminating intermediate
message list allocations.
"""


def get_extended_test_message_count():
    """Get the total number of extended test messages."""
    return 12


def write_extended_test_messages(writer, message_classes):
    """
    Write all extended test messages to a writer object.
    
    This function iterates through all extended test messages and encodes them
    directly using the writer's write() method.
    
    Args:
        writer: Writer object with write(msg_id, msg_data) method
        message_classes: Dictionary mapping message types to their classes
    
    Returns:
        Number of messages written
    """
    count = 0
    for i in range(get_extended_test_message_count()):
        msg_class, msg_data = get_extended_test_message(i, message_classes)
        msg_bytes = bytes(msg_class.pack())
        bytes_written = writer.write(msg_class.msg_id, msg_bytes)
        
        if bytes_written == 0:
            raise RuntimeError(f"Failed to encode extended message {i}: buffer full or encoding error")
        
        count += 1
    
    return count


def get_extended_test_message(index, message_classes):
    """
    Get an extended test message by index.
    
    Args:
        index: Message index (0-11)
        message_classes: Dictionary mapping message type names to their classes
    
    Returns:
        Tuple of (message_instance, message_type_name)
    """
    # Message 0: ExtendedIdMessage1
    if index == 0:
        return (
            message_classes['ExtendedIdMessage1'](
                sequence_number=12345678,
                label=b"Test Label Extended 1",
                value=3.14159,
                enabled=True
            ),
            'ExtendedIdMessage1'
        )
    
    # Message 1: ExtendedIdMessage2
    elif index == 1:
        return (
            message_classes['ExtendedIdMessage2'](
                sensor_id=-42,
                reading=2.718281828,
                status_code=50000,
                description=b"Extended ID test message 2"
            ),
            'ExtendedIdMessage2'
        )
    
    # Message 2: ExtendedIdMessage3
    elif index == 2:
        return (
            message_classes['ExtendedIdMessage3'](
                timestamp=1704067200000000,
                temperature=-40,
                humidity=85,
                location=b"Sensor Room A"
            ),
            'ExtendedIdMessage3'
        )
    
    # Message 3: ExtendedIdMessage4
    elif index == 3:
        return (
            message_classes['ExtendedIdMessage4'](
                event_id=999999,
                event_type=42,
                event_time=1704067200000,
                event_data=b"Event payload with extended message ID"
            ),
            'ExtendedIdMessage4'
        )
    
    # Message 4: ExtendedIdMessage5
    elif index == 4:
        return (
            message_classes['ExtendedIdMessage5'](
                x_position=100.5,
                y_position=-200.25,
                z_position=50.125,
                frame_number=1000000
            ),
            'ExtendedIdMessage5'
        )
    
    # Message 5: ExtendedIdMessage6
    elif index == 5:
        return (
            message_classes['ExtendedIdMessage6'](
                command_id=-12345,
                parameter1=1000,
                parameter2=2000,
                acknowledged=False,
                command_name=b"CALIBRATE_SENSOR"
            ),
            'ExtendedIdMessage6'
        )
    
    # Message 6: ExtendedIdMessage7
    elif index == 6:
        return (
            message_classes['ExtendedIdMessage7'](
                counter=4294967295,
                average=123.456789,
                minimum=-999.99,
                maximum=999.99
            ),
            'ExtendedIdMessage7'
        )
    
    # Message 7: ExtendedIdMessage8
    elif index == 7:
        return (
            message_classes['ExtendedIdMessage8'](
                level=255,
                offset=-32768,
                duration=86400000,
                tag=b"TEST123"
            ),
            'ExtendedIdMessage8'
        )
    
    # Message 8: ExtendedIdMessage9
    elif index == 8:
        return (
            message_classes['ExtendedIdMessage9'](
                big_number=-9223372036854775808,
                big_unsigned=18446744073709551615,
                precision_value=1.23456789012345
            ),
            'ExtendedIdMessage9'
        )
    
    # Message 9: ExtendedIdMessage10
    elif index == 9:
        return (
            message_classes['ExtendedIdMessage10'](
                small_value=127,
                short_text=b"ABC",
                flag=True
            ),
            'ExtendedIdMessage10'
        )
    
    # Message 10: LargePayloadMessage1
    elif index == 10:
        sensor_readings = [1.1, 2.2, 3.3, 4.4, 5.5] + [0.0] * 95  # 100 total
        return (
            message_classes['LargePayloadMessage1'](
                sensor_readings=sensor_readings,
                reading_count=5,
                timestamp=1704067200000,
                device_name=b"TestDevice001"
            ),
            'LargePayloadMessage1'
        )
    
    # Message 11: LargePayloadMessage2
    elif index == 11:
        # Large data array: 512 bytes
        large_data = list(range(256)) + list(range(256))
        return (
            message_classes['LargePayloadMessage2'](
                large_data=large_data
            ),
            'LargePayloadMessage2'
        )
    
    else:
        raise IndexError(f"Invalid extended message index: {index}")
