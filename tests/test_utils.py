#!/usr/bin/env python3
"""
Shared test utilities for struct-frame test suite.
"""

import sys


def _check(condition: bool, msg: str) -> None:
    """Assert *condition* is truthy; print a FAIL message and exit if not."""
    if not condition:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)
