#!/usr/bin/env python3
"""
Simple entry point for running the struct-frame test suite.

This script provides a single command to run all tests in the struct-frame project.
"""

import sys
from pathlib import Path

# Add the tests directory to the Python path
tests_dir = Path(__file__).parent / "tests"
sys.path.insert(0, str(tests_dir))


try:
    from run_tests import main as run_tests_main
    
    # Run tests - the runner handles cleaning, generation, compilation, and testing
    # main() returns 0 for success, 1 for failure
    exit_code = run_tests_main()
    sys.exit(exit_code)
except ImportError as e:
    print(f"[ERROR] Failed to import test runner: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test run failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

