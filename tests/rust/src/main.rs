// Rust test harness for struct-frame generated code
// Tests cross-platform encoding/decoding compatibility
//
// Usage: struct_frame_rust_tests <runner> <mode> <profile> <file>
//   runner:  test_standard | test_extended | test_variable_flag
//   mode:    encode | decode | both
//   profile: standard | sensor | ipc | bulk | network
//   file:    path to binary output/input file

use struct_frame_sdk::envelope_test::*;
use struct_frame_sdk::extended_test::*;
use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::{
    encode_message_crc, encode_message_minimal, AccumulatingReader, ProfileConfig,
    StructFrameSdk,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG, PROFILE_SENSOR_CONFIG,
    PROFILE_STANDARD_CONFIG,
};

const BUFFER_SIZE: usize = 65536;
const STANDARD_MESSAGE_COUNT: usize = 21;
const EXTENDED_MESSAGE_COUNT: usize = 10;
const VARIABLE_FLAG_MESSAGE_COUNT: usize = 7;

// ============================================================================
// Message creation helpers - mirror standard_messages
// ============================================================================

fn create_serialization_test(
    magic: u32,
    s: &[u8],
    flt: f32,
    bl: bool,
    arr: &[i32],
) -> SerializationTestMessage {
    let mut msg = SerializationTestMessage::default();
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
) -> BasicTypesMessage {
    let mut msg = BasicTypesMessage::default();
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

fn create_union_with_array() -> UnionTestMessage {
    let mut msg = UnionTestMessage::default();
    let mut arr = ComprehensiveArrayMessage::default();
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
    arr.fixed_statuses[0] = Status::ACTIVE;
    arr.fixed_statuses[1] = Status::ERROR;
    arr.bounded_statuses_count = 1;
    arr.bounded_statuses[0] = Status::INACTIVE;
    arr.fixed_sensors[0].id = 1;
    arr.fixed_sensors[0].value = 25.5;
    arr.fixed_sensors[0].status = Status::ACTIVE;
    let ts = b"TempSensor";
    arr.fixed_sensors[0].name[..ts.len()].copy_from_slice(ts);
    arr.bounded_sensors_count = 0;
    msg.set_array_payload(&arr);
    msg
}

fn create_union_with_test() -> UnionTestMessage {
    let mut msg = UnionTestMessage::default();
    let mut test = SerializationTestMessage::default();
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

fn create_message_test() -> Message {
    let mut msg = Message::default();
    msg.severity = MsgSeverity::SEV_MSG;
    let m = b"test";
    msg.module_length = m.len() as u8;
    msg.module[..m.len()].copy_from_slice(m);
    let txt = b"A really good";
    msg.msg_length = txt.len() as u8;
    msg.r#msg[..txt.len()].copy_from_slice(txt);
    msg
}

// ============================================================================
// Extended message creation helpers -- mirror extended_messages.hpp
// ============================================================================

fn create_ext_id_10() -> ExtendedIdMessage10 {
    let mut msg = ExtendedIdMessage10::default();
    msg.small_value = 256;
    let text = b"Boundary Test";
    msg.short_text[..text.len()].copy_from_slice(text);
    msg.flag = true;
    msg
}

fn create_ext_id_2() -> ExtendedIdMessage2 {
    let mut msg = ExtendedIdMessage2::default();
    msg.sensor_id = -42;
    msg.reading = 2.718281828;
    msg.status_code = 50000;
    let desc = b"Extended ID test message 2";
    msg.description_length = desc.len() as u8;
    msg.description[..desc.len()].copy_from_slice(desc);
    msg
}

fn create_ext_id_9() -> ExtendedIdMessage9 {
    let mut msg = ExtendedIdMessage9::default();
    msg.big_number = -9223372036854775807i64;
    msg.big_unsigned = 18446744073709551615u64;
    msg.precision_value = 1.7976931348623157e+308f64;
    msg
}

fn create_ext_large_1() -> LargePayloadMessage1 {
    let mut msg = LargePayloadMessage1::default();
    for i in 0..64usize {
        msg.sensor_readings[i] = (i + 1) as f32;
    }
    msg.reading_count = 64;
    msg.timestamp = 1704067200000000i64;
    let name = b"Large Sensor Array Device";
    msg.device_name[..name.len()].copy_from_slice(name);
    msg
}

fn create_ext_large_2() -> LargePayloadMessage2 {
    let mut msg = LargePayloadMessage2::default();
    for i in 0..256usize {
        msg.large_data[i] = i as u8;
    }
    for i in 256..280usize {
        msg.large_data[i] = (i - 256) as u8;
    }
    msg
}

fn create_ext_var_single(
    timestamp: u64,
    count: u8,
    crc: u32,
    start_value: u8,
) -> ExtendedVariableSingleArray {
    let mut msg = ExtendedVariableSingleArray::default();
    msg.timestamp = timestamp;
    msg.telemetry_data_count = count;
    for i in 0..count as usize {
        msg.telemetry_data[i] = ((start_value as usize + i) % 256) as u8;
    }
    msg.crc = crc;
    msg
}

// ============================================================================
// Variable-flag message creation helpers -- mirror variable_flag_messages.hpp
// ============================================================================

fn create_non_variable() -> TruncationTestNonVariable {
    let mut msg = TruncationTestNonVariable::default();
    msg.sequence_id = 0xDEADBEEF;
    msg.data_array_count = 67;
    for i in 0..67u8 {
        msg.data_array[i as usize] = i;
    }
    msg.footer = 0xCAFE;
    msg
}

fn create_truncation_variable() -> TruncationTestVariable {
    let mut msg = TruncationTestVariable::default();
    msg.sequence_id = 0xDEADBEEF;
    msg.data_array_count = 67;
    for i in 0..67u8 {
        msg.data_array[i as usize] = i;
    }
    msg.footer = 0xCAFE;
    msg
}

fn create_nested_variable() -> NestedVariableMessage {
    let mut msg = NestedVariableMessage::default();
    msg.sequence = 0x12345678;

    // Nested payload: id=7, label="Hello" (5 chars), samples=[10,20,30] (3 elements)
    msg.payload.id = 7;
    msg.payload.label_length = 5;
    msg.payload.label[..5].copy_from_slice(b"Hello");
    msg.payload.samples_count = 3;
    msg.payload.samples[0] = 10;
    msg.payload.samples[1] = 20;
    msg.payload.samples[2] = 30;

    // Top-level variable string
    let desc = b"nested variable test";
    msg.description_length = desc.len() as u8;
    msg.description[..desc.len()].copy_from_slice(desc);

    msg
}

fn create_multiple_arrays() -> VariableMultipleArrays {
    let mut msg = VariableMultipleArrays::default();
    msg.r#type = 5;

    msg.readings_count = 3;
    msg.readings[0] = 100;
    msg.readings[1] = 200;
    msg.readings[2] = 300;

    msg.values_count = 2;
    msg.values[0] = 1.5f32;
    msg.values[1] = 2.5f32;

    let lbl = b"multi arrays test";
    msg.label_length = lbl.len() as u8;
    msg.label[..lbl.len()].copy_from_slice(lbl);

    msg
}

fn create_mixed_fields() -> VariableMixedFields {
    let mut msg = VariableMixedFields::default();
    msg.fixed_id = 0xABCD1234;
    msg.fixed_value = 3.14f32;
    let name = b"DeviceName";
    msg.fixed_name[..name.len()].copy_from_slice(name);

    msg.variable_data_count = 5;
    msg.variable_data[0] = 1000;
    msg.variable_data[1] = 2000;
    msg.variable_data[2] = 3000;
    msg.variable_data[3] = 4000;
    msg.variable_data[4] = 5000;

    let vd = b"mixed fields test";
    msg.variable_desc_length = vd.len() as u8;
    msg.variable_desc[..vd.len()].copy_from_slice(vd);

    msg
}

fn create_variable_envelope_field_order() -> VariableEnvelopeMessage {
    let mut msg = VariableEnvelopeMessage::default();
    msg.priority = 7;
    let payload_a = VarEnvPayloadA { code: 0x42, value: 0x1234 };
    msg.set_payload_a(&payload_a);
    msg
}

fn create_variable_envelope_msgid() -> VariableEnvelopeMsgIdMessage {
    let mut msg = VariableEnvelopeMsgIdMessage::default();
    msg.priority = 3;
    let mut inner = BasicTypesMessage::default();
    inner.flag = true;
    inner.small_uint = 0xAB;
    inner.medium_uint = 0xCDEF;
    inner.regular_uint = 0x12345678u32;
    msg.set_basic(&inner);
    msg
}

// ============================================================================
// Expected payload helpers
// ============================================================================

fn pack_msg<M: struct_frame_sdk::StructFrameMessage>(msg: &M, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
    if use_fixed {
        (M::MSG_ID, msg.pack_max_size(buf))
    } else {
        (M::MSG_ID, msg.pack(buf))
    }
}

fn get_expected_payload_standard(index: usize, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
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
            let mut m = VariableSingleArray::default();
            m.message_id = 0x00000001; m.payload_count = 0; m.checksum = 0x0001;
            pack_msg(&m, buf, use_fixed)
        }
        12 => {
            let mut m = VariableSingleArray::default();
            m.message_id = 0x00000002; m.payload_count = 1; m.payload[0] = 42; m.checksum = 0x0002;
            pack_msg(&m, buf, use_fixed)
        }
        13 => {
            let mut m = VariableSingleArray::default();
            m.message_id = 0x00000003;
            m.payload_count = 67;
            for i in 0..67 { m.payload[i] = i as u8; }
            m.checksum = 0x0003;
            pack_msg(&m, buf, use_fixed)
        }
        14 => {
            let mut m = VariableSingleArray::default();
            m.message_id = 0x00000004;
            m.payload_count = 199;
            for i in 0..199 { m.payload[i] = i as u8; }
            m.checksum = 0x0004;
            pack_msg(&m, buf, use_fixed)
        }
        15 => {
            let mut m = VariableSingleArray::default();
            m.message_id = 0x00000005;
            m.payload_count = 200;
            for i in 0..200 { m.payload[i] = (i % 256) as u8; }
            m.checksum = 0x0005;
            pack_msg(&m, buf, use_fixed)
        }
        16 => pack_msg(&create_message_test(), buf, use_fixed),
        17 => pack_msg(&create_nested_enum_idle(), buf, use_fixed),
        18 => pack_msg(&create_nested_enum_active(), buf, use_fixed),
        19 => pack_msg(&create_collision_enum_running(), buf, use_fixed),
        _ => pack_msg(&create_collision_enum_failed(), buf, use_fixed),
    }
}

