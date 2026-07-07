// Negative tests for struct-frame Rust parser
//
// Tests error handling for:
// - Corrupted CRC/checksum
// - Truncated frames
// - Invalid start bytes
// - Malformed data

use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::pkg_test_messages::{
    PackageTestMessage, get_message_info as pkg_get_message_info,
};
use struct_frame_sdk::pkg_test_a::get_message_info as pkg_a_get_message_info;
use struct_frame_sdk::get_message_info;
use struct_frame_sdk::FrameMsgStatus;
use struct_frame_sdk::{
    encode_message_crc, encode_message_minimal, encode_with_crc,
    AccumulatingReader, BufferWriter, BufferReader,
    PROFILE_STANDARD_CONFIG, PROFILE_BULK_CONFIG, PROFILE_SENSOR_CONFIG, PROFILE_NETWORK_CONFIG,
    PROFILE_IPC_CONFIG,
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

    // Parse - the CRC-failed frame is surfaced as an invalid CrcFailure event
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure && f.frame_size > 0,
        None => false,
    }
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

    // Parse - garbage start bytes are surfaced as a SyncRecovery skip event
    let mut reader = BufferReader::new(PROFILE_STANDARD_CONFIG, data);
    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::SyncRecovery && f.frame_size > 0,
        None => false,
    }
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
    match result1 {
        Some(ref f) if f.valid => {}
        _ => return false,
    }

    // Second is surfaced as an invalid CrcFailure event
    match reader.next(&get_message_info) {
        Some(f) if !f.valid && f.status == FrameMsgStatus::CrcFailure => {}
        _ => return false,
    }

    // Third frame after the corrupt one is still delivered
    match reader.next(&get_message_info) {
        Some(f) => f.valid,
        None => false,
    }
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

    // Parse - the CRC-failed frame is surfaced as an invalid CrcFailure event
    let mut reader = BufferReader::new(PROFILE_BULK_CONFIG, data);
    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure && f.frame_size > 0,
        None => false,
    }
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
    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure,
        None => false,
    }
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
    match reader.next(&get_message_info) {
        Some(f) => !f.valid && f.status == FrameMsgStatus::CrcFailure,
        None => false,
    }
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

    // First frame is surfaced as an invalid CrcFailure event
    match reader.next(&get_message_info) {
        Some(f) if !f.valid && f.status == FrameMsgStatus::CrcFailure => {}
        _ => return false,
    }

    // Second frame must succeed after skipping the bad one
    match reader.next(&get_message_info) {
        Some(f) => f.valid,
        None => false,
    }
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
    match reader.next(&get_message_info) {
        Some(f) if f.valid => {}
        _ => return false,
    }

    // Frame 2 is surfaced as an invalid CrcFailure event — status must be preserved
    match reader.next(&get_message_info) {
        Some(f) if !f.valid && f.status == FrameMsgStatus::CrcFailure => {}
        _ => return false,
    }

    // Reader must decode frame 3 after advancing past the CRC error
    match reader.next(&get_message_info) {
        Some(f) => f.valid,
        None => false,
    }
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


// ============================================================================
// Helpers for the diagnostics / buffer-mode scenarios
// ============================================================================

/// Encode one Network-profile frame with the given sequence number.
fn encode_network_frame(seq: u8) -> Vec<u8> {
    let msg = create_test_message();
    let mut payload = vec![0u8; BasicTypesMessage::MAX_SIZE];
    let payload_len = msg.pack(&mut payload);
    let mut buf = vec![0u8; 1024];
    let frame_size = encode_with_crc(
        &PROFILE_NETWORK_CONFIG,
        &mut buf,
        seq,
        1,
        1,
        (BasicTypesMessage::MSG_ID >> 8) as u8,
        (BasicTypesMessage::MSG_ID & 0xFF) as u8,
        &payload[..payload_len],
        BasicTypesMessage::MAGIC1,
        BasicTypesMessage::MAGIC2,
    );
    buf.truncate(frame_size);
    buf
}

/// Encode two back-to-back Standard-profile frames; returns (data, first frame size).
fn encode_two_standard_frames() -> (Vec<u8>, usize) {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 2048);
    let first = writer.write_crc(&msg, 0);
    writer.write_crc(&msg, 0);
    (writer.data().to_vec(), first)
}

