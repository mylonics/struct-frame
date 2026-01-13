// Observer/Subscriber pattern for C++ struct-frame SDK
// Header-only implementation inspired by ETLCPP but with no dependencies
// No STL dependencies for embedded systems

#pragma once

namespace StructFrame {

// Forward declarations
template <typename TMessage, size_t MaxObservers = 16>
class Observable;

/**
 * Fixed-size observer list for embedded systems
 * No dynamic allocation, uses static array
 * @tparam T The pointer type to store
 * @tparam MaxObservers Maximum number of observers
 */
template <typename T, size_t MaxObservers = 16>
class FixedObserverList {
 private:
  T observers_[MaxObservers];
  size_t count_;

 public:
  FixedObserverList() : count_(0) {
    for (size_t i = 0; i < MaxObservers; ++i) {
      observers_[i] = nullptr;
    }
  }

  bool add(T observer) {
    if (count_ >= MaxObservers || observer == nullptr) {
      return false;
    }

    // Check if already exists
    for (size_t i = 0; i < count_; ++i) {
      if (observers_[i] == observer) {
        return false;
      }
    }

    observers_[count_++] = observer;
    return true;
  }

  bool remove(T observer) {
    for (size_t i = 0; i < count_; ++i) {
      if (observers_[i] == observer) {
        // Shift remaining elements
        for (size_t j = i; j < count_ - 1; ++j) {
          observers_[j] = observers_[j + 1];
        }
        observers_[count_ - 1] = nullptr;
        --count_;
        return true;
      }
    }
    return false;
  }

  void clear() {
    for (size_t i = 0; i < count_; ++i) {
      observers_[i] = nullptr;
    }
    count_ = 0;
  }

  size_t size() const { return count_; }

  T operator[](size_t index) const { return (index < count_) ? observers_[index] : nullptr; }
};

/**
 * Observer interface for receiving messages
 * @tparam TMessage The message type to observe
 */
template <typename TMessage>
class IObserver {
 public:
  virtual ~IObserver() = default;

  /**
   * Called when a message is received
   * @param message The received message
   * @param msgId The message ID
   */
  virtual void onMessage(const TMessage& message, uint8_t msgId) = 0;
};

/**
 * Function pointer-based observer for callback style subscription
 * No std::function dependency - uses plain function pointers
 * @tparam TMessage The message type to observe
 */
template <typename TMessage>
class FunctionObserver : public IObserver<TMessage> {
 public:
  using CallbackType = void (*)(const TMessage&, uint8_t);

  explicit FunctionObserver(CallbackType callback) : callback_(callback) {}

  void onMessage(const TMessage& message, uint8_t msgId) override {
    if (callback_) {
      callback_(message, msgId);
    }
  }

 private:
  CallbackType callback_;
};

/**
 * Lambda/callable-based observer for flexible callback subscription
 * Uses templates instead of std::function - zero heap allocation for the wrapper
 * @tparam TMessage The message type to observe
 * @tparam Callable The callable type (lambda, functor, etc.)
 */
template <typename TMessage, typename Callable>
class CallableObserver : public IObserver<TMessage> {
 public:
  explicit CallableObserver(Callable callback) : callback_(callback) {}

  void onMessage(const TMessage& message, uint8_t msgId) override {
    callback_(message, msgId);
  }

 private:
  Callable callback_;
};

/**
 * Observable subject that notifies observers of messages
 * @tparam TMessage The message type
 * @tparam MaxObservers Maximum number of observers (default 16)
 */
template <typename TMessage, size_t MaxObservers>
class Observable {
 public:
  /**
   * Subscribe an observer to this observable
   * @param observer The observer to add
   * @return true if successfully subscribed, false if full or already subscribed
   */
  bool subscribe(IObserver<TMessage>* observer) { return observers_.add(observer); }

  /**
   * Unsubscribe an observer from this observable
   * @param observer The observer to remove
   * @return true if successfully unsubscribed
   */
  bool unsubscribe(IObserver<TMessage>* observer) { return observers_.remove(observer); }

  /**
   * Notify all observers of a new message
   * @param message The message to send
   * @param msgId The message ID
   */
  void notify(const TMessage& message, uint8_t msgId) {
    for (size_t i = 0; i < observers_.size(); ++i) {
      IObserver<TMessage>* observer = observers_[i];
      if (observer) {
        observer->onMessage(message, msgId);
      }
    }
  }

  /**
   * Get the number of subscribed observers
   */
  size_t observerCount() const { return observers_.size(); }

  /**
   * Clear all observers
   */
  void clear() { observers_.clear(); }

 private:
  FixedObserverList<IObserver<TMessage>*, MaxObservers> observers_;
};

/**
 * RAII subscription handle that automatically unsubscribes on destruction
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

}  // namespace StructFrame
