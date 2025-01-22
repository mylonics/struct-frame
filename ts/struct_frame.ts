import { Struct } from 'typed-struct';
import * as sf_types from './struct_frame_types';

function fletcher_checksum_calculation(buffer: Uint8Array, data_length: number): sf_types.checksum_t {
    let checksum: sf_types.checksum_t = { byte1: 0, byte2: 0 };

    for (let i = 0; i < data_length; i++) {
        checksum.byte1 += buffer[i];
        checksum.byte2 += checksum.byte1;
    }
    return checksum;
}

export function msg_encode(buffer: sf_types.struct_frame_buffer, msg: any, msgid: number) {
    buffer.data[buffer.size++] = buffer.config.start_byte;
    buffer.crc_start_loc = buffer.size;
    buffer.data[buffer.size++] = msgid;

    if (buffer.config.has_len) {
        buffer.data[buffer.size++] = msg.getSize();
    }
    const rawData = Struct.raw(msg);
    for (let i = 0; i < rawData.length; i++) {
        buffer.data[buffer.size++] = rawData[i]
    }

    if (buffer.config.has_crc) {
        let crc = fletcher_checksum_calculation(buffer.data.slice(buffer.crc_start_loc), buffer.crc_start_loc + rawData.length);
        buffer.data[buffer.size++] = crc.byte1;
        buffer.data[buffer.size++] = crc.byte2;
    }
}

export function msg_reserve(buffer: sf_types.struct_frame_buffer, msg_id: number, msg_size: number) {
    throw new Error("Function Unimplemented");
    
    if (buffer.in_progress) {
        return;
    }
    buffer.in_progress = true;
    buffer.data[buffer.size++] = buffer.config.start_byte;

    buffer.data[buffer.size++] = msg_id;
    if (buffer.config.has_len) {
        buffer.data[buffer.size++] = msg_size;
    }

    let ret = Buffer.from(buffer.data, buffer.size, msg_size);
    buffer.size += msg_size;
    return ret;
}



export function msg_finish(buffer: sf_types.struct_frame_buffer) {
    throw new Error("Function Unimplemented");
    
    if (buffer.config.has_crc) {
        let crc = fletcher_checksum_calculation(buffer.data.slice(buffer.crc_start_loc), buffer.crc_start_loc - buffer.size);
        buffer.data[buffer.size++] = crc.byte1;
        buffer.data[buffer.size++] = crc.byte2;
        buffer.size += 2
    }
    buffer.in_progress = false;
}                                                                      