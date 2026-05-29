// Cargo-fuzz target for the struct-frame Rust streaming parser.
//
// Drives arbitrary bytes through `AccumulatingReader::next` for every shipped
// profile.  Any panic, integer overflow (under `RUSTFLAGS=-Coverflow-checks=on`),
// or memory-safety violation aborts the fuzz run and reports a finding.
#![no_main]

use libfuzzer_sys::fuzz_target;
use struct_frame_sdk::{
    AccumulatingReader, MessageInfo,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,
    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,
};

fn stub_info(_msg_id: u16) -> Option<MessageInfo> {
    // Small, well-formed MessageInfo for parsers that need a length lookup.
    // Most fuzz inputs will mismatch the embedded magic and be dropped, but
    // the parser must remain safe regardless.
    Some(MessageInfo { size: 64, magic1: 0, magic2: 0 })
}

fn drive(cfg: struct_frame_sdk::ProfileConfig, data: &[u8]) {
    let mut reader = AccumulatingReader::new(cfg, 1024);
    let mid = data.len() / 2;
    // Two-slice feed exercises the cross-buffer accumulation path.
    reader.add_data(&data[..mid]);
    for _ in 0..256 {
        if reader.next(&stub_info).is_none() { break; }
    }
    reader.add_data(&data[mid..]);
    for _ in 0..256 {
        if reader.next(&stub_info).is_none() { break; }
    }
}

fuzz_target!(|data: &[u8]| {
    if data.is_empty() { return; }
    drive(PROFILE_STANDARD_CONFIG, data);
    drive(PROFILE_SENSOR_CONFIG,   data);
    drive(PROFILE_IPC_CONFIG,      data);
    drive(PROFILE_BULK_CONFIG,     data);
    drive(PROFILE_NETWORK_CONFIG,  data);
});
