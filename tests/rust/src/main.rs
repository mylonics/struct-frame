// Rust test harness for struct-frame generated code
// Tests cross-platform encoding/decoding compatibility

use struct_frame_sdk::get_message_info;
use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::{
    AccumulatingReader,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,
    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,
    encode_message_crc, encode_message_minimal,
    ProfileConfig,
};

const BUFFER_SIZE: usize = 65536;
const MESSAGE_COUNT: usize = 17;

// ============================================================================
// Message creation helpers - mirror standard_messages
// ============================================================================

fn create_serialization_test(
    magic: u32,
    s: &[u8],
    flt: f32,
    bl: bool,
    arr: &[i32],
) -> SerializationTestSerializationTestMessage {
    let mut msg = SerializationTestSerializationTestMessage::default();
    msg.magic_number = magic;
    let len = s.len().min(msg.test_string.len());
    msg.test_string_length = len as u8;
    msg.test_string[..len].copy_from_slice(&s[..len]);
    msg.test_float = flt;
    msg.test_bool = bl;
    let count = arr.len().min(5);
    msg.test_array_count = count as u8;
    for i in 0..count {
        msg.test_array[i] = arr[i];
    }
    msg
}

fn create_basic_types(
    si: i8, mi: i16, ri: i32, li: i64,
    su: u8, mu: u16, ru: u32, lu: u64,
    sp: f32, dp: f64, fl: bool,
    dev: &[u8], desc: &[u8],
) -> SerializationTestBasicTypesMessage {
    let mut msg = SerializationTestBasicTypesMessage::default();
    msg.small_int = si;
    msg.medium_int = mi;
    msg.regular_int = ri;
    msg.large_int = li;
    msg.small_uint = su;
    msg.medium_uint = mu;
    msg.regular_uint = ru;
    msg.large_uint = lu;
    msg.single_precision = sp;
    msg.double_precision = dp;
    msg.flag = fl;
    let dev_len = dev.len().min(msg.device_id.len());
    msg.device_id[..dev_len].copy_from_slice(&dev[..dev_len]);
    let desc_len = desc.len().min(msg.description.len());
    msg.description_length = desc_len as u8;
    msg.description[..desc_len].copy_from_slice(&desc[..desc_len]);
    msg
}

fn create_union_with_array() -> SerializationTestUnionTestMessage {
    let mut msg = SerializationTestUnionTestMessage::default();
    let mut arr = SerializationTestComprehensiveArrayMessage::default();
    arr.fixed_ints[0] = 10; arr.fixed_ints[1] = 20; arr.fixed_ints[2] = 30;
    arr.fixed_floats[0] = 1.5; arr.fixed_floats[1] = 2.5;
    arr.fixed_bools[0] = true; arr.fixed_bools[1] = false;
    arr.fixed_bools[2] = true; arr.fixed_bools[3] = false;
    arr.bounded_uints_count = 2;
    arr.bounded_uints[0] = 100; arr.bounded_uints[1] = 200;
    arr.bounded_doubles_count = 1;
    arr.bounded_doubles[0] = 3.14159;
    let h = b"Hello";
    arr.fixed_strings[0][..h.len()].copy_from_slice(h);
    let w = b"World";
    arr.fixed_strings[1][..w.len()].copy_from_slice(w);
    arr.bounded_strings_count = 1;
    let t = b"Test";
    arr.bounded_strings[0][..t.len()].copy_from_slice(t);
    arr.fixed_statuses[0] = SerializationTestStatus::ACTIVE;
    arr.fixed_statuses[1] = SerializationTestStatus::ERROR;
    arr.bounded_statuses_count = 1;
    arr.bounded_statuses[0] = SerializationTestStatus::INACTIVE;
    arr.fixed_sensors[0].id = 1;
    arr.fixed_sensors[0].value = 25.5;
    arr.fixed_sensors[0].status = SerializationTestStatus::ACTIVE;
    let ts = b"TempSensor";
    arr.fixed_sensors[0].name[..ts.len()].copy_from_slice(ts);
    arr.bounded_sensors_count = 0;
    msg.set_array_payload(&arr);
    msg
}

