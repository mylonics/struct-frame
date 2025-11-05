#!/usr/bin/env node
// Decoder for cross-platform testing with framing
// Reads framed SerializationTestMessage from stdin and decodes it

const serializationTestModule = require('./serialization_test.sf');
const structFrameParserModule = require('./struct_frame_parser');

const serialization_test_SerializationTestMessage = serializationTestModule.serialization_test_SerializationTestMessage;
const FrameParser = structFrameParserModule.FrameParser;
const BasicPacketFormat = structFrameParserModule.BasicPacketFormat;

try {
  // Set up stdin to read binary data
  const chunks: Buffer[] = [];
  process.stdin.on('data', (chunk) => {
    chunks.push(chunk);
  });

  process.stdin.on('end', () => {
    const binaryData = Buffer.concat(chunks);

    if (binaryData.length === 0) {
      process.stderr.write('ERROR: No data received from stdin\n');
      process.exit(1);
    }

    // Create parser for deserialization
    const packetFormats: { [key: number]: any } = {
      0x90: new BasicPacketFormat()
    };
    const msgDefinitions: { [key: number]: any } = {
      204: serialization_test_SerializationTestMessage
    };

    const parser = new FrameParser(packetFormats, msgDefinitions);

    // Parse the binary data byte by byte
    let msg: any = null;
    for (const byte of binaryData) {
      const result = parser.parse_char(byte);
      if (result) {
        msg = result;
        break;
      }
    }

    if (msg === null) {
      process.stderr.write('ERROR: Failed to decode message\n');
      process.exit(1);
    }

    // Print decoded values in a consistent format
    console.log(`magic_number=0x${msg.magic_number.toString(16).toUpperCase().padStart(8, '0')}`);
    console.log(`test_string=${msg.test_string_data.substring(0, msg.test_string_length)}`);
    console.log(`test_float=${msg.test_float.toFixed(5)}`);
    console.log(`test_bool=${msg.test_bool}`);
    console.log(`test_array=${msg.test_array_data.slice(0, msg.test_array_count).join(',')}`);
  });

  // Resume stdin to start reading
  process.stdin.resume();
} catch (error) {
  process.stderr.write(`ERROR: Failed to decode: ${error}\n`);
  process.exit(1);
}
