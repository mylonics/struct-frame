#!/usr/bin/env python3
"""
Simple entry point for running the struct-frame test suite.

This script provides a single command to run all tests in the struct-frame project.
"""

import sys
import os
from pathlib import Path

# Add the tests directory to the Python path
tests_dir = Path(__file__).parent / "tests"
sys.path.insert(0, str(tests_dir))

try:
    from run_tests import main as run_tests_main, clean_test_files
    # Clean build/generated folders before running tests
    clean_test_files("tests/test_config.json", verbose=False)
    success = run_tests_main()
    sys.exit(0 if success else 1)
except ImportError:
    print("[ERROR] Failed to import test runner")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test run failed: {e}")
    sys.exit(1)
