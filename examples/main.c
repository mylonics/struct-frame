#include <stdio.h>

#include "../generated/c/struct_frame_gen.h"
#include "../generated/c/struct_frame_parser.h"

// CREATE_DEFAULT_STRUCT_BUFFER(tx_buffer, 256);
uint8_t tx_buffer_buffer[256];
struct_buffer tx_buffer = {default_parser, tx_buffer_buffer, 256, 0, 0, false, 0, 0, 0};

// CREATE_DEFAULT_STRUCT_BUFFER(rx_buffer, 256);
uint8_t rx_buffer_buffer[256];
struct_buffer rx_buffer = {default_parser, rx_buffer_buffer, 256, 0, 0, false, 0, 0, 0};

int main() {
  MylVehiclePose msg;
  msg.pitch = 100;
  msg.yaw_rate = -1.45;
  msg.test = 4883;
  myl_vehicle_pose_encode(&tx_buffer, &msg);

  MylVehicleHeartbeat *hb;
  if (myl_vehicle_heartbeat_reserve(&tx_buffer, &hb)) {
    hb->id = 23;
    hb->type = VEHICLE_TYPE_VEHICLE_TYPE_FW;
    myl_vehicle_heartbeat_finish(&tx_buffer);
  }

  MylVehiclePose msg2;
  MylVehicleHeartbeat *hb2;
  MylVehicleHeartbeat hb3;
  for (int i = 0; i < tx_buffer.size; i++) {
    if (parse_char(&rx_buffer, tx_buffer.data[i])) {
      switch (rx_buffer.msg_id_len.msg_id) {
        case MYL_VEHICLE_HEARTBEAT_MSG_ID:
          printf("got hb msg with id %d\n", rx_buffer.msg_id_len.msg_id);
          hb2 = myl_vehicle_heartbeat_get_ref(&rx_buffer);
          hb3 = myl_vehicle_heartbeat_get(&rx_buffer);
          break;
        case MYL_VEHICLE_POSE_MSG_ID:
          printf("got pose msg with id %d\n", rx_buffer.msg_id_len.msg_id);
          msg2 = myl_vehicle_pose_get(&rx_buffer);
          break;

        default:
          break;
      }
    }
  }

  MylVehiclePose msg3;
  MylVehicleHeartbeat *hb4;
  MylVehicleHeartbeat hb5;
  buffer_parser_result_t result = zero_initialized_parser_result;
  while (parse_buffer(tx_buffer_buffer, 256, &result)) {
    switch (result.msg_id_len.msg_id) {
      case MYL_VEHICLE_HEARTBEAT_MSG_ID:
        printf("got hb msg with id %d\n", result.msg_id_len.msg_id);
        hb4 = myl_vehicle_heartbeat_get_ref_from_buffer_result(result);
        hb5 = myl_vehicle_heartbeat_get_from_buffer_result(result);
        break;
      case MYL_VEHICLE_POSE_MSG_ID:
        printf("got pose msg with id %d\n", result.msg_id_len.msg_id);
        msg3 = myl_vehicle_pose_get_from_buffer_result(result);
        break;

      default:
        break;
    }
  }
  printf("%d %d  %d %d", hb->id, hb->type, hb2->id, hb2->type);

  return 0;
}