/// Diagnostics: cnt_crc_failures increments on a CRC failure.
fn test_diagnostic_crc_failure() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);
    let mut data = writer.data().to_vec();
    let frame_size = data.len();
    if frame_size < 4 {
        return false;
    }
    data[frame_size - 1] ^= 0xFF;
    data[frame_size - 2] ^= 0xFF;

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    for b in &data {
        reader.push_byte(*b, &get_message_info);
    }

    let diag = reader.diagnostics();
    diag.cnt_crc_failures == 1 && diag.cnt_sync_recoveries >= 1
}

/// Diagnostics: cnt_sync_recoveries increments when garbage bytes are fed.
/// (The unified Rust reader classifies data only once a full header's worth of
/// bytes is buffered, so feed a whole overhead-sized garbage chunk.)
fn test_diagnostic_sync_recovery() -> bool {
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&[0x90, 0xAB, 0x00, 0x00, 0x00, 0x00]); // bad start2 -> resync
    while reader.try_next(&get_message_info).is_some() {}
    reader.diagnostics().cnt_sync_recoveries >= 1
}

/// Diagnostics: cnt_len_errors increments when the header length field is out of
/// the [min_size, size] range. A zero length completes a (short, CRC-failing)
/// frame immediately, so the reader records the out-of-range length.
fn test_diagnostic_len_error() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 1024);
    writer.write_crc(&msg, 0);
    let mut data = writer.data().to_vec();
    if data.len() < 5 {
        return false;
    }

    // ProfileStandard header: [0x90][0x71][LEN][MSG_ID]... Zero out the length —
    // out of range as long as the message's min_size is non-zero.
    let info = match get_message_info(BasicTypesMessage::MSG_ID) {
        Some(i) => i,
        None => return false,
    };
    if info.min_size == 0 {
        return false;
    }
    data[2] = 0;

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&data);
    while reader.try_next(&get_message_info).is_some() {}

    reader.diagnostics().cnt_len_errors >= 1
}

/// Diagnostics: cnt_seq_gaps increments when a sequence number is skipped.
fn test_diagnostic_seq_gap() -> bool {
    let frame0 = encode_network_frame(0);
    let frame5 = encode_network_frame(5); // skips seq 1-4

    let mut reader = AccumulatingReader::new(PROFILE_NETWORK_CONFIG, 1024);
    let mut valid_count = 0;
    for b in frame0.iter().chain(frame5.iter()) {
        if let Some(f) = reader.push_byte(*b, &get_message_info) {
            if f.valid {
                valid_count += 1;
            }
        }
    }

    let diag = reader.diagnostics();
    valid_count == 2 && diag.cnt_seq_gaps == 1 && diag.cnt_crc_failures == 0
}

/// Diagnostics: reset_diagnostics() clears all counters.
fn test_diagnostic_reset() -> bool {
    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&[0x90, 0xAB, 0x00, 0x00, 0x00, 0x00]); // bad start2 -> resync
    while reader.try_next(&get_message_info).is_some() {}
    if reader.diagnostics().cnt_sync_recoveries < 1 {
        return false;
    }

    reader.reset_diagnostics();
    let diag = reader.diagnostics();
    diag.cnt_crc_failures == 0
        && diag.cnt_sync_recoveries == 0
        && diag.cnt_failed_bytes == 0
        && diag.cnt_len_errors == 0
        && diag.cnt_seq_gaps == 0
}

/// Buffer mode: a CRC-failed frame increments cnt_crc_failures, cnt_failed_bytes
/// and cnt_sync_recoveries — same counter semantics as stream mode.
fn test_buffer_mode_crc_counters() -> bool {
    let (mut data, frame_size) = encode_two_standard_frames();
    data[frame_size - 1] ^= 0xFF; // corrupt frame 1's CRC

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    reader.add_data(&data);

    let mut valid_count = 0;
    while let Some(f) = reader.try_next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        }
    }

    let diag = reader.diagnostics();
    valid_count == 1
        && diag.cnt_crc_failures == 1
        && diag.cnt_sync_recoveries == 1
        && diag.cnt_failed_bytes == frame_size as u32
}

