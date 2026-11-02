#!/usr/bin/env python3
"""Write seed inputs for the libFuzzer / atheris / cargo-fuzz parser harnesses.

    python tests/fuzz/make_seed_corpus.py <output-dir>

Each file is a valid or mutated frame stream for one profile, built from the same message
table the harnesses use, so the fuzzer starts from inputs that pass the checksum.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "fuzz_seeds")
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for profile in corpus.PROFILES:
        for seed in (1, 2, 3):
            streams = {
                "clean": corpus.clean_stream(profile, count=12, seed=seed, junk=False)[0],
                "corrupt": corpus.corrupted_stream(profile, count=12, seed=seed)[0],
                "noisy": corpus.noisy_stream(profile, count=12, seed=seed),
            }
            for kind, data in streams.items():
                (out / f"{profile}_{kind}_{seed}.bin").write_bytes(data[:4096])
                n += 1
    print(f"wrote {n} seeds to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
