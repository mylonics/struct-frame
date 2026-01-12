#!/usr/bin/env python3
"""
Test entry point for extended message ID and payload tests (Python).

Usage:
    test_runner_extended encode <frame_format> <output_file>
    test_runner_extended decode <frame_format> <input_file>

Frame formats (extended profiles only): profile_bulk, profile_network
"""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))

from test_codec import run_test_main
from extended_test_data import Config

if __name__ == "__main__":
    sys.exit(run_test_main(Config))

