"""IR and generated-output oracle for schema-frontend changes.

``ir_dump(schema)`` parses and validates a schema with the real generator and returns a
plain-data dump of the whole IR: every package, enum, message, field and oneof with all of
their attributes (comments included).  Positions (line/column) and absolute paths are left
out, so two front ends that build the same model from differently formatted sources give
equal dumps.

``output_hashes(schema)`` runs a full generation for every target language and returns the
sha256 of every *generated* file (runtime files copied from ``boilerplate/`` are skipped, so
runtime changes don't disturb the oracle).

Golden files in this directory hold both for every schema in the repository::

    python tests/ir_golden/ir_oracle.py --update     # rewrite the goldens
    python tests/ir_golden/ir_oracle.py              # compare (same as the pytest test)
"""

import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(REPO, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from struct_frame import generate as gen  # noqa: E402

BOILERPLATE = os.path.join(SRC, "struct_frame", "boilerplate")

# Schemas covered by the goldens (paths relative to the repository root). Files that are
# deliberately invalid (editor validation fixtures) are not listed.
SCHEMAS = [
    "examples/array_test.sf",
    "examples/basic/hello.sf",
    "examples/generic_robot.sf",
    "examples/multi_package/events.sf",
    "examples/multi_package/system.sf",
    "examples/package_ids/fleet.sf",
    "examples/package_ids/actuator_control.sf",
    "examples/package_ids/sensor_data.sf",
    "editors/vscode/examples/example.sf",
    "tests/benchmarks/schema/bench.sf",
    "tests/docs/schemas/example.sf",
    "tests/docs/schemas/sensor_system.sf",
    "tests/proto/constants.sf",
    "tests/proto/default_edges.sf",
    "tests/proto/default_values.sf",
    "tests/proto/envelope_messages.sf",
    "tests/proto/extended_messages.sf",
    "tests/proto/pkg_test_messages.sf",
    "tests/proto/test_messages.sf",
    "tests/proto/trimmed_union_codegen.sf",
    "tests/proto/trimmed_union_v2.sf",
    "tests/proto/trimmed_union_v3.sf",
    "tests/proto/trimmed_union_v4.sf",
    "tests/proto/wire_evolution_messages.sf",
    "tests/proto/wire_evolution_v1.sf",
    "tests/proto/wire_evolution_v2.sf",
]

# Attributes that describe *where* something was written, not what it is.
_POSITION_KEYS = frozenset({"line", "col", "error_line", "end_line", "_sf_line"})
# Internal bookkeeping with no meaning for generated code.
_SKIP_KEYS = frozenset({"validated", "_pending_extensions"})


def _plain(value, root):
    """Convert an IR attribute value to JSON-able plain data."""
    if isinstance(value, (bytes, bytearray)):
        return {"hex": bytes(value).hex()}
    if isinstance(value, float):
        if value != value:
            return {"float": "nan"}
        if value in (float("inf"), float("-inf")):
            return {"float": repr(value)}
        return value
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(v, root) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v, root) for k, v in value.items()}
    if isinstance(value, (gen.Enum, gen.Message)):
        # A reference (Field.type_ref): identify it, don't recurse.
        kind = "enum" if isinstance(value, gen.Enum) else "message"
        return {"ref": kind, "package": value.package, "name": value.name,
                "message": getattr(value, "message", None)}
    return {"repr": type(value).__name__}


def _object(obj, root):
    out = {"_class": type(obj).__name__}
    for key in sorted(vars(obj)):
        if key in _POSITION_KEYS or key in _SKIP_KEYS:
            continue
        val = getattr(obj, key)
        if key == "source_file":
            out[key] = os.path.basename(val) if val else val
        elif key == "fields" or key == "oneofs" or key == "enums":
            out[key] = {name: _object(child, root) for name, child in val.items()}
        else:
            out[key] = _plain(val, root)
    return out


def _package(pkg, root):
    return {
        "name": pkg.name,
        "package_id": pkg.package_id,
        "package_id_explicit": pkg.package_id_explicit,
        "file_docs": {os.path.basename(p): list(c) for p, c in sorted(pkg.file_docs.items())},
        "enums": {name: _object(e, root) for name, e in pkg.enums.items()},
        "messages": {name: _object(m, root) for name, m in pkg.messages.items()},
        "consts": {name: _object(c, root) for name, c in getattr(pkg, "consts", {}).items()},
        "services": {name: _object(s, root) for name, s in getattr(pkg, "services", {}).items()},
    }


