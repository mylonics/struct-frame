#!/usr/bin/env python3
"""Generate ``docs/.../reference/test-coverage.md`` from ``coverage_spec.py``.

The generated document is intentionally *not* hand-maintained.  This script:

1. Loads the structured coverage spec (:mod:`coverage_spec`).
2. **Walks ``tests/``** and **introspects the generator's feature set**
   (CLI flags in ``src/struct_frame/generate.py`` and frame profiles in the
   Python boilerplate) to detect drift -- e.g. a generator flag the spec never
   mentions, a frame profile that is missing, or a referenced test file that
   has been deleted.  This is what keeps the published table honest.
3. Renders the Markdown, including an auto-derived **Test Coverage Triage**
   section that converts every ``❌``/``⚠️`` cell into a tracked, linkable
   GitHub issue.

Usage::

    python tests/gen_test_coverage.py            # write the doc
    python tests/gen_test_coverage.py --check     # fail if the doc is stale
    python tests/gen_test_coverage.py --stdout    # print to stdout

CI runs ``--check`` so the doc cannot silently drift from the tests on disk.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import urllib.parse
from pathlib import Path

import coverage_spec as spec

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"
GENERATE_PY = REPO_ROOT / "src" / "struct_frame" / "generate.py"
PROFILES_PY = (
    REPO_ROOT / "src" / "struct_frame" / "boilerplate" / "py" / "frame_profiles.py"
)
OUTPUT_DOC = (
    REPO_ROOT
    / "docs"
    / "src"
    / "content"
    / "docs"
    / "reference"
    / "test-coverage.md"
)

GITHUB_SLUG = "mylonics/struct-frame"
NEW_ISSUE_URL = f"https://github.com/{GITHUB_SLUG}/issues/new"
ISSUE_SEARCH_URL = f"https://github.com/{GITHUB_SLUG}/issues"
TRIAGE_LABELS = "test-gap,coverage"


# ---------------------------------------------------------------------------
# Introspection of the generator feature set + tests/ tree
# ---------------------------------------------------------------------------
def discover_cli_flags():
    """Return the set of long-form CLI flags declared by the generator."""
    text = GENERATE_PY.read_text(encoding="utf-8")
    return set(re.findall(r"add_argument\(\s*'(--[a-zA-Z0-9_]+)'", text))


def discover_profiles():
    """Return the frame-profile names declared in the Python boilerplate."""
    text = PROFILES_PY.read_text(encoding="utf-8")
    return set(re.findall(r'name\s*=\s*"(Profile[A-Za-z0-9]+)"', text))


def discover_test_files():
    """Return every file path (relative to repo root) found under ``tests/``."""
    files = set()
    for path in TESTS_DIR.rglob("*"):
        if path.is_file():
            files.add(path.relative_to(REPO_ROOT).as_posix())
    return files


def spec_text():
    """Concatenate every piece of human-readable text in the spec."""
    chunks = [spec.INTRO]
    for section in spec.SECTIONS:
        chunks.append(section.get("intro", ""))
        for table in section["tables"]:
            chunks.append(table.get("intro", ""))
            chunks.append(table.get("caption", ""))
            for row in table["rows"]:
                chunks.append(row["label"])
                chunks.append(row.get("notes", ""))
    for section in spec.TRAILING_SECTIONS:
        chunks.append(section["body"])
    return "\n".join(chunks)


def validate():
    """Cross-check the spec against the live tests/ tree and generator.

    Returns a list of human-readable problem strings (empty when healthy).
    """
    problems = []
    blob = spec_text()

    # 1. Every generator CLI flag should be acknowledged by the spec so new
    #    flags can't ship untracked.  Path/namespace flags are pure plumbing.
    ignore_flags = {
        "--debug", "--build_c", "--build_cpp", "--build_ts", "--build_js",
        "--build_py", "--build_csharp", "--build_gql", "--build_rust",
        "--c_path", "--cpp_path", "--ts_path", "--js_path", "--py_path",
        "--csharp_path", "--gql_path", "--rust_path", "--catalog_path",
        "--hash_path", "--csharp_namespace", "--sdk", "--sdk_embedded",
    }
    for flag in sorted(discover_cli_flags() - ignore_flags):
        if flag not in blob:
            problems.append(
                f"generator CLI flag {flag} is not referenced in coverage_spec.py "
                f"(add a row to section 1)"
            )

    # 1b. Conversely, every flag-shaped row label in section 1 must name a real
    #     generator flag -- this catches stale rows for flags that were removed
    #     or never existed.
    known_flags = discover_cli_flags()
    for section in spec.SECTIONS:
        if section["number"] != "1":
            continue
        for table in section["tables"]:
            for row in table["rows"]:
                for flag in re.findall(r"`(--[a-zA-Z0-9_]+)`", row["label"]):
                    if flag not in known_flags:
                        problems.append(
                            f"spec section 1 references unknown generator flag "
                            f"{flag} (no matching add_argument in generate.py)"
                        )

    # 2. Every frame profile the generator ships must appear in the spec.
    for profile in sorted(discover_profiles()):
        if profile not in blob and profile.lower() not in blob.lower():
            problems.append(
                f"frame profile {profile} is not referenced in coverage_spec.py"
            )

    # 3. Every concrete tests/ file path mentioned in the spec must exist.
    present = discover_test_files()
    referenced = set(re.findall(r"`(tests/[^`]+)`", blob))
    for ref in sorted(referenced):
        # Skip glob/brace/placeholder paths -- they describe families of files.
        if any(ch in ref for ch in "{}*<>") or ref.endswith("/"):
            continue
        # Generated artifacts live under tests/generated and need not exist
        # in a fresh checkout.
        if ref.startswith("tests/generated/"):
            continue
        if ref not in present:
            problems.append(f"spec references missing test file: {ref}")

    return problems


# ---------------------------------------------------------------------------
# Triage extraction
# ---------------------------------------------------------------------------
def _priority_for(section_number, label):
    for sec, needle, prio in spec.PRIORITY_HINTS:
        if sec == section_number and (needle == "" or needle.lower() in label.lower()):
            return prio
    return "Medium"


def collect_gaps():
    """Return triage entries derived from every ❌/⚠️ cell in the spec."""
    gaps = []
    counter = 0
    for section in spec.SECTIONS:
        for table in section["tables"]:
            lang_cols = table.get("lang_cols", [])
            # Non-language matrices (a single boolean "Tested" column) describe
            # generator/tooling coverage; label them by scope instead of by a
            # bogus "Tested" language name.
            scope = table.get("scope")
            for row in table["rows"]:
                hit_langs = []
                worst = None
                for col in lang_cols:
                    value = row["cells"].get(col, "")
                    if value in spec.GAP_SYMBOLS:
                        hit_langs.append(scope if scope else col)
                        if worst is None or value == "❌":
                            worst = value
                if not hit_langs:
                    continue
                counter += 1
                area = re.sub(r"`", "", row["label"])
                subtitle = table.get("subtitle", "")
                gaps.append({
                    "id": f"TC-{section['number']}-{counter:02d}",
                    "section": section["number"],
                    "section_title": section["title"],
                    "subtitle": subtitle,
                    "area": area.strip(),
                    "symbol": worst,
                    "langs": hit_langs,
                    "priority": _priority_for(section["number"], row["label"]),
                })
    return gaps


def _issue_link(gap):
    """Build a 'file/track issue' link pre-filled for this gap."""
    langs = ", ".join(gap["langs"])
    where = gap["section_title"]
    if gap["subtitle"]:
        where += f" / {gap['subtitle']}"
    title = f"[test-gap {gap['id']}] {gap['area']} ({langs})"
    body = (
        f"Tracked from the Test Coverage matrix (`{gap['id']}`).\n\n"
        f"- **Area:** {gap['area']}\n"
        f"- **Section:** {where}\n"
        f"- **Languages with a gap:** {langs}\n"
        f"- **Current status:** {gap['symbol']}\n"
        f"- **Priority:** {gap['priority']}\n\n"
        f"Add or extend tests until every cell for this row is ✅ (or "
        f"documented N/A), then update `tests/coverage_spec.py`."
    )
    query = urllib.parse.urlencode({
        "title": title,
        "labels": TRIAGE_LABELS,
        "body": body,
    })
    return f"[track ↗]({NEW_ISSUE_URL}?{query})"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _render_table(table):
    out = []
    if table.get("subtitle"):
        out.append(f"### {table['subtitle']}\n")
    if table.get("intro"):
        out.append(table["intro"] + "\n")

    columns = table["columns"]
    # Columns that carry coverage symbols (present in at least one row's cells).
    # Any remaining columns (e.g. "Notes"/"File") are fed from the row's notes.
    cell_cols = [c for c in columns
                 if any(c in row["cells"] for row in table["rows"])]

    header = "| " + " | ".join([table["header"]] + columns) + " |"
    sep = "|" + "|".join(["--------"] * (len(columns) + 1)) + "|"
    out.append(header)
    out.append(sep)
    for row in table["rows"]:
        values = [row["label"]]
        for col in columns:
            if col in cell_cols:
                values.append(row["cells"].get(col, ""))
            else:
                values.append(row.get("notes", ""))
        out.append("| " + " | ".join(values) + " |")
    block = "\n".join(out)
    if table.get("caption"):
        block += "\n\n" + table["caption"]
    return block


def _render_triage(gaps):
    lines = [
        "## Test Coverage Triage\n",
        "Every `❌` and `⚠️` cell in the tables above is converted here into a "
        "tracked, linkable GitHub issue so coverage gaps are *owned* rather "
        "than merely listed. Triage ownership, retry budgets, and quarantine "
        "rules live in the [Test Stability Policy](test-stability).\n",
        f"Open gaps: **{len(gaps)}**. Each **track ↗** link opens a pre-filled "
        f"issue (labels `{TRIAGE_LABELS}`); replace it with the real issue URL "
        f"once filed. To see issues already filed, browse "
        f"[`label:test-gap`]({ISSUE_SEARCH_URL}?q=is%3Aissue+label%3Atest-gap).\n",
        "| ID | Priority | Area | Section | Gap | Languages | Issue |",
        "|----|----------|------|---------|-----|-----------|-------|",
    ]
    order = {"High": 0, "Medium": 1, "Low": 2}
    for gap in sorted(gaps, key=lambda g: (order.get(g["priority"], 1), g["id"])):
        section = f"§{gap['section']}"
        if gap["subtitle"]:
            section += f" · {gap['subtitle'].split(' ', 1)[0]}"
        lines.append(
            f"| `{gap['id']}` | {gap['priority']} | {gap['area']} | {section} "
            f"| {gap['symbol']} | {', '.join(gap['langs'])} | {_issue_link(gap)} |"
        )
    return "\n".join(lines)


def render():
    today = datetime.date.today().isoformat()
    parts = []

    # Frontmatter (Astro Starlight).
    parts.append(
        "---\n"
        "title: Test Coverage\n"
        f"description: {spec.DESCRIPTION}\n"
        "---\n"
    )
    parts.append(
        "<!-- GENERATED FILE - DO NOT EDIT.\n"
        "     Source of truth: tests/coverage_spec.py\n"
        "     Regenerate with: python tests/gen_test_coverage.py -->\n"
    )
    parts.append(spec.INTRO + "\n")

    # Legend.
    parts.append("## Legend\n")
    parts.append("| Symbol | Meaning |\n|--------|---------|")
    for symbol, meaning in spec.LEGEND:
        parts.append(f"| {symbol} | {meaning} |")
    langs = ", ".join(f"**{l}**" for l in spec.LANGS)
    parts.append(f"\nLanguages tracked: {langs}")
    parts.append("\n---\n")

    # Sections with matrices.
    for section in spec.SECTIONS:
        parts.append(f"## {section['number']}. {section['title']}\n")
        if section.get("intro"):
            parts.append(section["intro"] + "\n")
        for table in section["tables"]:
            parts.append(_render_table(table))
            parts.append("")
        parts.append("---\n")

    # Auto-derived triage section.
    gaps = collect_gaps()
    parts.append(_render_triage(gaps))
    parts.append("\n---\n")

    # Curated trailing prose sections.
    for section in spec.TRAILING_SECTIONS:
        parts.append(f"## {section['number']}. {section['title']}\n")
        parts.append(section["body"])
        parts.append("\n---\n")

    parts.append(
        f"*Generated from `tests/coverage_spec.py` by "
        f"`tests/gen_test_coverage.py` on {today}. "
        f"Do not edit this file directly -- update the spec and regenerate.*"
    )

    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if the committed doc is out of date")
    parser.add_argument("--stdout", action="store_true",
                        help="print the rendered doc to stdout instead of writing")
    parser.add_argument("--skip-validation", action="store_true",
                        help="skip the tests/ + generator drift checks")
    args = parser.parse_args(argv)

    problems = [] if args.skip_validation else validate()
    if problems:
        print("Coverage spec validation problems:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        # In --check mode validation problems are fatal; otherwise warn loudly
        # but still regenerate so the author can inspect the output.
        if args.check:
            return 1

    rendered = render()

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    if args.check:
        current = OUTPUT_DOC.read_text(encoding="utf-8") if OUTPUT_DOC.exists() else ""
        if current != rendered:
            print(
                f"{OUTPUT_DOC.relative_to(REPO_ROOT)} is out of date.\n"
                f"Run: python tests/gen_test_coverage.py",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT_DOC.relative_to(REPO_ROOT)} is up to date.")
        return 0

    OUTPUT_DOC.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT_DOC.relative_to(REPO_ROOT)} ({len(rendered)} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
