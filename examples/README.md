# Examples

Every example here is built or validated by `tests/test_examples.py` and
`tests/test_generator_regressions.py`, so they stay in step with the generator.
Run the commands from the repository root.

| Path | What it shows |
|------|---------------|
| `basic/hello.sf` + `hello.c`, `hello.py`, `hello.ts` | Encode two messages into a Standard-profile byte stream and decode them again, in C, Python and TypeScript |
| `array_test.sf` | Fixed and variable strings and arrays, nested messages and enums |
| `generic_robot.sf` | A larger schema with nested messages and `flatten` |
| `multi_package/` | Several packages in several files with `import`; compile `system.sf` |
| `package_ids/` | Package IDs, which let two packages reuse the same local message IDs; compile `fleet.sf` |

## Run the basic example

```bash
# Python
struct-frame examples/basic/hello.sf --build-py --py-path out/py
PYTHONPATH=out/py python examples/basic/hello.py

# C
struct-frame examples/basic/hello.sf --build-c --c-path out/c
gcc -std=c11 -Iout/c examples/basic/hello.c -o hello && ./hello

# TypeScript
struct-frame examples/basic/hello.sf --build-ts --ts-path out/ts
cp examples/basic/hello.ts out/ts/ && cd out/ts && npx ts-node hello.ts
```

Each prints the encoded size and the decoded `pose` and `heartbeat` values.

## Multi-file schemas

A file declares exactly one `package`. To use several packages, write an entry
file that `import`s the others and compile that:

```bash
struct-frame examples/multi_package/system.sf --build-py --py-path out/py
struct-frame examples/package_ids/fleet.sf --build-c --c-path out/c
```

When more than one package is compiled, the 16-bit message IDs
`(pkgid << 8) | msgid` must be unique across all of them. Messages from a package
with a package ID need a profile that carries the package-ID byte on the wire
(Bulk or Network).
