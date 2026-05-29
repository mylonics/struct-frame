---
title: Test Stability Policy
description: Flake and stability policy for the test suite — retry budgets, quarantine rules, and triage ownership.
---

This document defines how the project treats **flaky** and **unstable** tests:
how often a test may be retried, when it may be quarantined, and who is
responsible for triaging failures. The goal is a test suite where a red run
means a real regression — not noise — so contributors can trust CI.

A *flaky* test is one that passes and fails non-deterministically on the **same
code** (same commit, same inputs). Flakiness erodes trust in CI, hides real
regressions, and wastes reviewer time, so we treat it as a defect with the same
seriousness as a failing test.

## Principles

1. **Determinism is the default.** Tests must use fixed seeds, fixed clocks,
   and deterministic inputs. The suite already enforces this for generated
   code via `tests/check_determinism.py` and for wire formats via
   `tests/check_golden.py`; new tests are expected to hold the same bar.
2. **A failure is real until proven flaky.** Never re-run red CI hoping for
   green without first inspecting the failure. Re-running to "make it pass" is
   prohibited.
3. **Flakiness is a bug.** A confirmed flaky test gets an issue, an owner, and
   a deadline — exactly like any other defect.
4. **Quarantine is a last resort, never a destination.** Quarantining buys time
   to fix; it does not close the problem.

## Retry policy

Retries exist to absorb genuinely external, non-reproducible failures (network
hiccups installing dependencies, runner provisioning errors), **not** to mask
product or test defects.

| Scope | Max automatic retries | Where it applies |
|-------|-----------------------|------------------|
| Whole CI job (infrastructure) | 1 re-run of the job | Manual "Re-run failed jobs" only, with justification in the PR |
| Network / dependency install step | 2 | `apt-get`, `pip install`, `npm ci`, toolchain setup |
| Individual test case logic | **0** | The functional assertions in `tests/` |

Rules:

- **No automatic retries are added around functional assertions.** The test
  bodies under `tests/` must not wrap logic in retry loops to paper over
  non-determinism. If a test needs a retry to pass, it is flaky and must be
  fixed or quarantined.
- **Infrastructure retries must be bounded** (see table) and must back off.
  Unbounded `while` retry loops are not allowed.
- **Re-running a red CI run manually** is allowed **at most once** and only when
  the failure is identified as infrastructure (not a test or product defect).
  The person who re-runs records why in the PR conversation.
- Timeouts count as failures, not as a reason to retry. A test that times out
  intermittently is flaky.

## Quarantine policy

Quarantine isolates a confirmed-flaky test so it stops blocking unrelated PRs
while its owner fixes the root cause.

A test **may** be quarantined when **all** of the following hold:

1. It has failed non-deterministically on `main` (or on an unrelated PR) at
   least **twice**, with evidence linked (CI run URLs).
2. A tracking issue exists, labelled `flaky-test`, with an assigned owner.
3. The flake is **not** masking a real regression — i.e. the failure mode has
   been understood well enough to be confident it is non-deterministic noise.

How to quarantine:

- **Preferred:** narrow the scope. Skip only the unstable case, not the whole
  file, using the suite's existing skip mechanism (`--skip-lang` for a whole
  language phase; an explicit early `return`/skip with a `# QUARANTINE:
  <issue-url>` comment for a single case).
- Every quarantine **must** reference its tracking issue in a
  `QUARANTINE: <issue-url>` comment adjacent to the skip, so the reason is
  discoverable in code review and greppable in CI logs.
- A quarantined test still runs in **non-gating** mode where practical (e.g. a
  `continue-on-error` matrix leg, mirroring how `test.yml` already tolerates
  the .NET 8 leg) so we keep collecting signal on the flake.

Quarantine has a **maximum lifetime of 14 days**. If the tracking issue is not
resolved by then, the owner must either (a) delete the test if it provides no
value, or (b) escalate to the maintainers to reprioritise. Quarantined tests
are reviewed at least weekly.

## Triage ownership

| Role | Responsibility |
|------|----------------|
| **PR author** | Investigates any failure on their PR before re-running. Must not merge over a red or quarantined-without-issue state. |
| **Flake owner** (assignee on the `flaky-test` issue) | Reproduces, root-causes, and fixes the flake within the quarantine lifetime; closes the tracking issue. |
| **Maintainers** | Own flakes seen on `main` with no obvious owner; assign an owner within 2 business days; run the weekly quarantine review. |

Default ownership routing for a flake on `main`:

- The author of the most recent change to the affected test or the code under
  test is the first-line owner.
- If that is unclear, the maintainers triage and assign.

## Lifecycle of a flaky test

1. **Detect** — a test fails non-deterministically. Capture the CI run URL(s).
2. **File** — open an issue labelled `flaky-test` with the evidence, the
   affected test, and a hypothesis. Cross-link it from the
   [Test Coverage Triage](test-coverage#test-coverage-triage) table if the
   flake also represents a coverage gap.
3. **Assign** — an owner is set per the routing above.
4. **Quarantine (optional)** — if the flake is blocking others and the criteria
   above are met, quarantine it with a `QUARANTINE:` comment linking the issue.
5. **Fix** — make the test deterministic (fix seeds/clocks/ordering, remove
   shared mutable state, stabilise timing assumptions) or fix the underlying
   product bug the flake exposed.
6. **Un-quarantine** — re-enable the test, confirm it is green across several
   consecutive runs, and close the issue.

## Common flake sources to check first

- **Unseeded randomness.** Property tests (`tests/test_property_roundtrip.py`)
  must pin Hypothesis seeds/`derandomize` in CI. Fuzz harnesses
  (`tests/c/fuzz_parser.c`, `tests/py/fuzz_parser.py`, the Rust target) save the
  reproducing input on failure — attach it to the issue.
- **Ordering / shared state.** Tests that depend on filesystem ordering or
  reuse generated artifacts under `tests/generated/` without regenerating.
- **Timing.** Real sleeps, wall-clock comparisons, or transport timeouts in the
  SDK tests. Prefer injected clocks and mock transports (as the
  `StructFrameSdk` subscribe/dispatch tests already do).
- **Toolchain drift.** Behaviour that differs across the GCC/Clang, Python,
  Node, or .NET matrix legs — pin versions and reproduce on the failing leg.

## Related

- [Test Coverage](test-coverage) — the generated coverage matrix and its
  auto-derived triage table.
- [Testing](testing) — how to run the suite locally.
