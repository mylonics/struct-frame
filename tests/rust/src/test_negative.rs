// Negative tests for struct-frame Rust parser
//
// Tests error handling for:
// - Corrupted CRC/checksum
// - Truncated frames
// - Invalid start bytes
// - Malformed data

use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::get_message_info;
use struct_frame_sdk::FrameMsgStatus;
use struct_frame_sdk::{
    encode_message_crc, encode_message_minimal, encode_with_crc,
    AccumulatingReader, BufferWriter, BufferReader,
    PROFILE_STANDARD_CONFIG, PROFILE_BULK_CONFIG, PROFILE_SENSOR_CONFIG, PROFILE_NETWORK_CONFIG,
};

// ============================================================================
// Helper: create a test message
// ============================================================================

fn create_test_message() -> BasicTypesMessage {
    let mut msg = BasicTypesMessage::default();
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

    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure && f.frame_size > 0,
        None => false,
    }
}

/// Test: AccumulatingReader handles garbage data
fn test_streaming_garbage() -> bool {
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);

    // Feed random garbage bytes
    let garbage: &[u8] = &[0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A];
    reader.add_data(garbage);

    let result = reader.next(&get_message_info);
    match result {
        Some(f) => !f.valid && f.status == FrameMsgStatus::SyncRecovery && f.frame_size > 0,
        None => false,
    }
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
    let partial = reader.next(&get_message_info);
    if partial.is_some() {
        return false;
    }

    // Feed second half - adds to internal buffer completing the frame
    reader.add_data(&buf[mid..frame_size]);

    // Call next() once all data is present - should successfully decode the frame
    let result = reader.next(&get_message_info);
    let frame = match result {
        Some(f) => f,
        None => return false,
    };
    if !frame.valid || frame.msg_id != BasicTypesMessage::MSG_ID {
        return false;
    }

    let decoded = match BasicTypesMessage::unpack(&frame.msg_data) {
        Some(m) => m,
        None => return false,
    };
    if decoded.small_int != msg.small_int {
        return false;
    }
    if decoded.flag != msg.flag {
        return false;
    }

    // No extra complete frame should remain.
    reader.next(&get_message_info).is_none()
}

/// Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values).
/// ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
/// Corrupting byte 3 (msg_id) to 0xFF causes get_message_info to return None → CRC uses {0,0} → fails.
fn test_invalid_msg_id() -> bool {
    let msg = create_test_message();

    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_crc(&PROFILE_STANDARD_CONFIG, &mut buf, &msg, 0);
    if frame_size < 5 {
        return false;
    }

    // Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
    // 0xFF is not a known message ID → get_message_info returns None → CRC uses {0,0} → fails
    buf[3] = 0xFF;

    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, buf[..frame_size].to_vec());
    let result = reader.next(&get_message_info);
    result.is_none() // Expect failure: CRC mismatch due to wrong magic values
}

/// Test: Minimal profile (no CRC) rejects a truncated frame.
/// ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
/// Parser uses get_message_info to determine expected payload size; truncated buffer → rejected.
fn test_minimal_profile_truncated_frame() -> bool {
    let msg = create_test_message();

    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_minimal(&PROFILE_SENSOR_CONFIG, &mut buf, &msg);
    if frame_size <= 5 {
        return false;
    }

    // Provide fewer bytes than the full frame to trigger truncation error
    let truncated = frame_size - 5;
    let mut reader = BufferReader::new(PROFILE_SENSOR_CONFIG, buf[..truncated].to_vec());
    let result = reader.next(&get_message_info);
    result.is_none() // Expect failure: buffer too small for expected payload
}

/// Test: Network profile validates sys_id/comp_id as part of CRC-protected header.
/// ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
/// sys_id is at byte 3 (within CRC region); corrupting it causes CRC failure.
fn test_network_sysid_compid() -> bool {
    let msg = create_test_message();

    // Build the payload manually
    let mut payload = vec![0u8; BasicTypesMessage::MAX_SIZE];
    let payload_len = msg.pack(&mut payload);

    let mut buf = vec![0u8; 1024];
    // Encode with seq=1, sys_id=5, comp_id=10
    let frame_size = encode_with_crc(
        &PROFILE_NETWORK_CONFIG,
        &mut buf,
        1,   // seq
        5,   // sys_id
        10,  // comp_id
        (BasicTypesMessage::MSG_ID >> 8) as u8, // pkg_id
        (BasicTypesMessage::MSG_ID & 0xFF) as u8, // msg_id
        &payload[..payload_len],
        BasicTypesMessage::MAGIC1,
        BasicTypesMessage::MAGIC2,
    );

    if frame_size < 10 {
        return false;
    }

    // Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
    // sys_id is inside the CRC-protected region so CRC will fail
    buf[3] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_NETWORK_CONFIG, buf[..frame_size].to_vec());
    let result = reader.next(&get_message_info);
    result.is_none() // Expect failure: corrupted sys_id invalidates CRC
}

