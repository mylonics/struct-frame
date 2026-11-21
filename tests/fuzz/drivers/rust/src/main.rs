// Stream driver: stream_driver <profile> <stream.bin> <chunk> [system]
// With `system` the reader delivers system frames (printed with msg_id + 65536) and a final
// "-1 <cnt_system_frames> <cnt_system_rejected> <cnt_crc_failures> <cnt_seq_gaps>" line follows.
// The message table matches tests/fuzz/corpus.py.
#![allow(dead_code)]

use struct_frame_sdk as sf;
use struct_frame_sdk::{AccumulatingReader, MessageInfo};

fn get_info(id: u16) -> Option<MessageInfo> {
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

fn fnv1a(d: &[u8]) -> u32 {
    let mut h: u32 = 0x811C9DC5;
    for &b in d {
        h = (h ^ b as u32).wrapping_mul(0x01000193);
    }
    h
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 && args.len() != 5 {
        std::process::exit(64);
    }
    let deliver = args.len() == 5 && args[4] == "system";
    let cfg = match args[1].as_str() {
        "standard" => sf::PROFILE_STANDARD_CONFIG,
        "sensor" => sf::PROFILE_SENSOR_CONFIG,
        "ipc" => sf::PROFILE_IPC_CONFIG,
        "bulk" => sf::PROFILE_BULK_CONFIG,
        "network" => sf::PROFILE_NETWORK_CONFIG,
        _ => std::process::exit(64),
    };
    let chunk: usize = args[3].parse().unwrap();
    let data = std::fs::read(&args[2]).unwrap();
    let mut reader = AccumulatingReader::new(cfg, 1024);
    reader.set_deliver_system_frames(deliver);
    let mut pos = 0;
    while pos < data.len() {
        let end = (pos + chunk).min(data.len());
        reader.add_data(&data[pos..end]);
        pos = end;
        for _ in 0..1_000_000 {
            match reader.try_next(&get_info) {
                None => break,
                Some(f) => {
                    if f.valid {
                        let id = f.msg_id as u32 + if f.is_system { 65536 } else { 0 };
                        println!("{} {} {}", id, f.msg_len, fnv1a(&f.msg_data));
                    }
                }
            }
        }
    }
    if deliver {
        let d = reader.diagnostics();
        println!("-1 {} {} {} {}", d.cnt_system_frames, d.cnt_system_rejected, d.cnt_crc_failures, d.cnt_seq_gaps);
    }
}
