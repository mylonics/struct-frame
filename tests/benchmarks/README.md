# Tier D benchmarks

> **What these measure.**
> - **Python and C** run the real thing: `run_all.py` generates code from
>   `schema/bench.sf`, then encodes with the generated `serialize` plus the runtime's
>   `BufferWriter` / `buffer_writer_write` and decodes with the runtime parser plus the
>   generated `deserialize`. Standard, Sensor, IPC, Bulk and Network profiles are covered.
> - **C++, TypeScript, JavaScript, C# and Rust** are still small, self-contained *reference
>   models* of framing (their own Fletcher-16 and frame layout). They do not call the
>   generated code, so they compare the cost of the framing arithmetic per language, not
>   struct-frame itself. Porting them to the generated code is the remaining benchmark work.
>
> **Method.** Each scenario warms up for 1,280 operations, then times batches of 64
> operations and reports per-operation latency from the batch time, so the clock reads are
> outside the per-message cost. C and C++ are built with `-O2`, Rust with `--release`
> and C# with `-c Release`. JIT languages (C#, JS, TS) get no extra warm-up beyond the
> above, so compare them with care.
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
