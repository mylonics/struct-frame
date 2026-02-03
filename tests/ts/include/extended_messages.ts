/**
 * Extended test message definitions (TypeScript).
 * Provides getMessage(index) function for extended message ID and payload testing.
 *
 * This file matches the C++ extended_messages.hpp structure.
 */

import {
  ExtendedTestExtendedIdMessage1,
  ExtendedTestExtendedIdMessage2,
  ExtendedTestExtendedIdMessage3,
  ExtendedTestExtendedIdMessage4,
  ExtendedTestExtendedIdMessage5,
  ExtendedTestExtendedIdMessage6,
  ExtendedTestExtendedIdMessage7,
  ExtendedTestExtendedIdMessage8,
  ExtendedTestExtendedIdMessage9,
  ExtendedTestExtendedIdMessage10,
  ExtendedTestLargePayloadMessage1,
  ExtendedTestLargePayloadMessage2,
  ExtendedTestExtendedVariableSingleArray,
} from '../../generated/ts/extended_test.structframe';

// Type alias for message union (like C++ MessageVariant)
export type MessageType =
  | ExtendedTestExtendedIdMessage1
  | ExtendedTestExtendedIdMessage2
  | ExtendedTestExtendedIdMessage3
  | ExtendedTestExtendedIdMessage4
  | ExtendedTestExtendedIdMessage5
  | ExtendedTestExtendedIdMessage6
  | ExtendedTestExtendedIdMessage7
  | ExtendedTestExtendedIdMessage8
  | ExtendedTestExtendedIdMessage9
  | ExtendedTestExtendedIdMessage10
  | ExtendedTestLargePayloadMessage1
  | ExtendedTestLargePayloadMessage2
  | ExtendedTestExtendedVariableSingleArray;

// Message count
export const MESSAGE_COUNT = 17;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createExtId1(): ExtendedTestExtendedIdMessage1 {
  return new ExtendedTestExtendedIdMessage1({
    sequence_number: 12345678,
    label: 'Test Label Extended 1',
    value: 3.14159,
    enabled: true,
  });
}

function createExtId2(): ExtendedTestExtendedIdMessage2 {
  return new ExtendedTestExtendedIdMessage2({
    sensor_id: -42,
    reading: 2.718281828,
    status_code: 50000,
    description_length: 'Extended ID test message 2'.length,
    description_data: 'Extended ID test message 2',
  });
}

function createExtId3(): ExtendedTestExtendedIdMessage3 {
  return new ExtendedTestExtendedIdMessage3({
    timestamp: 1704067200000000n,
    temperature: -40,
    humidity: 85,
    location: 'Sensor Room A',
  });
}

function createExtId4(): ExtendedTestExtendedIdMessage4 {
  return new ExtendedTestExtendedIdMessage4({
    event_id: 999999,
    event_type: 42,
    event_time: 1704067200000n,
    event_data_length: 'Event payload with extended message ID'.length,
    event_data_data: 'Event payload with extended message ID',
  });
}

function createExtId5(): ExtendedTestExtendedIdMessage5 {
  return new ExtendedTestExtendedIdMessage5({
    x_position: 100.5,
    y_position: -200.25,
    z_position: 50.125,
    frame_number: 1000000,
  });
}

function createExtId6(): ExtendedTestExtendedIdMessage6 {
  return new ExtendedTestExtendedIdMessage6({
    command_id: -12345,
    parameter1: 1000,
    parameter2: 2000,
    acknowledged: false,
    command_name: 'CALIBRATE_SENSOR',
  });
}

function createExtId7(): ExtendedTestExtendedIdMessage7 {
  return new ExtendedTestExtendedIdMessage7({
    counter: 4294967295,
    average: 123.456789,
    minimum: -999.99,
    maximum: 999.99,
  });
}

function createExtId8(): ExtendedTestExtendedIdMessage8 {
  return new ExtendedTestExtendedIdMessage8({
    level: 255,
    offset: -32768,
    duration: 86400000,
    tag: 'TEST123',
  });
}

