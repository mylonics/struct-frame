// Typed view of the struct-frame language facts.
//
// facts/language-facts.json is generated from src/struct_frame/language_facts.py in the
// struct-frame repo (`python src/struct_frame/language_facts.py --write`) -- the same
// tables the compiler uses -- so primitive types, option names, accepted values and
// limits here always match the compiler. Never hand-edit the JSON; human-readable
// documentation for each name lives in docs.ts.
import * as rawFacts from './facts/language-facts.json';

export type OptionScope = 'file' | 'message' | 'oneof' | 'enum' | 'field';

interface Bounds { min: string; max: string }

interface LanguageFacts {
  schema_version: number;
  primitives: Array<{ name: string; kind: string; size: number | null }>;
  integer_ranges: Record<string, Bounds>;
  float_max: number;
  enum: { size: number; value_range: Bounds };
  option_qualifiers: string[];
  options: Record<OptionScope, Record<string, string>>;
  option_aliases: Partial<Record<OptionScope, Record<string, string>>>;
  discriminator: { modes: string[]; aliases: Record<string, string> };
  true_values: string[];
  false_values: string[];
  limits: {
    msgid: Bounds;
    msgid_with_pkgid: Bounds;
    pkgid: Bounds;
    size_option: Bounds;
    one_byte_prefix_max: string;
    extensions_start_min: string;
    magic_bytes_count: string;
    magic_byte: Bounds;
    oneof_size_min: string;
  };
}

const SUPPORTED_SCHEMA_VERSION = 1;

const facts: LanguageFacts = rawFacts;
if (facts.schema_version !== SUPPORTED_SCHEMA_VERSION) {
  throw new Error(`language-facts.json schema_version ${facts.schema_version} is not supported (expected ${SUPPORTED_SCHEMA_VERSION})`);
}

const toRange = (bounds: Bounds): { min: number; max: number } => ({ min: Number(bounds.min), max: Number(bounds.max) });

// ── Types ───────────────────────────────────────────────────────────────────

/** All built-in field types, in compiler order. */
export const PRIMITIVE_TYPES: readonly string[] = facts.primitives.map(p => p.name);
/** Built-in types with a fixed wire size (everything except string and bytes). */
export const FIXED_SIZE_PRIMITIVES: readonly string[] = facts.primitives.filter(p => p.size !== null).map(p => p.name);
const PRIMITIVE_BY_NAME = new Map(facts.primitives.map(p => [p.name, p]));

export function isPrimitive(type: string): boolean {
  return PRIMITIVE_BY_NAME.has(type);
}

export function primitiveSize(type: string): number | null | undefined {
  return PRIMITIVE_BY_NAME.get(type)?.size;
}

/** string and bytes: sized by [size=] / [max_size=], arrays also need [element_size=]. */
export function isStringLike(type: string): boolean {
  const kind = PRIMITIVE_BY_NAME.get(type)?.kind;
  return kind === 'string' || kind === 'bytes';
}

export const INT_RANGES: Readonly<Record<string, { min: bigint; max: bigint }>> = Object.fromEntries(
  Object.entries(facts.integer_ranges).map(([name, bounds]) => [name, { min: BigInt(bounds.min), max: BigInt(bounds.max) }])
);

export const FLOAT_MAX = facts.float_max;
export const ENUM_VALUE_RANGE = toRange(facts.enum.value_range);

// ── Options ─────────────────────────────────────────────────────────────────

export const OPTION_SCOPES: readonly OptionScope[] = ['file', 'message', 'oneof', 'enum', 'field'];

/** Canonical option names per scope (aliases excluded). */
export const OPTION_NAMES: Readonly<Record<OptionScope, readonly string[]>> = {
  file: Object.keys(facts.options.file),
  message: Object.keys(facts.options.message),
  oneof: Object.keys(facts.options.oneof),
  enum: Object.keys(facts.options.enum),
  field: Object.keys(facts.options.field)
};

