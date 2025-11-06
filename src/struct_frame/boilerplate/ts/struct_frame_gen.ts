
// This file should be updated to import and aggregate all generated .sf files
// For now, it returns 0 for unknown message IDs, which allows the parser to handle unknown messages gracefully
// In a production setup, you should import all your .sf files and call their get_message_length functions

export function get_message_length(msg_id: number) {
  // TODO: Import and aggregate all .sf files
  // Example:
  // import * as module1 from './module1.sf';
  // import * as module2 from './module2.sf';
  // const length = module1.get_message_length(msg_id) || module2.get_message_length(msg_id);
  // return length;
  
  // Returning 0 for unknown message IDs allows graceful handling of unsupported messages
  return 0;
}
