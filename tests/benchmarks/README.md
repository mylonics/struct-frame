# Tier D benchmarks

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
