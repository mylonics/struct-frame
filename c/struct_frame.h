#pragma once
#include "stdint.h"
#include "stdbool.h"
#include "string.h"
#include "struct_frame_types.h"

struct checksum_t fletcher_checksum_calculation(uint8_t *buffer,
                                                uint8_t data_length)
{
    checksum_t checksum;

    for (int i = 0; i < data_length; i++)
    {
        checksum.byte1 += buffer[i];
        checksum.byte2 += checksum.byte1;
    }
    return checksum;
}

void msg_encode(struct_buffer *buffer, void *msg_buffer, uint8_t msg_id, uint8_t size)
{
    buffer->data[buffer->size++] = buffer->config.start_byte;
    buffer->crc_start_loc = buffer->size;
    buffer->data[buffer->size++] = msg_id;

    if (buffer->config.has_len)
    {
        buffer->data[buffer->size++] = size;
    }
    memcpy(buffer->data + buffer->size, (uint8_t *)msg_buffer, size);
    buffer->size += size;
    if (buffer->config.has_crc)
    {
        checksum_t crc = fletcher_checksum_calculation(buffer->data + buffer->crc_start_loc, buffer->crc_start_loc - buffer->size);
        buffer->data[buffer->size++] = crc.byte1;
        buffer->data[buffer->size++] = crc.byte2;
    }
}

void *msg_reserve(struct_buffer *buffer, uint8_t msg_id, uint8_t size)
{
    if (buffer->in_progress)
    {
        return 0;
    }
    buffer->in_progress = true;
    buffer->data[buffer->size++] = buffer->config.start_byte;
    size_t msg_start_loc = buffer->size;

    buffer->data[buffer->size++] = msg_id;
    if (buffer->config.has_len)
    {
        buffer->data[buffer->size++] = size;
    }

    void *out = &buffer->data[buffer->size];
    buffer->size += size;

    return out;
}

void msg_finish(struct_buffer *buffer)
{
    if (buffer->config.has_crc)
    {
        checksum_t crc = fletcher_checksum_calculation(buffer->data + buffer->crc_start_loc, buffer->crc_start_loc - buffer->size);
        buffer->data[buffer->size++] = crc.byte1;
        buffer->data[buffer->size++] = crc.byte2;
    }
    buffer->in_progress = false;
}

#define MESSAGE_HELPER(name, msg_size, msg_id)                             \
    void name##_encode(struct_buffer *buffer, name *name##_obj)            \
    {                                                                      \
        msg_encode(buffer, name##_obj, msg_id, msg_size);                  \
    }                                                                      \
    bool name##_reserve(struct_buffer *buffer, name **msg)                 \
    {                                                                      \
        void *ptr = msg_reserve(buffer, msg_id, msg_size);                 \
        if (ptr)                                                           \
        {                                                                  \
            *msg = (name *)ptr;                                            \
            return true;                                                   \
        }                                                                  \
        return false;                                                      \
    }                                                                      \
    void name##_finish(struct_buffer *buffer)                              \
    {                                                                      \
        msg_finish(buffer);                                                \
    }                                                                      \
    name name##_get(struct_buffer *buffer)                                 \
    {                                                                      \
        name msg = *(name *)(buffer->data);                                \
        return msg;                                                        \
    }                                                                      \
    name name##_get_from_buffer_result(buffer_parser_result_t result)      \
    {                                                                      \
        name msg = *(name *)(result.msg_loc);                              \
        return msg;                                                        \
    }                                                                      \
    name *name##_get_ref(struct_buffer *buffer)                            \
    {                                                                      \
        return (name *)(buffer->data);                                     \
    }                                                                      \
    name *name##_get_ref_from_buffer_result(buffer_parser_result_t result) \
    {                                                                      \
        return (name *)(result.msg_loc);                                   \
    }
