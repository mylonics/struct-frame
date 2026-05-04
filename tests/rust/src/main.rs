// Rust test harness for struct-frame generated code
// Tests cross-platform encoding/decoding compatibility
//
// Usage: struct_frame_rust_tests <runner> <mode> <profile> <file>
//   runner:  test_standard | test_extended | test_variable_flag
//   mode:    encode | decode | both
//   profile: standard | sensor | ipc | bulk | network
//   file:    path to binary output/input file

use struct_frame_sdk::extended_test::*;
use struct_frame_sdk::get_message_info;
use struct_frame_sdk::serialization_test::*;
use struct_frame_sdk::{
    encode_message_crc, encode_message_minimal, AccumulatingReader, ProfileConfig,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG, PROFILE_SENSOR_CONFIG,
    PROFILE_STANDARD_CONFIG,
};

const BUFFER_SIZE: usize = 65536;
const STANDARD_MESSAGE_COUNT: usize = 17;
const EXTENDED_MESSAGE_COUNT: usize = 17;
const VARIABLE_FLAG_MESSAGE_COUNT: usize = 5;

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

fn create_ext_id_1() -> ExtendedIdMessage1 {
    let mut msg = ExtendedIdMessage1::default();
    msg.sequence_number = 12345678;
    let s = b"Test Label Extended 1";
    msg.label[..s.len()].copy_from_slice(s);
    msg.value = 3.14159f32;
    msg.enabled = true;
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

fn create_ext_id_3() -> ExtendedIdMessage3 {
    let mut msg = ExtendedIdMessage3::default();
    msg.timestamp = 1704067200000000u64;
    msg.temperature = -40;
    msg.humidity = 85;
    let loc = b"Sensor Room A";
    msg.location[..loc.len()].copy_from_slice(loc);
    msg
}

fn create_ext_id_4() -> ExtendedIdMessage4 {
    let mut msg = ExtendedIdMessage4::default();
    msg.event_id = 999999;
    msg.event_type = 42;
    msg.event_time = 1704067200000i64;
    let data = b"Event payload with extended message ID";
    msg.event_data_length = data.len() as u8;
    msg.event_data[..data.len()].copy_from_slice(data);
    msg
}

fn create_ext_id_5() -> ExtendedIdMessage5 {
    let mut msg = ExtendedIdMessage5::default();
    msg.x_position = 100.5f32;
    msg.y_position = -200.25f32;
    msg.z_position = 50.125f32;
    msg.frame_number = 1000000;
    msg
}

fn create_ext_id_6() -> ExtendedIdMessage6 {
    let mut msg = ExtendedIdMessage6::default();
    msg.command_id = -12345;
    msg.parameter1 = 1000;
    msg.parameter2 = 2000;
    msg.acknowledged = false;
    let name = b"CALIBRATE_SENSOR";
    msg.command_name[..name.len()].copy_from_slice(name);
    msg
}

fn create_ext_id_7() -> ExtendedIdMessage7 {
    let mut msg = ExtendedIdMessage7::default();
    msg.counter = 4294967295u32;
    msg.average = 123.456789;
    msg.minimum = -999.99f32;
    msg.maximum = 999.99f32;
    msg
}

fn create_ext_id_8() -> ExtendedIdMessage8 {
    let mut msg = ExtendedIdMessage8::default();
    msg.level = 255;
    msg.offset = -32768;
    msg.duration = 86400000;
    let tag = b"TEST123";
    msg.tag[..tag.len()].copy_from_slice(tag);
    msg
}

fn create_ext_id_9() -> ExtendedIdMessage9 {
    let mut msg = ExtendedIdMessage9::default();
    msg.big_number = -9223372036854775807i64;
    msg.big_unsigned = 18446744073709551615u64;
    msg.precision_value = 1.7976931348623157e+308f64;
    msg
}

fn create_ext_id_10() -> ExtendedIdMessage10 {
    let mut msg = ExtendedIdMessage10::default();
    msg.small_value = 256;
    let text = b"Boundary Test";
    msg.short_text[..text.len()].copy_from_slice(text);
    msg.flag = true;
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
        _ => pack_msg(&create_message_test(), buf, use_fixed),
    }
}

