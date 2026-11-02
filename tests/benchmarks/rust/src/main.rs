// Tier D benchmark for Rust: runs the generated message types and the real frame_profiles
// encoder/parser from tests/benchmarks/generated/rust (the `struct_frame_sdk` crate), built by
// run_all.py from tests/benchmarks/schema/bench.sf. Emits results matching schema.json.
use std::hint::black_box;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use struct_frame_sdk::bench::{get_message_info, Large, Medium, Small};
use struct_frame_sdk::frame_base::StructFrameMessage;
use struct_frame_sdk::frame_profiles::{
    encode_message_crc, encode_message_minimal, parse_frame, ProfileConfig, PROFILE_BULK_CONFIG,
    PROFILE_IPC_CONFIG, PROFILE_NETWORK_CONFIG, PROFILE_SENSOR_CONFIG, PROFILE_STANDARD_CONFIG,
};

const BATCH: usize = 64;
const WARMUP_BATCHES: usize = 20;

trait BenchMsg: StructFrameMessage + Sized {
    fn filled() -> Self;
    fn first(&self) -> u8;
}

macro_rules! bench_msg {
    ($t:ty, $n:expr) => {
        impl BenchMsg for $t {
            fn filled() -> Self {
                let mut data = [0u8; $n];
                for (i, b) in data.iter_mut().enumerate() {
                    *b = (i * 31) as u8;
                }
                Self { data }
            }
            fn first(&self) -> u8 {
                self.data[0]
            }
        }
    };
}
bench_msg!(Small, 32);
bench_msg!(Medium, 96);
bench_msg!(Large, 512);

fn encode_once<M: BenchMsg>(cfg: &ProfileConfig, msg: &M, out: &mut [u8]) -> usize {
    let n = if cfg.payload.has_crc {
        encode_message_crc(cfg, out, msg, 0)
    } else {
        encode_message_minimal(cfg, out, msg)
    };
    assert!(n > 0, "encode failed");
    black_box(&out[..n]);
    n
}

fn decode_once<M: BenchMsg>(cfg: &ProfileConfig, frame: &[u8]) -> usize {
    let info = parse_frame(cfg, frame, &get_message_info);
    assert!(info.valid, "decode failed");
    let msg = M::unpack_frame(&info).expect("unpack failed");
    black_box(msg.first());
    frame.len()
}

fn pct(v: &mut [u64], q: f64) -> u64 {
    v.sort_unstable();
    v[(((v.len() - 1) as f64) * q) as usize]
}

fn run<M: BenchMsg>(name: &str, cfg: ProfileConfig, op: &str, iters: usize) -> String {
    let msg = M::filled();
    let mut frame = vec![0u8; 2048];
    let n = encode_once(&cfg, &msg, &mut frame);
    let encoded = frame[..n].to_vec();
    let is_encode = op == "encode";
    let one = |frame: &mut [u8]| -> usize {
        if is_encode {
            encode_once(&cfg, &msg, frame)
        } else {
            decode_once::<M>(&cfg, &encoded)
        }
    };
    for _ in 0..WARMUP_BATCHES * BATCH {
        black_box(one(&mut frame));
    }
    let batches = (iters / BATCH).max(1);
    let mut lat = Vec::with_capacity(batches);
    let mut bytes = 0usize;
    let start = Instant::now();
    for _ in 0..batches {
        let t = Instant::now();
        for _ in 0..BATCH {
            bytes += one(&mut frame);
        }
        lat.push(t.elapsed().as_nanos() as u64 / BATCH as u64);
    }
    let dur = start.elapsed().as_secs_f64().max(1e-9);
    let count = batches * BATCH;
    let max = *lat.iter().max().unwrap();
    let (p50, p95, p99) = (pct(&mut lat, 0.50), pct(&mut lat, 0.95), pct(&mut lat, 0.99));
    format!(
        "{{\"name\":\"{name}_{op}\",\"profile\":\"{name}\",\"operation\":\"{op}\",\"msg_count\":{count},\
\"bytes_total\":{bytes},\"duration_s\":{dur:.9},\"msg_per_sec\":{:.3},\"mb_per_sec\":{:.3},\
\"latency_ns\":{{\"p50\":{p50},\"p95\":{p95},\"p99\":{p99},\"max\":{max}}}}}",
        count as f64 / dur,
        bytes as f64 / dur / 1e6
    )
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut iters: usize = std::env::var("BENCH_ITERATIONS").ok().and_then(|v| v.parse().ok()).unwrap_or(50_000);
    let mut out = String::from("tests/benchmarks/results/rust.json");
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--iterations" if i + 1 < args.len() => {
                iters = args[i + 1].parse().unwrap();
                i += 1;
            }
            "--output" if i + 1 < args.len() => {
                out = args[i + 1].clone();
                i += 1;
            }
            _ => {}
        }
        i += 1;
    }
    let mut scenarios = Vec::new();
    for op in ["encode", "decode"] {
        scenarios.push(run::<Small>("standard", PROFILE_STANDARD_CONFIG, op, iters));
    }
    for op in ["encode", "decode"] {
        scenarios.push(run::<Large>("bulk", PROFILE_BULK_CONFIG, op, iters));
    }
    for op in ["encode", "decode"] {
        scenarios.push(run::<Medium>("network", PROFILE_NETWORK_CONFIG, op, iters));
    }
    for op in ["encode", "decode"] {
        scenarios.push(run::<Small>("sensor", PROFILE_SENSOR_CONFIG, op, iters));
    }
    for op in ["encode", "decode"] {
        scenarios.push(run::<Small>("ipc", PROFILE_IPC_CONFIG, op, iters));
    }
    let ts = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
    let json = format!(
        "{{\"schema_version\":\"1\",\"language\":\"rust\",\"runner_version\":\"tier-d-2-generated\",\
\"timestamp\":\"{ts}\",\"host\":{{\"os\":\"{}\",\"arch\":\"{}\",\"cpu\":\"unknown\"}},\"scenarios\":[{}]}}\n",
        std::env::consts::OS,
        std::env::consts::ARCH,
        scenarios.join(",")
    );
    if let Some(parent) = std::path::Path::new(&out).parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    std::fs::write(&out, json).expect("write results");
}
