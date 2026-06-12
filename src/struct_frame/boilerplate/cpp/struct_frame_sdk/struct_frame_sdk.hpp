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
#include <utility>

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
 *
 * Discarding without assigning to a named variable immediately unsubscribes —
 * mark the return type [[nodiscard]] at call site to catch this mistake at
 * compile time. The class itself is [[nodiscard]] to trigger a warning.
 */
class [[nodiscard]] SubscriptionHandle {
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
// StructFrameSdkConfigT
// ============================================================================

template <typename TransportT>
struct StructFrameSdkConfigT {
  TransportT* transport = nullptr;
};

enum class SendError : uint8_t {
  None = 0,
  NoTransport,   ///< transport_ is null
  EncodeFailed,  ///< frame did not fit in MaxFrameSize (or encode returned 0)
  PartialWrite,  ///< transport wrote fewer bytes than the encoded frame
};

struct [[nodiscard]] SendResult {
  bool success = false;
  size_t attempted_bytes = 0;
  size_t bytes_written = 0;
  SendError error = SendError::None;

  explicit operator bool() const { return success; }
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
 *   TransportT       — concrete transport type used by this SDK instance
 *
 * Usage:
 *   // Concrete transport type selected at compile time:
 *   StructFrameSdkT<ProfileSensorConfig, 2048, 8, 256, 32, MyTransport>
 *       sdk(&transport, &get_msg_info);
 *
 * Thread safety:
 *   This class is NOT thread-safe. All methods — including Feed(), Send(),
 *   subscribe(), and subscribeFrameInfo() — must be called from a single
 *   thread or protected by an external mutex.
 *
 *   The transport data callback (registered in the constructor) calls Feed()
 *   on whatever thread the transport fires it. If that is a different thread
 *   from the one calling Send() or subscribe(), external synchronisation is
 *   required.
 *
 *   Subscribe/unsubscribe IS reentrant with respect to dispatch: it is safe
 *   to call subscribe() or let a SubscriptionHandle go out of scope inside a
 *   subscriber callback, because the slot array is never compacted during
 *   dispatch.
 */
template <typename Config, size_t MaxBuffer = 8192, size_t MaxSubscriptions = 32, size_t MaxFrameSize = 512,
          size_t MaxCallableSize = 64, typename TransportT = BaseTransport>
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
  StructFrameSdkT(TransportT* transport, MessageInfoFn get_message_info)
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
  * Construct with a StructFrameSdkConfigT (transport only; get_message_info still required).
   */
  StructFrameSdkT(const StructFrameSdkConfigT<TransportT>& config, MessageInfoFn get_message_info)
      : StructFrameSdkT(config.transport, get_message_info) {}

