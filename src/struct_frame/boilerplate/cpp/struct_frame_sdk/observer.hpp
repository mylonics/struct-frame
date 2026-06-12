// Observer/Subscriber pattern for C++ struct-frame SDK
// Header-only implementation inspired by ETLCPP but with no dependencies
// No STL dependencies for embedded systems
//
// Note: StructFrameSdkT (struct_frame_sdk.hpp) uses its own inline-callable
// Slot system for subscriptions — that system has no heap allocation and
// supports arbitrary callables. This observer pattern (IObserver / Observable)
// is a separate, virtual-dispatch-based alternative exported by sdk.hpp and
// sdk_embedded.hpp. Use it when a virtual interface is more natural (e.g.,
// class-based designs). Prefer the StructFrameSdkT subscribe() API for
// embedded use where virtual dispatch overhead is unacceptable.

#pragma once

#include <cstddef>
#include <cstdint>

namespace structframe {
namespace sdk {

// Forward declarations
template <typename TMessage, size_t MaxObservers = 16>
class Observable;

/**
 * Fixed-size observer list for embedded systems.
 * Uses a null-slot model: remove() nullifies the slot without compacting,
 * so it is safe to call remove() from inside a notify() callback without
 * skipping subsequent observers.
 *
 * @tparam T The pointer type to store
 * @tparam MaxObservers Maximum number of observers
 */
template <typename T, size_t MaxObservers = 16>
class FixedObserverList {
 private:
  T observers_[MaxObservers];

 public:
  FixedObserverList() {
    for (size_t i = 0; i < MaxObservers; ++i) {
      observers_[i] = nullptr;
    }
  }

  bool add(T observer) {
    if (observer == nullptr) return false;
    T* free_slot = nullptr;
    for (size_t i = 0; i < MaxObservers; ++i) {
      if (observers_[i] == observer) return false;  // already registered
      if (observers_[i] == nullptr && free_slot == nullptr) free_slot = &observers_[i];
    }
    if (free_slot == nullptr) return false;  // full
    *free_slot = observer;
    return true;
  }

  bool remove(T observer) {
    for (size_t i = 0; i < MaxObservers; ++i) {
      if (observers_[i] == observer) {
        observers_[i] = nullptr;  // null slot; no shift — safe during notify()
        return true;
      }
    }
    return false;
  }

  void clear() {
    for (size_t i = 0; i < MaxObservers; ++i) {
      observers_[i] = nullptr;
    }
  }

  size_t size() const {
    size_t n = 0;
    for (size_t i = 0; i < MaxObservers; ++i) {
      if (observers_[i] != nullptr) ++n;
    }
    return n;
  }

  T operator[](size_t index) const { return (index < MaxObservers) ? observers_[index] : nullptr; }

  static constexpr size_t capacity() { return MaxObservers; }
};

/**
 * Observer interface for receiving messages.
 * @tparam TMessage The message type to observe
 */
template <typename TMessage>
class IObserver {
 public:
  virtual ~IObserver() = default;

  /**
   * Called when a message is received.
   * @param message The received message
   * @param msgId The message ID (uint16_t to match StructFrameSdkT)
   */
  virtual void onMessage(const TMessage& message, uint16_t msgId) = 0;
};

/**
 * Function pointer-based observer for callback style subscription.
 * No std::function dependency — uses plain function pointers.
 * @tparam TMessage The message type to observe
 */
template <typename TMessage>
class FunctionObserver : public IObserver<TMessage> {
 public:
  using CallbackType = void (*)(const TMessage&, uint16_t);

  explicit FunctionObserver(CallbackType callback) : callback_(callback) {}

  void onMessage(const TMessage& message, uint16_t msgId) override {
    if (callback_) {
      callback_(message, msgId);
    }
  }

 private:
  CallbackType callback_;
};

/**
 * Lambda/callable-based observer for flexible callback subscription.
 * Uses templates instead of std::function — zero heap allocation for the wrapper.
 * @tparam TMessage The message type to observe
 * @tparam Callable The callable type (lambda, functor, etc.)
 */
template <typename TMessage, typename Callable>
class CallableObserver : public IObserver<TMessage> {
 public:
  explicit CallableObserver(Callable callback) : callback_(callback) {}

  void onMessage(const TMessage& message, uint16_t msgId) override {
    callback_(message, msgId);
  }

 private:
  Callable callback_;
};

/**
 * Observable subject that notifies observers of messages.
 *
 * notify() is safe to call while observers are being added or removed from
 * inside a callback: removal nullifies the slot without compacting the array,
 * so no observer is skipped. Destroying an observer object while it is still
 * registered is undefined behaviour — always call unsubscribe() first.
 *
 * @tparam TMessage The message type
 * @tparam MaxObservers Maximum number of observers (default 16)
 */
template <typename TMessage, size_t MaxObservers>
class Observable {
 public:
  /**
   * Subscribe an observer to this observable.
   * @param observer The observer to add
   * @return true if successfully subscribed, false if full or already subscribed
   */
  bool subscribe(IObserver<TMessage>* observer) { return observers_.add(observer); }

  /**
   * Unsubscribe an observer from this observable.
   * Safe to call from inside an onMessage() callback.
   * @param observer The observer to remove
   * @return true if successfully unsubscribed
   */
  bool unsubscribe(IObserver<TMessage>* observer) { return observers_.remove(observer); }

  /**
   * Notify all observers of a new message.
   * Iterates all slots (not just active count) so that removals during
   * notification cannot cause observers to be skipped.
   * @param message The message to send
   * @param msgId The message ID
   */
  void notify(const TMessage& message, uint16_t msgId) {
    for (size_t i = 0; i < FixedObserverList<IObserver<TMessage>*, MaxObservers>::capacity(); ++i) {
      IObserver<TMessage>* observer = observers_[i];
      if (observer) {
        observer->onMessage(message, msgId);
      }
    }
  }

  /**
   * Get the number of active subscribed observers.
   */
  size_t observerCount() const { return observers_.size(); }

  /**
   * Clear all observers.
   */
  void clear() { observers_.clear(); }

 private:
  FixedObserverList<IObserver<TMessage>*, MaxObservers> observers_;
};

/**
 * RAII subscription handle that automatically unsubscribes on destruction.
 * @tparam TMessage The message type
 */
template <typename TMessage, size_t MaxObservers = 16>
class Subscription {
 public:
  Subscription() : observable_(nullptr), observer_(nullptr) {}

  Subscription(Observable<TMessage, MaxObservers>* observable, IObserver<TMessage>* observer)
      : observable_(observable), observer_(observer) {}

  ~Subscription() { unsubscribe(); }

  // Move semantics
  Subscription(Subscription&& other) noexcept : observable_(other.observable_), observer_(other.observer_) {
    other.observable_ = nullptr;
    other.observer_ = nullptr;
  }

  Subscription& operator=(Subscription&& other) noexcept {
    if (this != &other) {
      unsubscribe();
      observable_ = other.observable_;
      observer_ = other.observer_;
      other.observable_ = nullptr;
      other.observer_ = nullptr;
    }
    return *this;
  }

  // Disable copy
  Subscription(const Subscription&) = delete;
  Subscription& operator=(const Subscription&) = delete;

  void unsubscribe() {
    if (observable_ && observer_) {
      observable_->unsubscribe(observer_);
      observable_ = nullptr;
      observer_ = nullptr;
    }
  }

 private:
  Observable<TMessage, MaxObservers>* observable_;
  IObserver<TMessage>* observer_;
};

}  // namespace sdk
}  // namespace structframe
