#!/usr/bin/env python3
"""Test entry point for variable flag tests (Python)."""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

import variable_flag_messages
from struct_frame.generated.serialization_test import get_message_info
from test_harness import run

TEST_NAME = "VariableFlagMessages"
PROFILES = "bulk"

if __name__ == "__main__":
    sys.exit(run(variable_flag_messages, get_message_info, TEST_NAME, PROFILES))