/// Buffer mode: sequence gaps are detected on frames consumed via add_data.
fn test_buffer_mode_seq_gap() -> bool {
    let mut data = encode_network_frame(0);
    data.extend_from_slice(&encode_network_frame(5)); // skips seq 1-4

    let mut reader = AccumulatingReader::new(PROFILE_NETWORK_CONFIG, 1024);
    reader.add_data(&data);

    let mut valid_count = 0;
    while let Some(f) = reader.try_next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        }
    }

    let diag = reader.diagnostics();
    valid_count == 2 && diag.cnt_seq_gaps == 1 && diag.cnt_crc_failures == 0
}

/// Sensor (minimal) profile buffer: an unknown msg_id after a valid start byte
/// triggers a resync scan to the next start byte instead of discarding the buffer.
fn test_sensor_buffer_unknown_msg_id_resync() -> bool {
    let info = match get_message_info(BasicTypesMessage::MSG_ID) {
        Some(i) => i,
        None => return false,
    };

    // [0x70][0xFF (unknown)] then a valid sensor frame [0x70][msg_id][payload@size]
    let mut data = vec![0u8; 4 + info.size]; // zeroed payload is fine for framing
    data[0] = 0x70;
    data[1] = 0xFF;
    data[2] = 0x70;
    data[3] = (BasicTypesMessage::MSG_ID & 0xFF) as u8;

    let mut reader = BufferReader::new(PROFILE_SENSOR_CONFIG, data);
    let mut saw_sync = false;
    let mut valid_count = 0;
    while let Some(f) = reader.next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        } else if f.status == FrameMsgStatus::SyncRecovery {
            saw_sync = true;
        }
    }
    saw_sync && valid_count == 1
}

/// IPC (no start bytes) buffer: an unknown msg_id advances one byte and the
/// following valid frame is still delivered.
fn test_ipc_buffer_unknown_msg_id() -> bool {
    let info = match get_message_info(BasicTypesMessage::MSG_ID) {
        Some(i) => i,
        None => return false,
    };

    let mut data = vec![0u8; 2 + info.size];
    data[0] = 0xFF; // unknown msg_id
    data[1] = (BasicTypesMessage::MSG_ID & 0xFF) as u8;

    let mut reader = BufferReader::new(PROFILE_IPC_CONFIG, data);
    let mut saw_sync = false;
    let mut valid_count = 0;
    while let Some(f) = reader.next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        } else if f.status == FrameMsgStatus::SyncRecovery {
            saw_sync = true;
        }
    }
    saw_sync && valid_count == 1
}

/// Split sweep: two back-to-back frames delivered intact when the byte stream is
/// split into two add_data chunks at every possible offset.
fn test_split_sweep_all_boundaries() -> bool {
    let (data, _) = encode_two_standard_frames();
    let total = data.len();

    for split in 1..total {
        let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
        let mut valid_count = 0;

        reader.add_data(&data[..split]);
        while let Some(f) = reader.try_next(&get_message_info) {
            if f.valid {
                valid_count += 1;
            }
        }
        reader.add_data(&data[split..]);
        while let Some(f) = reader.try_next(&get_message_info) {
            if f.valid {
                valid_count += 1;
            }
        }

        if valid_count != 2 {
            return false;
        }
        if reader.has_partial() {
            return false;
        }
    }
    true
}

/// Streaming: two back-to-back frames are both decoded byte-by-byte.
fn test_streaming_two_frames() -> bool {
    let (data, _) = encode_two_standard_frames();

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    let mut valid_count = 0;
    for b in &data {
        if let Some(f) = reader.push_byte(*b, &get_message_info) {
            if f.valid {
                valid_count += 1;
            }
        }
    }
    valid_count == 2
}


