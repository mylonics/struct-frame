import * as mv from '../generated/ts/myl_vehicle.structframe';
import { parse_char, parse_buffer } from '../generated/ts/struct_frame_parser';
import { struct_frame_buffer, buffer_parser_result_t, } from '../generated/ts/struct_frame_types';
import { type ExtractType } from '../generated/ts/struct_base';

let tx_buffer = new struct_frame_buffer(256)
let rx_buffer = new struct_frame_buffer(256)

let msg = new mv.myl_vehicle_pose();
msg.pitch = 100;
msg.yaw_rate = -1.45;
msg.test = 4883;
mv.myl_vehicle_pose_encode(tx_buffer, msg);

let hb = new mv.myl_vehicle_heartbeat();

hb.id = 23;
hb.type = mv.myl_vehicletype.FW;
mv.myl_vehicle_heartbeat_encode(tx_buffer, hb);


let msg2: ExtractType<typeof mv.myl_vehicle_pose>;
let hb3: ExtractType<typeof mv.myl_vehicle_heartbeat> | undefined;
for (let i = 0; i < tx_buffer.size; i++) {
  if (parse_char(rx_buffer, tx_buffer.data[i])) {
    switch (rx_buffer.msg_id_len.msg_id) {
      case mv.myl_vehicle_heartbeat_msgid:
        console.log("got hb msg with id %d", rx_buffer.msg_id_len.msg_id);
        hb3 = new mv.myl_vehicle_heartbeat(rx_buffer.msg_data);
        break;
      case mv.myl_vehicle_pose_msgid:
        console.log("got pose msg with id %d", rx_buffer.msg_id_len.msg_id);
        msg2 = new mv.myl_vehicle_pose(rx_buffer.msg_data);
        break;

      default:
        break;
    }
  }
}


let msg3: ExtractType<typeof mv.myl_vehicle_pose>;
let hb5: ExtractType<typeof mv.myl_vehicle_heartbeat> | undefined;

let result: buffer_parser_result_t = new buffer_parser_result_t();
while (parse_buffer(tx_buffer.data, tx_buffer.max_size, result)) {
  switch (result.msg_id_len.msg_id) {
    case mv.myl_vehicle_heartbeat_msgid:
      console.log("got hb msg with id %d", result.msg_id_len.msg_id);
      hb5 = new mv.myl_vehicle_heartbeat(rx_buffer.msg_data);
      break;
    case mv.myl_vehicle_pose_msgid:
      console.log("got pose msg with id %d", result.msg_id_len.msg_id);
      msg3 = new mv.myl_vehicle_pose(rx_buffer.msg_data);
      break;

    default:
      break;
  }
}

if (hb && hb3 && hb5) {
  //console.log("%d %d  %d %d", hb.id, hb.type, hb3.id, hb3.type, hb5.id, hb5.type);
  console.log(hb)
  console.log(hb3)
  console.log(hb5)
}

