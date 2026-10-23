/**
 * Encode two messages into a Standard-profile byte stream and decode them again.
 *
 *   python -m struct_frame examples/basic/hello.sf --build_ts --ts_path out/ts
 *   cp examples/basic/hello.ts out/ts/ && cd out/ts && npx ts-node hello.ts
 */
import { AccumulatingReader, BufferWriter, ProfileStandardConfig } from './frame-profiles';
import { Heartbeat, Pose, VehicleType, getMessageInfo } from './hello.structframe';

// ---- encode ----
const writer = new BufferWriter(ProfileStandardConfig, 256);
writer.write(new Pose({ pitch: 100, yawRate: -1.45, sample: 4883 }));
writer.write(new Heartbeat({ id: 23, type: VehicleType.Quadcopter }));
const stream = writer.data();
console.log(`encoded ${stream.length} bytes`);

// ---- decode: feed bytes as they arrive (here, one at a time like a UART) ----
const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo);
for (const byte of stream) {
  const frame = reader.pushByte(byte);
  if (!frame.valid) continue;
  if (frame.msgId === Pose._msgid) {
    const pose = Pose.deserialize(frame);
    console.log(`pose: pitch=${pose.pitch.toFixed(1)} yawRate=${pose.yawRate.toFixed(2)} sample=${pose.sample}`);
  } else if (frame.msgId === Heartbeat._msgid) {
    const hb = Heartbeat.deserialize(frame);
    console.log(`heartbeat: id=${hb.id} type=${hb.type}`);
  }
}
