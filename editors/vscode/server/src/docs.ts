// Human-written documentation for every name in facts/language-facts.json.
//
// The names themselves come from the compiler (see facts.ts); this file only adds the
// prose. __tests__/facts.test.ts fails when the compiler gains a primitive, option or
// discriminator mode that has no entry here, so new language features always get hover
// text. Numbers that the compiler defines are interpolated from LIMITS, never retyped.
import { INT_RANGES, LIMITS, OptionScope, ENUM_VALUE_RANGE, OPTION_NAMES, OPTION_ALIASES } from './facts';

const range = (r: { min: number; max: number }): string => `${r.min}–${r.max}`;
const intRange = (type: string): string => `${INT_RANGES[type].min} to ${INT_RANGES[type].max}`;
const SIZE = range(LIMITS.sizeOption);
const PREFIX_MAX = LIMITS.oneBytePrefixMax;

export const PRIMITIVE_TYPE_DOCS: Readonly<Record<string, string>> = {
  int8: `Signed 8-bit integer (${intRange('int8')})`,
  int16: `Signed 16-bit integer (${intRange('int16')})`,
  int32: `Signed 32-bit integer (${intRange('int32')})`,
  int64: `Signed 64-bit integer (${intRange('int64')})`,
  uint8: `Unsigned 8-bit integer (${intRange('uint8')})`,
  uint16: `Unsigned 16-bit integer (${intRange('uint16')})`,
  uint32: `Unsigned 32-bit integer (${intRange('uint32')})`,
  uint64: `Unsigned 64-bit integer (${intRange('uint64')})`,
  float: 'Single-precision floating point (32-bit IEEE 754)',
  double: 'Double-precision floating point (64-bit IEEE 754)',
  bool: 'Boolean value (1 byte: true or false)',
  string: 'UTF-8 string. Needs `[size=N]` (fixed, null-padded) or `[max_size=N]` (length prefix + up to N bytes).',
  bytes: 'Raw byte array. Same wire layout as `string`: needs `[size=N]` or `[max_size=N]`.'
};

const DISCRIMINATOR_TEXT = 'Controls how the active oneof variant is identified on the wire: `auto` | `msgid` | `field_order` | `none`.';
const EXTENSIONS_TEXT = `First extension field number (≥ ${LIMITS.extensionsStartMin}); it must equal an existing field number. ` +
  'Fields numbered this or higher are **extension fields**: newer senders include them, older receivers zero-fill them. ' +
  'Magic bytes and base sizes only use the fields before it, so adding extension fields never changes the magic bytes.';

/** Option documentation (markdown), keyed by scope and canonical option name. */
export const OPTION_DOCS: Readonly<Record<OptionScope, Readonly<Record<string, string>>>> = {
  file: {
    pkgid: `Package identifier (${range(LIMITS.pkgid)}). Messages are addressed as \`(pkgid << 8) | msgid\`, so with a pkgid every msgid must be ${range(LIMITS.msgidWithPkgid)}. Required on each package when compiling several packages together.`
  },
  message: {
    msgid: `Message identifier used for routing and deserialization: ${range(LIMITS.msgid)} without \`option pkgid\`, ${range(LIMITS.msgidWithPkgid)} with one. Must be unique within the package.`,
    variable: 'Enables variable-length encoding: bounded `[max_size=N]` fields and trimmed oneofs transmit only the bytes in use instead of the full allocated size.',
    discriminator: `Default discriminator mode for this message's oneofs. ${DISCRIMINATOR_TEXT}`,
    is_envelope: 'Marks this message as an envelope/container: it must have exactly one `oneof` whose variants are all message types. Also accepted as `envelope`.',
    extensions_start: `${EXTENSIONS_TEXT} Cannot be combined with oneofs (use the oneof-level option instead).`,
    magic_bytes: `Overrides the calculated two-byte CRC seed, e.g. \`"0xA3, 0x7F"\`: exactly ${LIMITS.magicBytesCount} comma-separated values, each ${range(LIMITS.magicByte)} (hex or decimal). Use it when a schema change would alter the calculated magic bytes but the wire layout is genuinely unchanged.`
  },
  oneof: {
    discriminator: DISCRIMINATOR_TEXT,
    variable: 'Adds a `uint16` length prefix before the variant bytes so receivers can skip unknown variants (forward compatible). The parent message must also be `option variable = true`.',
    max_size: 'Minimum in-memory union buffer size for a non-variable (trimmed) oneof. Must be at least the largest variant. Not valid with `option variable = true`.',
    min_size: 'Guarantees a minimum wire payload size for a variable oneof, or for a trimmed oneof that is the only variable-length field. Must not exceed the buffer size.',
    extensions_start: EXTENSIONS_TEXT
  },
  enum: {
    extensions_start: 'Entries with a value at or above this number are extensions: they do not change the generated hash, so adding them keeps older code compatible.'
  },
  field: {
    size: `Fixed-size allocation (${SIZE}). Strings/bytes are padded to exactly N bytes; arrays always hold exactly N elements. No count/length prefix.`,
    max_size: `Bounded variable size (${SIZE}). Strings/bytes get a length prefix + up to N bytes; arrays get a count prefix + up to N elements. The prefix is \`uint8\` (1 byte) when N ≤ ${PREFIX_MAX}, \`uint16\` (2 bytes) above.`,
    element_size: `Only for \`repeated string\` / \`repeated bytes\` arrays (${SIZE}): bytes reserved for each element. Combine with \`size\` or \`max_size\`.`,
    flatten: 'Only on message-typed fields: inlines the nested message\'s fields into the parent. Field names must not collide. Affects Python and GraphQL output only.',
    default: 'Initialization and decode-fallback value for integer, bool, float, double, enum and sized string/bytes fields. Not supported on repeated, message-typed or oneof fields; never changes wire layout, size or magic bytes.'
  }
};

