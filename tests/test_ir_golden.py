"""The parsed IR and the generated output of every repository schema match the goldens.

The goldens in ``tests/ir_golden/`` pin the complete model the front end builds (all
attributes of every package, enum, message, field and oneof, comments included) and the
sha256 of every generated file. A front-end change that alters any of them fails here.

Regenerate after an *intentional* change with::

    python tests/ir_golden/ir_oracle.py --update
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ir_golden"))

import ir_oracle  # noqa: E402


@pytest.mark.parametrize("schema", ir_oracle.SCHEMAS)
def test_ir_and_outputs_match_golden(schema):
    golden = ir_oracle.load_golden(schema)
    actual = ir_oracle.compute(schema)
    import json
    actual = json.loads(json.dumps(actual))
    assert actual["ir"] == golden["ir"], f"IR of {schema} changed"
    assert actual["outputs"] == golden["outputs"], f"generated output of {schema} changed"
    assert actual["outputs_no_packed"] == golden["outputs_no_packed"], \
        f"--no_packed output of {schema} changed"
