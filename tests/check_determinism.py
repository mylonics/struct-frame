#!/usr/bin/env python3
"""
Generated-file determinism check.

Regenerates all test outputs to a temporary directory and diffs them against
the committed tests/generated/ tree. Exits with code 1 if any file differs,
was added, or was removed — which would mean a committed artefact is stale or
the generator is non-deterministic.

Usage:
    python tests/check_determinism.py
    python tests/check_determinism.py --verbose
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROTO_FILES = [
    "test_messages.sf",
    "pkg_test_messages.sf",
    "extended_messages.sf",
    "envelope_messages.sf",
]

# Language id  → (gen_flag, subdir)
LANGUAGES = [
    ("c",      "--build_c",      "c"),
    ("cpp",    "--build_cpp",    "cpp"),
    ("py",     "--build_py",     "py"),
    ("ts",     "--build_ts",     "ts"),
    ("js",     "--build_js",     "js"),
    ("gql",    "--build_gql",    "gql"),
    ("csharp", "--build_csharp", "csharp"),
    ("rust",   "--build_rust",   "rust"),
]

# File names to skip everywhere (exact match on the filename component).
# These are either path-dependent caching artefacts or build/toolchain outputs.
IGNORE_NAMES = {
    "sf_compile.json",   # catalog – may contain absolute paths
    ".structframe.hash",  # cache key includes output-directory paths
}

# Directory segments that mark entire subtrees to skip.
IGNORE_DIR_SEGMENTS = {
    "__pycache__",  # Python bytecode
    "obj",          # C# / MSBuild build artefacts
    "bin",          # C# compiled output
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _collect(root: Path) -> dict[str, str]:
    """Return {relative_path: sha256} for every file under root."""
    result = {}
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if f.name in IGNORE_NAMES:
            continue
        rel = f.relative_to(root)
        if any(part in IGNORE_DIR_SEGMENTS for part in rel.parts[:-1]):
            continue
        result[str(rel)] = _sha256(f)
    return result


def _generate(tmpdir: Path, project_root: Path, verbose: bool) -> bool:
    """Run the generator for all proto files into tmpdir. Returns True on success."""
    proto_dir = project_root / "tests" / "proto"
    env = {**os.environ, "PYTHONPATH": str(project_root / "src")}

    for proto_file in PROTO_FILES:
        proto_path = proto_dir / proto_file
        cmd = [sys.executable, "-m", "struct_frame", str(proto_path), "--equality", "--force"]
        for _id, gen_flag, subdir in LANGUAGES:
            out = tmpdir / subdir
            out.mkdir(parents=True, exist_ok=True)
            # Derive the --<lang>_path flag: strip leading "--build_" → "<lang>_path"
            path_flag = "--" + gen_flag.lstrip("-").replace("build_", "") + "_path"
            cmd += [gen_flag, path_flag, str(out)]
        cmd += ["--catalog_path", str(tmpdir)]

        if verbose:
            print(f"  Generating {proto_file}…")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True,
                                cwd=str(project_root))
        if result.returncode != 0:
            print(f"[FAIL] Generation failed for {proto_file}")
            print(result.stderr)
            return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check generated-file determinism.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    committed = project_root / "tests" / "generated"

    with tempfile.TemporaryDirectory(prefix="sf_det_") as tmp:
        tmpdir = Path(tmp)

        print("Generating code to temporary directory…")
        if not _generate(tmpdir, project_root, args.verbose):
            return 1

        print("Comparing against committed tests/generated/…")
        committed_files = _collect(committed)
        generated_files = _collect(tmpdir)

        added   = sorted(set(generated_files) - set(committed_files))
        removed = sorted(set(committed_files) - set(generated_files))
        changed = sorted(
            p for p in set(committed_files) & set(generated_files)
            if committed_files[p] != generated_files[p]
        )

        if not (added or removed or changed):
            print("[OK] All generated files are deterministic and up to date.")
            return 0

        print("\n[FAIL] Generated output differs from committed files:\n")
        for p in added:
            print(f"  + {p}  (new — not in committed tree)")
        for p in removed:
            print(f"  - {p}  (missing — in committed tree but not regenerated)")
        for p in changed:
            print(f"  ~ {p}  (content changed)")

        print(
            f"\n{len(added)} added, {len(removed)} removed, {len(changed)} changed.\n"
            "Run the test suite to regenerate, then commit the updated files."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
