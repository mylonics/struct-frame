# API stability tests

The Python test compares the current `struct_frame` public API to a checked-in `snapshot.json`. Refresh the snapshot only during intentional public API changes:

```bash
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py --update
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py
```

The npm, NuGet, and crates.io directories contain runnable scaffolds. Add published API baselines (`.d.ts`, `PublicAPI.Shipped.txt`, or `cargo-public-api` output) there to turn them into strict checks.