/// Buffer mode: a garbage tail that looks like a truncated frame start is
/// buffered; the reader must resync past it and keep delivering the frames
/// that follow (livelock regression test).
fn test_buffer_mode_garbage_prefix_recovers() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 2048);
    writer.write_crc(&msg, 0);
    let frame = writer.data().to_vec();
    if frame.len() < 6 {
        return false;
    }

    let mut chunk1 = frame.clone();
    chunk1.push(0x90); // looks like a truncated frame start
    chunk1.push(0xFF);

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 1024);
    let mut valid_count = 0;
    let mut saw_sync = false;

    reader.add_data(&chunk1);
    while let Some(f) = reader.try_next(&get_message_info) {
        if f.valid {
            valid_count += 1;
        } else if f.status == FrameMsgStatus::SyncRecovery {
            saw_sync = true;
        }
    }

    for _ in 0..3 {
        reader.add_data(&frame);
        while let Some(f) = reader.try_next(&get_message_info) {
            if f.valid {
                valid_count += 1;
            } else if f.status == FrameMsgStatus::SyncRecovery {
                saw_sync = true;
            }
        }
    }

    valid_count == 4 && saw_sync
}

/// Buffer mode: a corrupted length field claiming more bytes than the reader's
/// capacity must not wedge the reader permanently (livelock regression test).
fn test_buffer_mode_oversized_length_recovers() -> bool {
    let msg = create_test_message();
    let mut writer = BufferWriter::new(PROFILE_STANDARD_CONFIG, 2048);
    writer.write_crc(&msg, 0);
    let frame = writer.data().to_vec();
    if frame.len() < 6 {
        return false;
    }

    // Bogus header claiming a 255-byte payload — the total (261) exceeds the
    // 256-byte reader capacity, so this frame can never complete.
    let bogus = [0x90u8, 0x71, 0xFF, (BasicTypesMessage::MSG_ID & 0xFF) as u8];

    let mut reader = AccumulatingReader::new(PROFILE_STANDARD_CONFIG, 256);

    reader.add_data(&bogus);
    while reader.try_next(&get_message_info).is_some() {}

    let mut valid_count = 0;
    let rounds = 256 / frame.len() + 3;
    for _ in 0..rounds {
        reader.add_data(&frame);
        while let Some(f) = reader.try_next(&get_message_info) {
            if f.valid {
                valid_count += 1;
            }
        }
    }
    if valid_count < 1 {
        return false;
    }

    // The reader must keep delivering fresh frames after recovery.
    let mut probe_valid = 0;
    for _ in 0..3 {
        reader.add_data(&frame);
        while let Some(f) = reader.try_next(&get_message_info) {
            if f.valid {
                probe_valid += 1;
            }
        }
    }
    probe_valid >= 1
}


// ============================================================================
// Package / cross-package corruption scenarios (parity with C/C++/TS/JS/C#)
// ============================================================================

/// Encode one Bulk-profile PackageTestMessage frame.
fn encode_bulk_pkg_frame() -> Vec<u8> {
    let msg = PackageTestMessage::default();
    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_crc(&PROFILE_BULK_CONFIG, &mut buf, &msg, 0);
    buf.truncate(frame_size);
    buf
}

/// Bulk profile: corrupting the pkg_id byte invalidates the CRC.
fn test_bulk_corrupted_pkg_id() -> bool {
    let mut data = encode_bulk_pkg_frame();
    if data.len() < 7 {
        return false;
    }
    // Bulk layout: [0x90][0x74][LEN_LO][LEN_HI][PKG_ID][MSG_ID]...
    data[4] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_BULK_CONFIG, data);
    match reader.next(&pkg_get_message_info) {
        Some(f) => !f.valid,
        None => false,
    }
}

/// Bulk profile: corrupting the msg_id low byte invalidates the CRC.
fn test_bulk_corrupted_msg_id_low_byte() -> bool {
    let mut data = encode_bulk_pkg_frame();
    if data.len() < 7 {
        return false;
    }
    data[5] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_BULK_CONFIG, data);
    match reader.next(&pkg_get_message_info) {
        Some(f) => !f.valid,
        None => false,
    }
}

/// Cross-package rejection: a frame from one package fails CRC validation when
/// decoded with another package's message info (different pkg_id / magic bytes).
fn test_cross_package_rejection() -> bool {
    let data = encode_bulk_pkg_frame();

    let mut reader = BufferReader::new(PROFILE_BULK_CONFIG, data);
    match reader.next(&pkg_a_get_message_info) {
        Some(f) => !f.valid,
        None => false,
    }
}

