// Negative tests for struct-frame Rust parser
//
// Tests error handling for:
// - Corrupted CRC/checksum
// - Truncated frames
// - Invalid start bytes
// - Malformed data

use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::get_message_info;
use struct_frame_sdk::{
    encode_message_crc, AccumulatingReader, BufferWriter, BufferReader,
    PROFILE_STANDARD_CONFIG, PROFILE_BULK_CONFIG,
};

// ============================================================================
// Helper: create a test message
// ============================================================================

fn create_test_message() -> SerializationTestBasicTypesMessage {
    let mut msg = SerializationTestBasicTypesMessage::default();
    msg.small_int = 42;
    msg.medium_int = 1000;
    msg.regular_int = 100000;
    msg.large_int = 1000000000;
    msg.small_uint = 200;
    msg.medium_uint = 50000;
    msg.regular_uint = 3000000000;
    msg.large_uint = 9000000000000000000;
    msg.single_precision = 3.14159;
    msg.double_precision = 2.71828;
    msg.flag = true;
    let dev = b"DEVICE123";
    msg.device_id[..dev.len()].copy_from_slice(dev);
    let desc = b"Test device";
    msg.description_length = desc.len() as u8;
    msg.description[..desc.len()].copy_from_slice(desc);
    msg
}

// ============================================================================
// Test functions
// ============================================================================

/// Test: Parser rejects frame with corrupted CRC
fn test_corrupted_crc() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    let frame_size = data.len();
    if frame_size < 4 {
        return false;
    }

    // Corrupt the CRC (last 2 bytes)
    data[frame_size - 1] ^= 0xFF;
    data[frame_size - 2] ^= 0xFF;

    // Try to parse - should fail
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: Parser rejects truncated frame
fn test_truncated_frame() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let data = writer.data().to_vec();
    let frame_size = data.len();
    if frame_size < 10 {
        return false;
    }

    // Truncate the frame (cut off last 5 bytes)
    let truncated = data[..frame_size - 5].to_vec();

    // Try to parse - should fail
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, truncated);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: Parser rejects frame with invalid start bytes
fn test_invalid_start_bytes() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    if data.len() < 2 {
        return false;
    }

    // Corrupt start bytes
    data[0] = 0xDE;
    data[1] = 0xAD;

    // Try to parse - should fail
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: Parser handles zero-length buffer
fn test_zero_length_buffer() -> bool {
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, vec![]);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: Parser handles corrupted length field
fn test_corrupted_length() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    if data.len() < 4 {
        return false;
    }

    // Corrupt length field (byte 2 for ProfileStandard: [0x90][0x71][LEN][MSG_ID]...)
    // Set it to a very large value
    data[2] = 0xFF;

    // Try to parse - should fail due to buffer too small for claimed length
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: AccumulatingReader rejects corrupted CRC in streaming mode
fn test_streaming_corrupted_crc() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    let frame_size = data.len();
    if frame_size < 4 {
        return false;
    }

    // Corrupt the CRC (last byte)
    data[frame_size - 1] ^= 0xFF;

    // Try to parse with AccumulatingReader (byte by byte)
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    for byte in &data {
        reader.add_data(std::slice::from_ref(byte));
    }

    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: AccumulatingReader handles garbage data
fn test_streaming_garbage() -> bool {
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);

    // Feed random garbage bytes
    let garbage: &[u8] = &[0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A];
    reader.add_data(garbage);

    let result = reader.next(&get_message_info);
    result.is_none() // Expect no valid frame
}

