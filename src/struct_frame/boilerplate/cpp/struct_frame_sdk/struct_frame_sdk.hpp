// Struct Frame SDK Client for C++
// Header-only, zero heap allocation implementation.
//
// All internal state is preallocated. Incoming bytes are automatically
// parsed and dispatched to registered subscribers with no dynamic memory use.

#pragma once

#include "transport.hpp"
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <new>

namespace structframe {
namespace sdk {

// ============================================================================
// frame_parser interface
// ============================================================================

/**
 * Frame parser interface implemented by generated frame parsers.
 */
class frame_parser {
public:
    virtual ~frame_parser() = default;

    /**
     * Parse a buffer and return the first valid frame found.
     * Returns FrameMsgInfo with valid=true on success; valid=false if no
     * complete frame is present yet.
     */
    virtual structframe::FrameMsgInfo parse(const uint8_t* data, size_t length) = 0;

    /**
     * Frame (serialize + wrap) a payload for sending.
     * @return Number of bytes written to output, 0 on failure.
     */
    virtual size_t frame(uint8_t msgId, const uint8_t* data, size_t dataLen,
                         uint8_t* output, size_t outputMaxLen) = 0;
};

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

    SubscriptionHandle(SubscriptionHandle&& other) noexcept
        : sdk_(other.sdk_), slot_idx_(other.slot_idx_) {
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
    frame_parser* parser = nullptr;
};

// ============================================================================
// StructFrameSdkT — main SDK (zero heap, auto-dispatch)
// ============================================================================

/**
 * Struct Frame SDK client.
 *
 * All internal state is stack/member allocated — no dynamic memory.
 * Incoming bytes from the transport are automatically parsed and dispatched
 * to all matching subscribers without any explicit user action.
 *
 * Template parameters (adjust for your platform):
 *   MaxBuffer        — receive ring buffer size in bytes          (default 8192)
 *   MaxSubscriptions — maximum concurrent subscriptions           (default 32)
 *   MaxFrameSize     — maximum outgoing frame size in bytes       (default 512)
 *   MaxCallableSize  — max size of a captured lambda/functor      (default 64)
 *                      Exceeding this causes a compile-time error.
 *
 * Usage:
 *   StructFrameSdk sdk(config);          // default sizes
 *   StructFrameSdkT<4096,8,256> sdk(c); // custom sizes
 */
template<
    size_t MaxBuffer        = 8192,
    size_t MaxSubscriptions = 32,
    size_t MaxFrameSize     = 512,
    size_t MaxCallableSize  = 64
>
class StructFrameSdkT : public IStructFrameSdk {
public:
    // Non-copyable, non-movable: internal buffer addresses must remain stable.
    StructFrameSdkT(const StructFrameSdkT&) = delete;
    StructFrameSdkT& operator=(const StructFrameSdkT&) = delete;
    StructFrameSdkT(StructFrameSdkT&&) = delete;
    StructFrameSdkT& operator=(StructFrameSdkT&&) = delete;

    explicit StructFrameSdkT(const StructFrameSdkConfig& config)
        : transport_(config.transport),
          parser_(config.parser),
          buffer_len_(0) {
        for (size_t i = 0; i < MaxSubscriptions; ++i) {
            slots_[i].active = false;
        }
        if (transport_ != nullptr) {
            transport_->OnData(&StructFrameSdkT::DataCallbackWrapper, this);
            transport_->OnError(&StructFrameSdkT::ErrorCallbackWrapper, this);
            transport_->OnClose(&StructFrameSdkT::CloseCallbackWrapper, this);
        }
    }

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

    bool IsConnected() const {
        return transport_ != nullptr && transport_->IsConnected();
    }

    // -----------------------------------------------------------------------
    // Subscribe
    // -----------------------------------------------------------------------

    /**
     * Subscribe to messages of type TMessage identified by msgId.
     *
     * The callback is stored inline inside the SDK — no heap allocation.
     * Callback signature: void(const TMessage&, uint8_t msgId)
     *
     * Returns a SubscriptionHandle (RAII). Keep it alive as long as the
     * subscription is needed; destroying it auto-unsubscribes.
     *
     * Lambdas that capture more than MaxCallableSize bytes trigger a
     * static_assert at compile time.
     */
    template<typename TMessage, typename Callable>
    SubscriptionHandle subscribe(uint8_t msgId, Callable&& callback) {
        static_assert(sizeof(Callable) <= MaxCallableSize,
            "Captured lambda/functor exceeds MaxCallableSize. "
            "Reduce captures or increase MaxCallableSize template parameter.");
        static_assert(alignof(Callable) <= alignof(std::max_align_t),
            "Callable alignment requirement exceeds max_align_t.");

        const size_t idx = FindFreeSlot();
        if (idx == SubscriptionHandle::INVALID) {
            return SubscriptionHandle(); // all slots full
        }

        Slot& slot = slots_[idx];
        slot.active  = true;
        slot.msg_id  = msgId;

        // Placement-construct the callable into the inline storage.
        new (slot.callable_storage) Callable(static_cast<Callable&&>(callback));

        // Non-capturing lambdas that reference TMessage/Callable as template
        // parameters are implicitly convertible to plain function pointers.

        slot.dispatch_bytes = [](const uint8_t* payload, size_t len,
                                 uint8_t id, void* ctx) {
            TMessage msg{};
            msg.deserialize(payload, len);
            (*static_cast<Callable*>(ctx))(msg, id);
        };

        slot.dispatch_typed = [](const void* msg, uint8_t id, void* ctx) {
            (*static_cast<Callable*>(ctx))(
                *static_cast<const TMessage*>(msg), id);
        };

        slot.destroy_fn = [](void* ctx) {
            static_cast<Callable*>(ctx)->~Callable();
        };

        return SubscriptionHandle(this, idx);
    }

