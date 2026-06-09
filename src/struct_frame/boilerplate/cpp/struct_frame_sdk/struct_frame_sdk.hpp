// Struct Frame SDK Client for C++
// Header-only, zero heap allocation, zero virtual dispatch implementation.
//
// All internal state is preallocated. Incoming bytes are automatically
// parsed and dispatched to registered subscribers with no dynamic memory use.
// The frame profile Config and message-info callback are compile-time template
// parameters — all parse/encode calls are fully inlined with no vtable overhead.

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <new>
#include <type_traits>

#include "transport.hpp"

namespace structframe {
struct MessageInfo;

namespace sdk {

// ============================================================================
// IStructFrameSdk — non-template base used by SubscriptionHandle
// ============================================================================

class IStructFrameSdk {
 public:
  virtual ~IStructFrameSdk() = default;
  virtual void FreeSlot(size_t idx) = 0;
};

// ============================================================================
// SubscriptionHandle — RAII, move-only subscription token
// ============================================================================

/**
 * Returned by StructFrameSdk::subscribe(). Auto-unsubscribes on destruction.
 * Must be kept alive (as a class member or named local) for as long as the
 * subscription is needed.
 */
class SubscriptionHandle {
 public:
  static constexpr size_t INVALID = ~size_t{0};

  SubscriptionHandle() : sdk_(nullptr), slot_idx_(INVALID) {}
  SubscriptionHandle(IStructFrameSdk* sdk, size_t idx) : sdk_(sdk), slot_idx_(idx) {}

  ~SubscriptionHandle() { Unsubscribe(); }

  SubscriptionHandle(SubscriptionHandle&& other) noexcept : sdk_(other.sdk_), slot_idx_(other.slot_idx_) {
    other.sdk_ = nullptr;
    other.slot_idx_ = INVALID;
  }

  SubscriptionHandle& operator=(SubscriptionHandle&& other) noexcept {
    if (this != &other) {
      Unsubscribe();
      sdk_ = other.sdk_;
      slot_idx_ = other.slot_idx_;
      other.sdk_ = nullptr;
      other.slot_idx_ = INVALID;
    }
    return *this;
  }

  SubscriptionHandle(const SubscriptionHandle&) = delete;
  SubscriptionHandle& operator=(const SubscriptionHandle&) = delete;

  void Unsubscribe() {
    if (sdk_ != nullptr && slot_idx_ != INVALID) {
      sdk_->FreeSlot(slot_idx_);
      sdk_ = nullptr;
      slot_idx_ = INVALID;
    }
  }

  bool IsActive() const { return sdk_ != nullptr && slot_idx_ != INVALID; }

 private:
  IStructFrameSdk* sdk_;
  size_t slot_idx_;
};

// ============================================================================
// StructFrameSdkConfig
// ============================================================================

struct StructFrameSdkConfig {
  Transport* transport = nullptr;
};

// ============================================================================
// StructFrameSdkT — main SDK (zero heap, zero virtual dispatch, auto-dispatch)
// ============================================================================

/**
 * Struct Frame SDK client.
 *
 * All internal state is stack/member allocated — no dynamic memory.
 * Incoming bytes from the transport are automatically parsed and dispatched
 * to all matching subscribers without any explicit user action.
 *
 * The frame profile Config is a compile-time template parameter, so all
 * parse/encode calls are fully inlined with zero virtual dispatch overhead.
 *
 * Template parameters (adjust for your platform):
 *   Config           — frame profile configuration (e.g., ProfileStandardConfig)
 *   MaxBuffer        — receive buffer size in bytes                    (default 8192)
 *   MaxSubscriptions — maximum concurrent subscriptions               (default 32)
 *   MaxFrameSize     — maximum outgoing frame size in bytes            (default 512)
 *   MaxCallableSize  — max size of a captured lambda/functor           (default 64)
 *                      Exceeding this causes a compile-time error.
 *
 * Usage:
 *   // With function pointer:
 *   // Custom sizes for embedded:
 *   StructFrameSdkT<ProfileSensorConfig, 2048, 8, 256, 32> sdk(t, &get_msg_info);
 */
template <typename Config, size_t MaxBuffer = 8192, size_t MaxSubscriptions = 32, size_t MaxFrameSize = 512,
          size_t MaxCallableSize = 64>
class StructFrameSdkT : public IStructFrameSdk {
 public:
  using MessageInfoFn = structframe::MessageInfo (*)(uint16_t);

