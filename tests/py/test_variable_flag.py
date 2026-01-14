#!/usr/bin/env python3
"""
Test entry point for variable flag truncation tests (Python).

This test validates that messages with option variable = true properly
truncate unused array space, while non-variable messages do not.

Usage:
    test_variable_flag encode <frame_format> <output_file>
    test_variable_flag decode <frame_format> <input_file>

Frame formats: profile_bulk (only profile that supports extended features)
"""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))

from test_codec import run_test_main
from variable_flag_test_data import Config

if __name__ == "__main__":
    sys.exit(run_test_main(Config))