@contextlib.contextmanager
def _quiet():
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


def ir_dump(schema_path):
    """Parse + validate *schema_path* and return a plain-data dump of the IR."""
    gen.reset_parse_state()
    with _quiet() as (out, err):
        ok = gen.parseFile(schema_path) and gen.validate_packages()
        if ok:
            gen.normalize_output_order()
    if not ok:
        raise RuntimeError(f"{schema_path} failed to parse/validate:\n{out.getvalue()}{err.getvalue()}")
    root = os.path.dirname(os.path.abspath(schema_path))
    dump = {
        "packages": [_package(pkg, root) for pkg in gen.packages.values()],
        "package_imports": {k: sorted(v) for k, v in sorted(gen.package_imports.items())},
        "schema_hash": gen.compute_schema_hash(gen.packages),
        "documentation_hash": gen.compute_documentation_hash(gen.packages),
    }
    gen.reset_parse_state()
    return dump


def _boilerplate_relpaths():
    # Names of the copied runtime files. The C# runtime (csharp/Framework/) is excluded by
    # path below; its built-in SfSystem schema files share names (Constants.cs,
    # MessageDefinitions.cs) with every application package's generated C# files.
    rel = set()
    framework = os.path.join(BOILERPLATE, "csharp", "Framework")
    for dirpath, _dirs, files in os.walk(BOILERPLATE):
        if os.path.commonpath([dirpath, framework]) == framework:
            continue
        for name in files:
            rel.add(name)
    return rel


_RUNTIME_NAMES = None


def output_hashes(schema_path, extra_args=()):
    """sha256 of every generated (non-runtime) file for all languages."""
    global _RUNTIME_NAMES
    if _RUNTIME_NAMES is None:
        _RUNTIME_NAMES = _boilerplate_relpaths()
    with tempfile.TemporaryDirectory(prefix="sf_oracle_") as tmp:
        argv = [schema_path, "--lang", "all", "--out", tmp, "--catalog_path", tmp,
                "--equality", "--generate_tests", "--sdk", "--force", "-q", *extra_args]
        with _quiet() as (out, err):
            status = gen.main(argv)
        if status:
            raise RuntimeError(f"generation failed for {schema_path}:\n{out.getvalue()}{err.getvalue()}")
        hashes = {}
        for dirpath, _dirs, files in os.walk(tmp):
            for name in files:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, tmp).replace(os.sep, "/")
                if name in _RUNTIME_NAMES or name.endswith(".structframe.hash") or name == ".structframe-manifest.json":
                    continue
                if "/struct_frame_sdk/" in rel or "/struct-frame-sdk/" in rel or "/Framework/" in rel:
                    continue
                with open(full, "rb") as f:
                    data = f.read().replace(b"\r\n", b"\n")
                hashes[rel] = hashlib.sha256(data).hexdigest()
    gen.reset_parse_state()
    return dict(sorted(hashes.items()))


def golden_path(schema):
    slug = schema.replace("/", "__").rsplit(".", 1)[0]
    return os.path.join(HERE, slug + ".json")


def compute(schema, path=None):
    """Oracle data for *schema* (repo-relative); *path* overrides where it is read from."""
    path = path or os.path.join(REPO, schema)
    return {
        "schema": schema,
        "ir": ir_dump(path),
        "outputs": output_hashes(path),
        "outputs_no_packed": output_hashes(path, ("--no_packed",)),
    }


def load_golden(schema):
    with open(golden_path(schema), encoding="utf-8") as f:
        return json.load(f)


def write_golden(schema, data):
    with open(golden_path(schema), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--update", action="store_true", help="rewrite the golden files")
    ap.add_argument("schemas", nargs="*", help="limit to these schemas (repo-relative)")
    args = ap.parse_args(argv)
    failed = 0
    for schema in args.schemas or SCHEMAS:
        data = json.loads(json.dumps(compute(schema)))
        if args.update:
            write_golden(schema, data)
            print(f"wrote {os.path.relpath(golden_path(schema), REPO)}")
            continue
        if not os.path.exists(golden_path(schema)):
            print(f"MISSING {schema}")
            failed += 1
        elif load_golden(schema) != data:
            print(f"DIFF    {schema}")
            failed += 1
        else:
            print(f"ok      {schema}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