fn create_nested_enum_idle() -> NestedEnumMessage {
    NestedEnumMessage {
        mode: NestedEnumMessageOperationMode::IDLE,
        value: 0,
        enabled: false,
    }
}

fn create_nested_enum_active() -> NestedEnumMessage {
    NestedEnumMessage {
        mode: NestedEnumMessageOperationMode::ACTIVE,
        value: 42,
        enabled: true,
    }
}

fn create_collision_enum_running() -> CollisionEnumMessage {
    CollisionEnumMessage {
        status: CollisionEnumMessageStatus::RUNNING,
        id: 7,
        time: 1.23,
    }
}

fn create_collision_enum_failed() -> CollisionEnumMessage {
    CollisionEnumMessage {
        status: CollisionEnumMessageStatus::FAILED,
        id: 0,
        time: 0.0,
    }
}

fn get_expected_payload_extended(index: usize, buf: &mut [u8]) -> (u16, usize) {
    // Extended profiles always have a length field, so always use variable pack()
    // Order: ExtId10 (256), ExtId2 (1000), ExtId9 (4000), Large1, Large2, Var×5
    match index {
        0  => pack_msg(&create_ext_id_10(),  buf, false),
        1  => pack_msg(&create_ext_id_2(),   buf, false),
        2  => pack_msg(&create_ext_id_9(),   buf, false),
        3  => pack_msg(&create_ext_large_1(), buf, false),
        4  => pack_msg(&create_ext_large_2(), buf, false),
        5  => pack_msg(&create_ext_var_single(1, 0,   1, 0),  buf, false),
        6  => pack_msg(&create_ext_var_single(2, 1,   2, 42), buf, false),
        7  => pack_msg(&create_ext_var_single(3, 83,  3, 0),  buf, false),
        8  => pack_msg(&create_ext_var_single(4, 249, 4, 0),  buf, false),
        _  => pack_msg(&create_ext_var_single(5, 250, 5, 0),  buf, false),
    }
}

fn get_expected_payload_variable_flag(index: usize, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
    match index {
        0 => pack_msg(&create_non_variable(),                     buf, use_fixed),
        1 => pack_msg(&create_truncation_variable(),              buf, use_fixed),
        2 => pack_msg(&create_nested_variable(),                  buf, use_fixed),
        3 => pack_msg(&create_multiple_arrays(),                  buf, use_fixed),
        4 => pack_msg(&create_mixed_fields(),                     buf, use_fixed),
        5 => pack_msg(&create_variable_envelope_field_order(),    buf, use_fixed),
        _ => pack_msg(&create_variable_envelope_msgid(),          buf, use_fixed),
    }
}

// ============================================================================
// Encode functions (one per test type)
// ============================================================================

fn encode_standard(config: &ProfileConfig, output: &mut [u8]) -> usize {
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
        let mut m = VariableSingleArray::default();
        m.message_id = 0x00000001; m.payload_count = 0; m.checksum = 0x0001;
        enc!(m);
    }
    {
        let mut m = VariableSingleArray::default();
        m.message_id = 0x00000002; m.payload_count = 1; m.payload[0] = 42; m.checksum = 0x0002;
        enc!(m);
    }
    {
        let mut m = VariableSingleArray::default();
        m.message_id = 0x00000003;
        m.payload_count = 67;
        for i in 0..67 { m.payload[i] = i as u8; }
        m.checksum = 0x0003;
        enc!(m);
    }
    {
        let mut m = VariableSingleArray::default();
        m.message_id = 0x00000004;
        m.payload_count = 199;
        for i in 0..199 { m.payload[i] = i as u8; }
        m.checksum = 0x0004;
        enc!(m);
    }
    {
        let mut m = VariableSingleArray::default();
        m.message_id = 0x00000005;
        m.payload_count = 200;
        for i in 0..200 { m.payload[i] = (i % 256) as u8; }
        m.checksum = 0x0005;
        enc!(m);
    }

    enc!(create_message_test());
    enc!(create_nested_enum_idle());
    enc!(create_nested_enum_active());
    enc!(create_collision_enum_running());
    enc!(create_collision_enum_failed());

    written
}

