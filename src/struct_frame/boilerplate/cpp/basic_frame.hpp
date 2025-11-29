/*
 * BasicFrame - Simple frame format with CRC (C++ version)
 * 
 * Format: [START1=0x90] [START2=0x91] [MSG_ID] [MSG...] [CRC1] [CRC2]
 * 
 * This frame format requires a message ID to message length lookup function
 * since the length is not included in the packet.
 * 
 * Use Case: When all message lengths are known at compile time and bandwidth
 * efficiency is important.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <functional>

namespace StructFrame {

/* Frame constants */
constexpr uint8_t BASIC_FRAME_START_BYTE1 = 0x90;
constexpr uint8_t BASIC_FRAME_START_BYTE2 = 0x91;
constexpr size_t BASIC_FRAME_HEADER_SIZE = 3;  /* start1 + start2 + msg_id */
constexpr size_t BASIC_FRAME_FOOTER_SIZE = 2;  /* crc1 + crc2 */
constexpr size_t BASIC_FRAME_OVERHEAD = BASIC_FRAME_HEADER_SIZE + BASIC_FRAME_FOOTER_SIZE;

/* Checksum result */
struct BasicFrameChecksum {
    uint8_t byte1;
    uint8_t byte2;
};

/* Parse result */
struct BasicFrameMsgInfo {
    bool valid;
    uint8_t msg_id;
    uint8_t msg_len;
    uint8_t* msg_data;
    
    BasicFrameMsgInfo() : valid(false), msg_id(0), msg_len(0), msg_data(nullptr) {}
    BasicFrameMsgInfo(bool v, uint8_t id, uint8_t len, uint8_t* data) 
        : valid(v), msg_id(id), msg_len(len), msg_data(data) {}
};

/* Parser state enumeration */
enum class BasicFrameParserState : uint8_t {
    LookingForStart1 = 0,
    LookingForStart2 = 1,
    GettingMsgId = 2,
    GettingPayload = 3
};

/*===========================================================================
 * Checksum Calculation
 *===========================================================================*/

/**
 * Calculate Fletcher-16 checksum over the given data
 */
inline BasicFrameChecksum basic_frame_checksum(const uint8_t* data, size_t length) {
    BasicFrameChecksum ck{0, 0};
    for (size_t i = 0; i < length; i++) {
        ck.byte1 = static_cast<uint8_t>(ck.byte1 + data[i]);
        ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
    }
    return ck;
}

/*===========================================================================
 * Encode Buffer Class
 *===========================================================================*/

class BasicFrameEncodeBuffer {
public:
    BasicFrameEncodeBuffer(uint8_t* data, size_t max_size)
        : data_(data), max_size_(max_size), size_(0), in_progress_(false) {}
    
    void reset() {
        size_ = 0;
        in_progress_ = false;
    }
    
    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }
    size_t max_size() const { return max_size_; }
    bool in_progress() const { return in_progress_; }
    
    /**
     * Encode a message into the buffer
     */
    bool encode(uint8_t msg_id, const void* msg, size_t msg_size) {
        if (in_progress_) {
            return false;
        }
        
        size_t total_size = BASIC_FRAME_OVERHEAD + msg_size;
        if (size_ + total_size > max_size_) {
            return false;
        }
        
        uint8_t* packet_start = data_ + size_;
        
        /* Write header */
        packet_start[0] = BASIC_FRAME_START_BYTE1;
        packet_start[1] = BASIC_FRAME_START_BYTE2;
        packet_start[2] = msg_id;
        
        /* Write message data */
        if (msg_size > 0 && msg != nullptr) {
            std::memcpy(packet_start + BASIC_FRAME_HEADER_SIZE, msg, msg_size);
        }
        
        /* Calculate checksum over msg_id + msg data */
        BasicFrameChecksum ck = basic_frame_checksum(packet_start + 2, msg_size + 1);
        packet_start[BASIC_FRAME_HEADER_SIZE + msg_size] = ck.byte1;
        packet_start[BASIC_FRAME_HEADER_SIZE + msg_size + 1] = ck.byte2;
        
        size_ += total_size;
        return true;
    }
    
    /**
     * Reserve space in buffer for zero-copy encoding
     * Returns pointer to message data area, or nullptr on failure
     */
    uint8_t* reserve(uint8_t msg_id, size_t msg_size) {
        if (in_progress_) {
            return nullptr;
        }
        
        size_t total_size = BASIC_FRAME_OVERHEAD + msg_size;
        if (size_ + total_size > max_size_) {
            return nullptr;
        }
        
        uint8_t* packet_start = data_ + size_;
        
        /* Write header */
        packet_start[0] = BASIC_FRAME_START_BYTE1;
        packet_start[1] = BASIC_FRAME_START_BYTE2;
        packet_start[2] = msg_id;
        
        in_progress_ = true;
        reserved_msg_size_ = msg_size;
        return packet_start + BASIC_FRAME_HEADER_SIZE;
    }
    
    /**
     * Finish a reserved encoding by adding checksum
     */
    bool finish() {
        if (!in_progress_) {
            return false;
        }
        
        uint8_t* packet_start = data_ + size_;
        
        /* Calculate checksum over msg_id + msg data */
        BasicFrameChecksum ck = basic_frame_checksum(packet_start + 2, reserved_msg_size_ + 1);
        packet_start[BASIC_FRAME_HEADER_SIZE + reserved_msg_size_] = ck.byte1;
        packet_start[BASIC_FRAME_HEADER_SIZE + reserved_msg_size_ + 1] = ck.byte2;
        
        size_ += BASIC_FRAME_OVERHEAD + reserved_msg_size_;
        in_progress_ = false;
        return true;
    }
    
