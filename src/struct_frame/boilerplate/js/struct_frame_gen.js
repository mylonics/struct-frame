/**
 * Struct frame message length aggregator for JavaScript.
 * Human-readable JavaScript version of the TypeScript boilerplate.
 */
"use strict";

// This file should be updated to import and aggregate all generated .sf files
// For now, it returns 0 for unknown message IDs, which allows the parser to handle unknown messages gracefully
// In a production setup, you should import all your .sf files and call their get_message_length functions

function get_message_length(msg_id) {
  // TODO: Import and aggregate all .sf files
  // Example:
  // const module1 = require('./module1.sf');
  // const module2 = require('./module2.sf');
  // const length = module1.get_message_length(msg_id) || module2.get_message_length(msg_id);
  // return length;
  
  // Returning 0 for unknown message IDs allows graceful handling of unsupported messages
  return 0;
}
module.exports.get_message_length = get_message_length;
