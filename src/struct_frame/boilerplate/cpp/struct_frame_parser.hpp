#pragma once

#include "struct_frame_types.hpp"
#include "struct_frame.hpp"

namespace StructFrame {

// Parse buffer function for processing multiple bytes at once
inline MessageInfo parse_buffer(ParserStateData* state) {
    MessageInfo invalid_info{false, 0, 0, nullptr};
    
    if (!state->buffer || state->buffer_size == 0) {
        return invalid_info;
    }
    
    while (state->read_location < state->buffer_size && !state->finished) {
        uint8_t byte = state->buffer[state->read_location++];
        
        switch (state->state) {
            case ParserState::LookingForStartByte:
                if (state->format->check_start_byte(byte)) {
                    state->packet_start_index = state->read_location - 1;
                    state->state = ParserState::GettingHeader;
                    state->packet_size = 1;
                }
                break;
                
            case ParserState::GettingHeader:
                state->packet_size++;
                if (state->format->process_header_byte(byte, state->packet_size - 1)) {
                    size_t msg_id = state->format->get_msg_id(state->buffer + state->packet_start_index);
                    size_t msg_length = 0;
                    
                    // Need external callback to get message length
                    // This would be implemented by the user
                    state->packet_size = state->format->get_full_packet_length(msg_length);
                    state->state = ParserState::GettingPayload;
                }
                break;
                
            case ParserState::GettingPayload:
                if (state->read_location - state->packet_start_index >= state->packet_size) {
                    state->state = ParserState::LookingForStartByte;
                    MessageInfo info = state->format->validate_packet(
                        state->buffer + state->packet_start_index, 
                        state->packet_size
                    );
                    
                    if (state->read_location >= state->buffer_size) {
                        state->finished = true;
                    }
                    
                    return info;
                }
                break;
        }
    }
    
    if (state->read_location >= state->buffer_size) {
        state->finished = true;
    }
    
    return invalid_info;
}

// Device base class for implementing communication devices
class Device {
public:
    Device(PacketFormat* format, uint8_t* tx_buffer, size_t tx_buffer_size)
        : format_(format),
          encode_buffer_(tx_buffer, tx_buffer_size),
          parser_(format, [this](size_t msg_id, size_t* size) {
              return this->get_message_length(msg_id, size);
          }) {}
    
    virtual ~Device() = default;
    
    // Process received data
    void process_rx_data(uint8_t* buffer, size_t length) {
        for (size_t i = 0; i < length; ++i) {
            MessageInfo info = parser_.parse_byte(buffer[i]);
            if (info.valid) {
                handle_message(info);
            }
        }
    }
    
    // Get encode buffer for message transmission
    EncodeBuffer& get_encode_buffer() {
        return encode_buffer_;
    }
    
    // Get the transmit buffer data
    uint8_t* get_tx_data() {
        return encode_buffer_.data();
    }
    
    size_t get_tx_size() const {
        return encode_buffer_.size();
    }
    
    void reset_tx_buffer() {
        encode_buffer_.reset();
    }
    
protected:
    // Must be implemented by derived classes
    virtual bool get_message_length(size_t msg_id, size_t* size) = 0;
    virtual void handle_message(const MessageInfo& info) = 0;
    
    PacketFormat* format_;
    EncodeBuffer encode_buffer_;
    FrameParser parser_;
};

}  // namespace StructFrame