private:
    uint8_t* data_;
    size_t max_size_;
    size_t size_;
    bool in_progress_;
    size_t reserved_msg_size_ = 0;
};

/*===========================================================================
 * Parser Class
 *===========================================================================*/

class BasicFrameParser {
public:
    using MsgLengthCallback = std::function<bool(uint8_t msg_id, size_t* length)>;
    
    BasicFrameParser(uint8_t* buffer, size_t buffer_size, MsgLengthCallback msg_length_cb)
        : state_(BasicFrameParserState::LookingForStart1),
          buffer_(buffer),
          buffer_max_size_(buffer_size),
          buffer_index_(0),
          packet_size_(0),
          msg_id_(0),
          get_msg_length_(std::move(msg_length_cb)) {}
    
    void reset() {
        state_ = BasicFrameParserState::LookingForStart1;
        buffer_index_ = 0;
        packet_size_ = 0;
        msg_id_ = 0;
    }
    
    /**
     * Parse a single byte
     * Returns a BasicFrameMsgInfo with valid=true when a complete valid message is received
     */
    BasicFrameMsgInfo parse_byte(uint8_t byte) {
        BasicFrameMsgInfo result;
        
        switch (state_) {
            case BasicFrameParserState::LookingForStart1:
                if (byte == BASIC_FRAME_START_BYTE1) {
                    buffer_[0] = byte;
                    buffer_index_ = 1;
                    state_ = BasicFrameParserState::LookingForStart2;
                }
                break;
                
            case BasicFrameParserState::LookingForStart2:
                if (byte == BASIC_FRAME_START_BYTE2) {
                    buffer_[1] = byte;
                    buffer_index_ = 2;
                    state_ = BasicFrameParserState::GettingMsgId;
                } else if (byte == BASIC_FRAME_START_BYTE1) {
                    buffer_[0] = byte;
                    buffer_index_ = 1;
                } else {
                    state_ = BasicFrameParserState::LookingForStart1;
                }
                break;
                
            case BasicFrameParserState::GettingMsgId: {
                buffer_[2] = byte;
                buffer_index_ = 3;
                msg_id_ = byte;
                
                size_t msg_length = 0;
                if (get_msg_length_ && get_msg_length_(byte, &msg_length)) {
                    packet_size_ = BASIC_FRAME_OVERHEAD + msg_length;
                    if (packet_size_ <= buffer_max_size_) {
                        state_ = BasicFrameParserState::GettingPayload;
                    } else {
                        state_ = BasicFrameParserState::LookingForStart1;
                    }
                } else {
                    state_ = BasicFrameParserState::LookingForStart1;
                }
                break;
            }
                
            case BasicFrameParserState::GettingPayload:
                if (buffer_index_ < buffer_max_size_) {
                    buffer_[buffer_index_++] = byte;
                }
                
                if (buffer_index_ >= packet_size_) {
                    size_t msg_length = packet_size_ - BASIC_FRAME_OVERHEAD;
                    BasicFrameChecksum ck = basic_frame_checksum(buffer_ + 2, msg_length + 1);
                    
                    if (ck.byte1 == buffer_[packet_size_ - 2] &&
                        ck.byte2 == buffer_[packet_size_ - 1]) {
                        result.valid = true;
                        result.msg_id = msg_id_;
                        result.msg_len = static_cast<uint8_t>(msg_length);
                        result.msg_data = buffer_ + BASIC_FRAME_HEADER_SIZE;
                    }
                    
                    state_ = BasicFrameParserState::LookingForStart1;
                }
                break;
        }
        
        return result;
    }
    
