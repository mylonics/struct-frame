#!/usr/bin/env python3
"""Test entry point for extended message tests (Python)."""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

import extended_messages
from struct_frame.generated.extended_test import get_message_info
from test_harness import run

TEST_NAME = "ExtendedMessages"
PROFILES = "bulk, network"

if __name__ == "__main__":
    sys.exit(run(extended_messages, get_message_info, TEST_NAME, PROFILES))