/// Test: BufferReader advances past a CRC-failed frame and decodes the next valid frame.
/// Catches the A2 stall: BufferReader was not advancing past CRC failures.
fn test_buffer_reader_skips_crc_failure() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 2048);
    writer.write_crc(&msg, 0);
    let first_frame_end = writer.size();
    writer.write_crc(&msg, 0);
    let total = writer.size();

    let mut data = writer.data().to_vec();
    data[first_frame_end - 1] ^= 0xFF;
    data[first_frame_end - 2] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data[..total].to_vec());

    let result1 = reader.next(&get_message_info);
    if result1.is_some() {
        return false; // First frame must fail (CRC corrupted)
    }

    let result2 = reader.next(&get_message_info);
    result2.is_some() // Second frame must succeed after skipping the bad one
}

/// Test: AccumulatingReader buffer mode recovers after a CRC failure in add_data path.
/// Catches the A3 stall: CRC-bad frames caused a permanent loop in buffer mode.
fn test_buffer_mode_recovers_after_crc_failure() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);
    let frame_size = writer.size();

    let mut bad_data = writer.data().to_vec();
    bad_data[frame_size - 1] ^= 0xFF;
    bad_data[frame_size - 2] ^= 0xFF;

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&bad_data[..frame_size]);
    let result1 = reader.next(&get_message_info);
    let bad = match result1 {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure && f.frame_size > 0,
        None => false,
    };
    if !bad {
        return false;
    }

    // Feed a valid frame — reader must not be stuck on the bad one
    let mut writer2 = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer2.write_crc(&msg, 0);
    let good_data = writer2.data().to_vec();

    reader.add_data(&good_data);
    let result2 = reader.next(&get_message_info);
    result2.is_some()
}

/// Test: Stream mode recovers after garbage prefix and decodes a valid frame.
fn test_stream_recovers_after_garbage() -> bool {
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);

    let garbage: &[u8] = &[0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56];
    reader.add_data(garbage);

    let msg = create_test_message();
    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_crc(&PROFILE_STANDARD_CONFIG, &mut buf, &msg, 0);

    reader.add_data(&buf[..frame_size]);
    reader.next(&get_message_info).is_some()
}

/// Test: After a CRC failure the reader continues and decodes the next valid frame.
/// Verifies that a None result for a CRC-corrupted frame does not prevent subsequent
/// frames from being decoded — the reader must advance past the bad frame.
fn test_crc_error_then_valid_frame() -> bool {
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 4096);

    let mut msg = create_test_message();

    // Frame 1: valid
    msg.small_int = 1;
    writer.write_crc(&msg, 0);

    // Frame 2: CRC-corrupted
    msg.small_int = 2;
    writer.write_crc(&msg, 0);
    let frame2_end = writer.size();

    // Frame 3: valid
    msg.small_int = 3;
    writer.write_crc(&msg, 0);
    let total = writer.size();

    let mut data = writer.data().to_vec();
    data[frame2_end - 1] ^= 0xFF;
    data[frame2_end - 2] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data[..total].to_vec());

    // Frame 1 must decode successfully
    let result1 = reader.next(&get_message_info);
    if result1.is_none() {
        return false;
    }

    // Frame 2 must fail (CRC error) — reader must advance to frame 3
    let result2 = reader.next(&get_message_info);
    if result2.is_some() {
        return false;
    }

    // Reader must decode frame 3 after advancing past the CRC error
    let result3 = reader.next(&get_message_info);
    result3.is_some()
}

