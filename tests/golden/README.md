# Canonical Wire-Format Test Vectors

This directory contains byte-exact encoded frames produced by the Python
reference encoder, one file per `(suite, profile)` combination. They are the
project's wire-format regression suite — equivalent to a Protocol Buffers
`testdata/` directory.

| File | Encoder | Profile |
| --- | --- | --- |
| `standard_standard.bin` | `tests/py/test_standard.py` | `standard` |
| `standard_sensor.bin` | `tests/py/test_standard.py` | `sensor` |
| `standard_ipc.bin` | `tests/py/test_standard.py` | `ipc` |
| `standard_bulk.bin` | `tests/py/test_standard.py` | `bulk` |
| `standard_network.bin` | `tests/py/test_standard.py` | `network` |
| `extended_bulk.bin` | `tests/py/test_extended.py` | `bulk` |
| `extended_network.bin` | `tests/py/test_extended.py` | `network` |
| `variable_bulk.bin` | `tests/py/test_variable_flag.py` | `bulk` |

## How they are used

* `tests/check_golden.py` re-encodes the same fixtures and diffs against
  these files. CI fails on any difference.
* A new implementation seeking to claim struct-frame conformance must decode
  every file here and re-encode the fixtures byte-identically — see
  [`docs/src/content/docs/reference/conformance.md`](../../docs/src/content/docs/reference/conformance.md).

## Updating the goldens

Only update when a deliberate wire-format change has been made:

```bash
python tests/check_golden.py --update
git add tests/golden/
git commit -m "wire: regenerate goldens for <reason>"
```

The commit MUST be accompanied by:

1. A `CHANGELOG.md` entry that says *"wire-format change"* explicitly.
2. An update to `docs/src/content/docs/reference/conformance.md` describing
   the new format.
3. A version bump per the policy in conformance.md § 8.

If `check_golden.py` reports drift in CI and you did not intend to change
the wire format, the diff is a bug — don't `--update`, fix the cause.
