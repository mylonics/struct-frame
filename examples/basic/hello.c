/*
 * Encode two messages into a Standard-profile byte stream and decode them again.
 *
 *   struct-frame examples/basic/hello.sf --build-c --c-path out/c
 *   gcc -std=c11 -Iout/c examples/basic/hello.c -o hello && ./hello
 */
#include <stdio.h>

#include "frame_profiles.h"
#include "hello.structframe.h"

int main(void) {
  /* ---- encode ---- */
  uint8_t tx[256];
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, tx, sizeof(tx));

  /* The generated <Type>_write functions fill in the message ID and checksum magic bytes. */
  HelloPose pose = {.pitch = 100.0f, .yaw_rate = -1.45f, .sample = 4883};
  HelloPose_write(&writer, &pose);

  HelloHeartbeat hb = {.id = 23, .type = VEHICLE_TYPE_QUADCOPTER};
  HelloHeartbeat_write(&writer, &hb);

  size_t encoded = buffer_writer_size(&writer);
  printf("encoded %zu bytes\n", encoded);

  /* ---- decode: feed bytes as they arrive (here, all at once) ---- */
  uint8_t internal[256];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal, sizeof(internal),
                           hello_get_message_info);
  accumulating_reader_add_data(&reader, tx, encoded);

  /* try_next keeps going past corrupt frames; it stops when the data is used up. */
  frame_msg_info_t frame;
  while (accumulating_reader_try_next(&reader, &frame)) {
    if (!frame.valid) continue;
    if (frame.msg_id == HELLO_POSE_MSG_ID) {
      HelloPose decoded;
      HelloPose_deserialize(frame.msg_data, frame.msg_len, &decoded);
      printf("pose: pitch=%.1f yaw_rate=%.2f sample=%u\n", decoded.pitch, decoded.yaw_rate,
             (unsigned)decoded.sample);
    } else if (frame.msg_id == HELLO_HEARTBEAT_MSG_ID) {
      HelloHeartbeat decoded;
      HelloHeartbeat_deserialize(frame.msg_data, frame.msg_len, &decoded);
      printf("heartbeat: id=%u type=%u\n", (unsigned)decoded.id, (unsigned)decoded.type);
    }
  }
  return 0;
}
