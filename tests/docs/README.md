# Documentation sample checks

Extract samples with:

```bash
python tests/docs/extract_samples.py
python tests/docs/run_samples.py --quick
```

Fenced code blocks with info strings `c`, `cpp`, `python`, `ts`, `js`, `rust`, or `csharp` are extracted. Add `skip` or `no-compile` to the info string for illustrative snippets that should not be compiled. `expect-error` is reserved for future negative examples.

## Modes

- `--quick`: only Python (byte-compiled) and JavaScript (syntax-checked) samples run; C, C++, TypeScript, Rust and C# are skipped. For fast local runs.
- Default (full, used by CI): generates code from the schemas in `tests/docs/schemas/` for every language, then
  compiles the C, C++, TypeScript, Rust and C# samples against it (statements outside a function are wrapped in
  `main`; C# builds as top-level statements). About 30 samples compile today.

A sample that needs the reader's own code (their variables, handlers or a differently named package) carries
`no-compile` in its code fence and is skipped, as are blocks the runner recognises as fragments (`...`,
placeholders, indented continuation). When a snippet refers to the `example` or `sensor_system` packages, keep it
consistent with the matching schema in `tests/docs/schemas/` so it keeps compiling.

`tests/test_doc_api_names.py` backs this up for the skipped snippets: every type, function and method name used in
a code block must exist in that language's runtime or generated code.