  // Non-copyable, non-movable: internal buffer addresses must remain stable.
  StructFrameSdkT(const StructFrameSdkT&) = delete;
  StructFrameSdkT& operator=(const StructFrameSdkT&) = delete;
  StructFrameSdkT(StructFrameSdkT&&) = delete;
  StructFrameSdkT& operator=(StructFrameSdkT&&) = delete;

  /**
   * Construct the SDK with a transport and message-info callback.
   *
   * @param transport  Transport for sending/receiving data (may be nullptr for feed-only use)
   * @param get_message_info  Callable: MessageInfo(uint16_t msg_id) — returns
   *                          size/magic info for a given message ID
   */
  StructFrameSdkT(Transport* transport, MessageInfoFn get_message_info)
      : transport_(transport), get_message_info_(get_message_info), buffer_len_(0) {
    for (size_t i = 0; i < MaxSubscriptions; ++i) {
      slots_[i].active = false;
    }
    if (transport_ != nullptr) {
      transport_->OnData(&StructFrameSdkT::DataCallbackWrapper, this);
      transport_->OnError(&StructFrameSdkT::ErrorCallbackWrapper, this);
      transport_->OnClose(&StructFrameSdkT::CloseCallbackWrapper, this);
    }
  }

  /**
   * Construct with a StructFrameSdkConfig (transport only; get_message_info still required).
   */
  StructFrameSdkT(const StructFrameSdkConfig& config, MessageInfoFn get_message_info)
      : StructFrameSdkT(config.transport, get_message_info) {}

  ~StructFrameSdkT() {
    for (size_t i = 0; i < MaxSubscriptions; ++i) {
      DestroySlot(i);
    }
  }

  // -----------------------------------------------------------------------
  // Transport lifecycle
  // -----------------------------------------------------------------------

  void Connect() {
    if (transport_ != nullptr) transport_->Connect();
  }

  void Disconnect() {
    if (transport_ != nullptr) transport_->Disconnect();
  }

  bool IsConnected() const { return transport_ != nullptr && transport_->IsConnected(); }

  // -----------------------------------------------------------------------
  // Subscribe
  // -----------------------------------------------------------------------

  /**
   * Subscribe to messages of type TMessage identified by msgId.
   *
   * The callback is stored inline inside the SDK — no heap allocation.
   * Callback signature: void(const TMessage&, uint16_t msgId)
   *
   * Returns a SubscriptionHandle (RAII). Keep it alive as long as the
   * subscription is needed; destroying it auto-unsubscribes.
   *
   * Lambdas that capture more than MaxCallableSize bytes trigger a
   * static_assert at compile time.
   */
  template <typename TMessage, typename Callable>
  SubscriptionHandle subscribe(uint16_t msgId, Callable&& callback) {
    static_assert(sizeof(Callable) <= MaxCallableSize,
                  "Captured lambda/functor exceeds MaxCallableSize. "
                  "Reduce captures or increase MaxCallableSize template parameter.");
    static_assert(alignof(Callable) <= alignof(std::max_align_t),
                  "Callable alignment requirement exceeds max_align_t.");

    const size_t idx = FindFreeSlot();
    if (idx == SubscriptionHandle::INVALID) {
      return SubscriptionHandle();  // all slots full
    }

    Slot& slot = slots_[idx];
    slot.active = true;
    slot.msg_id = msgId;

    // Placement-construct the callable into the inline storage.
    new (slot.callable_storage) Callable(static_cast<Callable&&>(callback));

    slot.dispatch_bytes = [](const uint8_t* payload, size_t len, uint16_t id, void* ctx) {
      TMessage msg{};
      msg.deserialize(payload, len);
      (*static_cast<Callable*>(ctx))(msg, id);
    };

    slot.dispatch_typed = [](const void* msg, uint16_t id, void* ctx) {
      (*static_cast<Callable*>(ctx))(*static_cast<const TMessage*>(msg), id);
    };

    slot.destroy_fn = [](void* ctx) { static_cast<Callable*>(ctx)->~Callable(); };

    return SubscriptionHandle(this, idx);
  }

