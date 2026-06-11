// struct-frame Rust SDK client
// High-level observer-pattern interface for routing framed messages to handlers.

use std::collections::HashMap;
use crate::frame_base::{FrameMsgInfo, MessageInfo};
use crate::frame_profiles::AccumulatingReader;

/// Subscription handle returned by `subscribe()`.
/// Call `sdk.unsubscribe(handle)` to remove the handler.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Subscription {
    pub(crate) msg_id: u16,
    pub(crate) id: usize,
}

/// A registered message handler callback.
pub type MessageHandler = Box<dyn Fn(&FrameMsgInfo) + Send + 'static>;

/// Verbose send result used by SDK send helpers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SendResult {
    pub success: bool,
    pub attempted_bytes: usize,
    pub bytes_written: usize,
}

/// High-level SDK that routes incoming framed data to per-message-ID handlers.
///
/// # Example
/// ```rust,ignore
/// let sdk = StructFrameSdk::new(reader, serialization_test::get_message_info);
/// let sub = sdk.subscribe(BasicTypesMessage::MSG_ID, |frame| {
///     let msg = BasicTypesMessage::unpack(&frame.payload).unwrap();
///     println!("received regular_int={}", msg.regular_int);
/// });
/// sdk.inject_data(&raw_bytes);
/// sdk.unsubscribe(sub);
/// ```
pub struct StructFrameSdk {
    handlers: HashMap<u16, Vec<(usize, MessageHandler)>>,
    reader: AccumulatingReader,
    next_id: usize,
    get_message_info: Box<dyn Fn(u16) -> Option<MessageInfo>>,
}

impl StructFrameSdk {
    /// Create a new SDK backed by `reader` for frame parsing.
    ///
    /// * `reader` — an `AccumulatingReader` already configured for the desired
    ///   profile (e.g. `new_standard_reader(4096)`).
    /// * `get_message_info` — the generated per-package `get_message_info`
    ///   function, used to validate frame CRCs and look up payload sizes.
    pub fn new(
        reader: AccumulatingReader,
        get_message_info: impl Fn(u16) -> Option<MessageInfo> + 'static,
    ) -> Self {
        StructFrameSdk {
            handlers: HashMap::new(),
            reader,
            next_id: 0,
            get_message_info: Box::new(get_message_info),
        }
    }

    /// Register a handler for all incoming frames with the given `msg_id`.
    ///
    /// Returns a `Subscription` that can be passed to `unsubscribe()`.
    pub fn subscribe(
        &mut self,
        msg_id: u16,
        handler: impl Fn(&FrameMsgInfo) + Send + 'static,
    ) -> Subscription {
        let id = self.next_id;
        self.next_id += 1;
        self.handlers
            .entry(msg_id)
            .or_default()
            .push((id, Box::new(handler)));
        Subscription { msg_id, id }
    }

    /// Remove the handler identified by `subscription`.
    pub fn unsubscribe(&mut self, subscription: Subscription) {
        if let Some(handlers) = self.handlers.get_mut(&subscription.msg_id) {
            handlers.retain(|(id, _)| *id != subscription.id);
        }
    }

    /// Feed raw bytes into the internal buffer.
    ///
    /// All complete frames found in the buffer are parsed and dispatched to
    /// any registered handlers for their `msg_id`.  Partial frames remain in
    /// the internal buffer and will be processed when more data arrives.
    pub fn inject_data(&mut self, data: &[u8]) {
        self.reader.add_data(data);
        loop {
            let frame = self.reader.next(self.get_message_info.as_ref());
            match frame {
                None => break,
                Some(f) => {
                    self.dispatch(f);
                }
            }
        }
    }

    /// Feed one byte into the internal buffer.
    ///
    /// If the byte completes a frame the frame is dispatched to registered
    /// handlers.  Returns `true` when at least one frame was dispatched.
    pub fn push_byte(&mut self, byte: u8) -> bool {
        match self.reader.push_byte(byte, self.get_message_info.as_ref()) {
            None => false,
            Some(f) => {
                self.dispatch(f);
                true
            }
        }
    }

    /// Send already-framed bytes through a transport closure.
    ///
    /// The transport closure must return the number of bytes actually written.
    pub fn send_framed<F>(&self, frame: &[u8], mut send: F) -> SendResult
    where
        F: FnMut(&[u8]) -> usize,
    {
        let attempted = frame.len();
        let written = send(frame);
        SendResult {
            success: written == attempted,
            attempted_bytes: attempted,
            bytes_written: written,
        }
    }

    /// Alias for `send_framed` when forwarding complete frame bytes unchanged.
    pub fn send_direct<F>(&self, frame: &[u8], send: F) -> SendResult
    where
        F: FnMut(&[u8]) -> usize,
    {
        self.send_framed(frame, send)
    }

    fn dispatch(&self, frame: FrameMsgInfo) {
        if let Some(handlers) = self.handlers.get(&frame.msg_id) {
            for (_, handler) in handlers {
                handler(&frame);
            }
        }
    }
}
