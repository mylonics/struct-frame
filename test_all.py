#!/usr/bin/env python3
"""
Simple entry point for running the struct-frame test suite.

This script provides a single command to run all tests in the struct-frame project.
"""

import sys
import os
import shutil
from pathlib import Path

# Add the tests directory to the Python path
tests_dir = Path(__file__).parent / "tests"
sys.path.insert(0, str(tests_dir))


def clean_generated_folder():
    """Delete the tests/generated folder completely before running tests."""
    generated_dir = Path(__file__).parent / "tests" / "generated"
    if generated_dir.exists():
        print("[CLEAN] Deleting tests/generated folder...")
        shutil.rmtree(generated_dir)
        print("[CLEAN] Done.")
    else:
        print("[CLEAN] tests/generated folder does not exist, skipping.")
    
    # Also clean ts/ts_out folder (TypeScript build output)
    ts_out_dir = Path(__file__).parent / "tests" / "ts" / "ts_out"
    if ts_out_dir.exists():
        print("[CLEAN] Deleting tests/ts/ts_out folder...")
        shutil.rmtree(ts_out_dir)
        print("[CLEAN] Done.")
    else:
        print("[CLEAN] tests/ts/ts_out folder does not exist, skipping.")


try:
    from run_tests import main as run_tests_main, clean_test_files
    
    # Always delete the tests/generated folder first
    clean_generated_folder()
    
    # Clean build folders (not generated, those are already deleted)
    print("[CLEAN] Cleaning build folders...")
    clean_test_files("tests/test_config.json", verbose=False)
    print("[CLEAN] Done.\n")
    
    # Run tests with verbose_failure enabled by default
    # Pass command line args through
    success = run_tests_main()
    sys.exit(0 if success else 1)
except ImportError as e:
    print(f"[ERROR] Failed to import test runner: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test run failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
