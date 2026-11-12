#!/usr/bin/env python3
"""Encode two messages into a Standard-profile byte stream and decode them again.

    struct-frame examples/basic/hello.sf --build-py --py-path out/py
    PYTHONPATH=out/py python examples/basic/hello.py
"""
from structframe.frame_profiles import AccumulatingReader, BufferWriter, PROFILE_STANDARD_CONFIG
from structframe.hello import Heartbeat, Pose, VehicleType, get_message_info

# ---- encode ----
writer = BufferWriter(PROFILE_STANDARD_CONFIG, 256)
writer.write(Pose(pitch=100.0, yaw_rate=-1.45, sample=4883))
writer.write(Heartbeat(id=23, type=VehicleType.QUADCOPTER))
stream = writer.data()
print(f"encoded {len(stream)} bytes")

# ---- decode: feed bytes as they arrive (here, one at a time like a UART) ----
reader = AccumulatingReader(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info)
for byte in stream:
    frame = reader.push_byte(byte)
    if not frame.valid:
        continue
    if frame.msg_id == Pose.MSG_ID:
        pose = Pose.deserialize(frame.msg_data)
        print(f"pose: pitch={pose.pitch:.1f} yaw_rate={pose.yaw_rate:.2f} sample={pose.sample}")
    elif frame.msg_id == Heartbeat.MSG_ID:
        hb = Heartbeat.deserialize(frame.msg_data)
        print(f"heartbeat: id={hb.id} type={hb.type}")
