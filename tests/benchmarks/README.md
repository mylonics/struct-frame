# Tier D benchmarks

> **What these measure.** Each `bench.*` is a small, self-contained *reference model* of
> framing (its own Fletcher-16 and frame layout) written in that language. They do **not**
> call the generated code or the struct-frame runtime, so they compare how fast each
> language can do the framing arithmetic, not how fast struct-frame is. They are useful as
> a smoke test and for relative language cost, not as struct-frame performance numbers.
>
> **Fairness.** C and C++ are built with `-O2`, Rust with `--release` and C# with
> `-c Release`. JIT-compiled languages (C#, JS, TS) are measured without a warm-up phase, so
> compare them against each other with care.
>
> **Baselines.** The checked-in files in `baselines/` are placeholders
> (`"runner_version": "placeholder-baseline"`), so `check_regression.py` skips every
> language and the CI job is informational only. Record real baselines on a stable runner
> (see below) before treating it as a regression gate.

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