    /**
     * Parse a buffer of bytes
     */
    BasicFrameMsgInfo parse_buffer(const uint8_t* data, size_t data_size, size_t& r_loc) {
        BasicFrameMsgInfo result;
        
        while (r_loc < data_size) {
            result = parse_byte(data[r_loc]);
            r_loc++;
            if (result.valid) {
                return result;
            }
        }
        
        return result;
    }
    
private:
    BasicFrameParserState state_;
    uint8_t* buffer_;
    size_t buffer_max_size_;
    size_t buffer_index_;
    size_t packet_size_;
    uint8_t msg_id_;
    MsgLengthCallback get_msg_length_;
};

/*===========================================================================
 * Static Helper Functions
 *===========================================================================*/

/**
 * Encode a message directly into a buffer
 * Returns the number of bytes written, or 0 on failure
 */
inline size_t basic_frame_encode(uint8_t* buffer, size_t buffer_size,
                                  uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    size_t total_size = BASIC_FRAME_OVERHEAD + msg_size;
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = BASIC_FRAME_START_BYTE1;
    buffer[1] = BASIC_FRAME_START_BYTE2;
    buffer[2] = msg_id;
    
    if (msg_size > 0 && msg != nullptr) {
        std::memcpy(buffer + BASIC_FRAME_HEADER_SIZE, msg, msg_size);
    }
    
    BasicFrameChecksum ck = basic_frame_checksum(buffer + 2, msg_size + 1);
    buffer[BASIC_FRAME_HEADER_SIZE + msg_size] = ck.byte1;
    buffer[BASIC_FRAME_HEADER_SIZE + msg_size + 1] = ck.byte2;
    
    return total_size;
}

/**
 * Validate a complete packet in a buffer
 */
inline BasicFrameMsgInfo basic_frame_validate_packet(const uint8_t* buffer, size_t length) {
    BasicFrameMsgInfo result;
    
    if (length < BASIC_FRAME_OVERHEAD) {
        return result;
    }
    
    if (buffer[0] != BASIC_FRAME_START_BYTE1 || buffer[1] != BASIC_FRAME_START_BYTE2) {
        return result;
    }
    
    size_t msg_length = length - BASIC_FRAME_OVERHEAD;
    
    BasicFrameChecksum ck = basic_frame_checksum(buffer + 2, msg_length + 1);
    if (ck.byte1 == buffer[length - 2] && ck.byte2 == buffer[length - 1]) {
        result.valid = true;
        result.msg_id = buffer[2];
        result.msg_len = static_cast<uint8_t>(msg_length);
        result.msg_data = const_cast<uint8_t*>(buffer + BASIC_FRAME_HEADER_SIZE);
    }
    
    return result;
}

/*===========================================================================
 * Message Helper Template
 *===========================================================================*/

/**
 * Template helper for message encoding/decoding
 */
template<typename T, uint8_t MsgId, size_t MsgSize>
struct BasicFrameMessageHelper {
    static constexpr uint8_t MSG_ID = MsgId;
    static constexpr size_t MSG_SIZE = MsgSize;
    
    static bool encode(BasicFrameEncodeBuffer& buf, const T& msg) {
        return buf.encode(MSG_ID, &msg, MSG_SIZE);
    }
    
    static T* reserve(BasicFrameEncodeBuffer& buf) {
        return reinterpret_cast<T*>(buf.reserve(MSG_ID, MSG_SIZE));
    }
    
    static bool finish(BasicFrameEncodeBuffer& buf) {
        return buf.finish();
    }
    
    static T get(const BasicFrameMsgInfo& info) {
        return *reinterpret_cast<T*>(info.msg_data);
    }
    
    static T* get_ref(const BasicFrameMsgInfo& info) {
        return reinterpret_cast<T*>(info.msg_data);
    }
};

}  // namespace StructFrame
