# API stability tests

The Python test compares the current `struct_frame` public API to a checked-in `snapshot.json`. Refresh the snapshot only during intentional public API changes:

```bash
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py --update
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py
```

NuGet and crates.io checks are strict by default: missing baselines fail the check.
For local bootstrap workflows, pass `--allow-missing-baseline` to warn+skip.

Add published API baselines (`.d.ts`, `PublicAPI.Shipped.txt`, or
`cargo-public-api` output) to keep these checks actionable in CI.