fn encode_extended(config: &ProfileConfig, output: &mut [u8]) -> usize {
    let mut written = 0;

    macro_rules! enc {
        ($msg:expr) => {{
            let frame_len = encode_message_crc(config, &mut output[written..], &$msg, 0);
            written += frame_len;
        }};
    }

    // Encode order: ExtId10, ExtId2, ExtId9, Large1, Large2, Var×5
    enc!(create_ext_id_10());
    enc!(create_ext_id_2());
    enc!(create_ext_id_9());
    enc!(create_ext_large_1());
    enc!(create_ext_large_2());
    enc!(create_ext_var_single(1, 0,   1, 0));
    enc!(create_ext_var_single(2, 1,   2, 42));
    enc!(create_ext_var_single(3, 83,  3, 0));
    enc!(create_ext_var_single(4, 249, 4, 0));
    enc!(create_ext_var_single(5, 250, 5, 0));

    written
}

fn encode_variable_flag(config: &ProfileConfig, output: &mut [u8]) -> usize {
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

    enc!(create_non_variable());
    enc!(create_truncation_variable());
    enc!(create_nested_variable());
    enc!(create_multiple_arrays());
    enc!(create_mixed_fields());
    enc!(create_variable_envelope_field_order());
    enc!(create_variable_envelope_msgid());

    written
}

// ============================================================================
// Generic decode-and-validate
// ============================================================================

