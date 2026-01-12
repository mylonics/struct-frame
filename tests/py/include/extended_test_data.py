#!/usr/bin/env python3
"""
Extended test message data definitions (Python).
Hardcoded test messages for extended message ID and payload testing.

This module follows the same pattern as C, C++, TypeScript, and JavaScript
test data files.
"""

# ============================================================================
# Message count
# ============================================================================

MESSAGE_COUNT = 12


def get_extended_test_message_count():
    """Get the total number of extended test messages."""
    return MESSAGE_COUNT


# ============================================================================
# Message creation
# ============================================================================

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
                x_position=1.0,
                y_position=2.0,
                z_position=3.0,
                frame_number=255
            ),
            'ExtendedIdMessage5'
        )
    
    # Message 5: ExtendedIdMessage6
    elif index == 5:
        return (
            message_classes['ExtendedIdMessage6'](
                command_id=12345,
                parameter1=100,
                parameter2=200,
                acknowledged=True,
                command_name=b"Command parameters ext 6"
            ),
            'ExtendedIdMessage6'
        )
    
    # Message 6: ExtendedIdMessage7
    elif index == 6:
        return (
            message_classes['ExtendedIdMessage7'](
                counter=0xFFFFFFFF,
                average=3.14159265,
                minimum=1.0,
                maximum=100.0
            ),
            'ExtendedIdMessage7'
        )
    
    # Message 7: ExtendedIdMessage8
    elif index == 7:
        return (
            message_classes['ExtendedIdMessage8'](
                level=8,
                offset=888,
                duration=8888,
                tag=b"Tag8----"
            ),
            'ExtendedIdMessage8'
        )
    
    # Message 8: ExtendedIdMessage9
    elif index == 8:
        return (
            message_classes['ExtendedIdMessage9'](
                big_number=9876543210,
                big_unsigned=9876543210,
                precision_value=9.87654321
            ),
            'ExtendedIdMessage9'
        )
    
    # Message 9: ExtendedIdMessage10
    elif index == 9:
        return (
            message_classes['ExtendedIdMessage10'](
                small_value=1000,
                short_text=b"Log message 10--",
                flag=True
            ),
            'ExtendedIdMessage10'
        )
    
    # Message 10: LargePayloadMessage1 - payload > 255 bytes
    elif index == 10:
        # Create a large payload with 64 float sensor readings (256 bytes)
        sensor_readings = [float(i) for i in range(64)]
        return (
            message_classes['LargePayloadMessage1'](
                sensor_readings=sensor_readings,
                reading_count=64,
                timestamp=1704067200000,
                device_name=b"Large Payload Device 1          "
            ),
            'LargePayloadMessage1'
        )
    
    # Message 11: LargePayloadMessage2 - payload > 255 bytes
    elif index == 11:
        # Create a large payload (280 bytes)
        large_data = bytes([ord('Y')] * 280)
        return (
            message_classes['LargePayloadMessage2'](
                large_data=large_data
            ),
            'LargePayloadMessage2'
        )
    
    return None, None


# ============================================================================
# Test configuration
# ============================================================================

class ExtendedTestConfig:
    """Test configuration for extended messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 8192
    FORMATS_HELP = "profile_bulk, profile_network"
    TEST_NAME = "extended"
    
    @staticmethod
    def supports_format(format_name):
        """Check if the given format is supported (only extended profiles)."""
        return format_name in ['profile_bulk', 'profile_network']


# Export config instance
extended_test_config = ExtendedTestConfig()