  /**
   * Subscribe with a plain function pointer (no capture needed).
   */
  template <typename TMessage>
  SubscriptionHandle subscribe(uint16_t msgId, void (*callback)(const TMessage&, uint16_t)) {
    return subscribe<TMessage>(msgId, [callback](const TMessage& msg, uint16_t id) { callback(msg, id); });
  }

  /**
   * Subscribe to every complete frame as raw FrameMsgInfo.
   *
   * Callback signature: void(const FrameMsgInfo&)
   */
  template <typename Callable>
  SubscriptionHandle subscribeFrameInfo(Callable&& callback) {
    static_assert(sizeof(Callable) <= MaxCallableSize,
                  "Captured lambda/functor exceeds MaxCallableSize. "
                  "Reduce captures or increase MaxCallableSize template parameter.");
    static_assert(alignof(Callable) <= alignof(std::max_align_t),
                  "Callable alignment requirement exceeds max_align_t.");

    const size_t idx = FindFreeSlot();
    if (idx == SubscriptionHandle::INVALID) {
      return SubscriptionHandle();
    }

    Slot& slot = slots_[idx];
    slot.active = true;
    slot.msg_id = 0;
    slot.match_all = true;

    new (slot.callable_storage) Callable(static_cast<Callable&&>(callback));

    slot.dispatch_bytes = nullptr;
    slot.dispatch_typed = nullptr;
    slot.dispatch_frame_info = [](const FrameMsgInfo& frame, void* ctx) { (*static_cast<Callable*>(ctx))(frame); };

    slot.destroy_fn = [](void* ctx) { static_cast<Callable*>(ctx)->~Callable(); };

    return SubscriptionHandle(this, idx);
  }

  // -----------------------------------------------------------------------
  // Notify (direct dispatch, bypasses transport/parser)
  // -----------------------------------------------------------------------

  /**
   * Directly dispatch a pre-deserialized message to all matching subscribers.
   * Useful for injecting messages in tests or for internally generated events.
   */
  template <typename TMessage>
  void NotifyObservers(uint16_t msgId, const TMessage& message) {
    for (size_t i = 0; i < MaxSubscriptions; ++i) {
      Slot& slot = slots_[i];
      if (slot.active && slot.msg_id == msgId && slot.dispatch_typed != nullptr) {
        slot.dispatch_typed(&message, msgId, slot.callable_storage);
      }
    }
  }

  // -----------------------------------------------------------------------
  // Feed (explicit parse trigger)
  // -----------------------------------------------------------------------

  /**
   * Feed raw bytes into the receive buffer and parse/dispatch any complete
   * frames. Called automatically via the transport data callback; can also
   * be called directly for testing or non-transport use.
   */
  void Feed(const uint8_t* data, size_t length) {
    if (data == nullptr || length == 0) return;
    if (buffer_len_ + length > MaxBuffer) {
      buffer_len_ = 0;  // overflow: drop buffered data
    }
    std::memcpy(buffer_ + buffer_len_, data, length);
    buffer_len_ += length;
    ParseBuffer();
  }

  // -----------------------------------------------------------------------
  // Send
  // -----------------------------------------------------------------------

  /**
   * Serialize and send a typed message through the transport.
   * Uses FrameEncoderWithCrc or FrameEncoderMinimal based on the profile
   * — fully inlined, no virtual dispatch.
   * Returns true if the frame was successfully handed to the transport.
   */
  template <typename TMessage>
  bool Send(const TMessage& message) {
    if (transport_ == nullptr) return false;
    uint8_t frame_buf[MaxFrameSize];
    size_t framedLen;

    if constexpr (Config::has_length || Config::has_crc) {
      framedLen = structframe::FrameEncoderWithCrc<Config>::encode(frame_buf, MaxFrameSize, message);
    } else {
      framedLen = structframe::FrameEncoderMinimal<Config>::encode(frame_buf, MaxFrameSize, message);
    }

    if (framedLen == 0) return false;
    transport_->Send(frame_buf, framedLen);
    return true;
  }

