#!/usr/bin/env python3
"""Every generated GraphQL document must be a valid schema according to graphql-core.

The structural checks in test_generator_regressions.py only look for dangling type references.
This test builds the schemas with the reference implementation, so invalid SDL (duplicate
fields, bad directive use, unknown scalars, broken descriptions) also fails.

For each test schema it generates GraphQL, then:

* builds the stitched ``schema.graphql`` on its own, and
* builds every per-package file together with the type and enum definitions of the other
  packages generated in the same run (per-package files reference imported packages' types).

graphql-core is a test-only dependency (``pip install graphql-core``). Without it the test skips,
unless ``gql`` is listed in SF_REQUIRE_LANGS.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, run_generator

try:
    import graphql
except ModuleNotFoundError:  # pragma: no cover - depends on the environment
    if "gql" in os.environ.get("SF_REQUIRE_LANGS", "").split(","):
        raise
    pytest.skip("graphql-core not installed (pip install graphql-core)", allow_module_level=True)

PROTOS = sorted((REPO_ROOT / "tests" / "proto").glob("*.sf"))


def _generate(proto: Path, out: Path) -> list:
    result = run_generator(proto, "--build_gql", "--gql_path", str(out), "--force")
    assert result.returncode == 0, f"{proto.name}: generation failed\n{result.stdout}\n{result.stderr}"
    files = sorted(out.glob("*.graphql"))
    assert files, f"{proto.name}: no GraphQL output"
    return files


def _shared_definitions(files, exclude: Path) -> list:
    """Object and enum definitions from the other per-package files (not their Query type)."""
    defs = []
    for f in files:
        if f == exclude or f.name == "schema.graphql":
            continue
        for d in graphql.parse(f.read_text(encoding="utf-8")).definitions:
            if isinstance(d, graphql.language.EnumTypeDefinitionNode):
                defs.append(d)
            elif isinstance(d, graphql.language.ObjectTypeDefinitionNode) and d.name.value != "Query":
                defs.append(d)
    return defs


@pytest.mark.parametrize("proto", PROTOS, ids=[p.stem for p in PROTOS])
def test_generated_graphql_builds(proto, tmp_path):
    files = _generate(proto, tmp_path / "gql")

    stitched = tmp_path / "gql" / "schema.graphql"
    assert stitched.exists(), "schema.graphql was not written"
    graphql.build_schema(stitched.read_text(encoding="utf-8"))

    for f in files:
        if f.name == "schema.graphql":
            continue
        doc = graphql.parse(f.read_text(encoding="utf-8"))
        own = {d.name.value for d in doc.definitions if hasattr(d, "name") and d.name is not None}
        extra = [d for d in _shared_definitions(files, f) if d.name.value not in own]
        combined = graphql.language.DocumentNode(definitions=tuple(doc.definitions) + tuple(extra))
        try:
            graphql.build_ast_schema(combined)
        except graphql.GraphQLError as e:  # pragma: no cover - failure path
            pytest.fail(f"{proto.name} -> {f.name}: {e}")
