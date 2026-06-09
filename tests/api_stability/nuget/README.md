# NuGet API stability scaffold

`check_api.py` is strict by default: if `PublicAPI.Shipped.txt` is missing,
the check fails.

For local bootstrap only, you can run:

```bash
python tests/api_stability/nuget/check_api.py --allow-missing-baseline
```

Add a previous-release `PublicAPI.Shipped.txt` to enforce real compatibility checks.
