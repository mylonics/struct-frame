# crates.io API stability scaffold

`check_api.py` is strict by default: if `public-api.txt` is missing,
the check fails.

For local bootstrap only, you can run:

```bash
python tests/api_stability/crates/check_api.py --allow-missing-baseline
```

Add a previous-release `public-api.txt` (for example from `cargo public-api`)
to enforce real compatibility checks.
