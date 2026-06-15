# API stability tests

The Python test compares the current `struct_frame` public API to a checked-in `snapshot.json`. NuGet and crates.io checks compare generated output against their own baseline files.

Refresh all baselines only during intentional public API changes:

```bash
# 1. Generate code for the relevant languages
python tests/run_tests.py --only-generate --skip-lang c --skip-lang cpp --skip-lang py --skip-lang js --skip-lang gql

# 2. Update all baselines
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py --update
python tests/api_stability/nuget/check_api.py --update
python tests/api_stability/crates/check_api.py --update
```

Then verify the checks pass:

```bash
PYTHONPATH=src python tests/api_stability/python/test_api_stability.py
node tests/api_stability/npm/check_api.js
python tests/api_stability/nuget/check_api.py
python tests/api_stability/crates/check_api.py
```

NuGet and crates.io checks are strict by default: missing baselines fail the check.
For local bootstrap workflows, pass `--allow-missing-baseline` to warn+skip.

Add published API baselines (`.d.ts`, `PublicAPI.Shipped.txt`, or
`cargo-public-api` output) to keep these checks actionable in CI.