fn get_expected_payload_extended(index: usize, buf: &mut [u8]) -> (u16, usize) {
    // Extended profiles always have a length field, so always use variable pack()
    match index {
        0  => pack_msg(&create_ext_id_1(),  buf, false),
        1  => pack_msg(&create_ext_id_2(),  buf, false),
        2  => pack_msg(&create_ext_id_3(),  buf, false),
        3  => pack_msg(&create_ext_id_4(),  buf, false),
        4  => pack_msg(&create_ext_id_5(),  buf, false),
        5  => pack_msg(&create_ext_id_6(),  buf, false),
        6  => pack_msg(&create_ext_id_7(),  buf, false),
        7  => pack_msg(&create_ext_id_8(),  buf, false),
        8  => pack_msg(&create_ext_id_9(),  buf, false),
        9  => pack_msg(&create_ext_id_10(), buf, false),
        10 => pack_msg(&create_ext_large_1(), buf, false),
        11 => pack_msg(&create_ext_large_2(), buf, false),
        12 => pack_msg(&create_ext_var_single(1, 0,   1, 0),  buf, false),
        13 => pack_msg(&create_ext_var_single(2, 1,   2, 42), buf, false),
        14 => pack_msg(&create_ext_var_single(3, 83,  3, 0),  buf, false),
        15 => pack_msg(&create_ext_var_single(4, 249, 4, 0),  buf, false),
        _  => pack_msg(&create_ext_var_single(5, 250, 5, 0),  buf, false),
    }
}

fn get_expected_payload_variable_flag(index: usize, buf: &mut [u8], use_fixed: bool) -> (u16, usize) {
    match index {
        0 => pack_msg(&create_non_variable(),        buf, use_fixed),
        1 => pack_msg(&create_truncation_variable(), buf, use_fixed),
        2 => pack_msg(&create_nested_variable(),     buf, use_fixed),
        3 => pack_msg(&create_multiple_arrays(),     buf, use_fixed),
        _ => pack_msg(&create_mixed_fields(),        buf, use_fixed),
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

    enc!(create_ext_id_1());
    enc!(create_ext_id_2());
    enc!(create_ext_id_3());
    enc!(create_ext_id_4());
    enc!(create_ext_id_5());
    enc!(create_ext_id_6());
    enc!(create_ext_id_7());
    enc!(create_ext_id_8());
    enc!(create_ext_id_9());
    enc!(create_ext_id_10());
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

    written
}

// ============================================================================
// Generic decode-and-validate
// ============================================================================

fn decode_validate_with<F>(
    config: ProfileConfig,
    data: &[u8],
    expected_count: usize,
    get_expected: F,
) -> usize
where
    F: Fn(usize, &mut [u8]) -> (u16, usize),
{
    let mut reader = AccumulatingReader::new(config, 65536);
    reader.add_data(data);

    let mut count = 0;
    let mut expected_buf = vec![0u8; 65536];

    while let Some(frame) = reader.next(&get_message_info) {
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
// Main
// ============================================================================

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 5 {
        eprintln!("Usage:");
        eprintln!("  {} <runner> <mode> <profile> <file>", args[0]);
        eprintln!("\nRunners: test_standard, test_extended, test_variable_flag");
        eprintln!("Modes:   encode, decode, both");
        eprintln!("Profiles: standard, sensor, ipc, bulk, network");
        std::process::exit(1);
    }

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
                })
            }),
        ),
        "test_extended" => (
            EXTENDED_MESSAGE_COUNT,
            Box::new(|cfg, buf| encode_extended(cfg, buf)),
            Box::new(|cfg, data| {
                decode_validate_with(cfg, data, EXTENDED_MESSAGE_COUNT, |i, buf| {
                    get_expected_payload_extended(i, buf)
                })
            }),
        ),
        "test_variable_flag" => (
            VARIABLE_FLAG_MESSAGE_COUNT,
            Box::new(|cfg, buf| encode_variable_flag(cfg, buf)),
            Box::new(move |cfg, data| {
                decode_validate_with(cfg, data, VARIABLE_FLAG_MESSAGE_COUNT, move |i, buf| {
                    get_expected_payload_variable_flag(i, buf, use_fixed)
                })
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