fn create_union_with_test() -> SerializationTestUnionTestMessage {
    let mut msg = SerializationTestUnionTestMessage::default();
    let mut test = SerializationTestSerializationTestMessage::default();
    test.magic_number = 0x12345678;
    let s = b"Union test message";
    test.test_string_length = s.len() as u8;
    test.test_string[..s.len()].copy_from_slice(s);
    test.test_float = 99.99;
    test.test_bool = true;
    test.test_array_count = 5;
    test.test_array[0] = 1; test.test_array[1] = 2; test.test_array[2] = 3;
    test.test_array[3] = 4; test.test_array[4] = 5;
    msg.set_test_payload(&test);
    msg
}

fn create_message_test() -> SerializationTestMessage {
    let mut msg = SerializationTestMessage::default();
    msg.severity = SerializationTestMsgSeverity::SEV_MSG;
    let m = b"test";
    msg.module_length = m.len() as u8;
    msg.module[..m.len()].copy_from_slice(m);
    let txt = b"A really good";
    msg.msg_length = txt.len() as u8;
    msg.r#msg[..txt.len()].copy_from_slice(txt);
    msg
}

// ============================================================================
// Expected payload: pack the message and return (msg_id, len)
// ============================================================================

fn pack_msg<M: struct_frame_sdk::StructFrameMessage>(msg: &M, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
    if use_fixed {
        (M::MSG_ID, msg.pack_max_size(buf))
    } else {
        (M::MSG_ID, msg.pack(buf))
    }
}

fn get_expected_payload(index: usize, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
    match index {
        0 => pack_msg(&create_serialization_test(0xDEADBEEF, b"Cross-platform test!", 3.14159, true, &[100, 200, 300]), buf, use_fixed),
        1 => pack_msg(&create_serialization_test(0, b"", 0.0, false, &[]), buf, use_fixed),
        2 => pack_msg(&create_serialization_test(0xFFFFFFFF, b"Maximum length test string for coverage!", 999999.9, true,
                &[2147483647, -2147483648i32, 0, 1, -1]), buf, use_fixed),
        3 => pack_msg(&create_serialization_test(0xAAAAAAAA, b"Negative test", -273.15, false, &[-100, -200, -300, -400]), buf, use_fixed),
        4 => pack_msg(&create_serialization_test(1234567890, b"Special: !@#$%^&*()", 2.71828, true, &[0, 1, 1, 2, 3]), buf, use_fixed),
        5 => pack_msg(&create_basic_types(42, 1000, 123456, 9876543210i64,
                200, 50000, 4000000000u32, 9223372036854775807u64,
                3.14159, 2.718281828459045, true, b"DEVICE-001", b"Basic test values"), buf, use_fixed),
        6 => pack_msg(&create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, false, b"", b""), buf, use_fixed),
        7 | 10 => pack_msg(&create_basic_types(-128, -32768, -2147483648i32, -9223372036854775807i64,
                255, 65535, 4294967295u32, 9223372036854775807u64,
                -273.15, -9999.999999, false, b"NEG-TEST", b"Negative and max values"), buf, use_fixed),
        8 => pack_msg(&create_union_with_array(), buf, use_fixed),
        9 => pack_msg(&create_union_with_test(), buf, use_fixed),
        11 => {
            let mut m = SerializationTestVariableSingleArray::default();
            m.message_id = 0x00000001; m.payload_count = 0; m.checksum = 0x0001;
            pack_msg(&m, buf, use_fixed)
        }
        12 => {
            let mut m = SerializationTestVariableSingleArray::default();
            m.message_id = 0x00000002; m.payload_count = 1; m.payload[0] = 42; m.checksum = 0x0002;
            pack_msg(&m, buf, use_fixed)
        }
        13 => {
            let mut m = SerializationTestVariableSingleArray::default();
            m.message_id = 0x00000003;
            m.payload_count = 67;
            for i in 0..67 { m.payload[i] = i as u8; }
            m.checksum = 0x0003;
            pack_msg(&m, buf, use_fixed)
        }
        14 => {
            let mut m = SerializationTestVariableSingleArray::default();
            m.message_id = 0x00000004;
            m.payload_count = 199;
            for i in 0..199 { m.payload[i] = i as u8; }
            m.checksum = 0x0004;
            pack_msg(&m, buf, use_fixed)
        }
        15 => {
            let mut m = SerializationTestVariableSingleArray::default();
            m.message_id = 0x00000005;
            m.payload_count = 200;
            for i in 0..200 { m.payload[i] = (i % 256) as u8; }
            m.checksum = 0x0005;
            pack_msg(&m, buf, use_fixed)
        }
        _ => pack_msg(&create_message_test(), buf, use_fixed),
    }
}