fn decode_validate_with<F, G>(
    config: ProfileConfig,
    data: &[u8],
    expected_count: usize,
    get_expected: F,
    msg_info_fn: G,
) -> usize
where
    F: Fn(usize, &mut [u8]) -> (u16, usize),
    G: Fn(u16) -> Option<struct_frame_sdk::MessageInfo>,
{
    let mut reader = AccumulatingReader::new(config, 65536);
    reader.add_data(data);

    let mut count = 0;
    let mut expected_buf = vec![0u8; 65536];

    while let Some(frame) = reader.next(&msg_info_fn) {
        if !frame.valid { break; }

        let (expected_id, expected_len) = get_expected(count, &mut expected_buf);

        if frame.msg_id != expected_id {
            eprintln!("[DECODE] msg {}: expected msg_id=0x{:04x}, got 0x{:04x}", count, expected_id, frame.msg_id);
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
        if count >= expected_count { break; }
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

/// Returns true if the profile uses fixed-size encoding (no length field).
fn profile_uses_fixed(config: &ProfileConfig) -> bool {
    !config.payload.has_length
}

// ============================================================================
// Envelope SDK tests (is_envelope, msgid/field_order discriminator)
// ============================================================================

fn run_envelope_sdk_tests() {
    let mut passed = 0usize;
    let mut failed = 0usize;

    macro_rules! expect {
        ($cond:expr, $name:expr) => {
            if $cond {
                println!("  PASS  {}", $name);
                passed += 1;
            } else {
                eprintln!("  FAIL  {}", $name);
                failed += 1;
            }
        };
    }

    println!("=== Rust EnvelopeSdk tests ===");

    // --- CommandEnvelope with msgid discriminator ---
    let mut env = CommandEnvelope::default();
    env.sequence_number = 42;
    env.priority = 5;
    env.run_immediately = true;
    let mut adc = ADCCommand::default();
    adc.channel = 2;
    adc.sample_rate = 1000;
    adc.enable = true;
    env.set_adc(&adc);

    expect!(env.command_discriminator == ADCCommand::MSG_ID,
            "CommandEnvelope: discriminator == ADCCommand::MSG_ID");

    // Encode with ProfileStandard (MSG_ID=200 fits in u8)
    let mut writer = struct_frame_sdk::new_standard_writer(2048);
    let written = writer.write_crc(&env, 0);
    expect!(written > 0, "CommandEnvelope: write_crc returned > 0");

    let encoded = writer.data().to_vec();
    let mut reader = struct_frame_sdk::new_standard_reader(4096);
    reader.add_data(&encoded);
    let frame = reader.next(&struct_frame_sdk::envelope_test::get_message_info);
    expect!(frame.is_some(), "CommandEnvelope: frame parsed");
    if let Some(f) = frame {
        expect!(f.valid, "CommandEnvelope: frame valid");
        expect!(f.msg_id == CommandEnvelope::MSG_ID, "CommandEnvelope: msg_id matches");
        let decoded = CommandEnvelope::unpack(&f.payload);
        expect!(decoded.is_some(), "CommandEnvelope: unpack succeeded");
        if let Some(d) = decoded {
            expect!(d.sequence_number == 42, "CommandEnvelope: sequence_number round-trips");
            expect!(d.priority == 5, "CommandEnvelope: priority round-trips");
            expect!(d.run_immediately, "CommandEnvelope: run_immediately round-trips");
            expect!(d.command_discriminator == ADCCommand::MSG_ID,
                    "CommandEnvelope: discriminator round-trips");
            let adc2 = d.get_adc();
            expect!(adc2.is_some(), "CommandEnvelope: get_adc() returns Some");
            if let Some(a) = adc2 {
                expect!(a.channel == 2, "CommandEnvelope: adc.channel round-trips");
                expect!(a.sample_rate == 1000, "CommandEnvelope: adc.sample_rate round-trips");
                expect!(a.enable, "CommandEnvelope: adc.enable round-trips");
            }
        }
    }

    // --- RawDataEnvelope with field_order discriminator ---
    let mut raw_env = RawDataEnvelope::default();
    raw_env.priority = 3;
    raw_env.timestamp_us = 999_000;
    let mut sample = RawSamplePayload::default();
    sample.channel = 7;
    sample.value = 2.718_f32;
    sample.flags = 0xBE;
    raw_env.set_sample(&sample);

    // field_order discriminator: sample is 1st field → discriminator == 1
    expect!(raw_env.payload_discriminator == 1,
            "RawDataEnvelope: field_order discriminator == 1 for first variant");

    let mut raw_writer = struct_frame_sdk::new_bulk_writer(2048);
    let raw_written = raw_writer.write_crc(&raw_env, 0);
    expect!(raw_written > 0, "RawDataEnvelope: write_crc returned > 0");

    let raw_encoded = raw_writer.data().to_vec();
    let mut raw_reader = struct_frame_sdk::new_bulk_reader(4096);
    raw_reader.add_data(&raw_encoded);
    let raw_frame = raw_reader.next(&struct_frame_sdk::envelope_test::get_message_info);
    expect!(raw_frame.is_some(), "RawDataEnvelope: frame parsed");
    if let Some(f) = raw_frame {
        expect!(f.valid, "RawDataEnvelope: frame valid");
        let raw_decoded = RawDataEnvelope::unpack(&f.payload);
        expect!(raw_decoded.is_some(), "RawDataEnvelope: unpack succeeded");
        if let Some(d) = raw_decoded {
            expect!(d.priority == 3, "RawDataEnvelope: priority round-trips");
            expect!(d.timestamp_us == 999_000, "RawDataEnvelope: timestamp_us round-trips");
            expect!(d.payload_discriminator == 1,
                    "RawDataEnvelope: discriminator round-trips == 1");
            let s2 = d.get_sample();
            expect!(s2.is_some(), "RawDataEnvelope: get_sample() returns Some");
            if let Some(s) = s2 {
                expect!(s.channel == 7, "RawDataEnvelope: sample.channel round-trips");
                expect!((s.value - 2.718_f32).abs() < 1e-4, "RawDataEnvelope: sample.value round-trips");
                expect!(s.flags == 0xBE, "RawDataEnvelope: sample.flags round-trips");
            }
        }
    }

    println!("\nSummary: {} passed, {} failed", passed, failed);
    if failed > 0 {
        std::process::exit(1);
    }
    std::process::exit(0);
}

// ============================================================================
// Main
// ============================================================================
// Oneof special tests (discriminator=none and multi-oneof)
// ============================================================================

fn run_oneof_special_tests() {
    let mut passed = 0usize;
    let mut failed = 0usize;

    macro_rules! expect {
        ($cond:expr, $name:expr) => {
            if $cond {
                println!("  PASS  {}", $name);
                passed += 1;
            } else {
                eprintln!("  FAIL  {}", $name);
                failed += 1;
            }
        };
    }

    println!("=== Rust oneof special tests ===");

    // --- NoneDiscriminatorMessage: no discriminator field, data bytes preserved ---
    let mut msg1 = NoneDiscriminatorMessage::default();
    msg1.header = 0xAB;
    // Set a BasicTypesMessage into the union bytes
    let mut basic = BasicTypesMessage::default();
    basic.small_int = -42;
    basic.medium_uint = 5000;
    msg1.set_basic(&basic);

    // Serialize and deserialize via pack/unpack
    let mut buf1 = [0u8; NoneDiscriminatorMessage::MAX_SIZE];
    msg1.pack_max_size(&mut buf1);
    let dec1 = NoneDiscriminatorMessage::unpack(&buf1);
    expect!(dec1.is_some(), "NoneDiscriminator: unpack succeeds");
    if let Some(d) = dec1 {
        expect!(d.header == 0xAB, "NoneDiscriminator: header round-trips");
        // Without a discriminator the receiver must know which variant to use
        let b = d.get_basic();
        expect!(b.is_some(), "NoneDiscriminator: get_basic() returns Some");
        if let Some(b) = b {
            expect!(b.small_int == -42, "NoneDiscriminator: basic.small_int round-trips");
            expect!(b.medium_uint == 5000, "NoneDiscriminator: basic.medium_uint round-trips");
        }
    }

    // --- MultiOneofMessage: two independent oneofs ---
    let mut msg2 = MultiOneofMessage::default();
    msg2.selector = 7;
    // first_payload: BasicTypesMessage variant (msgid discriminator auto-set by set_basic)
    let mut basic2 = BasicTypesMessage::default();
    basic2.small_int = 99;
    msg2.set_basic(&basic2);
    // second_payload: discriminator=none, use msg_payload variant (Message type)
    let mut msg_payload = Message::default();
    msg_payload.severity = MsgSeverity::SEV_WARN;
    msg2.set_msg_payload(&msg_payload);

    let mut buf2 = [0u8; MultiOneofMessage::MAX_SIZE];
    msg2.pack_max_size(&mut buf2);
    let dec2 = MultiOneofMessage::unpack(&buf2);
    expect!(dec2.is_some(), "MultiOneof: unpack succeeds");
    if let Some(d) = dec2 {
        expect!(d.selector == 7, "MultiOneof: selector round-trips");
        expect!(d.first_payload_discriminator == BasicTypesMessage::MSG_ID,
                "MultiOneof: first_payload discriminator is BasicTypesMessage MSG_ID");
        let b2 = d.get_basic();
        expect!(b2.is_some(), "MultiOneof: get_basic() returns Some");
        if let Some(b) = b2 {
            expect!(b.small_int == 99, "MultiOneof: basic.small_int round-trips");
        }
        // second_payload: no discriminator — caller must know which variant is active
        let mp = d.get_msg_payload();
        expect!(mp.is_some(), "MultiOneof: get_msg_payload() returns Some");
        if let Some(m) = mp {
            expect!(m.severity == MsgSeverity::SEV_WARN, "MultiOneof: msg_payload.severity round-trips");
        }
    }

    println!("\nSummary: {} passed, {} failed", passed, failed);
    if failed > 0 {
        std::process::exit(1);
    }
    std::process::exit(0);
}

// ============================================================================
// Streaming tests (AccumulatingReader::push_byte)
// ============================================================================

fn run_streaming_tests() {
    let mut passed = 0usize;
    let mut failed = 0usize;

    macro_rules! expect {
        ($cond:expr, $name:expr) => {
            if $cond {
                println!("  PASS  {}", $name);
                passed += 1;
            } else {
                eprintln!("  FAIL  {}", $name);
                failed += 1;
            }
        };
    }

    println!("\n========================================");
    println!("STREAMING TESTS - Rust AccumulatingReader (push_byte)");
    println!("========================================\n");

    // Helper: encode a BasicTypesMessage with the given profile, returning the raw frame bytes.
    fn encode_frame(config: struct_frame_sdk::ProfileConfig, regular_int: i32) -> Vec<u8> {
        let mut msg = BasicTypesMessage::default();
        msg.regular_int = regular_int;
        let mut writer = struct_frame_sdk::BufferWriter::new(config, 512);
        writer.write_crc(&msg, 0);
        writer.data().to_vec()
    }

    // Test 1: Standard profile – push bytes one-by-one, last byte completes the frame
    {
        let frame = encode_frame(PROFILE_STANDARD_CONFIG, 9876);
        let mut reader = struct_frame_sdk::new_standard_reader(512);
        let mut result: Option<struct_frame_sdk::FrameMsgInfo> = None;
        for (i, &byte) in frame.iter().enumerate() {
            let r = reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info);
            if i < frame.len() - 1 {
                if r.is_some() { failed += 1; break; }
            } else {
                result = r;
            }
        }
        let valid = result.as_ref().map_or(false, |f| {
            f.valid
                && f.msg_id == BasicTypesMessage::MSG_ID
                && BasicTypesMessage::unpack(&f.payload)
                    .map_or(false, |m| m.regular_int == 9876)
        });
        expect!(valid, "Standard profile: push_byte decodes complete frame");
    }

    // Test 2: Sensor profile (minimal, no CRC) – push bytes one-by-one
    {
        let mut msg = BasicTypesMessage::default();
        msg.small_int = 7;
        let mut writer = struct_frame_sdk::BufferWriter::new(PROFILE_SENSOR_CONFIG, 512);
        writer.write_minimal(&msg);
        let frame = writer.data().to_vec();
        let mut reader = struct_frame_sdk::new_sensor_reader(512);
        let mut last: Option<struct_frame_sdk::FrameMsgInfo> = None;
        for &byte in &frame {
            last = reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info);
        }
        let valid = last.as_ref().map_or(false, |f| f.valid && f.msg_id == BasicTypesMessage::MSG_ID);
        expect!(valid, "Sensor profile: push_byte decodes minimal frame");
    }

    // Test 3: Two consecutive frames decoded via push_byte
    {
        let frame1 = encode_frame(PROFILE_STANDARD_CONFIG, 1111);
        let frame2 = encode_frame(PROFILE_STANDARD_CONFIG, 2222);
        let mut reader = struct_frame_sdk::new_standard_reader(512);
        let mut r1: Option<struct_frame_sdk::FrameMsgInfo> = None;
        for &byte in &frame1 {
            r1 = reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info);
        }
        let mut r2: Option<struct_frame_sdk::FrameMsgInfo> = None;
        for &byte in &frame2 {
            r2 = reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info);
        }
        let v1 = r1.as_ref().map_or(false, |f| {
            f.valid && BasicTypesMessage::unpack(&f.payload).map_or(false, |m| m.regular_int == 1111)
        });
        let v2 = r2.as_ref().map_or(false, |f| {
            f.valid && BasicTypesMessage::unpack(&f.payload).map_or(false, |m| m.regular_int == 2222)
        });
        expect!(v1, "Two consecutive frames: first frame decodes correctly");
        expect!(v2, "Two consecutive frames: second frame decodes correctly");
    }

    // Test 4: Garbage bytes before a valid frame are silently discarded
    {
        let frame = encode_frame(PROFILE_STANDARD_CONFIG, 5555);
        let mut reader = struct_frame_sdk::new_standard_reader(512);
        // Push garbage that doesn't contain the start-byte sequence
        let garbage: &[u8] = &[0x00, 0x11, 0x22, 0x33, 0x44, 0x55];
        let mut garbage_fired = false;
        for &byte in garbage {
            if reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info).is_some() {
                garbage_fired = true;
            }
        }
        let mut result: Option<struct_frame_sdk::FrameMsgInfo> = None;
        for &byte in &frame {
            result = reader.push_byte(byte, &struct_frame_sdk::serialization_test::get_message_info);
        }
        expect!(!garbage_fired, "Garbage prefix: garbage bytes do not produce a frame");
        let valid = result.as_ref().map_or(false, |f| {
            f.valid && BasicTypesMessage::unpack(&f.payload).map_or(false, |m| m.regular_int == 5555)
        });
        expect!(valid, "Garbage prefix: real frame after garbage is decoded correctly");
    }

    println!("\n========================================");
    println!("Summary: {} passed, {} failed", passed, failed);
    println!("========================================\n");
    if failed > 0 {
        std::process::exit(1);
    }
    std::process::exit(0);
}