  /**
   * Frame and send a pre-serialized payload through the transport.
   * Uses an internal raw-frame encoder — fully inlined, no virtual dispatch.
   * Returns true on success.
   */
  bool SendRaw(uint16_t msgId, const uint8_t* data, size_t dataLen) {
    if (transport_ == nullptr) return false;
    uint8_t frame_buf[MaxFrameSize];
    const size_t framedLen = EncodeRawFrame(msgId, data, dataLen, frame_buf, MaxFrameSize, get_message_info_);
    if (framedLen == 0) return false;
    transport_->Send(frame_buf, framedLen);
    return true;
  }

  /**
   * Forward a parsed FrameMsgInfo through this SDK's transport.
   *
   * This is useful when bridging SDK instances with different profiles:
   * subscribeFrameInfo on one side, then Send(frame_info) on the other side.
   */
  bool Send(const FrameMsgInfo& frame_info) {
    if (transport_ == nullptr) return false;
    if (!frame_info.valid || frame_info.msg_data == nullptr) return false;
    return SendRaw(frame_info.msg_id, frame_info.msg_data, frame_info.msg_len);
  }

  /**
   * Directly forward a complete frame through this SDK's transport.
   *
   * This bypasses re-encoding and assumes the source and destination use
   * the same frame profile.
   */
  bool SendDirect(const FrameMsgInfo& frame_info) {
    if (transport_ == nullptr) return false;
    if (frame_info.frame_data != nullptr && frame_info.frame_size > 0) {
      transport_->Send(frame_info.frame_data, frame_info.frame_size);
      return true;
    }
    return false;
  }

  // IStructFrameSdk
  void FreeSlot(size_t idx) override {
    if (idx < MaxSubscriptions) DestroySlot(idx);
  }

 private:
  struct Slot {
    bool active = false;
    uint16_t msg_id = 0;
    bool match_all = false;
    void (*dispatch_bytes)(const uint8_t* payload, size_t len, uint16_t msgId, void* ctx) = nullptr;
    void (*dispatch_typed)(const void* msg, uint16_t msgId, void* ctx) = nullptr;
    void (*dispatch_frame_info)(const FrameMsgInfo& frame, void* ctx) = nullptr;
    void (*destroy_fn)(void* ctx) = nullptr;
    alignas(alignof(std::max_align_t)) uint8_t callable_storage[MaxCallableSize];
  };

  Transport* transport_;
  MessageInfoFn get_message_info_;
  Slot slots_[MaxSubscriptions];
  uint8_t buffer_[MaxBuffer];
  size_t buffer_len_;

  // -----------------------------------------------------------------------
  // Internal helpers
  // -----------------------------------------------------------------------