// ============================================================================
// Encode all test messages into the output buffer
// ============================================================================

fn encode_all(config: &ProfileConfig, output: &mut [u8]) -> usize {
    let mut written = 0;

    macro_rules! enc {
        ($msg:expr) => {{
            let frame_len = if config.payload.has_crc {
                encode_message_crc(config, &mut output[written..], &$msg, 0)
            } else {
                encode_message_minimal(config, &mut output[written..], &$msg)
            };
            written += frame_len;
        }};
    }

    enc!(create_serialization_test(0xDEADBEEF, b"Cross-platform test!", 3.14159, true, &[100, 200, 300]));
    enc!(create_serialization_test(0, b"", 0.0, false, &[]));
    enc!(create_serialization_test(0xFFFFFFFF, b"Maximum length test string for coverage!", 999999.9, true,
        &[2147483647, -2147483648i32, 0, 1, -1]));
    enc!(create_serialization_test(0xAAAAAAAA, b"Negative test", -273.15, false, &[-100, -200, -300, -400]));
    enc!(create_serialization_test(1234567890, b"Special: !@#$%^&*()", 2.71828, true, &[0, 1, 1, 2, 3]));

    enc!(create_basic_types(42, 1000, 123456, 9876543210i64,
        200, 50000, 4000000000u32, 9223372036854775807u64,
        3.14159, 2.718281828459045, true, b"DEVICE-001", b"Basic test values"));
    enc!(create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, false, b"", b""));
    enc!(create_basic_types(-128, -32768, -2147483648i32, -9223372036854775807i64,
        255, 65535, 4294967295u32, 9223372036854775807u64,
        -273.15, -9999.999999, false, b"NEG-TEST", b"Negative and max values"));

    enc!(create_union_with_array());
    enc!(create_union_with_test());

    enc!(create_basic_types(-128, -32768, -2147483648i32, -9223372036854775807i64,
        255, 65535, 4294967295u32, 9223372036854775807u64,
        -273.15, -9999.999999, false, b"NEG-TEST", b"Negative and max values"));

    {
        let mut m = SerializationTestVariableSingleArray::default();
        m.message_id = 0x00000001; m.payload_count = 0; m.checksum = 0x0001;
        enc!(m);
    }
    {
        let mut m = SerializationTestVariableSingleArray::default();
        m.message_id = 0x00000002; m.payload_count = 1; m.payload[0] = 42; m.checksum = 0x0002;
        enc!(m);
    }
    {
        let mut m = SerializationTestVariableSingleArray::default();
        m.message_id = 0x00000003;
        m.payload_count = 67;
        for i in 0..67 { m.payload[i] = i as u8; }
        m.checksum = 0x0003;
        enc!(m);
    }
    {
        let mut m = SerializationTestVariableSingleArray::default();
        m.message_id = 0x00000004;
        m.payload_count = 199;
        for i in 0..199 { m.payload[i] = i as u8; }
        m.checksum = 0x0004;
        enc!(m);
    }
    {
        let mut m = SerializationTestVariableSingleArray::default();
        m.message_id = 0x00000005;
        m.payload_count = 200;
        for i in 0..200 { m.payload[i] = (i % 256) as u8; }
        m.checksum = 0x0005;
        enc!(m);
    }

    enc!(create_message_test());

    written
}

// ============================================================================
// Decode and validate all messages
// ============================================================================