// ============================================================================
// SDK subscribe / dispatch tests
// ============================================================================

fn run_sdk_subscribe_tests() {
    let mut passed = 0usize;
    let mut failed = 0usize;

    macro_rules! expect {
        ($cond:expr, $name:expr) => {
            if $cond {
                println!("  PASS  {}", $name);
                passed += 1;
            } else {
                eprintln!("  FAIL  {}", $name);
                failed += 1;
            }
        };
    }

    println!("\n========================================");
    println!("SDK SUBSCRIBE/DISPATCH TESTS - Rust");
    println!("========================================\n");

    fn encode_basic(regular_int: i32) -> Vec<u8> {
        let mut msg = BasicTypesMessage::default();
        msg.regular_int = regular_int;
        let mut writer = struct_frame_sdk::BufferWriter::new(PROFILE_STANDARD_CONFIG, 512);
        writer.write_crc(&msg, 0);
        writer.data().to_vec()
    }

    fn expected_basic_payload(regular_int: i32) -> Vec<u8> {
        let mut msg = BasicTypesMessage::default();
        msg.regular_int = regular_int;
        let mut payload = vec![0u8; BasicTypesMessage::MAX_SIZE];
        let n = msg.pack(&mut payload);
        payload[..n].to_vec()
    }

    // Test 1: subscribe + inject_data dispatches to handler
    {
        let reader = struct_frame_sdk::new_standard_reader(512);
        let mut sdk = StructFrameSdk::new(reader, struct_frame_sdk::serialization_test::get_message_info);

        let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::<(u16, i32, Vec<u8>)>::new()));
        let received2 = received.clone();
        sdk.subscribe(BasicTypesMessage::MSG_ID, move |frame| {
            if let Some(m) = BasicTypesMessage::unpack(&frame.payload) {
            received2.lock().unwrap().push((frame.msg_id, m.regular_int, frame.payload.clone()));
            }
        });

        sdk.inject_data(&encode_basic(42));
        let vals = received.lock().unwrap();
        expect!(vals.len() == 1, "subscribe: handler invoked on inject_data");
        expect!(vals.first().map(|v| v.0) == Some(BasicTypesMessage::MSG_ID),
            "subscribe: msg_id value correct");
        expect!(vals.first().map(|v| v.1) == Some(42), "subscribe: regular_int value correct");
        expect!(vals.first().map(|v| v.2.as_slice()) == Some(expected_basic_payload(42).as_slice()),
            "subscribe: payload bytes preserved");
    }

    // Test 2: multiple handlers for same message ID
    {
        let reader = struct_frame_sdk::new_standard_reader(512);
        let mut sdk = StructFrameSdk::new(reader, struct_frame_sdk::serialization_test::get_message_info);

        let count_a = std::sync::Arc::new(std::sync::Mutex::new(0usize));
        let count_b = std::sync::Arc::new(std::sync::Mutex::new(0usize));
        let ca = count_a.clone();
        let cb = count_b.clone();
        sdk.subscribe(BasicTypesMessage::MSG_ID, move |_| { *ca.lock().unwrap() += 1; });
        sdk.subscribe(BasicTypesMessage::MSG_ID, move |_| { *cb.lock().unwrap() += 1; });

        sdk.inject_data(&encode_basic(1));
        expect!(*count_a.lock().unwrap() == 1, "multiple handlers: first handler fires");
        expect!(*count_b.lock().unwrap() == 1, "multiple handlers: second handler fires");
    }

    // Test 3: unsubscribe stops handler delivery
    {
        let reader = struct_frame_sdk::new_standard_reader(512);
        let mut sdk = StructFrameSdk::new(reader, struct_frame_sdk::serialization_test::get_message_info);

        let count = std::sync::Arc::new(std::sync::Mutex::new(0usize));
        let c = count.clone();
        let sub = sdk.subscribe(BasicTypesMessage::MSG_ID, move |_| { *c.lock().unwrap() += 1; });

        sdk.inject_data(&encode_basic(1));
        expect!(*count.lock().unwrap() == 1, "unsubscribe: handler fires before unsubscribe");

        sdk.unsubscribe(sub);
        sdk.inject_data(&encode_basic(2));
        expect!(*count.lock().unwrap() == 1, "unsubscribe: handler silent after unsubscribe");
    }

    // Test 4: no matching handler registered – frame does not dispatch
    {
        let reader = struct_frame_sdk::new_standard_reader(512);
        let mut sdk = StructFrameSdk::new(reader, struct_frame_sdk::serialization_test::get_message_info);

        let count = std::sync::Arc::new(std::sync::Mutex::new(0usize));
        let c = count.clone();
        // Subscribe to a different ID than the frame under test.
        sdk.subscribe(SerializationTestMessage::MSG_ID, move |_| { *c.lock().unwrap() += 1; });

        sdk.inject_data(&encode_basic(99));
        expect!(*count.lock().unwrap() == 0,
                "no handler: unmatched message id does not dispatch");
    }

    // Test 5: push_byte byte-by-byte dispatches on the final byte
    {
        let reader = struct_frame_sdk::new_standard_reader(512);
        let mut sdk = StructFrameSdk::new(reader, struct_frame_sdk::serialization_test::get_message_info);

        let received = std::sync::Arc::new(std::sync::Mutex::new(Vec::<(u16, i32, Vec<u8>)>::new()));
        let recv2 = received.clone();
        sdk.subscribe(BasicTypesMessage::MSG_ID, move |frame| {
            if let Some(m) = BasicTypesMessage::unpack(&frame.payload) {
                recv2.lock().unwrap().push((frame.msg_id, m.regular_int, frame.payload.clone()));
            }
        });

        let frame = encode_basic(777);
        let mut dispatched_count = 0usize;
        for &byte in &frame {
            if sdk.push_byte(byte) { dispatched_count += 1; }
        }
        expect!(dispatched_count == 1, "push_byte: exactly one frame dispatched");
        let vals = received.lock().unwrap();
        expect!(vals.first().map(|v| v.0) == Some(BasicTypesMessage::MSG_ID),
            "push_byte: msg_id value correct");
        expect!(vals.first().map(|v| v.1) == Some(777), "push_byte: regular_int value correct");
        expect!(vals.first().map(|v| v.2.as_slice()) == Some(expected_basic_payload(777).as_slice()),
            "push_byte: payload bytes preserved");
    }

    println!("\n========================================");
    println!("Summary: {} passed, {} failed", passed, failed);
    println!("========================================\n");
    if failed > 0 {
        std::process::exit(1);
    }
    std::process::exit(0);
}

