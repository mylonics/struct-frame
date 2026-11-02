// Cargo-fuzz target for the struct-frame Rust streaming parser.
//
// Drives arbitrary bytes through `AccumulatingReader::next` for every shipped
// profile.  Any panic, integer overflow (under `RUSTFLAGS=-Coverflow-checks=on`),
// or memory-safety violation aborts the fuzz run and reports a finding.
#![no_main]

use libfuzzer_sys::fuzz_target;
use struct_frame_sdk::{
    frame_base::MessageInfo,
    frame_profiles::ProfileConfig,
    AccumulatingReader,
    PROFILE_BULK_CONFIG, PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG,
    PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,
};

// Real message table, identical to tests/fuzz/corpus.py, so seed frames from
// tests/fuzz/make_seed_corpus.py pass the checksum and reach the deeper parser paths.
fn stub_info(id: u16) -> Option<MessageInfo> {
    let (size, m1, m2) = match id {
        1 => (8, 11, 22),
        2 => (32, 33, 44),
        3 => (100, 55, 66),
        4 => (1, 77, 88),
        5 => (200, 99, 111),
        _ => return None,
    };
    Some(MessageInfo::new(size, m1, m2))
}

fn drive(cfg: ProfileConfig, data: &[u8]) {
    let mut reader = AccumulatingReader::new(cfg, 1024);
    let mid = data.len() / 2;
    // Two-slice feed exercises the cross-buffer accumulation path.
    reader.add_data(&data[..mid]);
    for _ in 0..256 {
        if reader.try_next(&stub_info).is_none() { break; }
    }
    reader.add_data(&data[mid..]);
    for _ in 0..256 {
        if reader.try_next(&stub_info).is_none() { break; }
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
