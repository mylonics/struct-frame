# AI Agent Guide for struct-frame Testing

> **This document is intentionally short.** The previous version of this guide
> referenced proto files (`basic_types.proto`, `comprehensive_arrays.proto`,
> `nested_messages.proto`, `serialization_test.proto`), CLI flags
> (`--generate-only`, `--skip-c`, `--skip-ts`), and bugs that no longer exist.
> It was deleted in favour of pointing at the live, maintained docs below.

## Where to look

| If you want to… | Read |
| --- | --- |
| Run the test suite | [`tests/README.md`](tests/README.md) |
| See what every language tests today | [`docs/src/content/docs/reference/test-coverage.md`](docs/src/content/docs/reference/test-coverage.md) |
| Understand the wire format and the canonical test vectors | [`docs/src/content/docs/reference/conformance.md`](docs/src/content/docs/reference/conformance.md) |
| Add or debug negative / malformed-frame tests | [`tests/NEGATIVE_TESTS.md`](tests/NEGATIVE_TESTS.md) |
| See user-facing testing docs (rendered on the site) | [`docs/src/content/docs/reference/testing.md`](docs/src/content/docs/reference/testing.md) |
| Understand the generator and codebase layout | [`DEVGUIDE.md`](DEVGUIDE.md), [`REVIEW.md`](REVIEW.md) |

## Cardinal rules for agents working on tests

1. **The test-coverage matrix is the source of truth.** Before claiming a
   feature is "tested in all languages", check
   `docs/src/content/docs/reference/test-coverage.md`. When you add or close a
   coverage gap, update that file in the same PR.

2. **Seven languages, not three.** Every per-language test suite
   (`test_standard`, `test_extended`, `test_variable_flag`, `test_negative`)
   exists in **C, C++, Python, TypeScript, JavaScript, C#, and Rust**. If you
   change a shared test scenario, change it in all seven.

3. **Wire format is sacred.** If a change alters serialised bytes, run
   `python tests/check_golden.py` and update `tests/golden/` deliberately, in
   its own commit, with a note in `CHANGELOG.md`. Drift detected by
   `check_golden.py` is *always* a real bug or a deliberate format change —
   never silently regenerate the goldens to make CI green.

4. **Use the existing CLI.** Current flags are
   `--verbose / --skip-lang LANG / --only-generate / --only-compile /
   --profile NAME / --no-clean / --no-parallel / --no-color`. There is no
   `--generate-only`, no `--skip-c`, no `--skip-ts`.

5. **Don't grep for `*.proto`.** Definitions live in `tests/proto/*.sf`.

6. **Never delete the `ProjectReference` in `tests/csharp/StructFrameTests.csproj`.**
   It points at `tests/generated/csharp/StructFrame.csproj` — generated,
   gitignored, and the *only* source of the `StructFrame` namespace. If you see
   `CS0246: The type or namespace name 'StructFrame' could not be found (are you
   missing a using directive or an assembly reference?)`, the generated library is
   missing; run `python test_all.py` to regenerate it. Removing the reference
   turns one missing-library problem into ~224 CS0246 errors, and the next agent
   adds it back — this file has oscillated for exactly this reason.

7. **Don't run bare `dotnet build` on the generated C# project.** A `dotnet build`
   run by hand starts the persistent .NET build server, which holds directory
   handles under `tests/generated/csharp`. The next `clean()` then deletes the
   folder's *contents* and fails to remove the folder itself (`WinError 32`),
   aborting the run with the generated library already gone — which is what
   produces the CS0246 storm above. `run_tests.py` now runs
   `dotnet build-server shutdown` before cleaning and fails loudly rather than
   continuing on a half-deleted tree, but if you build C# by hand, shut the server
   down yourself afterwards. Omitting `-c`/`--framework` also builds every TFM in
   `Debug`, leaving intermediates the runner did not expect.

## Quick reference

```bash
# Full suite (calls tests/run_tests.py)
python test_all.py

# Single language
python tests/run_tests.py --skip-lang c --skip-lang cpp --skip-lang csharp --skip-lang rust --skip-lang ts --skip-lang js

# Single profile
python tests/run_tests.py --profile ProfileStandard

# Regenerate code without running tests
python tests/run_tests.py --only-generate

# Wire-format regression
python tests/check_golden.py            # verify
python tests/check_golden.py --update   # regenerate (deliberate format change only)

# Generator determinism
python tests/check_determinism.py
```
