"""Single source of truth for the Test Coverage reference document.

This module holds the *semantic* coverage data (which feature is tested in
which language, plus curated notes).  The renderer in
``tests/gen_test_coverage.py`` walks ``tests/`` and the generator's feature set
to validate this spec (catching drift such as a referenced test file that no
longer exists or a generator CLI flag that the spec forgot about) and then
emits ``docs/src/content/docs/reference/test-coverage.md``.

Keeping the data here -- rather than hand-editing the rendered Markdown -- is
what lets the ``--check`` mode guarantee the published table stays honest.

Coverage symbols
----------------
``✅`` tested, ``⚠️`` partially tested, ``❌`` not tested, ``N/A`` not
applicable, ``—`` self/diagonal cell.
"""

from __future__ import annotations

# Languages tracked across the coverage matrices, in column order.
LANGS = ["C", "C++", "Python", "TS", "JS", "C#", "Rust"]

# Coverage symbols that represent a *gap* and therefore get triaged.
GAP_SYMBOLS = {"❌", "⚠️"}

DESCRIPTION = (
    "Maps every feature, message type, profile, and error path to its test "
    "coverage across all languages."
)

INTRO = (
    "This document maps every feature, message type, frame profile, and error "
    "path to its test coverage. Each row cross-references the actual test "
    "files in `tests/`.\n\n"
    "**This file is generated** by `tests/gen_test_coverage.py` from "
    "`tests/coverage_spec.py`. Do not edit it by hand -- update the spec and "
    "re-run the generator (`python tests/gen_test_coverage.py`). CI runs the "
    "generator in `--check` mode so the published table cannot drift from the "
    "tests that actually exist on disk."
)

LEGEND = [
    ("✅", "Tested"),
    ("⚠️", "Partially tested"),
    ("❌", "Not tested"),
    ("N/A", "Not applicable to this language"),
]


def _row(label, cells, notes=""):
    """Build a language-matrix row.

    ``cells`` maps a subset of :data:`LANGS` to coverage symbols; any language
    not present defaults to an empty string (rendered as a blank cell).
    """
    return {"label": label, "cells": cells, "notes": notes}


def _full(label, symbol, notes=""):
    """A matrix row where every tracked language shares the same symbol."""
    return _row(label, {lang: symbol for lang in LANGS}, notes)


# ---------------------------------------------------------------------------
# Section model
# ---------------------------------------------------------------------------
# Each section is a dict with:
#   number:   section number used for stable triage IDs
#   title:    human heading (without the leading number)
#   intro:    optional Markdown rendered before the tables
#   tables:   list of tables. Each table is a dict with
#               header:    column label for the first ("row") column
#               columns:   the value columns (usually LANGS, or custom)
#               lang_cols: subset of columns considered for triage (gaps)
#               rows:      list produced by _row()/_full()
#               caption:   optional Markdown rendered after the table
#   notes:    optional list of Markdown blockquote/prose blocks after tables