const SCOPE_LABEL: Record<OptionScope, string> = {
  file: 'file option',
  message: 'message option',
  oneof: 'oneof option',
  enum: 'enum option',
  field: 'field option'
};

/** Documentation for an option name (aliases resolve to their canonical entry). */
export function optionDoc(scope: OptionScope, name: string): string | undefined {
  return OPTION_DOCS[scope][OPTION_ALIASES[scope][name] ?? name];
}

/** Hover markdown for an option, with a heading. */
export function optionHover(scope: OptionScope, name: string): string | undefined {
  const doc = optionDoc(scope, name);
  if (doc === undefined) return undefined;
  const canonical = OPTION_ALIASES[scope][name];
  const alias = canonical ? ` — alias of \`${canonical}\`` : '';
  return `**${name}** *(${SCOPE_LABEL[scope]})*${alias}\n\n${doc}`;
}

export const DISCRIMINATOR_DOCS: Readonly<Record<string, string>> = {
  auto: 'Default. Uses `msgid` (uint16, 2 bytes) if every variant is a message with a msgid; otherwise `field_order` (uint8, 1 byte).',
  msgid: 'uint16 discriminator holding the active variant\'s message ID. Every variant must be a message with a distinct `msgid`.',
  field_order: 'uint8 discriminator holding the 1-based declaration order of the active variant. Generates a typed companion enum.',
  none: 'No discriminator stored (0 bytes). The application must track the active variant out-of-band. Also written `false`, `off` or `disabled`.'
};

const optionList = (scope: OptionScope): string => OPTION_NAMES[scope].map(name => `\`${name}\``).join(', ');

export const KEYWORD_DOCS: Readonly<Record<string, string>> = {
  package: '**package** *(keyword)*\n\nDeclares the namespace for all messages/enums in this file. Used as a prefix or namespace in generated code.\n\n```sf\npackage sensor_data;\n```',
  import: '**import** *(keyword)*\n\nIncludes types from another `.sf` file. Imported message and enum types can be used as field types.\n\n```sf\nimport "types.sf";\n```',
  message: '**message** *(keyword)*\n\nDefines a packed struct (fixed-size unless `option variable = true`). Top-level routable messages need `option msgid`. Field numbers run 1..N in declaration order.\n\n```sf\nmessage Heartbeat {\n  option msgid = 1;\n  uint64 timestamp = 1;\n}\n```',
  enum: `**enum** *(keyword)*\n\nDefines an enumeration stored as \`uint8\` (1 byte): values must be unique and ${range(ENUM_VALUE_RANGE)}. Can be declared at file level or nested inside a message.\n\n\`\`\`sf\nenum State { IDLE = 0; RUNNING = 1; }\n\`\`\``,
  repeated: `**repeated** *(keyword)*\n\nDeclares an array field. Needs \`[size=N]\` (fixed count) or \`[max_size=N]\` (variable count, ${SIZE}); \`repeated string\` / \`repeated bytes\` also need \`[element_size=M]\`.\n\nThe count prefix is \`uint8\` (1 byte) when \`max_size\` ≤ ${PREFIX_MAX}, \`uint16\` (2 bytes) above.`,
  oneof: `**oneof** *(keyword)*\n\nDeclares a union where only one variant is active at a time. Oneof options: ${optionList('oneof')}.`,
  option: `**option** *(keyword)*\n\nSets a file, message, oneof or enum option.\n\n- File: ${optionList('file')}\n- Message: ${optionList('message')}\n- Oneof: ${optionList('oneof')}\n- Enum: ${optionList('enum')}\n\nField options (${optionList('field')}) are written inside \`[...]\` after the field number.`
};
