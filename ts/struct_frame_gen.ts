
import * as myl_vehicle from './myl_vehicle.sf';

export function get_message_length(msg_id: number) {
  return myl_vehicle.get_message_length(msg_id);
}
