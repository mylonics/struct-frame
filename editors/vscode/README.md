# Struct Frame Language Support

VS Code language support for [struct-frame](https://github.com/mylonics/struct-frame) schema files (`.sf`).

The extension is developed in the struct-frame repository
([`editors/vscode`](https://github.com/mylonics/struct-frame/tree/main/editors/vscode)) and reads its
language rules (primitive types, option names, accepted values and limits) from the compiler itself.
Each extension version matches the struct-frame release with the same version number.

## Features

- **Syntax Highlighting**: messages, enums, primitive types, keywords, comments, field options and string literals
- **Diagnostics**: the schema rules the compiler enforces, as you type. These cover option names and values, `size`/`max_size`/`element_size` limits, msgid and pkgid ranges, duplicate message ids across imports, field numbering, oneof discriminators and sizes, enum value ranges, magic bytes, extension anchors and default values. Unknown option names are warnings, for forward compatibility.
- **Go-to-Definition**: jump to a message or enum definition, including across imported files and into generated code
- **Autocomplete**: context-aware suggestions:
  - top-level keywords (`message`, `enum`, `package`, `import`, `option`, `repeated`, `oneof`)
  - field types: every primitive type plus the messages and enums from the current file and its imports
  - inside `[...]`: the field options that apply to the field's type
  - after `option`: the options for the current scope (file, message, oneof or enum)
- **Hover Documentation**: types, options, discriminator modes and keywords. With a `sf_compile.json` catalog it also shows message sizes, magic bytes and the generated files.
- **Document Symbols / Outline**: all messages and enums with their fields and enum values

## struct-frame Syntax

struct-frame uses a protobuf-like syntax:

```sf
package sensor_data;

option pkgid = 1;

enum SensorStatus {
  OFFLINE = 0;
  ONLINE  = 1;
  ERROR   = 2;
}

message SensorReading {
  option msgid = 1;
  option variable = true;
  option magic_bytes = "0xA3, 0x7F";

  SensorStatus status    = 1 [default=ONLINE];
  float        value     = 2 [default=0.0];
  string       name      = 3 [size=16, default="unknown"];
  repeated uint8 data    = 4 [max_size=200];
  uint32       timestamp = 5;
}

message DeviceStatus {
  option msgid = 3;
  uint8 device_id = 1;
}

message Container {
  option msgid = 2;
  option variable = true;
  SensorReading reading = 1;

  oneof payload {
    option variable = true;
    SensorReading sensor = 1;
    DeviceStatus  device = 2;
  }
}
```

**Primitive types**: `int8`, `int16`, `int32`, `int64`, `uint8`, `uint16`, `uint32`, `uint64`, `float`, `double`, `bool`, `string`, `bytes`

**Field options** (in `[...]`, also written `(sf.size)` or `(struct_frame.size)`): `size`, `max_size`, `element_size`, `flatten`, `default`

**File option**: `pkgid`

**Message options**: `msgid`, `variable`, `discriminator`, `is_envelope` (alias `envelope`), `magic_bytes`, `extensions_start`

**Oneof options**: `discriminator` (`auto`, `msgid`, `field_order`, `none`), `variable`, `max_size`, `min_size`, `extensions_start`

**Enum option**: `extensions_start`

### Message IDs

Without `option pkgid`, a message id is `msgid` (0–65535). With `option pkgid = P`, `msgid` must be
0–255 and the id on the wire is `(P << 8) | msgid`. A file without its own pkgid inherits the pkgid of
the file that imports it.

### Default values

`default` is an initialization and decode-fallback value. It does not change wire layout, field size
or magic bytes. It is supported on integer types, `bool`, `float`, `double`, enum members, and fixed or
bounded strings and bytes:

```sf
enum State { IDLE = 0; READY = 1; }

message Defaults {
  State state = 1 [default=READY];
  bool enabled = 2 [default=true];
  string label = 3 [size=16, default="ready"];
}
```

Defaults are not supported on repeated fields, message-typed fields or fields inside a `oneof`.

## Settings

- `structFrameLs.compileConfigPath`: path to the `sf_compile.json` catalog the compiler writes
  (see `--catalog-path`). It can be relative to the workspace root or absolute. Default: `sf_compile.json`.

## Development

The extension's source is in the struct-frame repository. You need Node.js 22 or later.

```bash
cd editors/vscode
npm ci
npm test
```

To debug, open the `editors/vscode` folder in VS Code and press **F5** to start the Extension
Development Host.

The language tables come from `src/struct_frame/language_facts.py` through the generated
`server/src/facts/language-facts.json`. Never edit the JSON by hand. After changing the Python
tables, run `python src/struct_frame/language_facts.py --write` from the repository root, then add hover
text for any new name in `server/src/docs.ts`. The tests check that every name is documented and that
the server reports no errors on any schema in the repository that the compiler accepts.

## License

MIT
