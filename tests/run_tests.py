#!/usr/bin/env python3
"""
Generic Test Suite Runner for struct-frame Project

This script is completely configuration-driven. It reads test_config.json
and executes all tests without any hardcoded knowledge of what tests exist.

Usage:
    python run_tests.py [--config CONFIG] [--verbose] [--skip-lang LANG] [--only-generate]

The test runner functionality has been split into modular components:
    - runner/base.py: Base utilities (logging, command execution, config loading)
    - runner/tool_checker.py: Tool availability checking
    - runner/code_generator.py: Code generation from proto files
    - runner/compiler.py: Compilation for C, C++, TypeScript
    - runner/test_executor.py: Test suite and cross-platform test execution
    - runner/output_formatter.py: Result formatting and summary printing
    - runner/runner.py: Main ConfigDrivenTestRunner that composes all components
"""

import argparse
import sys

# Import the modular test runner
from runner import ConfigDrivenTestRunner


def main():
    parser = argparse.ArgumentParser(
        description="Run configuration-driven tests for struct-frame")
    parser.add_argument("--config", default="tests/test_config.json",
                        help="Path to test configuration file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--skip-lang", action="append",
                        dest="skip_languages", help="Skip specific language")
    parser.add_argument("--only-generate", action="store_true",
                        help="Only run code generation")
    parser.add_argument("--check-tools", action="store_true",
                        help="Only check tool availability, don't run tests")

    args = parser.parse_args()
    runner = ConfigDrivenTestRunner(args.config, verbose=args.verbose)
    runner.skipped_languages = args.skip_languages or []

    if args.check_tools:
        return runner.print_tool_availability()

    return runner.run_all_tests(generate_only=args.only_generate)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
