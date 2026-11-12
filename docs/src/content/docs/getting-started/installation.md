---
title: Installation
description: Install Struct Frame via pip and set up language-specific requirements.
---

Install via pip:

```bash
pip install struct-frame
```

This installs the `struct-frame` command. The same program runs as `python -m struct_frame` (the Python module is `struct_frame`, with an underscore):

```bash
struct-frame --version
struct-frame --help
```

## VS Code Extension

The **Struct Frame Language Support** extension (`mylonics.struct-frame-ls`) adds language server support for `.sf` files in VS Code:

- **Syntax Highlighting** — Messages, enums, primitive types, keywords, comments, field options, and string literals
- **Diagnostics** — The same schema rules the compiler enforces (option names and values, size limits, msgid/pkgid ranges, field numbering, oneof and default-value rules), as you type
- **Go-to-Definition** — Jump to message or enum definitions, including across imported files and into generated code
- **Autocomplete** — Context-aware suggestions for keywords, field types, field options, and file, message, oneof and enum options
- **Hover Documentation** — Types, options and discriminator modes; message sizes and magic bytes when a `sf_compile.json` catalog is available
- **Document Outline** — All messages and enums listed with their fields and enum values

Install from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=mylonics.struct-frame-ls) or [Open VSX Registry](https://open-vsx.org/extension/mylonics/struct-frame-ls), or search for **Struct Frame** in the Extensions panel.

The extension lives in this repository ([`editors/vscode`](https://github.com/mylonics/struct-frame/tree/main/editors/vscode)) and reads its language rules from the compiler, so it always matches the struct-frame release with the same version number. A new extension version is only published when the extension itself changes, so its version can trail the latest `pip` release.

## Language-Specific Requirements

Depending on which languages you plan to use:

- **C**: GCC or compatible C compiler
- **C++**: G++ with C++20 support or later
- **TypeScript/JavaScript**: Node.js and npm
- **Python**: Python 3.9 or later (already required for code generation) and `proto-schema-parser` 2.0.0 or later (older versions silently mis-attribute same-line trailing comments)
- **C#**: .NET SDK
- **GraphQL**: Any GraphQL server implementation
