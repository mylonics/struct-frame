#!/usr/bin/env python3
"""
Profile runner (Python).
Low-level encoding and decoding for message providers.

This file matches the C++ profile_runner.hpp structure.
ProfileRunner has NO knowledge of message types - all message-specific
logic is handled via callbacks (get_message, check_message).
"""

import sys
import os
from typing import Callable, Tuple

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from frame_profiles import (
    BufferWriter,
    AccumulatingReader,
    PROFILE_STANDARD_CONFIG,
    PROFILE_SENSOR_CONFIG,
    PROFILE_IPC_CONFIG,
    PROFILE_BULK_CONFIG,
    PROFILE_NETWORK_CONFIG,
)


# Buffer size for readers
BUFFER_SIZE = 16384


def encode(message_count: int, get_message: Callable, profile: str, buffer: bytearray) -> int:
    """
    Encode all messages to buffer using BufferWriter.
    
    Args:
        message_count: Number of messages to encode
        get_message: Function(index) -> message
        profile: Profile name (standard, sensor, ipc, bulk, network)
        buffer: Buffer to encode into
        
    Returns:
        Total bytes written
    """
    configs = {
        'standard': PROFILE_STANDARD_CONFIG,
        'sensor': PROFILE_SENSOR_CONFIG,
        'ipc': PROFILE_IPC_CONFIG,
        'bulk': PROFILE_BULK_CONFIG,
        'network': PROFILE_NETWORK_CONFIG,
    }

    config = configs.get(profile)
    if not config:
        return 0

    writer = BufferWriter(config, len(buffer))
    
    for i in range(message_count):
        msg = get_message(i)
        writer.write(msg)
    
    data = writer.data()
    buffer[:len(data)] = data
    return writer.size()


def parse(message_count: int, check_message: Callable, get_message_info: Callable, profile: str, buffer: bytes) -> int:
    """
    Parse all messages from buffer using AccumulatingReader.
    Uses check_message callback to validate each decoded message.
    
    Args:
        message_count: Expected number of messages
        check_message: Function(index, frame_info) -> bool to validate each message
        get_message_info: Function to get message info by msg_id
        profile: Profile name (standard, sensor, ipc, bulk, network)
        buffer: Buffer containing encoded data
        
    Returns:
        Number of messages that matched (message_count if all pass)
    """
    configs = {
        'standard': PROFILE_STANDARD_CONFIG,
        'sensor': PROFILE_SENSOR_CONFIG,
        'ipc': PROFILE_IPC_CONFIG,
        'bulk': PROFILE_BULK_CONFIG,
        'network': PROFILE_NETWORK_CONFIG,
    }

    config = configs.get(profile)
    if not config:
        return 0

    reader = AccumulatingReader(config, get_message_info=get_message_info, buffer_size=BUFFER_SIZE)
    reader.add_data(buffer)
    
    count = 0
    
    while True:
        result = reader.next()
        if result is None or not result.valid:
            break
        
        # Use callback to check if message matches expected
        if not check_message(count, result):
            break
        
        count += 1
    
    return count


def get_profile_ops(message_count: int, get_message: Callable, check_message: Callable, get_message_info: Callable, profile: str) -> Tuple[Callable, Callable]:
    """
    Get encode and parse functions for a profile.
    
    Returns:
        Tuple of (encode_fn, parse_fn) where:
        - encode_fn(buffer) -> bytes_written
        - parse_fn(buffer) -> messages_validated
    """
    def encode_fn(buffer: bytearray) -> int:
        return encode(message_count, get_message, profile, buffer)
    
    def parse_fn(buffer: bytes) -> int:
        return parse(message_count, check_message, get_message_info, profile, buffer)
    
    return encode_fn, parse_fn