    /**
     * Subscribe with a plain function pointer (no capture needed).
     */
    template<typename TMessage>
    SubscriptionHandle subscribe(uint8_t msgId,
                                 void (*callback)(const TMessage&, uint8_t)) {
        return subscribe<TMessage>(msgId,
            [callback](const TMessage& msg, uint8_t id) { callback(msg, id); });
    }

    // -----------------------------------------------------------------------
    // Notify (direct dispatch, bypasses transport/parser)
    // -----------------------------------------------------------------------

    /**
     * Directly dispatch a pre-deserialized message to all matching subscribers.
     * Useful for injecting messages in tests or for internally generated events.
     */
    template<typename TMessage>
    void NotifyObservers(uint8_t msgId, const TMessage& message) {
        for (size_t i = 0; i < MaxSubscriptions; ++i) {
            Slot& slot = slots_[i];
            if (slot.active && slot.msg_id == msgId &&
                slot.dispatch_typed != nullptr) {
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
            buffer_len_ = 0; // overflow: drop buffered data
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
     * Returns true if the frame was successfully handed to the transport.
     */
    template<typename TMessage>
    bool Send(const TMessage& message) {
        uint8_t payload[TMessage::MAX_SIZE];
        message.serialize(payload);
        return SendRaw(static_cast<uint8_t>(TMessage::MSG_ID), payload,
                       TMessage::MAX_SIZE);
    }

    /**
     * Frame and send a pre-serialized payload through the transport.
     * Returns true on success.
     */
    bool SendRaw(uint8_t msgId, const uint8_t* data, size_t dataLen) {
        if (parser_ == nullptr || transport_ == nullptr) return false;
        uint8_t frame_buf[MaxFrameSize];
        const size_t framedLen = parser_->frame(msgId, data, dataLen,
                                                frame_buf, MaxFrameSize);
        if (framedLen == 0) return false;
        transport_->Send(frame_buf, framedLen);
        return true;
    }

    // IStructFrameSdk
    void FreeSlot(size_t idx) override {
        if (idx < MaxSubscriptions) DestroySlot(idx);
    }

private:
    struct Slot {
        bool active = false;
        uint8_t msg_id = 0;
        void (*dispatch_bytes)(const uint8_t* payload, size_t len,
                               uint8_t msgId, void* ctx) = nullptr;
        void (*dispatch_typed)(const void* msg,
                               uint8_t msgId, void* ctx)  = nullptr;
        void (*destroy_fn)(void* ctx)                      = nullptr;
        alignas(alignof(std::max_align_t))
            uint8_t callable_storage[MaxCallableSize];
    };

    Transport*   transport_;
    frame_parser* parser_;
    Slot         slots_[MaxSubscriptions];
    uint8_t      buffer_[MaxBuffer];
    size_t       buffer_len_;

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

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
        slot.active        = false;
        slot.dispatch_bytes = nullptr;
        slot.dispatch_typed = nullptr;
        slot.destroy_fn    = nullptr;
    }

    void ParseBuffer() {
        while (buffer_len_ > 0) {
            const FrameMsgInfo result = parser_->parse(buffer_, buffer_len_);
            if (!result.valid) break;

            // Auto-dispatch: deserialize payload and notify all matching slots.
            Dispatch(result.msg_id, result.msg_data, result.msg_len);

            // Advance past the consumed frame.
            // frame_size is populated by all profile parsers; fall back to a
            // conservative estimate only if the parser does not set it.
            const size_t frameSize =
                result.frame_size > 0 ? result.frame_size : result.msg_len + 10;

            if (frameSize == 0 || frameSize > buffer_len_) {
                buffer_len_ = 0; // safety guard: prevents infinite loop
                break;
            }
            std::memmove(buffer_, buffer_ + frameSize, buffer_len_ - frameSize);
            buffer_len_ -= frameSize;
        }
    }

    void Dispatch(uint16_t msgId, const uint8_t* payload, size_t len) {
        const auto id8 = static_cast<uint8_t>(msgId);
        for (size_t i = 0; i < MaxSubscriptions; ++i) {
            Slot& slot = slots_[i];
            if (slot.active && slot.msg_id == id8 &&
                slot.dispatch_bytes != nullptr) {
                slot.dispatch_bytes(payload, len, id8, slot.callable_storage);
            }
        }
    }

    static void DataCallbackWrapper(const uint8_t* data, size_t length,
                                    void* user_data) {
        static_cast<StructFrameSdkT*>(user_data)->Feed(data, length);
    }

    static void ErrorCallbackWrapper(const char*, void*) {}

    static void CloseCallbackWrapper(void* user_data) {
        static_cast<StructFrameSdkT*>(user_data)->buffer_len_ = 0;
    }
};

// Convenience alias with default sizing — covers the common case and keeps
// existing code (StructFrameSdk sdk(config)) compiling unchanged.
using StructFrameSdk = StructFrameSdkT<>;

} // namespace sdk
} // namespace structframe
