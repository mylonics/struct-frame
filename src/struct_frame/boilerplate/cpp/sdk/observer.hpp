// Observer/Subscriber pattern for C++ struct-frame SDK
// Header-only implementation inspired by ETLCPP but with no dependencies

#pragma once

#include <vector>
#include <algorithm>
#include <functional>

namespace StructFrame {

// Forward declarations
template<typename TMessage>
class Observable;

/**
 * Observer interface for receiving messages
 * @tparam TMessage The message type to observe
 */
template<typename TMessage>
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
 * Lambda-based observer for functional style subscription
 * @tparam TMessage The message type to observe
 */
template<typename TMessage>
class LambdaObserver : public IObserver<TMessage> {
public:
    using CallbackType = std::function<void(const TMessage&, uint8_t)>;
    
    explicit LambdaObserver(CallbackType callback) : callback_(std::move(callback)) {}
    
    void onMessage(const TMessage& message, uint8_t msgId) override {
        if (callback_) {
            callback_(message, msgId);
        }
    }
    
private:
    CallbackType callback_;
};

/**
 * Observable subject that notifies observers of messages
 * @tparam TMessage The message type
 */
template<typename TMessage>
class Observable {
public:
    /**
     * Subscribe an observer to this observable
     * @param observer The observer to add
     */
    void subscribe(IObserver<TMessage>* observer) {
        if (observer && std::find(observers_.begin(), observers_.end(), observer) == observers_.end()) {
            observers_.push_back(observer);
        }
    }
    
    /**
     * Unsubscribe an observer from this observable
     * @param observer The observer to remove
     */
    void unsubscribe(IObserver<TMessage>* observer) {
        observers_.erase(
            std::remove(observers_.begin(), observers_.end(), observer),
            observers_.end()
        );
    }
    
    /**
     * Notify all observers of a new message
     * @param message The message to send
     * @param msgId The message ID
     */
    void notify(const TMessage& message, uint8_t msgId) {
        for (auto* observer : observers_) {
            if (observer) {
                observer->onMessage(message, msgId);
            }
        }
    }
    
    /**
     * Get the number of subscribed observers
     */
    size_t observerCount() const {
        return observers_.size();
    }
    
    /**
     * Clear all observers
     */
    void clear() {
        observers_.clear();
    }
    
private:
    std::vector<IObserver<TMessage>*> observers_;
};

/**
 * RAII subscription handle that automatically unsubscribes on destruction
 * @tparam TMessage The message type
 */
template<typename TMessage>
class Subscription {
public:
    Subscription() : observable_(nullptr), observer_(nullptr) {}
    
    Subscription(Observable<TMessage>* observable, IObserver<TMessage>* observer)
        : observable_(observable), observer_(observer) {}
    
    ~Subscription() {
        unsubscribe();
    }
    
    // Move semantics
    Subscription(Subscription&& other) noexcept
        : observable_(other.observable_), observer_(other.observer_) {
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
    Observable<TMessage>* observable_;
    IObserver<TMessage>* observer_;
};

} // namespace StructFrame
