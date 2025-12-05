#!/usr/bin/env python3
"""
Generic Test Suite Runner for struct-frame Project

This script is completely configuration-driven. It reads test_config.json
and executes all tests without any hardcoded knowledge of what tests exist.

Usage:
    python run_tests.py [--config CONFIG] [--verbose] [--skip-lang LANG] [--only-generate]
    python run_tests.py --clean          # Clean all generated/compiled files
    python run_tests.py --check-tools    # Check tool availability
"""

import argparse
import shutil
import sys
from pathlib import Path

from runner import TestRunner
from languages import get_language, get_all_language_ids


def clean_test_files(config_path: str, verbose: bool = False) -> bool:
    """Clean all generated and compiled test files."""
    project_root = Path(__file__).parent.parent

    cleaned_count = 0
    print("Cleaning test files...")

    for lang_id in get_all_language_ids():
        lang = get_language(lang_id, project_root)
        if not lang:
            continue

        gen_dir = project_root / lang.gen_output_dir
        if gen_dir.exists():
            if verbose:
                print(f"  Removing generated directory: {gen_dir}")
            shutil.rmtree(gen_dir)
            cleaned_count += 1

        if not lang.build_dir:
            continue

        build_dir = project_root / lang.build_dir
        if build_dir.exists():
            if verbose:
                print(f"  Removing build directory: {build_dir}")
            shutil.rmtree(build_dir)
            cleaned_count += 1

    print(f"Cleaned {cleaned_count} items")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run configuration-driven tests for struct-frame")
    parser.add_argument("--config", default="tests/test_config.json",
                        help="Path to test configuration file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--verbose-failure", action="store_true",
                        help="Show output only when tests fail")
    parser.add_argument("--skip-lang", action="append",
                        dest="skip_languages", help="Skip specific language")
    parser.add_argument("--only-generate", action="store_true",
                        help="Only run code generation")
    parser.add_argument("--check-tools", action="store_true",
                        help="Only check tool availability, don't run tests")
    parser.add_argument("--clean", action="store_true",
                        help="Clean all generated and compiled test files")

    args = parser.parse_args()

    if args.clean:
        return clean_test_files(args.config, verbose=args.verbose)

    runner = TestRunner(args.config, verbose=args.verbose,
                        verbose_failure=args.verbose_failure)
    runner.skipped_languages = args.skip_languages or []

    if args.check_tools:
        return runner.print_tool_availability()

    return runner.run_all_tests(generate_only=args.only_generate)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