/// Test: AccumulatingReader correctly recovers after a CRC-failed frame that was
/// assembled across two add_data() calls (the internal-buffer reassembly path).
/// Rust's AccumulatingReader loops internally on CRC failure, so the caller sees
/// frame3 returned directly; cnt_crc_failures in diagnostics confirms the failure
/// was detected.
fn test_split_buffer_crc_error_status() -> bool {
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 4096);
    let mut msg = create_test_message();

    // Frame 1: valid
    msg.small_int = 1;
    writer.write_crc(&msg, 0);

    // Frame 2: CRC-corrupted
    msg.small_int = 2;
    writer.write_crc(&msg, 0);
    let frame2_end = writer.size();

    // Frame 3: valid
    msg.small_int = 3;
    writer.write_crc(&msg, 0);
    let total = writer.size();

    let mut data = writer.data().to_vec();
    data[frame2_end - 1] ^= 0xFF;
    data[frame2_end - 2] ^= 0xFF;

    // Split: frame 2's two CRC bytes go in the second add_data() call
    let split_point = frame2_end - 2;
    let chunk1 = &data[..split_point];
    let chunk2 = &data[split_point..total];

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);

    reader.add_data(chunk1);

    // Frame 1 must decode from the first chunk
    let result1 = reader.next(&get_message_info);
    if result1.is_none() {
        return false;
    }

    // Frame 2 is incomplete — partial data buffered, waiting for more data
    let partial = reader.next(&get_message_info);
    if partial.is_some() {
        return false;
    }

    reader.add_data(chunk2);

    // next() should surface the CRC-failed frame first.
    let result2 = reader.next(&get_message_info);
    let crc_failed = match result2 {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure && f.frame_size > 0,
        None => false,
    };
    if !crc_failed {
        return false;
    }

    // Then the following valid frame should parse.
    let result3 = reader.next(&get_message_info);
    let frame3_valid = match result3 {
        Some(f) => f.valid,
        None => false,
    };
    if !frame3_valid {
        return false;
    }

    if reader.diagnostics().cnt_crc_failures != 1 {
        return false;
    }

    true
}

/// Test: try_next drain loop surfaces CRC/resync progress and still delivers
/// the following valid frame.
fn test_try_next_drain_contract() -> bool {
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 4096);
    let mut msg = create_test_message();

    msg.small_int = 1;
    writer.write_crc(&msg, 0);
    let first_end = writer.size();

    msg.small_int = 2;
    writer.write_crc(&msg, 0);
    let total = writer.size();

    let mut data = writer.data().to_vec();
    data[first_end - 1] ^= 0xFF;
    data[first_end - 2] ^= 0xFF;

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 4096);
    reader.add_data(&data[..total]);

    let mut valid_count = 0;
    let mut saw_crc_failure = false;
    while let Some(f) = reader.try_next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        } else if f.status == FrameMsgStatus::CrcFailure {
            saw_crc_failure = true;
        }
    }

    saw_crc_failure
        && valid_count == 1
        && !reader.has_more()
        && !reader.has_partial()
        && reader.partial_size() == 0
}

/// Test: try_next partial-pending contract.
fn test_try_next_partial_pending_contract() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);
    let data = writer.data().to_vec();
    let frame_size = writer.size();

    if frame_size < 10 {
        return false;
    }

    let mid = frame_size / 2;
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&data[..mid]);

    if reader.try_next(&get_message_info).is_some() {
        return false;
    }
    if !reader.has_partial() || reader.partial_size() == 0 {
        return false;
    }

    reader.add_data(&data[mid..frame_size]);
    let mut valid_count = 0;
    while let Some(f) = reader.try_next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        }
    }

    valid_count == 1
        && !reader.has_partial()
        && reader.partial_size() == 0
        && !reader.has_more()
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
        ("Buffer mode: recovers after CRC failure",  test_buffer_mode_recovers_after_crc_failure),
        ("Buffer reader: skips CRC-failed frame",    test_buffer_reader_skips_crc_failure),
        ("Bulk profile: Corrupted CRC",              test_bulk_profile_corrupted_crc),
        ("Corrupted CRC detection",                  test_corrupted_crc),
        ("Corrupted length field detection",         test_corrupted_length),
        ("Invalid message ID rejection",             test_invalid_msg_id),
        ("Invalid start bytes detection",            test_invalid_start_bytes),
        ("Minimal profile: Truncated frame",         test_minimal_profile_truncated_frame),
        ("Multiple frames: CRC error then valid frame", test_crc_error_then_valid_frame),
        ("Multiple frames: Corrupted middle frame",  test_multiple_corrupted_frames),
        ("Network profile: SysId/CompId corruption", test_network_sysid_compid),
        ("Partial frame across buffer boundary",     test_partial_frame_boundary),
        ("Split-buffer: CRC error status preserved", test_split_buffer_crc_error_status),
        ("TryNext drain: CRC/resync + valid", test_try_next_drain_contract),
        ("TryNext partial pending contract", test_try_next_partial_pending_contract),
        ("Stream mode: recovers after garbage prefix", test_stream_recovers_after_garbage),
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