fn decode_validate(config: ProfileConfig, data: &[u8], use_fixed: bool) -> usize {
    let mut reader = AccumulatingReader::new(config, 65536);
    reader.add_data(data);

    let mut count = 0;
    let mut expected_buf = [0u8; 1024];

    while let Some(frame) = reader.next(&get_message_info) {
        if !frame.valid { break; }

        let (expected_id, expected_len) = get_expected_payload(count, &mut expected_buf, use_fixed);

        if frame.msg_id != expected_id {
            eprintln!("[DECODE] msg {}: expected msg_id={}, got {}", count, expected_id, frame.msg_id);
            break;
        }

        if frame.payload.len() != expected_len || frame.payload[..expected_len] != expected_buf[..expected_len] {
            eprintln!("[DECODE] msg {}: payload mismatch (got {} bytes, expected {} bytes)",
                count, frame.payload.len(), expected_len);
            for i in 0..frame.payload.len().min(expected_len) {
                if frame.payload[i] != expected_buf[i] {
                    eprintln!("  First diff at byte {}: got 0x{:02x}, expected 0x{:02x}",
                        i, frame.payload[i], expected_buf[i]);
                    break;
                }
            }
            break;
        }

        count += 1;
        if count >= MESSAGE_COUNT { break; }
    }
    count
}

fn get_profile_config(profile: &str) -> ProfileConfig {
    match profile {
        "standard" => PROFILE_STANDARD_CONFIG,
        "sensor"   => PROFILE_SENSOR_CONFIG,
        "ipc"      => PROFILE_IPC_CONFIG,
        "bulk"     => PROFILE_BULK_CONFIG,
        "network"  => PROFILE_NETWORK_CONFIG,
        _ => {
            eprintln!("Unknown profile: {}", profile);
            std::process::exit(1);
        }
    }
}

/// Returns true if the profile uses fixed-size encoding (no length field, no CRC).
fn profile_uses_fixed(config: &ProfileConfig) -> bool {
    !config.payload.has_length
}

// ============================================================================
// Main
// ============================================================================

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage:");
        eprintln!("  {} encode <profile> <output_file>", args[0]);
        eprintln!("  {} decode <profile> <input_file>", args[0]);
        eprintln!("  {} both <profile> <file>", args[0]);
        eprintln!("\nProfiles: standard, sensor, ipc, bulk, network");
        std::process::exit(1);
    }

    let operation = &args[1];
    let profile = &args[2];
    let file_path = &args[3];
    let config = get_profile_config(profile);
    let use_fixed = profile_uses_fixed(&config);

    match operation.as_str() {
        "encode" => {
            let mut buffer = vec![0u8; BUFFER_SIZE];
            let written = encode_all(&config, &mut buffer);
            if written == 0 {
                eprintln!("[ENCODE] FAILED: No bytes written");
                std::process::exit(1);
            }
            match std::fs::write(file_path, &buffer[..written]) {
                Ok(_) => {
                    println!("[ENCODE] SUCCESS: Wrote {} bytes to {}", written, file_path);
                    std::process::exit(0);
                }
                Err(e) => {
                    eprintln!("[ENCODE] FAILED: {}", e);
                    std::process::exit(1);
                }
            }
        }
        "decode" => {
            let data = match std::fs::read(file_path) {
                Ok(d) => d,
                Err(e) => {
                    eprintln!("[DECODE] FAILED: Cannot read {}: {}", file_path, e);
                    std::process::exit(1);
                }
            };
            let count = decode_validate(config, &data, use_fixed);
            if count != MESSAGE_COUNT {
                eprintln!("[DECODE] FAILED: {}/{} messages validated", count, MESSAGE_COUNT);
                std::process::exit(1);
            }
            println!("[DECODE] SUCCESS: {} messages validated", count);
            std::process::exit(0);
        }
        "both" => {
            let mut buffer = vec![0u8; BUFFER_SIZE];
            let written = encode_all(&config, &mut buffer);
            if written == 0 {
                eprintln!("[BOTH] FAILED: Encoding error");
                std::process::exit(1);
            }
            let count = decode_validate(config, &buffer[..written], use_fixed);
            if count != MESSAGE_COUNT {
                eprintln!("[BOTH] FAILED: {}/{} messages validated", count, MESSAGE_COUNT);
                std::process::exit(1);
            }
            println!("[BOTH] SUCCESS: {} messages, {} bytes", count, written);
            std::process::exit(0);
        }
        _ => {
            eprintln!("Unknown operation: {}", operation);
            std::process::exit(1);
        }
    }
}
