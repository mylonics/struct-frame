#pragma once

#include "struct_frame_types.hpp"
#include <functional>
#include <unordered_map>

namespace StructFrame {

// Basic packet format class (similar to Python's BasicPacket)
class BasicPacket : public PacketFormat {
public:
    BasicPacket(uint8_t start_byte = 0x90, size_t header_length = 2, size_t footer_length = 2)
        : start_byte_(start_byte),
          header_length_(header_length),
          footer_length_(footer_length),
          desired_packet_length_(0) {}
    
    bool check_start_byte(uint8_t byte) override {
        return byte == start_byte_;
    }
    
    bool process_header_byte(uint8_t byte, size_t index) override {
        if (index < header_length_) {
            header_buffer_[index] = byte;
            return (index + 1) >= header_length_;
        }
        return false;
    }
    
    size_t get_msg_id(const uint8_t* data) override {
        return data[1];  // Message ID is at index 1
    }
    
    size_t get_full_packet_length(size_t msg_length) override {
        desired_packet_length_ = header_length_ + footer_length_ + msg_length;
        return desired_packet_length_;
    }
    
    MessageInfo validate_packet(const uint8_t* buffer, size_t length) override {
        MessageInfo info{false, 0, 0, nullptr};
        
        if (length < header_length_ + footer_length_) {
            return info;
        }
        
        size_t msg_length = length - header_length_ - footer_length_;
        
        // Calculate checksum on msg_id + msg data (buffer + 1 includes msg_id byte)
        Checksum calc = fletcher_checksum(buffer + 1, msg_length + 1);
        
        // Validate checksum
        if (calc.byte1 == buffer[length - 2] && calc.byte2 == buffer[length - 1]) {
            info.valid = true;
            info.length = static_cast<uint8_t>(msg_length);
            info.msg_id = buffer[1];
            info.msg_location = const_cast<uint8_t*>(buffer + header_length_);
        }
        
        return info;
    }
    
    size_t encode(uint8_t* buffer, uint8_t msg_id, const uint8_t* msg, uint8_t msg_size) override {
        buffer[0] = start_byte_;
        buffer[1] = msg_id;
        
        if (msg_size > 0) {
            std::memcpy(buffer + 2, msg, msg_size);
        }
        
        // Calculate checksum on msg_id + msg data (consistent with C and Python)
        Checksum checksum = fletcher_checksum(buffer + 1, msg_size + 1);
        buffer[2 + msg_size] = checksum.byte1;
        buffer[2 + msg_size + 1] = checksum.byte2;
        
        return header_length_ + msg_size + footer_length_;
    }
    
    uint8_t* encode_reserve(uint8_t* buffer, uint8_t msg_id, uint8_t msg_size) override {
        buffer[0] = start_byte_;
        buffer[1] = msg_id;
        return buffer + header_length_;
    }
    
    uint8_t encode_finish(uint8_t* buffer, uint8_t msg_size) override {
        // Calculate checksum on msg_id + msg data (buffer + 1 includes msg_id byte)
        Checksum checksum = fletcher_checksum(buffer + 1, msg_size + 1);
        buffer[header_length_ + msg_size] = checksum.byte1;
        buffer[header_length_ + msg_size + 1] = checksum.byte2;
        return header_length_ + msg_size + footer_length_;
    }
    
private:
    uint8_t start_byte_;
    size_t header_length_;
    size_t footer_length_;
    size_t desired_packet_length_;
    uint8_t header_buffer_[256];
};

// Frame parser (similar to Python's FrameParser)
class FrameParser {
public:
    using MessageLengthCallback = std::function<bool(size_t msg_id, size_t* size)>;
    
    FrameParser(PacketFormat* format, MessageLengthCallback msg_length_callback)
        : format_(format),
          msg_length_callback_(msg_length_callback),
          state_(ParserState::LookingForStartByte),
          header_index_(0),
          packet_index_(0),
          packet_size_(0) {}
    
    MessageInfo parse_byte(uint8_t byte) {
        MessageInfo invalid_info{false, 0, 0, nullptr};
        
        switch (state_) {
            case ParserState::LookingForStartByte:
                if (format_->check_start_byte(byte)) {
                    packet_buffer_[0] = byte;
                    header_index_ = 1;
                    state_ = ParserState::GettingHeader;
                }
                break;
                
            case ParserState::GettingHeader:
                packet_buffer_[header_index_++] = byte;
                
                if (format_->process_header_byte(byte, header_index_ - 1)) {
                    size_t msg_id = format_->get_msg_id(packet_buffer_);
                    size_t msg_length = 0;
                    
                    if (msg_length_callback_(msg_id, &msg_length)) {
                        packet_size_ = format_->get_full_packet_length(msg_length);
                        packet_index_ = header_index_;
                        state_ = ParserState::GettingPayload;
                    } else {
                        state_ = ParserState::LookingForStartByte;
                    }
                }
                break;
                
            case ParserState::GettingPayload:
                packet_buffer_[packet_index_++] = byte;
                
                if (packet_index_ >= packet_size_) {
                    state_ = ParserState::LookingForStartByte;
                    return format_->validate_packet(packet_buffer_, packet_size_);
                }
                break;
        }
        
        return invalid_info;
    }
    
    void reset() {
        state_ = ParserState::LookingForStartByte;
        header_index_ = 0;
        packet_index_ = 0;
        packet_size_ = 0;
    }
    
private:
    PacketFormat* format_;
    MessageLengthCallback msg_length_callback_;
    ParserState state_;
    size_t header_index_;
    size_t packet_index_;
    size_t packet_size_;
    uint8_t packet_buffer_[512];  // Reasonable max packet size
};

// Message encoder/decoder helper template
template<typename T>
class MessageHelper {
public:
    static bool encode(EncodeBuffer& buffer, PacketFormat* format, const T& msg, uint8_t msg_id, uint8_t msg_size) {
        return buffer.encode(format, msg_id, &msg, msg_size);
    }
    
    static T* reserve(EncodeBuffer& buffer, PacketFormat* format, uint8_t msg_id, uint8_t msg_size) {
        return reinterpret_cast<T*>(buffer.reserve(format, msg_id, msg_size));
    }
    
    static bool finish(EncodeBuffer& buffer, PacketFormat* format, uint8_t msg_size) {
        return buffer.finish(format, msg_size);
    }
    
    static T get(const MessageInfo& info) {
        return *reinterpret_cast<T*>(info.msg_location);
    }
    
    static T* get_ref(const MessageInfo& info) {
        return reinterpret_cast<T*>(info.msg_location);
    }
};

}  // namespace StructFrame
