#!/usr/bin/env python3
"""
Test entry point for standard message tests (Python).

Usage:
    test_runner encode <frame_format> <output_file>
    test_runner decode <frame_format> <input_file>

Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
"""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))

from test_codec import run_test_main, encode_standard_messages, decode_standard_messages
from standard_test_data import std_test_config

if __name__ == "__main__":
    sys.exit(run_test_main(std_test_config, encode_standard_messages, decode_standard_messages))
