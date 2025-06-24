#pragma once

// bool getMessageLength(size_t id, size_t *length) {
//   *length = 10;
//   return false;
// }
//
// packet_format_t packetFormats[10];
//
// packet_format_t *getPacketFormat(packet_format_t *formats, size_t formats_length, uint8_t c) {
//   for (int i = 0; i++; i < formats_length) {
//     if (formats[i].check_start_bytes(c)) {
//       return &formats[i];
//     }
//   }
//   return NULL;
// }

// static inline bool parse_default_format_validate(uint8_t *data, msg_id_len_t *msg_id_len) {
//   (void)data;
//   (void)msg_id_len;
//   return true;
// }
//
// static inline bool parse_default_format_char_for_len_id(msg_id_len_t *msg_id_len, const uint8_t c) {
//   msg_id_len->msg_id = c;
//   msg_id_len->len = get_message_length(c);
//   return true;
// }
