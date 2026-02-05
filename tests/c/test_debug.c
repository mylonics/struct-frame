#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "../../src/struct_frame/boilerplate/c/frame_profiles.h"
#include "../generated/c/serialization_test.structframe.h"

int main(void) {
    uint8_t buffer[4096];
    SerializationTestBasicTypesMessage msg;
    
    // Create writer
    buffer_writer_t writer;
    buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
    
    // Write three frames
    memset(&msg, 0, sizeof(msg));
    msg.small_int = 1;
    msg.flag = true;
    strncpy(msg.device_id, "DEV1", sizeof(msg.device_id) - 1);
    msg.description.length = 5;
    strncpy(msg.description.data, "First", 63);
    
    uint8_t payload1[256];
    size_t payload_size1 = SerializationTestBasicTypesMessage_serialize(&msg, payload1);
    buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                       payload1, payload_size1, 0, 0, 0, 0,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
    
    size_t first_frame_end = buffer_writer_size(&writer);
    printf("First frame ends at: %zu\n", first_frame_end);
    
    msg.small_int = 2;
    uint8_t payload2[256];
    size_t payload_size2 = SerializationTestBasicTypesMessage_serialize(&msg, payload2);
    buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                       payload2, payload_size2, 0, 0, 0, 0,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
    
    size_t second_frame_end = buffer_writer_size(&writer);
    printf("Second frame ends at: %zu\n", second_frame_end);
    
    msg.small_int = 3;
    uint8_t payload3[256];
    size_t payload_size3 = SerializationTestBasicTypesMessage_serialize(&msg, payload3);
    buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                       payload3, payload_size3, 0, 0, 0, 0,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                       SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
    
    size_t total_size = buffer_writer_size(&writer);
    printf("Total size: %zu\n", total_size);
    
    printf("Before corruption, CRC bytes at %zu: 0x%02X 0x%02X\n",
           second_frame_end - 2, buffer[second_frame_end - 2], buffer[second_frame_end - 1]);
    
    // Corrupt the second frame's CRC
    buffer[second_frame_end - 1] ^= 0xFF;
    buffer[second_frame_end - 2] ^= 0xFF;
    
    printf("After corruption, CRC bytes at %zu: 0x%02X 0x%02X\n",
           second_frame_end - 2, buffer[second_frame_end - 2], buffer[second_frame_end - 1]);
    
    // Parse all frames
    buffer_reader_t reader;
    buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, total_size, NULL);
    
    frame_msg_info_t result1 = buffer_reader_next(&reader);
    printf("First frame: valid=%d\n", result1.valid);
    
    frame_msg_info_t result2 = buffer_reader_next(&reader);
    printf("Second frame: valid=%d\n", result2.valid);
    
    return 0;
}