  static size_t EncodeRawFrame(uint16_t msgId, const uint8_t* data, size_t dataLen, uint8_t* output,
                               size_t outputMaxLen, MessageInfoFn get_message_info) {
    if (get_message_info == nullptr) return 0;

    const auto info = get_message_info(msgId);
    if (!info.valid) return 0;

    const size_t total = Config::overhead + dataLen;
    if (outputMaxLen < total || dataLen > Config::max_payload) return 0;

    size_t idx = 0;

    if constexpr (Config::num_start_bytes >= 1) output[idx++] = Config::computed_start_byte1();
    if constexpr (Config::num_start_bytes >= 2) output[idx++] = Config::computed_start_byte2();

    const size_t crc_start = idx;

    if constexpr (Config::has_seq) output[idx++] = 0;
    if constexpr (Config::has_sys_id) output[idx++] = 0;
    if constexpr (Config::has_comp_id) output[idx++] = 0;

    if constexpr (Config::has_length) {
      if constexpr (Config::length_bytes == 1) {
        output[idx++] = static_cast<uint8_t>(dataLen & 0xFF);
      } else {
        output[idx++] = static_cast<uint8_t>(dataLen & 0xFF);
        output[idx++] = static_cast<uint8_t>((dataLen >> 8) & 0xFF);
      }
    }

    if constexpr (Config::has_pkg_id) output[idx++] = static_cast<uint8_t>((msgId >> 8) & 0xFF);
    output[idx++] = static_cast<uint8_t>(msgId & 0xFF);

    std::memcpy(output + idx, data, dataLen);
    idx += dataLen;

    if constexpr (Config::has_crc) {
      size_t crc_len = idx - crc_start;
      size_t effective_base = crc_len;
      if constexpr (Config::has_length) {
        if (info.base_size <= dataLen) {
          effective_base = (crc_len - dataLen) + info.base_size;
        }
      }
      auto ck =
          structframe::fletcher_checksum_ext(output + crc_start, effective_base, crc_len, info.magic1, info.magic2);
      output[idx++] = ck.byte1;
      output[idx++] = ck.byte2;
    }

    return idx;
  }

  size_t FindFreeSlot() const {
    for (size_t i = 0; i < MaxSubscriptions; ++i) {
      if (!slots_[i].active) return i;
    }
    return SubscriptionHandle::INVALID;
  }

  void DestroySlot(size_t idx) {
    Slot& slot = slots_[idx];
    if (slot.active && slot.destroy_fn != nullptr) {
      slot.destroy_fn(slot.callable_storage);
    }
    slot.active = false;
    slot.match_all = false;
    slot.dispatch_bytes = nullptr;
    slot.dispatch_typed = nullptr;
    slot.dispatch_frame_info = nullptr;
    slot.destroy_fn = nullptr;
  }

  void ParseBuffer() {
    while (buffer_len_ > 0) {
      FrameMsgInfo result;

      // Compile-time dispatch: no virtual call, fully inlined.
      if constexpr (Config::has_length || Config::has_crc) {
        result = structframe::BufferParserWithCrc<Config>::parse(buffer_, buffer_len_, get_message_info_);
      } else {
        result = structframe::BufferParserMinimal<Config>::parse(buffer_, buffer_len_, get_message_info_);
      }

      if (result.frame_size == 0) break;

      // Auto-dispatch: notify raw-frame subscriptions for every complete
      // frame and typed subscriptions only for valid parsed messages.
      Dispatch(result);

      // Advance past the consumed frame.
      // frame_size is populated by all profile parsers; fall back to a
      // conservative estimate only if the parser does not set it.
      const size_t frameSize = result.frame_size > 0 ? result.frame_size : result.msg_len + 10;

      if (frameSize == 0 || frameSize > buffer_len_) {
        buffer_len_ = 0;  // safety guard: prevents infinite loop
        break;
      }
      std::memmove(buffer_, buffer_ + frameSize, buffer_len_ - frameSize);
      buffer_len_ -= frameSize;
    }
  }

  void Dispatch(const FrameMsgInfo& frame) {
    const uint16_t msg_id = frame.msg_id;
    for (size_t i = 0; i < MaxSubscriptions; ++i) {
      Slot& slot = slots_[i];
      if (!slot.active) {
        continue;
      }

      if (slot.dispatch_frame_info != nullptr && slot.match_all) {
        slot.dispatch_frame_info(frame, slot.callable_storage);
      }

      if (frame.valid && !slot.match_all && slot.msg_id == msg_id && slot.dispatch_bytes != nullptr) {
        slot.dispatch_bytes(frame.msg_data, frame.msg_len, msg_id, slot.callable_storage);
      }
    }
  }

  static void DataCallbackWrapper(const uint8_t* data, size_t length, void* user_data) {
    static_cast<StructFrameSdkT*>(user_data)->Feed(data, length);
  }

  static void ErrorCallbackWrapper(const char*, void*) {}

  static void CloseCallbackWrapper(void* user_data) { static_cast<StructFrameSdkT*>(user_data)->buffer_len_ = 0; }
};

}  // namespace sdk
}  // namespace structframe
