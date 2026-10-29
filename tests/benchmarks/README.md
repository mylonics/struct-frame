# Tier D benchmarks

> **What these measure.** Every language's benchmark runs the real thing: `run_all.py`
> generates code from `schema/bench.sf` (32-, 96- and 512-byte messages), then each benchmark
> encodes with the generated message plus the runtime's writer and decodes with the runtime's
> parser plus the generated `deserialize`. Standard, Sensor, IPC, Bulk and Network profiles are
> covered in Python, C, C++, TypeScript, JavaScript, C# and Rust. (The Rust message-level encoder
> has no sequence/address arguments, so its Network frames carry zeros there.)
>
> **Method.** Each scenario warms up for 1,280 operations, then times batches of 64
> operations and reports per-operation latency from the batch time, so the clock reads are
> outside the per-message cost. Latency is reported in whole nanoseconds, so very fast
> operations show a p50 of 0. C and C++ are built with `-O2` and use a compiler barrier so
> unread encodes are not optimised away; Rust uses `--release` and `black_box`; C# uses
> `-c Release`.
>
> **Baselines.** The checked-in files in `baselines/` are placeholders
> (`"runner_version": "placeholder-baseline"`), so `check_regression.py` skips every
> language and the CI job is informational only. Numbers recorded on a developer machine
> are not comparable with a CI runner, so baselines must come from the runner that
> enforces them: download the `benchmark-results` artifact from a green `main` run, copy
> `results/<lang>.json` over `baselines/<lang>.json`, then drop `continue-on-error` and
> `--allow-missing-baseline` from `.github/workflows/benchmark-regression.yml`.
>
> **Already paid off.** The first generated-code run showed the generated Python
> `get_message_info` re-running a failing relative import on every frame (about 8x slower
> decode); it now resolves the class once.

Run all available benchmark implementations:

```bash
python tests/benchmarks/run_all.py --quick
```

Each language emits `tests/benchmarks/results/<lang>.json` using `schema.json`. Refresh baselines after an intentional performance change by copying validated results into `tests/benchmarks/baselines/` and reviewing the diff:

```bash
python tests/benchmarks/run_all.py
cp tests/benchmarks/results/<lang>.json tests/benchmarks/baselines/<lang>.json
python tests/benchmarks/check_regression.py
```

Thresholds are configured in `thresholds.json`. CI uses `--quick` as a smoke/regression guard; local full runs should use the default iteration count or `BENCH_ITERATIONS`.
