//! Cross-language x cross-version wire-evolution file I/O (Rust).
//! See tests/cpp/test_wire_evolution_file_io.cpp for the full rationale.
//!
//! Usage:
//!   test_wire_evolution_file_io encode v1 <file>
//!   test_wire_evolution_file_io encode v2 <file>
//!   test_wire_evolution_file_io decode v1 <file>
//!   test_wire_evolution_file_io decode v2 <file>
//!
//! Canonical values must match every other language's file_io helper:
//! header=0x1234, seq=42, crc_seed=0xDEADBEEF.

use std::fs;
use std::process::ExitCode;

use struct_frame_sdk::wire_evolution_v1 as v1;
use struct_frame_sdk::wire_evolution_v2 as v2;

const HEADER: u16 = 0x1234;
const SEQ: u8 = 42;
const CRC_SEED: u32 = 0xDEADBEEF;

fn do_encode(version: &str, path: &str) -> u8 {
    let buf: Vec<u8> = if version == "v1" {
        let msg = v1::BaseExtensionMessage { header: HEADER, seq: SEQ };
        let mut buf = vec![0u8; v1::BaseExtensionMessage::SIZE];
        let n = msg.pack(&mut buf);
        buf.truncate(n);
        buf
    } else if version == "v2" {
        let msg = v2::BaseExtensionMessage { header: HEADER, seq: SEQ, crc_seed: CRC_SEED };
        let mut buf = vec![0u8; v2::BaseExtensionMessage::SIZE];
        let n = msg.pack(&mut buf);
        buf.truncate(n);
        buf
    } else {
        eprintln!("[ENCODE] FAILED: unknown version '{}'", version);
        return 1;
    };
    if fs::write(path, &buf).is_err() {
        eprintln!("[ENCODE] FAILED: cannot write {}", path);
        return 1;
    }
    println!("[ENCODE] SUCCESS: wrote {} bytes ({}) to {}", buf.len(), version, path);
    0
}

fn do_decode(version: &str, path: &str) -> u8 {
    let buf = match fs::read(path) {
        Ok(b) => b,
        Err(_) => {
            eprintln!("[DECODE] FAILED: cannot read {}", path);
            return 1;
        }
    };

    if version == "v1" {
        let msg = match v1::BaseExtensionMessage::unpack(&buf) {
            Some(m) => m,
            None => {
                eprintln!("[DECODE] FAILED: unpack returned None");
                return 1;
            }
        };
        if msg.header != HEADER || msg.seq != SEQ {
            eprintln!("[DECODE] FAILED: header=0x{:04x} (expected 0x{:04x}) seq={} (expected {})",
                      msg.header, HEADER, msg.seq, SEQ);
            return 1;
        }
        println!("[DECODE] SUCCESS: v1 header=0x{:04x} seq={}", msg.header, msg.seq);
        0
    } else if version == "v2" {
        let msg = match v2::BaseExtensionMessage::unpack(&buf) {
            Some(m) => m,
            None => {
                eprintln!("[DECODE] FAILED: unpack returned None");
                return 1;
            }
        };
        if msg.header != HEADER || msg.seq != SEQ {
            eprintln!("[DECODE] FAILED: header=0x{:04x} (expected 0x{:04x}) seq={} (expected {})",
                      msg.header, HEADER, msg.seq, SEQ);
            return 1;
        }
        // A legacy (v1-sized, 3-byte) frame decoded as v2 must zero-fill the
        // extension; a genuine v2-sized (7-byte) frame must preserve it.
        let expected_crc = if buf.len() >= v2::BaseExtensionMessage::BASE_SIZE + 4 { CRC_SEED } else { 0 };
        if msg.crc_seed != expected_crc {
            eprintln!("[DECODE] FAILED: crc_seed=0x{:08x} (expected 0x{:08x} for {}-byte input)",
                      msg.crc_seed, expected_crc, buf.len());
            return 1;
        }
        println!("[DECODE] SUCCESS: v2 header=0x{:04x} seq={} crc_seed=0x{:08x} (from {} bytes)",
                  msg.header, msg.seq, msg.crc_seed, buf.len());
        0
    } else {
        eprintln!("[DECODE] FAILED: unknown version '{}'", version);
        1
    }
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        eprintln!("Usage: {} <encode|decode> <v1|v2> <file>", args.first().map(|s| s.as_str()).unwrap_or("test_wire_evolution_file_io"));
        return ExitCode::from(2);
    }
    let mode = &args[1];
    let version = &args[2];
    let path = &args[3];

    let code = if mode == "encode" {
        do_encode(version, path)
    } else if mode == "decode" {
        do_decode(version, path)
    } else {
        eprintln!("Unknown mode: {}", mode);
        2
    };
    ExitCode::from(code)
}