/// Network profile: corrupting the pkg_id byte invalidates the CRC.
fn test_network_corrupted_pkg_id() -> bool {
    let msg = PackageTestMessage::default();
    let mut buf = vec![0u8; 1024];
    let frame_size = encode_message_crc(&PROFILE_NETWORK_CONFIG, &mut buf, &msg, 0);
    if frame_size < 10 {
        return false;
    }
    buf.truncate(frame_size);
    // Network layout: [0x90][0x78][SEQ][SYS][COMP][LEN_LO][LEN_HI][PKG_ID][MSG_ID]...
    buf[7] ^= 0xFF;

    let mut reader = BufferReader::new(PROFILE_NETWORK_CONFIG, buf);
    match reader.next(&pkg_get_message_info) {
        Some(f) => !f.valid,
        None => false,
    }
}


fn main() {
    println!("\n========================================");
    println!("NEGATIVE TESTS - Rust Parser");
    println!("========================================\n");

    println!("Test Results Matrix:\n");
    println!("{:<50} {:>6}", "Test Name", "Result");
    println!("{:<50} {:>6}", "==================================================", "======");

    let tests: &[(&str, fn() -> bool)] = &[
        ("Buffer mode: CRC failure counters",        test_buffer_mode_crc_counters),
        ("Buffer mode: Sequence gap counted",        test_buffer_mode_seq_gap),
        ("Buffer mode: garbage prefix partial recovers", test_buffer_mode_garbage_prefix_recovers),
        ("Buffer mode: oversized length recovers",   test_buffer_mode_oversized_length_recovers),
        ("Buffer mode: recovers after CRC failure",  test_buffer_mode_recovers_after_crc_failure),
        ("Buffer reader: skips CRC-failed frame",    test_buffer_reader_skips_crc_failure),
        ("Bulk profile: Corrupted CRC",              test_bulk_profile_corrupted_crc),
        ("Bulk profile: Corrupted pkg_id byte",      test_bulk_corrupted_pkg_id),
        ("Bulk profile: Corrupted msg_id low byte",  test_bulk_corrupted_msg_id_low_byte),
        ("Corrupted CRC detection",                  test_corrupted_crc),
        ("Corrupted length field detection",         test_corrupted_length),
        ("Cross-package rejection (pkgid mismatch)", test_cross_package_rejection),
        ("Diagnostics: CRC failure counter",         test_diagnostic_crc_failure),
        ("Diagnostics: Length error counter",        test_diagnostic_len_error),
        ("Diagnostics: Reset diagnostics",           test_diagnostic_reset),
        ("Diagnostics: Sequence gap counter",        test_diagnostic_seq_gap),
        ("Diagnostics: Sync recovery counter",       test_diagnostic_sync_recovery),
        ("Invalid message ID rejection",             test_invalid_msg_id),
        ("Invalid start bytes detection",            test_invalid_start_bytes),
        ("IPC buffer: unknown msg_id advances one byte", test_ipc_buffer_unknown_msg_id),
        ("Minimal profile: Truncated frame",         test_minimal_profile_truncated_frame),
        ("Multiple frames: CRC error then valid frame", test_crc_error_then_valid_frame),
        ("Multiple frames: Corrupted middle frame",  test_multiple_corrupted_frames),
        ("Network profile: Corrupted pkg_id byte",   test_network_corrupted_pkg_id),
        ("Network profile: SysId/CompId corruption", test_network_sysid_compid),
        ("Partial frame across buffer boundary",     test_partial_frame_boundary),
        ("Sensor buffer: unknown msg_id resync",     test_sensor_buffer_unknown_msg_id_resync),
        ("Split sweep: two frames at every boundary", test_split_sweep_all_boundaries),
        ("Split-buffer: CRC error status preserved", test_split_buffer_crc_error_status),
        ("TryNext drain: CRC/resync + valid", test_try_next_drain_contract),
        ("TryNext partial pending contract", test_try_next_partial_pending_contract),
        ("Stream mode: recovers after garbage prefix", test_stream_recovers_after_garbage),
        ("Streaming: Corrupted CRC detection",       test_streaming_corrupted_crc),
        ("Streaming: Garbage data handling",         test_streaming_garbage),
        ("Streaming: two frames byte-by-byte",       test_streaming_two_frames),
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
