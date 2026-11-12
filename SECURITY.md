# Security Policy

The struct-frame runtimes parse bytes from serial ports and networks, so a crash, out-of-bounds
access or hang on crafted input is a security problem, as is generated code that can be made to
overflow a buffer.

## Reporting a vulnerability

Open a [GitHub issue](https://github.com/mylonics/struct-frame/issues/new) and include:

- the struct-frame version (`struct-frame --version`) and the language runtime,
- the schema, and
- the input bytes (as hex) that trigger the problem, or a short program that reproduces it.

## Supported versions

Fixes are made on the latest release. Regenerate your code with the fixed version to pick them up:
the runtimes are copied into your output directory at generation time.
