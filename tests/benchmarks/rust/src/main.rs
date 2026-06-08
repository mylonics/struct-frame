use std::{env, fs, time::{Instant, SystemTime, UNIX_EPOCH}};

struct Scenario {
    name: &'static str,
    profile: &'static str,
    typ: u8,
    len: usize,
    network: bool,
}

fn fletcher(data: &[u8]) -> (u8, u8) {
    let (mut a, mut b) = (0u16, 0u16);
    for x in data {
        a = (a + *x as u16) & 0xff;
        b = (b + a) & 0xff;
    }
    (a as u8, b as u8)
}

fn verify_payload(payload: &[u8]) {
    let payload_len = payload.len();
    if payload_len == 0 {
        return;
    }
    for idx in [0usize, payload_len / 2, payload_len - 1] {
        let expected = ((idx * 31 + payload_len) & 0xff) as u8;
        assert_eq!(payload[idx], expected, "bad payload");
    }
}

fn encode(s: &Scenario, seq: u8) -> Vec<u8> {
    let mut body = Vec::new();
    if s.network {
        body.extend([seq, 1, 42, (s.len & 0xff) as u8, (s.len >> 8) as u8, 7, 3]);
    } else if s.profile == "bulk" {
        body.extend([(s.len & 0xff) as u8, (s.len >> 8) as u8, 7, 3]);
    } else {
        body.extend([(s.len & 0xff) as u8, 3]);
    }
    for i in 0..s.len {
        body.push(((i * 31 + s.len) & 0xff) as u8);
    }
    let (c1, c2) = fletcher(&body);
    let mut out = vec![0x90, s.typ];
    out.extend(body);
    out.extend([c1, c2]);
    out
}

fn decode(f: &[u8]) -> usize {
    let mut off = 2usize;
    let p = f[1] - 0x70;
    let len;
    if p == 8 {
        off += 3;
        len = f[off] as usize | ((f[off + 1] as usize) << 8);
        off += 4;
    } else if p == 4 {
        len = f[off] as usize | ((f[off + 1] as usize) << 8);
        off += 4;
    } else {
        len = f[off] as usize;
        off += 2;
    }
    let (c1, c2) = fletcher(&f[2..off + len]);
    assert_eq!((f[off + len], f[off + len + 1]), (c1, c2));
    verify_payload(&f[off..off + len]);
    len
}

fn pct(v: &mut [u128], q: f64) -> u128 {
    v.sort_unstable();
    v[((v.len() - 1) as f64 * q) as usize]
}

fn run_case(s: &Scenario, op: &str, iters: usize) -> String {
    let frames: Vec<_> = (0..8).map(|i| encode(s, i)).collect();
    let mut lat = Vec::with_capacity(iters);
    let mut bytes = 0usize;
    let start = Instant::now();
    for i in 0..iters {
        let t = Instant::now();
        if op == "encode" {
            let f = encode(s, i as u8);
            bytes += f.len();
        } else {
            let f = &frames[i & 7];
            decode(f);
            bytes += f.len();
        }
        lat.push(t.elapsed().as_nanos());
    }
    let dur = start.elapsed().as_secs_f64().max(1e-9);
    let max = *lat.iter().max().unwrap_or(&0);
    let p50 = pct(&mut lat.clone(), 0.50);
    let p95 = pct(&mut lat.clone(), 0.95);
    let p99 = pct(&mut lat, 0.99);
    format!(
        "{{\"name\":\"{}_{}\",\"profile\":\"{}\",\"operation\":\"{}\",\
         \"msg_count\":{},\"bytes_total\":{},\"duration_s\":{},\
         \"msg_per_sec\":{},\"mb_per_sec\":{},\
         \"latency_ns\":{{\"p50\":{},\"p95\":{},\"p99\":{},\"max\":{}}}}}",
        s.name, op, s.profile, op,
        iters, bytes, dur,
        iters as f64 / dur, bytes as f64 / dur / 1e6,
        p50, p95, p99, max,
    )
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut iters: usize = env::var("BENCH_ITERATIONS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(50_000);
    let mut output = "tests/benchmarks/results/rust.json".to_string();
    let mut i = 1;
    while i < args.len() {
        if args[i] == "--iterations" && i + 1 < args.len() {
            iters = args[i + 1].parse().unwrap();
            i += 1;
        } else if args[i] == "--output" && i + 1 < args.len() {
            output = args[i + 1].clone();
            i += 1;
        }
        i += 1;
    }
    let scens = [
        Scenario { name: "standard", profile: "standard", typ: 0x71, len: 32,  network: false },
        Scenario { name: "bulk",     profile: "bulk",     typ: 0x74, len: 512, network: false },
        Scenario { name: "network",  profile: "network",  typ: 0x78, len: 96,  network: true },
    ];
    let mut rows = Vec::new();
    for s in &scens {
        rows.push(run_case(s, "encode", iters));
        rows.push(run_case(s, "decode", iters));
    }
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let json = format!(
        "{{\"schema_version\":\"1\",\"language\":\"rust\",\"runner_version\":\"tier-d-1\",\
         \"timestamp\":\"{}\",\"host\":{{\"os\":\"{}\",\"arch\":\"{}\",\"cpu\":\"unknown\"}},\
         \"scenarios\":[{}]}}\n",
        ts, env::consts::OS, env::consts::ARCH, rows.join(","),
    );
    fs::create_dir_all(std::path::Path::new(&output).parent().unwrap()).unwrap();
    fs::write(output, json).unwrap();
}
