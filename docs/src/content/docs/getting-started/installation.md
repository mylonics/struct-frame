---
title: Installation
description: Install Struct Frame via pip and set up language-specific requirements.
---

Install via pip:

```bash
pip install struct-frame
```

The package name is `struct-frame`, but the Python module uses `struct_frame`:

```bash
python -m struct_frame --help
```

## VS Code Extension

The [struct-frame-ls](https://github.com/mylonics/struct-frame-ls) extension adds language server support for `.sf` files in VS Code:

- **Syntax Highlighting** — Messages, enums, primitive types, keywords, comments, field options, and string literals
- **Go-to-Definition** — Jump to message or enum definitions, including across imported files
- **Autocomplete** — Context-aware suggestions for keywords, field types, field options (`size=`, `max_size=`, `element_size=`, `flatten=`), and message options (`msgid`, `pkgid`, `variable`)
- **Hover Documentation** — Hover over a type to see its definition or a description of the primitive type
- **Document Outline** — All messages and enums listed with their fields and enum values

Install from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=mylonics.struct-frame-ls) or [Open VSX Registry](https://open-vsx.org/extension/mylonics/struct-frame-ls), or search for **struct-frame-ls** in the Extensions panel.

## Language-Specific Requirements

Depending on which languages you plan to use:

- **C**: GCC or compatible C compiler
- **C++**: G++ with C++20 support or later
- **TypeScript/JavaScript**: Node.js and npm
- **Python**: Python 3.8 or later (already required for code generation)
- **C#**: .NET SDK
- **GraphQL**: Any GraphQL server implementation