// ============================================================================

// ============================================================================
// Cross-version wire-evolution interop tests (v1 base-only <-> v2 +extensions)
//
// Unlike the single-schema round-trip runner, this uses two SEPARATELY
// generated schema versions of the same messages:
//   - wire_evolution_v1 -- base fields only (older, extension-unaware)
//   - wire_evolution_v2 -- base fields + `extensions_start` extension fields
// Each side has its own structs, magic constants and `get_message_info`,
// exactly as two independently built code-bases would.  The scenarios mirror
// the project's interop plan (1-10) over the length-bearing and length-less profiles.
// ============================================================================
fn run_wire_evolution_interop_tests() -> ! {
    use struct_frame_sdk::frame_base::{FrameMsgInfo, MessageInfo, StructFrameMessage};
    use struct_frame_sdk::{BufferReader, BufferWriter};
    use struct_frame_sdk::wire_evolution_v1 as v1;
    use struct_frame_sdk::wire_evolution_v2 as v2;

    let mut passed = 0usize;
    let mut failed = 0usize;
    macro_rules! check {
        ($cond:expr, $msg:expr) => {
            if $cond {
                println!("  [PASS] {}", $msg);
                passed += 1;
            } else {
                println!("  [FAIL] {}", $msg);
                failed += 1;
            }
        };
    }

    fn encode<M: StructFrameMessage>(config: ProfileConfig, msg: &M) -> Vec<u8> {
        let mut w = BufferWriter::new(config, 256);
        w.write_crc(msg, 0);
        w.data().to_vec()
    }
    fn parse(
        config: ProfileConfig,
        buf: Vec<u8>,
        gmi: &dyn Fn(u16) -> Option<MessageInfo>,
    ) -> Option<FrameMsgInfo> {
        let mut r = BufferReader::new(config, buf);
        r.next(gmi)
    }

    let profiles: [(ProfileConfig, &str); 3] = [
        (PROFILE_STANDARD_CONFIG, "standard"),
        (PROFILE_BULK_CONFIG, "bulk"),
        (PROFILE_NETWORK_CONFIG, "network"),
    ];

    // -- Scenario 1: newer sender -> older receiver over length-bearing profiles
    println!("Scenario 1: newer sender -> older receiver (length-bearing)");
    for (config, name) in profiles.iter() {
        let mut m = v2::BaseExtensionMessage::default();
        m.header = 0xBEEF;
        m.seq = 42;
        m.crc_seed = 0xDEADC0DE;
        let buf = encode(*config, &m);
        let frame = parse(*config, buf, &v1::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            format!("[S1/{}] v2->v1 frame validates CRC (magic from base)", name)
        );
        if let Some(f) = frame {
            let d = v1::BaseExtensionMessage::unpack(&f.payload);
            check!(
                d.map_or(false, |x| x.header == 0xBEEF && x.seq == 42),
                format!("[S1/{}] v1 decodes base; trailing ext bytes ignored", name)
            );
        }
    }

    // -- Scenario 2: older sender -> newer receiver (zero-fill extensions)
    println!("\nScenario 2: older sender -> newer receiver (zero-fill)");
    {
        let mut m = v1::BaseExtensionMessage::default();
        m.header = 0x1234;
        m.seq = 7;
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v2::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S2] v1->v2 base-only frame validates CRC"
        );
        if let Some(f) = frame {
            // Newer receiver zero-fills the missing extension bytes before decoding.
            let mut padded = vec![0u8; v2::BaseExtensionMessage::MAX_SIZE];
            padded[..f.payload.len()].copy_from_slice(&f.payload);
            let d = v2::BaseExtensionMessage::unpack(&padded);
            check!(
                d.as_ref().map_or(false, |x| x.header == 0x1234 && x.seq == 7),
                "[S2] v2 decodes base fields correctly"
            );
            check!(
                d.map_or(false, |x| x.crc_seed == 0),
                "[S2] v2 extension field zero-filled to default"
            );
        }
    }

    // -- Scenario 3: same-version sanity (v2 -> v2 with extension variant)
    println!("\nScenario 3: same-version sanity (v2 -> v2)");
    {
        let mut m = v2::OneOfExtensionMessage::default();
        m.device_id = 2;
        let mut c = v2::ExtCommandC::default();
        c.value_c = 3.14;
        c.mode_c = 2;
        m.set_cmd_c(&c);
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v2::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S3] v2->v2 (ext variant) frame validates CRC"
        );
        if let Some(f) = frame {
            let d = v2::OneOfExtensionMessage::unpack(&f.payload);
            check!(
                d.map_or(false, |x| x.command_discriminator == 3
                    && x.get_cmd_c().map_or(false, |cc| (cc.value_c - 3.14).abs() < 1e-4)),
                "[S3] v2 round-trips the extension variant"
            );
        }
    }

    // -- Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
    println!("\nScenario 4: newer ext oneof variant -> older receiver");
    {
        let mut m = v2::OneOfExtensionMessage::default();
        m.device_id = 9;
        let mut c = v2::ExtCommandD::default();
        c.value_d = 2.718281828;
        m.set_cmd_d(&c);
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v1::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S4] v2 ext-variant -> v1 frame validates CRC"
        );
        if let Some(f) = frame {
            let d = v1::OneOfExtensionMessage::unpack(&f.payload);
            check!(
                d.as_ref().map_or(false, |x| x.device_id == 9),
                "[S4] v1 still decodes the base header field"
            );
            // v1 knows nothing about discriminator 4; it must preserve the raw
            // value without corrupting the base field.
            check!(
                d.map_or(false, |x| x.command_discriminator == 4),
                "[S4] v1 preserves unknown ext discriminator without corruption"
            );
        }
    }

    // -- Scenario 5: older base oneof variant -> newer receiver decodes correctly
    println!("\nScenario 5: older base oneof variant -> newer receiver");
    {
        let mut m = v1::OneOfExtensionMessage::default();
        m.device_id = 5;
        let mut b = v1::BaseCommandB::default();
        b.value_b = -1234;
        b.active_b = true;
        m.set_cmd_b(&b);
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v2::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S5] v1 base-variant -> v2 frame validates CRC"
        );
        if let Some(f) = frame {
            let mut padded = vec![0u8; v2::OneOfExtensionMessage::MAX_SIZE];
            padded[..f.payload.len()].copy_from_slice(&f.payload);
            let d = v2::OneOfExtensionMessage::unpack(&padded);
            check!(
                d.map_or(false, |x| x.command_discriminator == 2
                    && x.get_cmd_b().map_or(false, |cb| cb.value_b == -1234)),
                "[S5] v2 decodes the older base oneof variant correctly"
            );
        }
    }

    // -- Scenario 6: multi-oneof, ext only in the second union
    println!("\nScenario 6: multi-oneof (ext only in 2nd union)");
    {
        let mut m = v2::MultiOneOfExtensionMessage::default();
        m.priority = 3;
        let mut a = v2::BaseCommandA::default();
        a.value_a = 100;
        a.flags_a = 5;
        m.set_first_a(&a);
        let mut c = v2::ExtCommandC::default();
        c.value_c = 2.71;
        c.mode_c = 1;
        m.set_second_ext(&c);
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v1::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC"
        );
        if let Some(f) = frame {
            let d = v1::MultiOneOfExtensionMessage::unpack(&f.payload);
            check!(
                d.map_or(false, |x| x.priority == 3
                    && x.base_union_discriminator == 1
                    && x.get_first_a().map_or(false, |fa| fa.value_a == 100)),
                "[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second"
            );
        }
    }

    // -- Scenario 7: corrupted extension bytes invalidate the full CRC
    println!("\nScenario 7: corrupted extension bytes invalidate CRC");
    {
        let mut m = v2::BaseExtensionMessage::default();
        m.header = 0xBEEF;
        m.seq = 42;
        m.crc_seed = 0xDEADC0DE;
        let mut buf = encode(PROFILE_STANDARD_CONFIG, &m);
        // Probe the frame layout (msg_len) to locate the extension region.
        let probe = parse(PROFILE_STANDARD_CONFIG, buf.clone(), &v1::get_message_info);
        if let Some(p) = probe {
            // Footer is 2 bytes; the extension region starts BASE_SIZE bytes into
            // the payload, which itself starts (frame_size - footer - msg_len) in.
            let payload_off = buf.len() - 2 - p.msg_len;
            let ext_off = payload_off + v2::BaseExtensionMessage::BASE_SIZE;
            buf[ext_off] ^= 0xFF;
        }
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v1::get_message_info);
        check!(
            frame.is_none(),
            "[S7] corrupted extension byte invalidates full CRC"
        );
    }

    println!("\nScenario 8: truncated payload rejected");
    {
        let mut m = v1::BaseExtensionMessage::default();
        m.header = 1;
        m.seq = 2;
        let mut buf = encode(PROFILE_STANDARD_CONFIG, &m);
        // Drop the last byte — fewer bytes than the length field claims.
        buf.pop();
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v1::get_message_info);
        check!(
            frame.map_or(true, |f| !f.valid),
            "[S8] truncated payload (fewer bytes than length claims) is rejected"
        );
    }

    println!("\nScenario 9: length-less profile guard (IPC)");
    {
        // Positive: same-version v2 over IPC validates.
        let mut same = v2::BaseExtensionMessage::default();
        same.header = 0xAA;
        same.seq = 5;
        same.crc_seed = 0x99;
        let mut w = BufferWriter::new(PROFILE_IPC_CONFIG, 256);
        w.write_minimal(&same);
        let frame_buf = w.data().to_vec();
        let mut r = BufferReader::new(PROFILE_IPC_CONFIG, frame_buf);
        let frame = r.next(&v2::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S9] IPC same-version v2 frame validates"
        );

        // Negative: base-only v1 frame (shorter) rejected by newer v2 receiver.
        let mut older = v1::BaseExtensionMessage::default();
        older.header = 0xAA;
        older.seq = 5;
        let mut w2 = BufferWriter::new(PROFILE_IPC_CONFIG, 256);
        w2.write_minimal(&older);
        let frame_buf2 = w2.data().to_vec();
        let mut r2 = BufferReader::new(PROFILE_IPC_CONFIG, frame_buf2);
        let frame2 = r2.next(&v2::get_message_info);
        check!(
            frame2.map_or(true, |f| !f.valid),
            "[S9] IPC base-only older frame is rejected by newer receiver \
             (both sides must agree on size)"
        );
    }

    println!("\nScenario 10: variable base + trailing extension (both directions)");
    {
        // Newer -> older: v1 locates variable base, ignores trailing ext bytes.
        let mut m = v2::VariableExtensionMessage::default();
        m.node_id = 7;
        m.readings_count = 3;
        m.readings[0] = 10; m.readings[1] = 20; m.readings[2] = 30;
        m.ext_timestamp = 0x12345678;
        let buf = encode(PROFILE_STANDARD_CONFIG, &m);
        let frame = parse(PROFILE_STANDARD_CONFIG, buf, &v1::get_message_info);
        check!(
            frame.as_ref().map_or(false, |f| f.valid),
            "[S10] v2 variable+ext -> v1 validates CRC"
        );
        if let Some(f) = frame {
            let d = v1::VariableExtensionMessage::unpack(&f.payload);
            check!(
                d.map_or(false, |x|
                    x.node_id == 7
                    && x.readings_count == 3
                    && x.readings[0] == 10
                    && x.readings[1] == 20
                    && x.readings[2] == 30),
                "[S10] v1 locates/decodes variable base; trailing ext bytes ignored"
            );
        }

        // Older -> newer: v2 zero-fills the trailing extension field.
        let mut m1 = v1::VariableExtensionMessage::default();
        m1.node_id = 9;
        m1.readings_count = 2;
        m1.readings[0] = 1; m1.readings[1] = 2;
        let buf2 = encode(PROFILE_STANDARD_CONFIG, &m1);
        let frame2 = parse(PROFILE_STANDARD_CONFIG, buf2, &v2::get_message_info);
        check!(
            frame2.as_ref().map_or(false, |f| f.valid),
            "[S10] v1 variable (base-only) -> v2 validates CRC"
        );
        if let Some(f2) = frame2 {
            // Pad payload to MAX_SIZE so unpack() uses fixed-size read (zero-fills ext).
            let mut padded = vec![0u8; v2::VariableExtensionMessage::MAX_SIZE];
            let copy_len = f2.payload.len().min(padded.len());
            padded[..copy_len].copy_from_slice(&f2.payload[..copy_len]);
            let d2 = v2::VariableExtensionMessage::unpack(&padded);
            check!(
                d2.as_ref().map_or(false, |x|
                    x.node_id == 9
                    && x.readings_count == 2
                    && x.readings[0] == 1
                    && x.readings[1] == 2),
                "[S10] v2 locates variable base after cross-version decode"
            );
            check!(
                d2.map_or(false, |x| x.ext_timestamp == 0),
                "[S10] v2 zero-fills the trailing extension field"
            );
        }
    }

    println!("\nResults: {} passed, {} failed", passed, failed);
    std::process::exit(if failed == 0 { 0 } else { 1 });
}

