#!/usr/bin/env python3
"""
Test codec - Extended message ID and payload tests (Python).
Uses the new Parser with header + payload architecture.
"""

import json
import os


def load_extended_messages():
    """Load extended messages from extended_messages.json"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'extended_messages.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'extended_messages.json'),
        'extended_messages.json',
        '../extended_messages.json',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                
                mixed_array = data.get('MixedMessages')
                if not mixed_array:
                    raise ValueError("MixedMessages array not found in extended_messages.json")
                
                messages = []
                for item in mixed_array:
                    msg_type = item.get('type')
                    msg_name = item.get('name')
                    
                    msg_arr = data.get(msg_type, [])
                    msg_data = next((m for m in msg_arr if m.get('name') == msg_name), None)
                    if msg_data:
                        messages.append({'type': msg_type, 'data': msg_data})
                
                return messages
    
    raise FileNotFoundError("Could not find extended_messages.json")


def create_extended_message(msg_class, test_msg, msg_type):
    """Create an extended message from test data."""
    if msg_type == 'ExtendedIdMessage1':
        return msg_class(
            sequence_number=test_msg['sequence_number'],
            label=test_msg['label'].encode('utf-8'),
            value=test_msg['value'],
            enabled=test_msg['enabled']
        )
    elif msg_type == 'ExtendedIdMessage2':
        return msg_class(
            sensor_id=test_msg['sensor_id'],
            reading=test_msg['reading'],
            status_code=test_msg['status_code'],
            description=test_msg['description'].encode('utf-8')
        )
    elif msg_type == 'ExtendedIdMessage3':
        timestamp = int(test_msg['timestamp']) if isinstance(test_msg['timestamp'], str) else test_msg['timestamp']
        return msg_class(
            timestamp=timestamp,
            temperature=test_msg['temperature'],
            humidity=test_msg['humidity'],
            location=test_msg['location'].encode('utf-8')
        )
    elif msg_type == 'ExtendedIdMessage4':
        event_time = int(test_msg['event_time']) if isinstance(test_msg['event_time'], str) else test_msg['event_time']
        return msg_class(
            event_id=test_msg['event_id'],
            event_type=test_msg['event_type'],
            event_time=event_time,
            event_data=test_msg['event_data'].encode('utf-8')
        )
    elif msg_type == 'ExtendedIdMessage5':
        return msg_class(
            x_position=test_msg['x_position'],
            y_position=test_msg['y_position'],
            z_position=test_msg['z_position'],
            frame_number=test_msg['frame_number']
        )
    elif msg_type == 'ExtendedIdMessage6':
        return msg_class(
            command_id=test_msg['command_id'],
            parameter1=test_msg['parameter1'],
            parameter2=test_msg['parameter2'],
            acknowledged=test_msg['acknowledged'],
            command_name=test_msg['command_name'].encode('utf-8')
        )
    elif msg_type == 'ExtendedIdMessage7':
        return msg_class(
            counter=test_msg['counter'],
            average=test_msg['average'],
            minimum=test_msg['minimum'],
            maximum=test_msg['maximum']
        )
    elif msg_type == 'ExtendedIdMessage8':
        return msg_class(
            level=test_msg['level'],
            offset=test_msg['offset'],
            duration=test_msg['duration'],
            tag=test_msg['tag'].encode('utf-8')
        )
    elif msg_type == 'ExtendedIdMessage9':
        big_number = int(test_msg['big_number']) if isinstance(test_msg['big_number'], str) else test_msg['big_number']
        big_unsigned = int(test_msg['big_unsigned']) if isinstance(test_msg['big_unsigned'], str) else test_msg['big_unsigned']
        return msg_class(
            big_number=big_number,
            big_unsigned=big_unsigned,
            precision_value=test_msg['precision_value']
        )
    elif msg_type == 'ExtendedIdMessage10':
        return msg_class(
            small_value=test_msg['small_value'],
            short_text=test_msg['short_text'].encode('utf-8'),
            flag=test_msg['flag']
        )
    elif msg_type == 'LargePayloadMessage1':
        timestamp = int(test_msg['timestamp']) if isinstance(test_msg['timestamp'], str) else test_msg['timestamp']
        return msg_class(
            sensor_readings=test_msg['sensor_readings'],
            reading_count=test_msg['reading_count'],
            timestamp=timestamp,
            device_name=test_msg['device_name'].encode('utf-8')
        )
    elif msg_type == 'LargePayloadMessage2':
        return msg_class(
            large_data=test_msg['large_data']
        )
    else:
        raise ValueError(f"Unknown message type: {msg_type}")


def encode_extended_messages(format_name):
    """Encode multiple extended test messages using the specified frame format."""
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from extended_test_sf import (
        ExtendedTestExtendedIdMessage1, ExtendedTestExtendedIdMessage2,
        ExtendedTestExtendedIdMessage3, ExtendedTestExtendedIdMessage4,
        ExtendedTestExtendedIdMessage5, ExtendedTestExtendedIdMessage6,
        ExtendedTestExtendedIdMessage7, ExtendedTestExtendedIdMessage8,
        ExtendedTestExtendedIdMessage9, ExtendedTestExtendedIdMessage10,
        ExtendedTestLargePayloadMessage1, ExtendedTestLargePayloadMessage2
    )
    
    from frame_profiles import (
        create_profile_bulk_writer, create_profile_network_writer
    )
    
    # Map message types to classes
    msg_classes = {
        'ExtendedIdMessage1': ExtendedTestExtendedIdMessage1,
        'ExtendedIdMessage2': ExtendedTestExtendedIdMessage2,
        'ExtendedIdMessage3': ExtendedTestExtendedIdMessage3,
        'ExtendedIdMessage4': ExtendedTestExtendedIdMessage4,
        'ExtendedIdMessage5': ExtendedTestExtendedIdMessage5,
        'ExtendedIdMessage6': ExtendedTestExtendedIdMessage6,
        'ExtendedIdMessage7': ExtendedTestExtendedIdMessage7,
        'ExtendedIdMessage8': ExtendedTestExtendedIdMessage8,
        'ExtendedIdMessage9': ExtendedTestExtendedIdMessage9,
        'ExtendedIdMessage10': ExtendedTestExtendedIdMessage10,
        'LargePayloadMessage1': ExtendedTestLargePayloadMessage1,
        'LargePayloadMessage2': ExtendedTestLargePayloadMessage2,
    }
    
    messages = load_extended_messages()
    
    # Only extended profiles support msg_id > 255
    capacity = 8192  # Larger for extended payloads
    writer_creators = {
        'profile_bulk': lambda: create_profile_bulk_writer(capacity),
        'profile_network': lambda: create_profile_network_writer(capacity),
    }
    
    creator = writer_creators.get(format_name)
    if not creator:
        raise ValueError(f"Format not supported for extended messages: {format_name}. Use profile_bulk or profile_network.")
    
    writer = creator()
    
    for item in messages:
        msg_type = item['type']
        test_msg = item['data']
        
        msg_class = msg_classes.get(msg_type)
        if not msg_class:
            raise ValueError(f"Unknown message type: {msg_type}")
        
        msg = create_extended_message(msg_class, test_msg, msg_type)
        msg_data = bytes(msg.pack())
        
        bytes_written = writer.write(msg.msg_id, msg_data)
        if bytes_written == 0:
            raise RuntimeError(f"Failed to encode message: buffer full or encoding error")
    
    return writer.data()


def decode_extended_messages(format_name, data):
    """Decode and validate multiple extended test messages."""
    import sys
    import os
    gen_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
    if os.path.exists(gen_path) and gen_path not in sys.path:
        sys.path.insert(0, gen_path)
    
    from extended_test_sf import (
        ExtendedTestExtendedIdMessage1, ExtendedTestExtendedIdMessage2,
        ExtendedTestExtendedIdMessage3, ExtendedTestExtendedIdMessage4,
        ExtendedTestExtendedIdMessage5, ExtendedTestExtendedIdMessage6,
        ExtendedTestExtendedIdMessage7, ExtendedTestExtendedIdMessage8,
        ExtendedTestExtendedIdMessage9, ExtendedTestExtendedIdMessage10,
        ExtendedTestLargePayloadMessage1, ExtendedTestLargePayloadMessage2
    )
    
    from frame_profiles import (
        create_profile_bulk_reader, create_profile_network_reader
    )
    
    # Map message types to classes
    msg_classes = {
        'ExtendedIdMessage1': ExtendedTestExtendedIdMessage1,
        'ExtendedIdMessage2': ExtendedTestExtendedIdMessage2,
        'ExtendedIdMessage3': ExtendedTestExtendedIdMessage3,
        'ExtendedIdMessage4': ExtendedTestExtendedIdMessage4,
        'ExtendedIdMessage5': ExtendedTestExtendedIdMessage5,
        'ExtendedIdMessage6': ExtendedTestExtendedIdMessage6,
        'ExtendedIdMessage7': ExtendedTestExtendedIdMessage7,
        'ExtendedIdMessage8': ExtendedTestExtendedIdMessage8,
        'ExtendedIdMessage9': ExtendedTestExtendedIdMessage9,
        'ExtendedIdMessage10': ExtendedTestExtendedIdMessage10,
        'LargePayloadMessage1': ExtendedTestLargePayloadMessage1,
        'LargePayloadMessage2': ExtendedTestLargePayloadMessage2,
    }
    
    # Only extended profiles support msg_id > 255
    reader_creators = {
        'profile_bulk': lambda: create_profile_bulk_reader(data),
        'profile_network': lambda: create_profile_network_reader(data),
    }
    
    creator = reader_creators.get(format_name)
    if not creator:
        raise ValueError(f"Format not supported for extended messages: {format_name}. Use profile_bulk or profile_network.")
    
    reader = creator()
    messages = load_extended_messages()
    message_count = 0
    
    while reader.has_more() and message_count < len(messages):
        result = reader.next()
        
        if not result or not result.valid:
            print(f"  Decoding failed for message {message_count}")
            return False, message_count
        
        item = messages[message_count]
        msg_type = item['type']
        test_msg = item['data']
        
        msg_class = msg_classes.get(msg_type)
        if not msg_class:
            print(f"  Unknown message type: {msg_type}")
            return False, message_count
        
        expected_msg_id = msg_class.msg_id
        
        # For extended profiles, combine pkg_id and msg_id to get full message ID
        # Full msg_id = (pkg_id << 8) | msg_id
        decoded_msg_id = (result.package_id << 8) | result.msg_id
        
        if decoded_msg_id != expected_msg_id:
            print(f"  Message ID mismatch for message {message_count}: expected {expected_msg_id}, got {decoded_msg_id} (pkg_id={result.package_id}, msg_id={result.msg_id})")
            return False, message_count
        
        # Decode and validate (just verify it decodes without error)
        msg = msg_class.create_unpack(result.msg_data)
        
        message_count += 1
    
    if message_count != len(messages):
        print(f"  Expected {len(messages)} messages, but decoded {message_count}")
        return False, message_count
    
    if reader.remaining != 0:
        print(f"  Extra data after messages: {reader.remaining} bytes remaining")
        return False, message_count
    
    return True, message_count