SECTIONS = [
    {
        "number": "1",
        "title": "Code Generation (Generator Smoke Tests)",
        "intro": (
            "These tests verify that `python -m struct_frame` generates valid, "
            "compilable output. They are exercised implicitly by every "
            "compile-and-run test."
        ),
        "tables": [
            {
                "header": "Feature",
                "columns": LANGS + ["Notes"],
                "lang_cols": LANGS,
                "rows": [
                    _full("Generate from single proto", "✅",
                          "All test suites exercise generation"),
                    _full("Generate from imported proto", "✅",
                          "`pkg_test_messages.sf` imports `pkg_test_a.sf`"),
                    _row("Multi-package generation",
                         {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                          "JS": "✅", "C#": "✅", "Rust": "✅"},
                         "`pkg_test_messages.sf` + `pkg_test_a.sf`; Rust covered by "
                         "round-trip tests (`test_roundtrip_pkg_test_messages.rs`, "
                         "`test_roundtrip_pkg_test_a.rs`)"),
                    _row("`--equality` flag",
                         {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                          "JS": "✅", "C#": "✅", "Rust": "✅"},
                         "Verified by `tests/test_equality.py` (C `*_equals()`, "
                         "C++ `operator==`, Python `__eq__`/`__ne__`, "
                         "TS/JS `equals()`, C# `Equals()`/`==`, Rust `PartialEq` derive)"),
                    _full("`--generate_tests` flag", "✅",
                          "Exercised by the Round-trip Tests phase for all seven targets"),
                    _row("`--validate` flag",
                         {"C": "✅", "C++": "✅", "Python": "✅", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"},
                         "Verified by `tests/test_validate_flag.py` (success path, "
                         "no-output guarantee, failure path)"),
                    _row("`--no_packed` flag",
                         {"C": "✅", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"},
                         "Verified by `tests/test_no_packed.py` (CLI generation, "
                         "absence of `#pragma pack`, round-trip parity)"),
                    _full("Hash / `--force` caching", "✅",
                          "Verified by `tests/test_caching.py` (hash file creation, "
                          "skip-on-match, `--force` bypass, structural change invalidation)"),
                ],
            },
        ],
    },
    {
        "number": "2",
        "title": "Proto Field Types",
        "intro": (
            "Test file references:\n"
            "- C: `tests/c/include/standard_messages.h`\n"
            "- C++: `tests/cpp/include/standard_messages.hpp`\n"
            "- Python: `tests/py/include/standard_messages.py`\n"
            "- TS/JS: `tests/ts/include/standard_messages.ts` / "
            "`tests/js/include/standard_messages.js`\n"
            "- C#: `tests/csharp/include/StandardMessages.cs`\n"
            "- Rust: `tests/rust/src/main.rs`\n\n"
            "Proto source: `tests/proto/test_messages.sf` (`BasicTypesMessage`, "
            "`ComprehensiveArrayMessage`, `SerializationTestMessage`)"
        ),
        "tables": [
            {
                "header": "Type",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.1 Primitive Types",
                "rows": [_full(t, "✅") for t in (
                    "`int8`", "`int16`", "`int32`", "`int64`", "`uint8`",
                    "`uint16`", "`uint32`", "`uint64`", "`float`", "`double`",
                    "`bool`")],
            },
            {
                "header": "Type",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.2 String Types",
                "rows": [
                    _full("Fixed string (`size=N`)", "✅"),
                    _full("Variable string (`max_size=N`)", "✅"),
                ],
            },
            {
                "header": "Type",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.3 Arrays",
                "rows": [
                    _full("Fixed array of primitives", "✅"),
                    _full("Bounded array of primitives", "✅"),
                    _full("Fixed array of strings", "✅"),
                    _full("Bounded array of strings", "✅"),
                    _full("Fixed array of enums", "✅"),
                    _full("Bounded array of enums", "✅"),
                    _full("Fixed array of nested messages", "✅"),
                    _full("Bounded array of nested messages", "✅"),
                ],
                "caption": "Test file: `ComprehensiveArrayMessage` in "
                           "`tests/proto/test_messages.sf`",
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.4 Enums",
                "rows": [
                    _full("Enum definition and serialization", "✅"),
                    _full("Enum to string conversion", "✅"),
                ],
                "caption": (
                    "> **C/C++:** `tests/test_proto_field_types.py` compiles and "
                    "runs a C/C++ binary that calls `{Pkg}{Enum}_to_string()` / "
                    "`{Enum}_to_string()`. **Python:** `.name` attribute verified "
                    "in the same standalone test. **TS/JS:** reverse-mapping "
                    "(`Priority[Priority.High]` / key-lookup) verified in "
                    "`test_standard.ts/.js`. **C#:** `Priority.HIGH.ToString()` "
                    "verified in `test_standard.cs`. **Rust:** "
                    "`format!(\"{:?}\", Priority::HIGH)` verified in "
                    "`tests/rust/src/main.rs`."
                ),
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.5 Nested Messages",
                "rows": [_full("Nested struct round-trip", "✅")],
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.6 Oneof / Union Types",
                "rows": [
                    _full("`oneof` with `msgid` discriminator", "✅"),
                    _full("`oneof` with `field_order` discriminator", "✅"),
                    _full("`oneof` with `discriminator = none`", "✅"),
                    _full("Multiple `oneof` fields in one message", "✅"),
                    _full("Envelope messages (`is_envelope`)", "✅"),
                ],
                "caption": (
                    "> **All gaps closed.** `discriminator = none` and "
                    "multi-oneof encode/decode tested in all 7 languages: Python "
                    "via `tests/test_proto_field_types.py`; C and C++ via "
                    "compiled binaries in the same file; TS/JS via "
                    "`checkDiscriminatorNone()`/`checkMultiOneof()` in their "
                    "standard test helpers; C# via "
                    "`CheckDiscriminatorNone()`/`CheckMultiOneof()` in "
                    "`tests/csharp/include/StandardMessages.cs`; Rust via the "
                    "`test_oneof_special` runner in `tests/rust/src/main.rs`."
                ),
            },
            {
                "header": "Option",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "2.7 Message Options",
                "rows": [
                    _full("`msgid`", "✅"),
                    _full("`variable = true`", "✅"),
                    _full("`pkgid` (package ID)", "✅"),
                    _full("`is_envelope`", "✅"),
                    _row("`flatten`",
                         {"C": "✅", "C++": "N/A", "Python": "✅", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                ],
                "caption": (
                    "> **C/Python `flatten`:** Verified by "
                    "`tests/test_proto_field_types.py` -- Python `to_dict()` "
                    "inlines inner fields; C generates the struct inline (compile "
                    "test). **Rust envelope:** `tests/rust/src/main.rs` "
                    "`test_envelope_sdk` runner tests `CommandEnvelope` (msgid "
                    "discriminator) and `RawDataEnvelope` (field_order "
                    "discriminator) round-trips."
                ),
            },
        ],
    },
    {
        "number": "3",
        "title": "Frame Profiles",
        "tables": [
            {
                "header": "Profile",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "3.1 Standard Test Suite (`test_standard.*`)",
                "intro": "Tests all five profiles with a standard set of messages.",
                "rows": [
                    _full("`profile_standard`", "✅"),
                    _full("`profile_sensor`", "✅"),
                    _full("`profile_ipc`", "✅"),
                    _full("`profile_bulk`", "✅"),
                    _full("`profile_network`", "✅"),
                ],
                "caption": "Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_standard.*`",
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "3.2 Extended Test Suite (`test_extended.*`)",
                "intro": "Tests extended message IDs (> 255) requiring Bulk/Network profiles.",
                "rows": [
                    _full("Extended msg ID (> 255) + `profile_bulk`", "✅"),
                    _full("Extended msg ID (> 255) + `profile_network`", "✅"),
                    _full("Payload > 255 bytes", "✅"),
                ],
                "caption": (
                    "Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_extended.*`  \n"
                    "Proto: `tests/proto/extended_messages.sf`"
                ),
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "3.3 Variable-Flag Test Suite (`test_variable_flag.*`)",
                "intro": "Tests `option variable = true` truncation behaviour with `profile_bulk`.",
                "rows": [
                    _full("`variable = true` truncation", "✅"),
                    _full("Single bounded array truncation", "✅"),
                    _full("Nested variable struct (variable parent + nested "
                          "struct with variable fields)", "✅"),
                    _full("Multiple bounded arrays truncation", "✅"),
                    _full("Mixed fixed + variable fields", "✅"),
                ],
                "caption": "Files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_variable_flag.*`",
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "3.4 Profiling / Performance Tests",
                "rows": [
                    _row("Encode/decode throughput",
                         {"C": "N/A", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _row("Packed vs unpacked struct comparison",
                         {"C": "N/A", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                ],
                "caption": (
                    "Files: `tests/cpp/test_profiling.cpp`, "
                    "`tests/cpp/test_profiling_generated.cpp`\n\n"
                    "> **Gap (Low):** Direct in-suite profiling assertions only "
                    "exist for C++. A separate multi-language benchmark harness "
                    "exists under `tests/benchmarks/`, but its committed "
                    "baselines are placeholders and the CI workflow is advisory, "
                    "so it is not counted here as enforced regression coverage."
                ),
            },
            {
                "header": "Profile",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "3.5 Per-Message Round-trip Tests (`test_roundtrip_<pkg>.*`)",
                "intro": (
                    "Generated by `--generate_tests` and run by the **Round-trip "
                    "Tests** phase of `tests/run_tests.py`. For every message in "
                    "every `.sf` file, fields are populated with deterministic "
                    "dummy values, the message is encoded through every frame "
                    "profile, decoded via the streaming reader, and compared "
                    "against the original. (msg, profile) pairs that are "
                    "intentionally incompatible (e.g. `MSG_ID > 255` on a profile "
                    "without `pkg_id`, or payload exceeding `Config::max_payload`) "
                    "are reported as **skipped** rather than failures."
                ),
                "rows": [
                    _full("`profile_standard` round-trip", "✅"),
                    _full("`profile_sensor` round-trip", "✅"),
                    _full("`profile_ipc` round-trip", "✅"),
                    _full("`profile_bulk` round-trip", "✅"),
                    _full("`profile_network` round-trip", "✅"),
                ],
                "caption": (
                    "Generated files: "
                    "`tests/generated/<lang>/test_roundtrip_<pkg>.{c,cpp,py,ts,js,cs,rs}` "
                    "for all seven targets."
                ),
            },
        ],
    },
    {
        "number": "4",
        "title": "Cross-Language Compatibility Matrix",
        "intro": (
            "The test runner builds a compatibility matrix by having each "
            "language encode a frame and every other language decode it."
        ),
        "tables": [
            {
                "header": "Encoder \\ Decoder",
                "columns": LANGS,
                "lang_cols": [],  # diagonal/cross matrix, not triaged per-cell
                "rows": [
                    _row("C", {"C": "—", "C++": "✅", "Python": "✅", "TS": "✅",
                               "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("C++", {"C": "✅", "C++": "—", "Python": "✅", "TS": "✅",
                                 "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("Python", {"C": "✅", "C++": "✅", "Python": "—", "TS": "✅",
                                    "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("TypeScript", {"C": "✅", "C++": "✅", "Python": "✅",
                                        "TS": "—", "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("JavaScript", {"C": "✅", "C++": "✅", "Python": "✅",
                                        "TS": "✅", "JS": "—", "C#": "✅", "Rust": "✅"}),
                    _row("C#", {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                                "JS": "✅", "C#": "—", "Rust": "✅"}),
                    _row("Rust", {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                                  "JS": "✅", "C#": "✅", "Rust": "—"}),
                ],
                "caption": "Cross-platform testing is driven by the "
                           "encode/validate/decode matrix phases in "
                           "`tests/run_tests.py`.",
            },
        ],
    },
    {
        "number": "5",
        "title": "Error Handling / Negative Tests",
        "intro": (
            "Test files: `tests/{c,cpp,py,ts,js,csharp,rust}/test_negative.*`\n\n"
            "See `tests/NEGATIVE_TESTS.md` for full scenario descriptions.\n\n"
            "The 20 scenarios in the table below are registered in every "
            "language's `test_negative.*` file. Individual languages carry "
            "additional language-specific scenarios: C/C++/TS/JS/C# (24 each) "
            "add bulk `pkg_id`/`msg_id` corruption, cross-package rejection, and "
            "network `pkg_id` corruption; Python (34) adds those plus "
            "diagnostic-counter and status-machine tests; Rust (20) currently "
            "matches the uniform set."
        ),
        "tables": [
            {
                "header": "Error Scenario (test name)",
                "columns": LANGS,
                "lang_cols": LANGS,
                "rows": [_full(s, "✅") for s in (
                    "Buffer mode: recovers after CRC failure",
                    "Buffer reader: skips CRC-failed frame",
                    "Bulk profile: Corrupted CRC",
                    "Corrupted CRC detection",
                    "Corrupted length field detection",
                    "Invalid message ID rejection",
                    "Invalid start bytes detection",
                    "Minimal profile: Truncated frame",
                    "Multiple frames: CRC error then valid frame",
                    "Multiple frames: Corrupted middle frame",
                    "Network profile: SysId/CompId corruption",
                    "Partial frame across buffer boundary",
                    "Split-buffer: CRC error status preserved",
                    "Stream mode: recovers after garbage prefix",
                    "Streaming: Corrupted CRC detection",
                    "Streaming: Garbage data handling",
                    "TryNext drain: CRC/resync + valid",
                    "TryNext partial pending contract",
                    "Truncated frame detection",
                    "Zero-length buffer handling")],
            },
        ],
    },
    {
        "number": "6",
        "title": "SDK Classes",
        "tables": [
            {
                "header": "Class",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "6.1 Encoders / Writers",
                "rows": [
                    _row("`BufferWriter<Config>` / `buffer_writer_t`",
                         {"C": "✅", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _full("`ProfileStandardWriter`", "✅"),
                    _full("`ProfileSensorWriter`", "✅"),
                    _full("`ProfileIpcWriter`", "✅"),
                    _full("`ProfileBulkWriter`", "✅"),
                    _full("`ProfileNetworkWriter`", "✅"),
                    _row("`FrameEncoder<TProfile>`",
                         {"C": "N/A", "C++": "N/A", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "✅", "Rust": "N/A"}),
                    _row("`FrameEncoderWithCrc` / `FrameEncoderMinimal`",
                         {"C": "N/A", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                ],
                "caption": (
                    "> **Closed.** `FrameEncoderWithCrc` and "
                    "`FrameEncoderMinimal` now have 15 direct unit tests across "
                    "all five profiles in `tests/cpp/test_sdk_units.cpp`."
                ),
            },
            {
                "header": "Class",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "6.2 Parsers / Readers",
                "rows": [
                    _row("`BufferReader<Config>` / `buffer_reader_t`",
                         {"C": "✅", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _full("`AccumulatingReader<Config>` (buffer mode)", "✅"),
                    _full("`AccumulatingReader<Config>` (stream/byte mode)", "✅"),
                    _full("`ProfileStandardAccumulatingReader`", "✅"),
                    _row("`BufferParserWithCrc`",
                         {"C": "N/A", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _row("`BufferParserMinimal`",
                         {"C": "N/A", "C++": "✅", "Python": "N/A", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                ],
                "caption": (
                    "> **Closed (C).** `accumulating_reader_push_byte` is now "
                    "exercised by `tests/c/test_streaming.c` (4 tests: single "
                    "frame, sensor profile, two consecutive frames, garbage-prefix "
                    "skip).\n>\n"
                    "> **Closed (C++).** `BufferParserWithCrc` and "
                    "`BufferParserMinimal` now have dedicated unit tests in "
                    "`tests/cpp/test_sdk_units.cpp` (15 tests across all "
                    "profiles).\n>\n"
                    "> **Closed (Rust).** `AccumulatingReader::push_byte` is now "
                    "exercised by the `test_streaming` runner in "
                    "`tests/rust/src/main.rs` (6 tests: standard profile, "
                    "sensor/minimal profile, two consecutive frames, "
                    "garbage-prefix skip). The Rust `bytes_to_drain_for_resync` "
                    "logic was also fixed to correctly await payload bytes for "
                    "minimal (no-length) profiles in streaming mode.\n>\n"
                    "> **Python / TypeScript / JavaScript / C# byte mode.** These "
                    "targets have no standalone `test_streaming` suite; their "
                    "byte-at-a-time `AccumulatingReader` recovery is exercised by "
                    "the streaming scenarios in each `test_negative.*` "
                    "(`Streaming: Corrupted CRC detection`, `Streaming: Garbage "
                    "data handling`, `Stream mode: recovers after garbage prefix`, "
                    "and `Partial frame across buffer boundary`). This is the "
                    "accepted substitute for a dedicated streaming suite on those "
                    "targets."
                ),
            },
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "6.3 High-Level SDK (Transport + Routing)",
                "rows": [
                    _row("`StructFrameSdk` subscribe/dispatch",
                         {"C": "N/A", "C++": "✅", "Python": "✅", "TS": "✅",
                          "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("`AsyncStructFrameSdk` subscribe/dispatch",
                         {"C": "N/A", "C++": "N/A", "Python": "✅", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _row("`request()` / `RequestAsync()` (send + await response)",
                         {"C": "N/A", "C++": "N/A", "Python": "✅", "TS": "✅",
                          "JS": "N/A", "C#": "✅", "Rust": "N/A"}),
                    _row("`AsyncStructFrameSdk.request()` (async request/response)",
                         {"C": "N/A", "C++": "N/A", "Python": "✅", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                    _row("Serial transport",
                         {"C": "N/A", "C++": "❌", "Python": "❌", "TS": "❌",
                          "JS": "❌", "C#": "❌", "Rust": "N/A"}),
                    _row("TCP transport",
                         {"C": "N/A", "C++": "❌", "Python": "✅", "TS": "❌",
                          "JS": "❌", "C#": "❌", "Rust": "N/A"}),
                    _row("UDP transport",
                         {"C": "N/A", "C++": "❌", "Python": "❌", "TS": "❌",
                          "JS": "❌", "C#": "❌", "Rust": "N/A"}),
                    _row("WebSocket transport",
                         {"C": "N/A", "C++": "❌", "Python": "❌", "TS": "❌",
                          "JS": "❌", "C#": "❌", "Rust": "N/A"}),
                    _row("Async transport (Python)",
                         {"C": "N/A", "C++": "N/A", "Python": "❌", "TS": "N/A",
                          "JS": "N/A", "C#": "N/A", "Rust": "N/A"}),
                ],
                "caption": (
                    "> **Closed.** `StructFrameSdk` subscribe/dispatch is now "
                    "tested with mock transports in six languages:\n"
                    "> - **C++** -- `tests/cpp/test_sdk_subscribe.cpp` (17 `run_test` registrations)\n"
                    "> - **Python** -- `tests/py/test_sdk.py` (8 test functions, 31 `run_test` assertions)\n"
                    "> - **TypeScript** -- `tests/ts/test_sdk.ts` (7 test functions, 25 `assert` assertions)\n"
                    "> - **C#** -- `tests/csharp/TestSdkSubscribe.cs` (32 `Assert` assertions)\n"
                    "> - **JavaScript** -- `tests/js/test_sdk.js` (7 test functions, 25 `assert` assertions)\n"
                    "> - **Rust** -- `tests/rust/src/main.rs` `test_sdk_subscribe` "
                    "runner (5 test blocks, 13 `expect!` assertions)\n>\n"
                    "> **Lifecycle parity (handler isolation).** Python, TypeScript, "
                    "and JavaScript `test_sdk.*` each add a `throwing handler does "
                    "not stop siblings` regression (the SDK isolates every handler "
                    "in try/catch), matching the C# "
                    "`TestThrowingHandlerDoesNotStopSiblings` lifecycle test. "
                    "`StrictOrdering` (FIFO send-queue) and persistent/transient "
                    "subscriber coexistence remain C#-only SDK features, so they "
                    "have no cross-language port.\n>\n"
                    "> The C# suite additionally registers five dedicated SDK "
                    "runners (selected via `--runner <name>` in "
                    "`tests/csharp/TestRunner.cs`):\n"
                    "> - `test_sdk_strict_ordering` -- `tests/csharp/TestSdkStrictOrdering.cs` "
                    "(`StrictOrdering=true` FIFO send-queue, cancel-on-disconnect, "
                    "restart-after-reconnect)\n"
                    "> - `test_sdk_lifecycle` -- `tests/csharp/TestSdkLifecycle.cs` "
                    "(connect/close lifecycle, persistent + transient subscriber "
                    "coexistence, error paths)\n"
                    "> - `test_sdk_client_wrapper` -- `tests/csharp/TestSdkClientWrapper.cs` "
                    "(generated package `Client` wrapper Subscribe/Send/"
                    "SendViaCommandEnvelope)\n"
                    "> - `test_sdk_profiles` -- `tests/csharp/TestSdkProfiles.cs` "
                    "(SDK round-trip under Bulk and Sensor profiles)\n"
                    "> - `test_base_transport` -- `tests/csharp/TestBaseTransport.cs` "
                    "(`BaseTransport` semaphore/ROM overload/AutoReconnect; "
                    "the file explicitly omits `SerialTransport` because the "
                    "test project does not enable the optional `System.IO.Ports` "
                    "dependency)\n>\n"
                    "> **Closed (Python async SDK).** `AsyncStructFrameSdk` "
                    "subscribe/dispatch/send_raw/send/register_codec/"
                    "__aenter__/__aexit__/close-callback are tested with a mock "
                    "async transport in "
                    "`tests/py/test_async_sdk.py` (40 `run_test` pattern hits, "
                    "36 live assertions).\n>\n"
                    "> **Closed (request/response).** `request()` / `request_raw()` "
                    "(Python sync), `async request()` (Python async), "
                    "`request<TResp>()` (TypeScript), and `RequestAsync<TReq,TResp>()` "
                    "(C#) are tested with mock transports:\n"
                    "> - **Python sync** -- `tests/py/test_request_response_sdk.py` "
                    "(20 assertions: basic, timeout, match predicate, concurrent "
                    "in-flight, `request_raw`, cleanup, codec integration)\n"
                    "> - **Python async** -- `tests/py/test_request_response_async_sdk.py` "
                    "(13 assertions: basic, timeout, match, concurrent, cleanup)\n"
                    "> - **TypeScript** -- `tests/ts/test_request_response_sdk.ts` "
                    "(basic, timeout, match, concurrent, cleanup)\n"
                    "> - **C#** -- `tests/csharp/TestSdkRequestResponse.cs` "
                    "(`test_sdk_request_response` runner: basic, timeout, match, "
                    "concurrent, cleanup, CancellationToken)\n>\n"
                    "> **Scope (by design).** Request/response is intentionally a "
                    "C#/Python/TypeScript SDK feature. The C++, JavaScript, and Rust "
                    "SDKs do not expose a `request()` / `RequestAsync()` API, so the "
                    "`N/A` cells in the two request/response rows above mark an "
                    "intentional scope decision -- not an untested gap.\n>\n"
                    "> **Closed (Python TCP).** The concrete `TcpTransport` is now "
                    "exercised end to end over a localhost socket in "
                    "`tests/py/test_tcp_transport.py` (9 assertions: connect/"
                    "is_connected lifecycle, peer->client receive, client->peer "
                    "send, a full `StructFrameSdk` frame dispatch over the live "
                    "socket, and peer-disconnect close-callback).\n>\n"
                    "> **Gap (Low):** Serial, UDP, and WebSocket transports -- and "
                    "TCP in C++/TS/JS/C# -- remain uncovered end to end. "
                    "`StructFrameSdk` and `AsyncStructFrameSdk` routing are tested "
                    "with mock transports, but those concrete socket/serial/"
                    "WebSocket classes are not yet exercised against a live endpoint."
                ),
            },
        ],
    },
    {
        "number": "7",
        "title": "Import / Multi-Package Tests",
        "tables": [
            {
                "header": "Feature",
                "columns": LANGS,
                "lang_cols": LANGS,
                "rows": [
                    _full("Single import (`import \"types.sf\"`)", "✅"),
                    _full("Package with `pkgid`", "✅"),
                    _row("Multi-package with no IDs",
                         {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                          "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _row("Package with missing `msgid` on message",
                         {"C": "✅", "C++": "✅", "Python": "✅", "TS": "✅",
                          "JS": "✅", "C#": "✅", "Rust": "✅"}),
                    _full("Circular import detection", "✅"),
                ],
                "caption": (
                    "Proto files: `tests/proto/pkg_test_messages.sf`, "
                    "`pkg_test_a.sf`, `common_types.sf`\n\n"
                    "> Circular import detection is tested in "
                    "`tests/test_generator_validation.py`."
                ),
            },
        ],
    },
    {
        "number": "8",
        "title": "Validation / Generator Error Paths",
        "intro": (
            "These are tests of the generator itself (Python, "
            "language-agnostic), not the generated code. Error-path rules "
            "verify that invalid proto inputs are rejected; the two "
            "`max_size > 255` rows verify that an over-255 bounded field is "
            "accepted and emits a two-byte count prefix."
        ),
        "tables": [
            {
                "header": "Validation Rule",
                "columns": ["Tested"],
                "lang_cols": ["Tested"],
                "scope": "generator",
                "rows": [
                    _row("Duplicate `msgid` within package", {"Tested": "✅"}),
                    _row("Duplicate `pkgid` across packages", {"Tested": "✅"}),
                    _row("Duplicate field numbers within message", {"Tested": "✅"}),
                    _row("Missing `size`/`max_size` on array", {"Tested": "✅"}),
                    _row("Missing `size`/`max_size` on string", {"Tested": "✅"}),
                    _row("Missing `element_size` on string array", {"Tested": "✅"}),
                    _row("`max_size` > 255 on array count: accepted (two-byte count)", {"Tested": "✅"}),
                    _row("`max_size` > 255 on string: accepted (two-byte count)", {"Tested": "✅"}),
                    _row("Envelope with zero oneofs", {"Tested": "✅"}),
                    _row("Envelope with non-message oneof fields", {"Tested": "✅"}),
                    _row("Envelope with `msgid` discriminator and messages "
                         "missing `msgid`", {"Tested": "✅"}),
                    _row("Invalid `discriminator` option value", {"Tested": "✅"}),
                    _row("Field number zero", {"Tested": "✅"}),
                    _row("Circular import detection", {"Tested": "✅"}),
                    _row("Multi-package without `pkgid`", {"Tested": "✅"}),
                ],
                "caption": (
                    "All 14 generator-side error rules plus 2 acceptance checks "
                    "(max_size > 255 is legal for array and string fields) are "
                    "covered by the 16 passing tests in "
                    "`tests/test_generator_validation.py`. Note: "
                    "`max_size` > 255 triggers a two-byte length-count prefix "
                    "in the generated code; it is explicitly validated as "
                    "*allowed* (not rejected)."
                ),
            },
        ],
    },
    {
        "number": "9",
        "title": "Wire-Evolution Tests",
        "intro": (
            "Tests that verify backward-compatible message handling: unknown "
            "fields are ignored, fields with new defaults are decoded correctly "
            "from older binaries, and field reordering does not break decoding."
        ),
        "tables": [
            {
                "header": "Feature",
                "columns": ["Tested", "File"],
                "lang_cols": ["Tested"],
                "rows": [
                    _row("Unknown trailing fields ignored on decode",
                         {"Tested": "✅"}, "`tests/test_wire_evolution.py`"),
                    _row("New-field default on decode from older binary",
                         {"Tested": "✅"}, "`tests/test_wire_evolution.py`"),
                    _row("Field reorder round-trip (producer → consumer)",
                         {"Tested": "✅"}, "`tests/test_wire_evolution.py`"),
                ],
                "caption": "Proto source: `tests/proto/test_messages.sf` "
                           "(Python generator + round-trip).",
            },
            {
                "header": "Cross-version interop scenario",
                "columns": LANGS,
                "lang_cols": LANGS,
                "subtitle": "9.1 Genuine Cross-Version Extension Interop",
                "rows": [
                    _row("Newer sender → older receiver (length-bearing; "
                         "base decodes, trailing ext bytes skipped)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Older sender → newer receiver (extension fields "
                         "zero-filled to defaults)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Same-version round-trip regression guard (v2 → v2)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Newer ext oneof variant → older receiver degrades "
                         "gracefully (unknown discriminator)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Older base oneof variant → newer receiver decodes",
                         {lang: "✅" for lang in LANGS}),
                    _row("Multi-oneof: base oneof unaffected while 2nd oneof "
                         "carries an extension variant",
                         {lang: "✅" for lang in LANGS}),
                    _row("Corrupted extension bytes invalidate full CRC "
                         "(magic from base still matches)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Truncated payload (length < base_size) rejected",
                         {lang: "✅" for lang in LANGS}),
                    _row("Length-less profile guard (Sensor/IPC: both sides "
                         "must agree on full message size)",
                         {lang: "✅" for lang in LANGS}),
                    _row("Variable base array + trailing extension field "
                         "interop (both directions)",
                         {lang: "✅" for lang in LANGS}),
                ],
                "caption": (
                    "> Genuine cross-version interop uses a paired schema set, "
                    "`tests/proto/wire_evolution_v1.sf` (base only, no "
                    "`extensions_start`) and `tests/proto/wire_evolution_v2.sf` "
                    "(same `msg_id`/base fields + extension fields), generated "
                    "into separate namespaces so each side is unaware of the "
                    "other's extra fields. Magic bytes and `base_size` match "
                    "across versions because they are computed from the base "
                    "fields only, which is what lets cross-version CRC "
                    "validation work over the length-bearing Standard/Bulk/"
                    "Network profiles.\n>\n"
                    "> Dedicated runners (scenarios 1–10 in every language):\n"
                    "> - **Python** -- `tests/test_wire_evolution_interop.py`\n"
                    "> - **C** -- `tests/c/test_wire_evolution_interop.c`\n"
                    "> - **C++** -- `tests/cpp/test_wire_evolution_interop.cpp`\n"
                    "> - **TypeScript** -- `tests/ts/test_wire_evolution_interop.ts`\n"
                    "> - **JavaScript** -- `tests/js/test_wire_evolution_interop.js`\n"
                    "> - **C#** -- `tests/csharp/test_wire_evolution_interop.cs` "
                    "(`--runner test_wire_evolution_interop`)\n"
                    "> - **Rust** -- `tests/rust/src/main.rs` "
                    "`test_wire_evolution_interop` runner\n"
                ),
            },
        ],
    },
    {
        "number": "10",
        "title": "Magic-Byte Tests",
        "intro": (
            "Tests that verify the per-message start-byte constants "
            "(`magic1`/`magic2`) are correctly embedded in encoded frames and "
            "validated on decode."
        ),
        "tables": [
            {
                "header": "Feature",
                "columns": ["Tested", "File"],
                "lang_cols": ["Tested"],
                "rows": [
                    _row("Magic bytes present in encoded frame",
                         {"Tested": "✅"}, "`tests/test_magic_bytes.py`"),
                    _row("Wrong magic bytes → frame rejected",
                         {"Tested": "✅"}, "`tests/test_magic_bytes.py`"),
                    _row("Correct magic bytes → frame accepted",
                         {"Tested": "✅"}, "`tests/test_magic_bytes.py`"),
                    _row("Magic bytes absent (profile without magic)",
                         {"Tested": "✅"}, "`tests/test_magic_bytes.py`"),
                ],
            },
        ],
    },
    {
        "number": "11",
        "title": "Wireshark Dissector",
        "tables": [
            {
                "header": "Feature",
                "columns": ["Tested"],
                "lang_cols": ["Tested"],
                "scope": "wireshark",
                "rows": [
                    _row("Lua dissector loads without errors", {"Tested": "✅"}),
                    _row("Standard profile frame dissection", {"Tested": "✅"}),
                    _row("Extended (Bulk) profile frame dissection", {"Tested": "✅"}),
                    _row("Network profile frame dissection", {"Tested": "✅"}),
                    _row("CRC validity surfaced by dissector", {"Tested": "✅"}),
                ],
                "caption": "> Automated dissector tests live in "
                           "`wireshark/test_dissector.py`: each test writes a "
                           "`LINKTYPE_USER0` pcap, runs `tshark` with "
                           "`wireshark/struct_frame.lua`, and asserts the parsed "
                           "fields (start byte, message/package/system/component "
                           "id, length, CRC validity). The `tshark` invocation "
                           "itself exercises the *loads-without-errors* path. CI "
                           "runs them in `.github/workflows/wireshark-dissector.yml` "
                           "(skipped automatically when `tshark` is unavailable).",
            },
        ],
    },
]


# Curated, prose-only sections rendered verbatim after the matrices.  These
# describe infrastructure that has no per-language coverage matrix.
TRAILING_SECTIONS = [
    {
        "number": "13",
        "title": "CI / Robustness Infrastructure",
        "body": (
            "Tier B/C of the test-suite-vs-protobuf gap analysis added the "
            "following CI surfaces. Each lives in `.github/workflows/`:\n\n"
            "| Workflow | Purpose |\n"
            "|----------|---------|\n"
            "| `test.yml` (extended) | Primary suite + OS matrix (Linux, macOS), "
            "Python 3.9 / 3.11 / 3.13 matrix, Node 18 / 20 / 22 matrix, .NET 8 / "
            "10 matrix, GCC vs Clang matrix |\n"
            "| `sanitizers.yml` | ASan+UBSan and TSan jobs for the C/C++ suite, "
            "plus a Valgrind memcheck job for C binaries |\n"
            "| `fuzz.yml` | Short per-push libFuzzer run on the C parser harness; "
            "atheris run on the Python parser |\n"
            "| `coverage.yml` | `coverage.py` instrumentation of the Python "
            "generator + Codecov upload |\n"
            "| `wireshark-dissector.yml` | Runs `wireshark/test_dissector.py` "
            "against the Lua dissector via `tshark` on golden pcaps |\n"
            "| `benchmark-regression.yml` | Advisory quick benchmark smoke; "
            "runs available language benchmarks and uploads results, but the "
            "job is `continue-on-error` and committed baselines are placeholders |\n"
            "| `api-stability.yml` | Advisory public API checks; Python, "
            "NuGet, and crates baselines are present, npm lacks a baseline, and "
            "the workflow is `continue-on-error` |\n"
            "| `doc-samples.yml` | Doctest-style extraction plus quick sample "
            "compilation; quick mode skips C, C++, TypeScript, Rust, and C# "
            "samples, and fragment-like snippets are intentionally skipped |\n\n"
            "Sanitizer flags are injected by exporting `CC` / `CXX` / `CFLAGS` / "
            "`CXXFLAGS` / `LDFLAGS`, which `tests/run_tests.py` honours at every "
            "C/C++ compile site. No runner changes are needed to introduce "
            "additional sanitizer or coverage jobs. Benchmark regression and "
            "API-stability jobs are signal-only today; failures there do not "
            "block merges until real baselines are established and "
            "`continue-on-error` is removed.\n\n"
            "### Fuzzing harnesses\n\n"
            "| Harness | File | Tooling |\n"
            "|---------|------|---------|\n"
            "| C accumulating-reader | `tests/c/fuzz_parser.c` | libFuzzer + "
            "ASan/UBSan |\n"
            "| Python `AccumulatingReader` | `tests/py/fuzz_parser.py` | atheris |\n"
            "| Rust `AccumulatingReader` | "
            "`tests/rust/fuzz/fuzz_targets/parser.rs` (+ `Cargo.toml`) | "
            "cargo-fuzz |\n\n"
            "The C++, TypeScript, JavaScript, and C# parsers have no dedicated "
            "fuzz harness yet; they rely on the cross-language decode matrix and "
            "their `test_negative.*` malformed-input suites for adversarial "
            "coverage. Adding native fuzzers (libFuzzer for C++, jsfuzz / "
            "fast-check for TS/JS, SharpFuzz for C#) is a tracked follow-up.\n\n"
            "### Property-based tests\n\n"
            "`tests/test_property_roundtrip.py` uses Hypothesis to generate "
            "random instances of selected message classes and assert that Python "
            "encode → Python decode round-trips preserve equality across the "
            "Standard, Bulk, and Network profiles. Cross-language fan-out is "
            "tracked as a follow-up.\n\n"
            "### Stability & flake policy\n\n"
            "Retry budgets, quarantine rules, and triage ownership for flaky "
            "tests are documented in [Test Stability Policy](test-stability)."
        ),
    },
    {
        "number": "14",
        "title": "Implementation And Shortcut Audit Notes",
        "body": (
            "A source/test sweep for `TODO`, `FIXME`, `NotImplemented`, "
            "placeholder, stub, dummy, and skip patterns found no dummy "
            "implementation in the core serialization generators or runtime "
            "encode/decode paths. The remaining findings are limited, "
            "intentional, or coverage-related:\n\n"
            "| Finding | Current status | Follow-up |\n"
            "|---------|----------------|-----------|\n"
            "| C++ generated envelope `wrap()` helper skips non-oneof array, "
            "string, and bytes envelope fields when building the convenience "
            "parameter list | Core serialization still handles those fields, "
            "but the helper is ergonomically incomplete | Implement helper "
            "parameters/initialization for bounded arrays, strings, and bytes |\n"
            "| C# `TcpTransport` / `UdpTransport` comments still describe the "
            "classes as stubs | The classes now contain `System.Net.Sockets` "
            "implementations; the stale comments are documentation debt, not "
            "a dummy implementation | Update comments and add socket-level "
            "transport tests |\n"
            "| C++ `serial_transport.hpp` includes an `EXAMPLE_IMPLEMENTATION` "
            "UART stub | This is behind a compile-time example macro; the real "
            "transport depends on a user-provided `ISerialPort` | Keep as an "
            "example, but cover concrete serial behavior with a fake `ISerialPort` |\n"
            "| Wireshark dissector cannot auto-detect no-header/no-start-byte "
            "frames | This is a genuine protocol-context limitation documented "
            "in `wireshark/struct_frame.lua` | Add manual profile configuration "
            "if no-header dissection is required |\n"
            "| Generated round-trip suites count profile/message incompatibility "
            "skips as passes | This is intentional to avoid false negatives for "
            "unsupported combinations, but pass totals can hide broad profile "
            "incompatibility when skip counts are high | Report pass/fail/skip "
            "separately per profile and fail when a profile is entirely skipped |\n"
            "| C++ SDK unit/subscribe tests use many bare `return false` checks "
            "with limited per-assert diagnostics | Behavioral coverage is good, "
            "but failures can be slower to triage than message-rich assertions "
            "| Add assertion helpers that include failed condition context "
            "without changing test semantics |\n"
            "| Multi-language benchmark baselines are placeholders | The runner "
            "validates result schema, but regression checks are advisory and "
            "non-gating | Refresh baselines from reviewed full benchmark runs "
            "and remove `continue-on-error` |\n"
            "| Documentation sample CI runs `tests/docs/run_samples.py` with "
            "`--quick` "
            "| Quick mode skips compiled C/C++/TS/Rust/C# samples and fragment-like "
            "snippets, so it is syntax-smoke coverage rather than full sample "
            "execution | Add a scheduled or release-blocking full sample job |"
        ),
    },
]


# Priority hints for the triage section, keyed by (section_number, row label
# substring).  Anything not matched defaults to "Medium".
PRIORITY_HINTS = [
    ("6", "transport", "Low"),
    ("6", "Async transport", "Low"),
    ("11", "", "Low"),
    ("3", "throughput", "Low"),
    ("3", "Packed", "Low"),
    ("1", "equality", "Low"),
    ("1", "validate", "Low"),
    ("1", "caching", "Low"),
    ("1", "legacy_enum", "Low"),
    ("7", "Circular", "Medium"),
    ("7", "Multi-package", "Medium"),
    ("7", "missing `msgid`", "Medium"),
    ("8", "", "High"),
]