  ~StructFrameSdkT() {
    // Unregister transport callbacks first so the transport cannot call
    // into a partially-destroyed object after this destructor returns.
    if (transport_ != nullptr) {
      transport_->OnData(nullptr, nullptr);
      transport_->OnError(nullptr, nullptr);
      transport_->OnClose(nullptr, nullptr);
    }
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
  [[nodiscard]] SubscriptionHandle subscribe(uint16_t msgId, Callable&& callback) {
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
    new (slot.callable_storage) Callable(std::forward<Callable>(callback));

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
  [[nodiscard]] SubscriptionHandle subscribe(uint16_t msgId, void (*callback)(const TMessage&, uint16_t)) {
    return subscribe<TMessage>(msgId, [callback](const TMessage& msg, uint16_t id) { callback(msg, id); });
  }

  /**
   * Subscribe to every complete frame as raw FrameMsgInfo.
   *
   * Callback signature: void(const FrameMsgInfo&)
   */
  template <typename Callable>
  [[nodiscard]] SubscriptionHandle subscribeFrameInfo(Callable&& callback) {
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

    new (slot.callable_storage) Callable(std::forward<Callable>(callback));

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
      buffer_len_ = 0;  // overflow: drop buffered partial frame
    }
    // Clamp to available space — prevents OOB write when length > MaxBuffer
    const size_t to_copy = length < (MaxBuffer - buffer_len_) ? length : (MaxBuffer - buffer_len_);
    std::memcpy(buffer_ + buffer_len_, data, to_copy);
    buffer_len_ += to_copy;
    ParseBuffer();
  }

  // -----------------------------------------------------------------------
  // Send
  // -----------------------------------------------------------------------

  /**
   * Serialize and send a typed message through the transport.
   * Uses FrameEncoderWithCrc or FrameEncoderMinimal based on the profile
   * — fully inlined, no virtual dispatch.
   * Returns verbose send result with attempted and actual bytes written.
   */
  template <typename TMessage>
  SendResult Send(const TMessage& message) {
    // For fixed-size messages the frame size is known at compile time.
    // Nested if constexpr is required because accessing T::IS_VARIABLE directly
    // in a compound expression is a hard error when IS_VARIABLE doesn't exist.
    if constexpr (!IsVariableMessage<TMessage>()) {
      static_assert(Config::overhead + TMessage::MAX_SIZE <= MaxFrameSize,
                    "Encoded frame exceeds MaxFrameSize. "
                    "Increase MaxFrameSize template parameter or reduce the message size.");
    }
    if (transport_ == nullptr) return {false, 0, 0, SendError::NoTransport};
    uint8_t frame_buf[MaxFrameSize];
    size_t framedLen;

    if constexpr (Config::has_length || Config::has_crc) {
      framedLen = structframe::FrameEncoderWithCrc<Config>::encode(frame_buf, MaxFrameSize, message);
    } else {
      framedLen = structframe::FrameEncoderMinimal<Config>::encode(frame_buf, MaxFrameSize, message);
    }

    if (framedLen == 0) return {false, 0, 0, SendError::EncodeFailed};
    const size_t written = transport_->Send(frame_buf, framedLen);
    const bool ok = (written == framedLen);
    return {ok, framedLen, written, ok ? SendError::None : SendError::PartialWrite};
  }

  /**
   * Frame and send a pre-serialized payload through the transport.
   * Uses an internal raw-frame encoder — fully inlined, no virtual dispatch.
   * Returns verbose send result with attempted and actual bytes written.
   */
  SendResult SendRaw(uint16_t msgId, const uint8_t* data, size_t dataLen) {
    if (transport_ == nullptr) return {};
    uint8_t frame_buf[MaxFrameSize];
    const size_t framedLen = EncodeRawFrame(msgId, data, dataLen, frame_buf, MaxFrameSize, get_message_info_);
    if (framedLen == 0) return {};
    const size_t written = transport_->Send(frame_buf, framedLen);
    return SendResult{written == framedLen, framedLen, written};
  }

  /**
   * Forward a parsed FrameMsgInfo through this SDK's transport.
   *
   * This is useful when bridging SDK instances with different profiles:
   * subscribeFrameInfo on one side, then Send(frame_info) on the other side.
   */
  SendResult Send(const FrameMsgInfo& frame_info) {
    if (transport_ == nullptr) return {};
    if (!frame_info.valid || frame_info.msg_data == nullptr) return {};
    return SendRaw(frame_info.msg_id, frame_info.msg_data, frame_info.msg_len);
  }

  /**
   * Directly forward a complete frame through this SDK's transport.
   *
   * This bypasses re-encoding and assumes the source and destination use
   * the same frame profile.
   */
  SendResult SendDirect(const FrameMsgInfo& frame_info) {
    if (transport_ == nullptr) return {};
    if (frame_info.frame_data != nullptr && frame_info.frame_size > 0) {
      const size_t written = transport_->Send(frame_info.frame_data, frame_info.frame_size);
      return SendResult{written == frame_info.frame_size, frame_info.frame_size, written};
    }
    return {};
  }

  // -----------------------------------------------------------------------
  // Transport event callbacks
  // -----------------------------------------------------------------------

  /**
   * Register a callback to be invoked when the transport reports an error.
   * Signature: void(const char* message, void* ctx)
   */
  void SetErrorCallback(void (*fn)(const char*, void*), void* ctx = nullptr) {
    error_fn_ = fn;
    error_ctx_ = ctx;
  }

  /**
   * Register a callback to be invoked when the transport closes.
   * Signature: void(void* ctx)
   */
  void SetCloseCallback(void (*fn)(void*), void* ctx = nullptr) {
    close_fn_ = fn;
    close_ctx_ = ctx;
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

  TransportT* transport_;
  MessageInfoFn get_message_info_;
  Slot slots_[MaxSubscriptions];
  uint8_t buffer_[MaxBuffer];
  size_t buffer_len_;
  void (*error_fn_)(const char*, void*) = nullptr;
  void* error_ctx_ = nullptr;
  void (*close_fn_)(void*) = nullptr;
  void* close_ctx_ = nullptr;

  // -----------------------------------------------------------------------
  // Internal helpers
  // -----------------------------------------------------------------------

  template <typename T>
  static constexpr bool IsVariableMessage() {
    if constexpr (requires { T::IS_VARIABLE; }) {
      return T::IS_VARIABLE;
    } else {
      return false;
    }
  }

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
    size_t offset = 0;

    while (offset < buffer_len_) {
      const size_t remaining = buffer_len_ - offset;
      FrameMsgInfo result;

      // Compile-time dispatch: no virtual call, fully inlined.
      if constexpr (Config::has_length || Config::has_crc) {
        result = structframe::BufferParserWithCrc<Config>::parse(buffer_ + offset, remaining, get_message_info_);
      } else {
        result = structframe::BufferParserMinimal<Config>::parse(buffer_ + offset, remaining, get_message_info_);
      }

      if (result.frame_size > 0) {
        // Complete frame (valid or CRC-failed) — dispatch and advance.
        Dispatch(result);
        offset += result.frame_size;
      } else if (result.status == FrameMsgStatus::WaitingForStart) {
        // Head byte is not a frame start — skip forward to the next one (C2: memchr).
        if constexpr (Config::num_start_bytes >= 1) {
          const size_t scan_start = offset + 1;
          if (scan_start < buffer_len_) {
            const void* p = std::memchr(buffer_ + scan_start,
                                        static_cast<int>(Config::computed_start_byte1()),
                                        buffer_len_ - scan_start);
            offset = p ? static_cast<size_t>(static_cast<const uint8_t*>(p) - buffer_) : buffer_len_;
          } else {
            offset = buffer_len_;
          }
        } else {
          // No start bytes in this profile — cannot resync; discard all
          offset = buffer_len_;
          break;
        }
      } else {
        // Collecting — frame is incomplete; need more data from next Feed()
        break;
      }
    }

    // Single compact at the end (C1: O(n) instead of per-frame memmove).
    if (offset > 0) {
      if (offset < buffer_len_) {
        std::memmove(buffer_, buffer_ + offset, buffer_len_ - offset);
      }
      buffer_len_ -= offset;
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

  static void ErrorCallbackWrapper(const char* msg, void* user_data) {
    auto* self = static_cast<StructFrameSdkT*>(user_data);
    if (self->error_fn_ != nullptr) self->error_fn_(msg, self->error_ctx_);
  }

  static void CloseCallbackWrapper(void* user_data) {
    auto* self = static_cast<StructFrameSdkT*>(user_data);
    self->buffer_len_ = 0;
    if (self->close_fn_ != nullptr) self->close_fn_(self->close_ctx_);
  }
};

}  // namespace sdk
}  // namespace structframe
