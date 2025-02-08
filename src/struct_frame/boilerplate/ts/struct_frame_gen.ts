
import * as bs from './biostream.sf';

export function get_message_length(msg_id: number) {
  console.log(msg_id)
  return bs.get_message_length(msg_id);
}