/// Test: Multiple frames with corrupted middle frame
fn test_multiple_corrupted_frames() -> bool {
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 4096);

    let mut msg1 = create_test_message();
    msg1.small_int = 1;
    writer.write_crc(&msg1, 0);

    let mut msg2 = create_test_message();
    msg2.small_int = 2;
    writer.write_crc(&msg2, 0);
    let second_frame_end = writer.size();

    let mut msg3 = create_test_message();
    msg3.small_int = 3;
    writer.write_crc(&msg3, 0);

    let mut data = writer.data().to_vec();

    // Corrupt the second frame's CRC (last 2 bytes of second frame)
    data[second_frame_end - 1] ^= 0xFF;
    data[second_frame_end - 2] ^= 0xFF;

    // Parse all frames
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);

    // First should be valid
    let result1 = reader.next(&get_message_info);
    if result1.is_none() {
        return false;
    }

    // Second should be invalid
    let result2 = reader.next(&get_message_info);
    result2.is_none() // Expect failure on second frame
}

/// Test: Bulk profile with corrupted CRC
fn test_bulk_profile_corrupted_crc() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_BULK_CONFIG, 1024);
    writer.write_crc(&msg, 0);

    let mut data = writer.data().to_vec();
    let frame_size = data.len();
    if frame_size < 4 {
        return false;
    }

    // Corrupt the CRC (last 2 bytes)
    data[frame_size - 1] ^= 0xFF;
    data[frame_size - 2] ^= 0xFF;

    // Try to parse - should fail
    let mut reader = BufferReader::new(PROFILE_BULK_CONFIG, data);
    let result = reader.next(&get_message_info);
    result.is_none() // Expect parsing to fail
}

/// Test: AccumulatingReader handles a frame fed in two separate add_data chunks
fn test_partial_frame_boundary() -> bool {
    let msg = create_test_message();

    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_crc(&PROFILE_STANDARD_CONFIG, &mut buf, &msg, 0);
    if frame_size < 10 {
        return false;
    }

    let mid = frame_size / 2;
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);

    // Feed first half via add_data, then call next() to save partial data to internal buffer
    reader.add_data(&buf[..mid]);
    let _ = reader.next(&get_message_info);  // Should return None but save partial data

    // Feed second half - adds to internal buffer completing the frame
    reader.add_data(&buf[mid..frame_size]);

    // Call next() once all data is present - should successfully decode the frame
    let result = reader.next(&get_message_info);
    result.is_some() // Expect success after accumulating both halves
}

// ============================================================================
// Test runner
// ============================================================================

fn run_test(name: &str, func: fn() -> bool) -> bool {
    let passed = func();
    println!("{:<50} {:>6}", name, if passed { "PASS" } else { "FAIL" });
    passed
}

fn main() {
    println!("\n========================================");
    println!("NEGATIVE TESTS - Rust Parser");
    println!("========================================\n");

    println!("Test Results Matrix:\n");
    println!("{:<50} {:>6}", "Test Name", "Result");
    println!("{:<50} {:>6}", "==================================================", "======");

    let tests: &[(&str, fn() -> bool)] = &[
        ("Bulk profile: Corrupted CRC",              test_bulk_profile_corrupted_crc),
        ("Corrupted CRC detection",                  test_corrupted_crc),
        ("Corrupted length field detection",         test_corrupted_length),
        ("Invalid start bytes detection",            test_invalid_start_bytes),
        ("Multiple frames: Corrupted middle frame",  test_multiple_corrupted_frames),
        ("Partial frame across buffer boundary",     test_partial_frame_boundary),
        ("Streaming: Corrupted CRC detection",       test_streaming_corrupted_crc),
        ("Streaming: Garbage data handling",         test_streaming_garbage),
        ("Truncated frame detection",                test_truncated_frame),
        ("Zero-length buffer handling",              test_zero_length_buffer),
    ];

    let mut tests_run = 0;
    let mut tests_passed = 0;

    for (name, func) in tests {
        tests_run += 1;
        if run_test(name, *func) {
            tests_passed += 1;
        }
    }

    let tests_failed = tests_run - tests_passed;

    println!("\n========================================");
    println!("Summary: {}/{} tests passed", tests_passed, tests_run);
    println!("========================================\n");

    std::process::exit(if tests_failed > 0 { 1 } else { 0 });
}
