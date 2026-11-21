#!/usr/bin/env python3
"""Add commits that git-changelog left out to a release's CHANGELOG.md section.

git-changelog (conventional convention) renders only feat/fix/perf/refactor/revert
commits and drops every other subject without a word. After it inserts a release
section, this script lists, under "### Other changes":

  * commits whose subject has no conventional type at all ("Updated csproj (#384)").
    These are always listed: they are usually real changes with a mistyped title.
  * if the section would otherwise list nothing, the hidden-type commits too
    (chore/docs/ci/test/...), so a release never ships with an empty entry.

Commits already linked from the section are skipped, so re-running is a no-op.
Exits non-zero only if the section is missing or the release range has no commits.

Usage: changelog_other_changes.py CHANGELOG.md v1.2.3 [--to REV]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Types git-changelog's ConventionalCommitConvention knows, and the ones it renders by default.
KNOWN = r"build|chore|ci|deps|docs?|feat|fix|perf|ref|refactor|revert|style|tests?"
RENDERED = {"feat", "fix", "perf", "ref", "refactor", "revert"}
TYPE_RE = re.compile(rf"^(?P<type>{KNOWN})(\([^)]*\))?!?: \S")

Commit = tuple[str, str, str]  # (sha, author, subject)


def find_section(text: str, tag: str) -> tuple[int, int] | None:
    """Return the (start, end) offsets of the "## [tag]" section, or None."""
    head = re.search(rf"(?m)^## \[{re.escape(tag)}\].*$", text)
    if not head:
        return None
    nxt = re.search(r"(?m)^## ", text[head.end():])
    return head.start(), (head.end() + nxt.start() if nxt else len(text))


def release_commits(rev_range: str) -> list[Commit]:
    """Non-merge commits in the range, minus version-bump commits."""
    log = subprocess.run(
        ["git", "log", "--no-merges", "--format=%H%x1f%an%x1f%s", rev_range],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    commits = [tuple(line.split("\x1f")) for line in log.splitlines() if line]
    return [c for c in commits if "[release]" not in c[2]]


def unlisted(commits: list[Commit], section: str) -> list[Commit]:
    """Commits to add under "Other changes": the untyped ones, or the hidden-type
    ones if the section would otherwise list nothing."""
    untyped, hidden = [], []
    for sha, author, subject in commits:
        if f"/commit/{sha}" in section:
            continue  # already listed (rendered by git-changelog, or an earlier run)
        m = TYPE_RE.match(subject)
        if not m:
            untyped.append((sha, author, subject))
        elif m.group("type") not in RENDERED:
            hidden.append((sha, author, subject))
    if untyped or re.search(r"(?m)^- \S", section):
        return untyped
    return hidden


def repo_url(section: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}"
    link = re.search(r"\((https?://[^)]+?)/releases/tag/", section)
    return link.group(1) if link else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("changelog", type=Path)
    ap.add_argument("tag", help="release tag whose section to check, e.g. v1.2.3")
    ap.add_argument("--to", default="HEAD", help="last commit of the release (default HEAD)")
    args = ap.parse_args()

    with open(args.changelog, encoding="utf-8", newline="") as f:
        text = f.read()
    bounds = find_section(text, args.tag)
    if bounds is None:
        print(f"::error::CHANGELOG.md has no section for {args.tag}")
        return 1
    start, end = bounds
    section = text[start:end]

    prev = re.search(r"\[Compare with ([^\]]+)\]", section)
    rev_range = f"{prev.group(1)}..{args.to}" if prev else args.to
    commits = release_commits(rev_range)
    if not commits:
        print(f"::error::No commits in {rev_range}: nothing to release.")
        return 1

    other = unlisted(commits, section)
    if not other:
        print(f"{args.tag}: changelog section already lists every change.")
        return 0

    base = repo_url(section)
    nl = "\r\n" if "\r\n" in text else "\n"
    bullets = "".join(f"- {subject} ([{sha[:7]}]({base}/commit/{sha}) by {author}).{nl}"
                      for sha, author, subject in other)
    new_section = f"{section.rstrip(nl)}{nl}{nl}### Other changes{nl}{nl}{bullets}{nl}"
    with open(args.changelog, "w", encoding="utf-8", newline="") as f:
        f.write(text[:start] + new_section + text[end:])

    listed = "; ".join(subject for _, _, subject in other)
    print(f"::warning::{args.tag}: added {len(other)} commit(s) that git-changelog does not list "
          f"(no feat:/fix:/perf:/refactor:/revert: type) under 'Other changes': {listed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
