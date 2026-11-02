#!/usr/bin/env python3
"""Encode two messages into a Standard-profile byte stream and decode them again.

    python -m struct_frame examples/basic/hello.sf --build_py --py_path out/py
    PYTHONPATH=out/py python examples/basic/hello.py
"""
from frame_profiles import AccumulatingReader, BufferWriter, PROFILE_STANDARD_CONFIG
from struct_frame.generated.hello import Heartbeat, Pose, VehicleType, get_message_info

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
