# Documentation sample checks

Extract samples with:

```bash
python tests/docs/extract_samples.py
python tests/docs/run_samples.py --quick
```

Fenced code blocks with info strings `c`, `cpp`, `python`, `ts`, `js`, `rust`, or `csharp` are extracted. Add `skip` or `no-compile` to the info string for illustrative snippets that should not be compiled. `expect-error` is reserved for future negative examples.
