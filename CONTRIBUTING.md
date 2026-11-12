# Contributing to Struct Frame

Thanks for helping. Bug reports, schema cases that break the generator, and fixes to any of the
seven runtimes are all welcome.

## Reporting a bug

Open an issue with:

- the struct-frame version (`struct-frame --version`),
- the smallest schema that shows the problem,
- the command line, and
- what you expected and what happened (for wire problems, the bytes as hex).

For security problems (crashes or out-of-bounds access on crafted input), see [SECURITY.md](SECURITY.md) for what to include.

## Setting up

```bash
git clone --recurse-submodules https://github.com/mylonics/struct-frame.git
cd struct-frame
pip install -e ".[test]"   # the generator in editable mode, plus the test dependencies
npm ci                     # TypeScript compiler and linters
```

The full suite also uses gcc/g++ (C++20), the .NET 8+ SDK and a Rust toolchain; languages whose
toolchain is missing are skipped. `git submodule update --init` fetches the vendored ASIO headers
used by the C++ SDK.

If an older struct-frame is installed from PyPI, make sure you are running your checkout:
`python -c "import struct_frame; print(struct_frame.__file__)"` should point into `src/`.

## Running the tests

```bash
python test_all.py                                    # generate, compile and test every available language
python test_all.py --require-langs c,cpp,py,ts,js     # fail instead of skipping a missing toolchain
python -m pytest tests                                # generator-level suites only (fast)
python tests/gen_test_coverage.py --check             # coverage doc is up to date
python src/struct_frame/language_facts.py --check     # editor language facts are up to date
```

## Making changes

- **Generator** (`src/struct_frame/generate.py`, `*_gen.py`): add a test that fails without your
  change, usually in `tests/test_generator_regressions.py` or a focused `tests/test_*.py`.
- **Runtimes** (`src/struct_frame/boilerplate/<lang>/`): every runtime must put the same bytes on
  the wire. Wire changes need the known-answer vectors in `tests/test_known_answer.py` and the
  [Conformance](docs/src/content/docs/reference/conformance.md) page updated.
- **JavaScript runtime**: `boilerplate/js/` is compiled from `boilerplate/ts/`. Edit the TypeScript
  and run `node_modules/.bin/tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json`.
- **Docs** live in `docs/src/content/docs/`. Code samples are checked by `tests/docs/` and
  `tests/test_doc_api_names.py`; programs in `examples/` are built and run by `tests/test_examples.py`.
- **New CLI options** need a row in `tests/coverage_spec.py` (then `python tests/gen_test_coverage.py`)
  and an entry in the [CLI reference](docs/src/content/docs/reference/cli-reference.md).
- **Schema language** (primitive types, options, accepted values, limits): change the tables in
  `src/struct_frame/language_facts.py`, which both the compiler and the VS Code extension read. Then
  run `python src/struct_frame/language_facts.py --write` and add hover text for any new name in
  `editors/vscode/server/src/docs.ts`. The extension's tests fail until every name is documented.
- **VS Code extension** (`editors/vscode/`, Node.js 22+): `cd editors/vscode && npm ci && npm test`.
  The tests include a check that the language server reports no errors on any schema the compiler
  accepts. To debug, open the `editors/vscode` folder in VS Code and press F5.

More detail on the layout, naming conventions and release process is in
[docs/src/content/docs/reference/development.md](docs/src/content/docs/reference/development.md)
and [docs/dev/](docs/dev/).

## Pull requests

Keep a pull request to one change, describe what it fixes and how you tested it, and make sure
`python test_all.py` passes for the languages you touched. The changelog is generated from commit
messages at release time, so write the first line of each commit for users.
