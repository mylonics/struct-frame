# Documentation sample checks

Extract samples with:

```bash
python tests/docs/extract_samples.py
python tests/docs/run_samples.py --quick
```

Fenced code blocks with info strings `c`, `cpp`, `python`, `ts`, `js`, `rust`, or `csharp` are extracted. Add `skip` or `no-compile` to the info string for illustrative snippets that should not be compiled. `expect-error` is reserved for future negative examples.

## Modes

- `--quick` (CI): only Python samples are byte-compiled; C, C++, TypeScript, Rust and C# are skipped, and JavaScript is syntax-checked.
- Default (full): also compiles the C/C++/TS/Rust/C# samples one by one. Most samples are
  fragments that rely on generated headers or an SDK include path, so a full run reports
  those as failures even though the prose is fine (last run: 18 such failures, 0 in
  Python/JS). Treat full mode as a diagnostic, not a gate, until the runner compiles each
  sample against freshly generated code. Mark deliberately partial blocks with `skip`.
