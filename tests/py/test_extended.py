#!/usr/bin/env python3
"""Test entry point for extended message tests (Python)."""

import sys
import os

# Add include directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

from extended_messages import MESSAGE_COUNT, get_message, check_message
from struct_frame.generated.extended_test import get_message_info
from test_harness import run

TEST_NAME = "ExtendedMessages"
PROFILES = "bulk, network"

if __name__ == "__main__":
    sys.exit(run(MESSAGE_COUNT, get_message, check_message, get_message_info, TEST_NAME, PROFILES))