fn main() {
    let args: Vec<String> = std::env::args().collect();

    // Cross-version (v1<->v2) wire-evolution interop tests.
    if args.len() >= 2 && args[1] == "test_wire_evolution_interop" {
        run_wire_evolution_interop_tests();
        // run_wire_evolution_interop_tests() always exits.
    }

    // Envelope SDK test can be invoked without the standard runner args.
    if args.len() >= 2 && args[1] == "test_envelope_sdk" {
        run_envelope_sdk_tests();
        // run_envelope_sdk_tests() always exits.
    }

    // Oneof special tests (discriminator=none, multi-oneof)
    if args.len() >= 2 && args[1] == "test_oneof_special" {
        run_oneof_special_tests();
        // run_oneof_special_tests() always exits.
    }

    // Streaming (push_byte) tests
    if args.len() >= 2 && args[1] == "test_streaming" {
        run_streaming_tests();
        // run_streaming_tests() always exits.
    }

    // SDK subscribe/dispatch tests
    if args.len() >= 2 && args[1] == "test_sdk_subscribe" {
        run_sdk_subscribe_tests();
        // run_sdk_subscribe_tests() always exits.
    }

    if args.len() < 5 {
        eprintln!("Usage:");
        eprintln!("  {} <runner> <mode> <profile> <file>", args[0]);
        eprintln!("\nRunners: test_standard, test_extended, test_variable_flag, test_envelope_sdk, test_oneof_special");
        eprintln!("Modes:   encode, decode, both");
        eprintln!("Profiles: standard, sensor, ipc, bulk, network");
        std::process::exit(1);
    }

    // Verify enum Debug formatting (enum-to-string) before dispatch
    assert_eq!(format!("{:?}", Priority::HIGH), "HIGH", "Rust Priority::HIGH Debug should be \"HIGH\"");
    assert_eq!(format!("{:?}", Priority::LOW), "LOW", "Rust Priority::LOW Debug should be \"LOW\"");
    assert_eq!(format!("{:?}", Priority::MEDIUM), "MEDIUM", "Rust Priority::MEDIUM Debug should be \"MEDIUM\"");
    assert_eq!(format!("{:?}", Priority::CRITICAL), "CRITICAL", "Rust Priority::CRITICAL Debug should be \"CRITICAL\"");
    assert_eq!(format!("{:?}", Status::ACTIVE), "ACTIVE", "Rust Status::ACTIVE Debug should be \"ACTIVE\"");
    assert_eq!(format!("{:?}", Status::INACTIVE), "INACTIVE", "Rust Status::INACTIVE Debug should be \"INACTIVE\"");

    let runner_name = args[1].as_str();
    let operation   = args[2].as_str();
    let profile     = args[3].as_str();
    let file_path   = &args[4];
    let config = get_profile_config(profile);
    let use_fixed = profile_uses_fixed(&config);

    // Select expected message count and encode/decode functions
    let (message_count, do_encode, do_decode): (
        usize,
        Box<dyn Fn(&ProfileConfig, &mut [u8]) -> usize>,
        Box<dyn Fn(ProfileConfig, &[u8]) -> usize>,
    ) = match runner_name {
        "test_standard" => (
            STANDARD_MESSAGE_COUNT,
            Box::new(|cfg, buf| encode_standard(cfg, buf)),
            Box::new(move |cfg, data| {
                decode_validate_with(cfg, data, STANDARD_MESSAGE_COUNT, move |i, buf| {
                    get_expected_payload_standard(i, buf, use_fixed)
                }, struct_frame_sdk::serialization_test::get_message_info)
            }),
        ),
        "test_extended" => (
            EXTENDED_MESSAGE_COUNT,
            Box::new(|cfg, buf| encode_extended(cfg, buf)),
            Box::new(|cfg, data| {
                decode_validate_with(cfg, data, EXTENDED_MESSAGE_COUNT, |i, buf| {
                    get_expected_payload_extended(i, buf)
                }, struct_frame_sdk::extended_test::get_message_info)
            }),
        ),
        "test_variable_flag" => (
            VARIABLE_FLAG_MESSAGE_COUNT,
            Box::new(|cfg, buf| encode_variable_flag(cfg, buf)),
            Box::new(move |cfg, data| {
                decode_validate_with(cfg, data, VARIABLE_FLAG_MESSAGE_COUNT, move |i, buf| {
                    get_expected_payload_variable_flag(i, buf, use_fixed)
                }, struct_frame_sdk::serialization_test::get_message_info)
            }),
        ),
        _ => {
            eprintln!("Unknown runner: {}", runner_name);
            std::process::exit(1);
        }
    };

    match operation {
        "encode" => {
            let mut buffer = vec![0u8; BUFFER_SIZE];
            let written = do_encode(&config, &mut buffer);
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
            let count = do_decode(config, &data);
            if count != message_count {
                eprintln!("[DECODE] FAILED: {}/{} messages validated", count, message_count);
                std::process::exit(1);
            }
            println!("[DECODE] SUCCESS: {} messages validated", count);
            std::process::exit(0);
        }
        "both" => {
            let mut buffer = vec![0u8; BUFFER_SIZE];
            let written = do_encode(&config, &mut buffer);
            if written == 0 {
                eprintln!("[BOTH] FAILED: Encoding error");
                std::process::exit(1);
            }
            let count = do_decode(config, &buffer[..written]);
            if count != message_count {
                eprintln!("[BOTH] FAILED: {}/{} messages validated", count, message_count);
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