function createExtId9(): ExtendedTestExtendedIdMessage9 {
  return new ExtendedTestExtendedIdMessage9({
    big_number: -9223372036854775807n,
    big_unsigned: 18446744073709551615n,
    precision_value: 1.7976931348623157e+308,
  });
}

function createExtId10(): ExtendedTestExtendedIdMessage10 {
  return new ExtendedTestExtendedIdMessage10({
    small_value: 256,
    short_text: 'Boundary Test',
    flag: true,
  });
}

function createLarge1(): ExtendedTestLargePayloadMessage1 {
  const sensorReadings: number[] = [];
  for (let i = 0; i < 64; i++) {
    sensorReadings.push(i + 1);
  }
  return new ExtendedTestLargePayloadMessage1({
    sensor_readings: sensorReadings,
    reading_count: 64,
    timestamp: 1704067200000000n,
    device_name: 'Large Sensor Array Device',
  });
}

function createLarge2(): ExtendedTestLargePayloadMessage2 {
  const largeData: number[] = [];
  for (let i = 0; i < 256; i++) {
    largeData.push(i);
  }
  for (let i = 256; i < 280; i++) {
    largeData.push(i - 256);
  }
  return new ExtendedTestLargePayloadMessage2({
    large_data: largeData,
  });
}

function createExtVarSingleEmpty(): ExtendedTestExtendedVariableSingleArray {
  return new ExtendedTestExtendedVariableSingleArray({
    timestamp: 0x0000000000000001n,
    telemetry_data_count: 0,
    telemetry_data_data: [],
    crc: 0x00000001,
  });
}

function createExtVarSingleSingle(): ExtendedTestExtendedVariableSingleArray {
  return new ExtendedTestExtendedVariableSingleArray({
    timestamp: 0x0000000000000002n,
    telemetry_data_count: 1,
    telemetry_data_data: [42],
    crc: 0x00000002,
  });
}

function createExtVarSingleThird(): ExtendedTestExtendedVariableSingleArray {
  return new ExtendedTestExtendedVariableSingleArray({
    timestamp: 0x0000000000000003n,
    telemetry_data_count: 83,
    telemetry_data_data: Array.from({ length: 83 }, (_, i) => i),
    crc: 0x00000003,
  });
}

function createExtVarSingleAlmost(): ExtendedTestExtendedVariableSingleArray {
  return new ExtendedTestExtendedVariableSingleArray({
    timestamp: 0x0000000000000004n,
    telemetry_data_count: 249,
    telemetry_data_data: Array.from({ length: 249 }, (_, i) => i % 256),
    crc: 0x00000004,
  });
}

function createExtVarSingleFull(): ExtendedTestExtendedVariableSingleArray {
  return new ExtendedTestExtendedVariableSingleArray({
    timestamp: 0x0000000000000005n,
    telemetry_data_count: 250,
    telemetry_data_data: Array.from({ length: 250 }, (_, i) => i % 256),
    crc: 0x00000005,
  });
}


// ============================================================================
// getMessage(index) - unified interface matching C++ MessageProvider pattern
// ============================================================================

export function getMessage(index: number): MessageType {
  switch (index) {
    case 0: return createExtId1();
    case 1: return createExtId2();
    case 2: return createExtId3();
    case 3: return createExtId4();
    case 4: return createExtId5();
    case 5: return createExtId6();
    case 6: return createExtId7();
    case 7: return createExtId8();
    case 8: return createExtId9();
    case 9: return createExtId10();
    case 10: return createLarge1();
    case 11: return createLarge2();
    case 12: return createExtVarSingleEmpty();
    case 13: return createExtVarSingleSingle();
    case 14: return createExtVarSingleThird();
    case 15: return createExtVarSingleAlmost();
    default: return createExtVarSingleFull();
  }
}
