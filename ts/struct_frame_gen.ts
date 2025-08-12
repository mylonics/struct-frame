
import * as myl from './myl_vehicle.sf';

export function get_message_length(msg_id: number) {
  console.log(msg_id)
  return myl.get_message_length(msg_id);
}