/** alias -> canonical name, per scope. */
export const OPTION_ALIASES: Readonly<Record<OptionScope, Readonly<Record<string, string>>>> = {
  file: facts.option_aliases.file ?? {},
  message: facts.option_aliases.message ?? {},
  oneof: facts.option_aliases.oneof ?? {},
  enum: facts.option_aliases.enum ?? {},
  field: facts.option_aliases.field ?? {}
};

/** Every accepted spelling (canonical names and aliases) for a scope. */
export function acceptedOptionNames(scope: OptionScope): string[] {
  return [...OPTION_NAMES[scope], ...Object.keys(OPTION_ALIASES[scope])];
}

export function isKnownOption(scope: OptionScope, name: string): boolean {
  return OPTION_NAMES[scope].includes(name) || name in OPTION_ALIASES[scope];
}

/** Resolve an alias (e.g. `envelope`) to its canonical name (`is_envelope`). */
export function canonicalOption(scope: OptionScope, name: string): string {
  return OPTION_ALIASES[scope][name] ?? name;
}

/** Read an option by canonical name, also accepting its aliases. */
export function getOption(options: Record<string, string>, scope: OptionScope, canonical: string): string | undefined {
  if (options[canonical] !== undefined) return options[canonical];
  for (const [alias, target] of Object.entries(OPTION_ALIASES[scope])) {
    if (target === canonical && options[alias] !== undefined) return options[alias];
  }
  return undefined;
}

export const OPTION_QUALIFIERS: readonly string[] = facts.option_qualifiers;
const escapeRegExp = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** Regex source matching a qualified field option name such as `(sf.size)`. */
export const QUALIFIED_OPTION_SOURCE = `\\((?:${OPTION_QUALIFIERS.map(escapeRegExp).join('|')})\\.\\w+\\)`;

/** Strip an optional `(sf.X)` / `(struct_frame.X)` qualifier, as the compiler does. */
export function normalizeFieldOptionKey(key: string): string {
  const trimmed = key.trim();
  for (const qualifier of OPTION_QUALIFIERS) {
    const prefix = `(${qualifier}.`;
    if (trimmed.startsWith(prefix) && trimmed.endsWith(')')) return trimmed.substring(prefix.length, trimmed.length - 1);
  }
  return trimmed;
}

// ── Option values ───────────────────────────────────────────────────────────

export const DISCRIMINATOR_MODES: readonly string[] = facts.discriminator.modes;
export const DISCRIMINATOR_ALIASES: Readonly<Record<string, string>> = facts.discriminator.aliases;

/** Lower-cased option value with surrounding quotes removed. */
export function optionValueText(value: string): string {
  return value.trim().replace(/^["']|["']$/g, '').trim().toLowerCase();
}

/** Canonical discriminator mode, or null when the value is not one the compiler accepts. */
export function normalizeDiscriminator(value: string): string | null {
  const text = optionValueText(value);
  const mode = DISCRIMINATOR_ALIASES[text] ?? text;
  return DISCRIMINATOR_MODES.includes(mode) ? mode : null;
}

export const TRUE_VALUES: readonly string[] = facts.true_values;
export const FALSE_VALUES: readonly string[] = facts.false_values;

/** The compiler treats these spellings of a bool option as true, and anything else as false. */
export function isTrueValue(value: string | undefined): boolean {
  return value !== undefined && TRUE_VALUES.includes(optionValueText(value));
}

export function isFalseValue(value: string | undefined): boolean {
  return value !== undefined && FALSE_VALUES.includes(optionValueText(value));
}

// ── Limits ──────────────────────────────────────────────────────────────────

export const LIMITS = {
  msgid: toRange(facts.limits.msgid),
  msgidWithPkgid: toRange(facts.limits.msgid_with_pkgid),
  pkgid: toRange(facts.limits.pkgid),
  sizeOption: toRange(facts.limits.size_option),
  oneBytePrefixMax: Number(facts.limits.one_byte_prefix_max),
  extensionsStartMin: Number(facts.limits.extensions_start_min),
  magicBytesCount: Number(facts.limits.magic_bytes_count),
  magicByte: toRange(facts.limits.magic_byte),
  oneofSizeMin: Number(facts.limits.oneof_size_min)
} as const;
