#pragma once

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <array>
#include <span>

namespace StructFrame {

// Checksum structure
struct Checksum {
    uint8_t byte1;
    uint8_t byte2;
};

// Message information structure
struct MessageInfo {
    bool valid;
    uint8_t length;
    uint8_t msg_id;
    uint8_t* msg_location;
};

// Parser states
enum class ParserState : uint8_t {
    LookingForStartByte = 0,
    GettingHeader = 1,
    GettingPayload = 2
};

// Fletcher checksum calculation
inline Checksum fletcher_checksum(const uint8_t* buffer, size_t length) {
    Checksum checksum{0, 0};
    
    for (size_t i = 0; i < length; i++) {
        checksum.byte1 += buffer[i];
        checksum.byte2 += checksum.byte1;
    }
    
    return checksum;
}

// Base packet format interface
class PacketFormat {
public:
    virtual ~PacketFormat() = default;
    
    virtual bool check_start_byte(uint8_t byte) = 0;
    virtual bool process_header_byte(uint8_t byte, size_t index) = 0;
    virtual size_t get_msg_id(const uint8_t* data) = 0;
    virtual size_t get_full_packet_length(size_t msg_length) = 0;
    virtual MessageInfo validate_packet(const uint8_t* buffer, size_t length) = 0;
    virtual size_t encode(uint8_t* buffer, uint8_t msg_id, const uint8_t* msg, uint8_t msg_size) = 0;
    virtual uint8_t* encode_reserve(uint8_t* buffer, uint8_t msg_id, uint8_t msg_size) = 0;
    virtual uint8_t encode_finish(uint8_t* buffer, uint8_t msg_size) = 0;
};

// Encoder buffer for message encoding
class EncodeBuffer {
public:
    EncodeBuffer(uint8_t* buffer, size_t max_size)
        : data_(buffer), max_size_(max_size), size_(0), in_progress_(false) {}
    
    bool encode(PacketFormat* format, uint8_t msg_id, const void* msg, uint8_t msg_size) {
        if (in_progress_) {
            return false;
        }
        in_progress_ = true;
        size_ += format->encode(data_, msg_id, static_cast<const uint8_t*>(msg), msg_size);
        in_progress_ = false;
        return true;
    }
    
    uint8_t* reserve(PacketFormat* format, uint8_t msg_id, uint8_t msg_size) {
        if (in_progress_) {
            return nullptr;
        }
        in_progress_ = true;
        return format->encode_reserve(data_, msg_id, msg_size);
    }
    
    bool finish(PacketFormat* format, uint8_t msg_size) {
        if (!in_progress_) {
            return false;
        }
        size_ += format->encode_finish(data_, msg_size);
        in_progress_ = false;
        return true;
    }
    
    uint8_t* data() { return data_; }
    size_t size() const { return size_; }
    size_t max_size() const { return max_size_; }
    void reset() { size_ = 0; in_progress_ = false; }
    
private:
    uint8_t* data_;
    size_t max_size_;
    size_t size_;
    bool in_progress_;
};

// Packet parser state
struct ParserStateData {
    ParserState state;
    size_t packet_size;
    PacketFormat* format;
    uint8_t* buffer;
    size_t buffer_size;
    size_t buffer_max_size;
    size_t packet_start_index;
    bool finished;
    size_t read_location;
};

}  // namespace StructFrame
