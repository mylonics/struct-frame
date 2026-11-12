// Every name the compiler defines (from the generated language-facts.json) must have
// documentation in docs.ts and appear in the TextMate grammar. When a new primitive,
// option or discriminator mode is added to src/struct_frame/language_facts.py, these
// tests point at exactly what the extension is missing.
import assert = require('node:assert/strict');
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test = require('node:test');
import {
  PRIMITIVE_TYPES, INT_RANGES, OPTION_NAMES, OPTION_ALIASES, OPTION_SCOPES, DISCRIMINATOR_MODES,
  DISCRIMINATOR_ALIASES, normalizeDiscriminator, normalizeFieldOptionKey, isTrueValue, LIMITS
} from '../facts';
import { PRIMITIVE_TYPE_DOCS, OPTION_DOCS, DISCRIMINATOR_DOCS, optionDoc } from '../docs';
import { EXTENSION_ROOT } from './lspClient';

test('every primitive type has documentation', () => {
  for (const type of PRIMITIVE_TYPES) assert.ok(PRIMITIVE_TYPE_DOCS[type], `no PRIMITIVE_TYPE_DOCS entry for '${type}'`);
  assert.deepEqual(Object.keys(PRIMITIVE_TYPE_DOCS).filter(type => !PRIMITIVE_TYPES.includes(type)), [], 'docs for types the compiler does not know');
});

test('every option in every scope (and every alias) has documentation', () => {
  for (const scope of OPTION_SCOPES) {
    for (const name of OPTION_NAMES[scope]) assert.ok(OPTION_DOCS[scope][name], `no OPTION_DOCS.${scope} entry for '${name}'`);
    for (const alias of Object.keys(OPTION_ALIASES[scope])) assert.ok(optionDoc(scope, alias), `alias '${alias}' (${scope}) resolves to no doc`);
    const stale = Object.keys(OPTION_DOCS[scope]).filter(name => !OPTION_NAMES[scope].includes(name));
    assert.deepEqual(stale, [], `OPTION_DOCS.${scope} documents options the compiler does not accept`);
  }
});

test('every discriminator mode has documentation', () => {
  for (const mode of DISCRIMINATOR_MODES) assert.ok(DISCRIMINATOR_DOCS[mode], `no DISCRIMINATOR_DOCS entry for '${mode}'`);
  for (const alias of Object.keys(DISCRIMINATOR_ALIASES)) assert.ok(normalizeDiscriminator(alias));
});

test('facts carry the compiler values exactly', () => {
  assert.ok(PRIMITIVE_TYPES.includes('bytes'));
  assert.equal(INT_RANGES.uint64.max, 18446744073709551615n);
  assert.equal(INT_RANGES.int64.min, -9223372036854775808n);
  assert.deepEqual(LIMITS.msgid, { min: 0, max: 65535 });
  assert.deepEqual(LIMITS.msgidWithPkgid, { min: 0, max: 255 });
  assert.ok(OPTION_NAMES.message.includes('discriminator'));
  assert.equal(OPTION_ALIASES.message.envelope, 'is_envelope');
  assert.equal(normalizeFieldOptionKey('(sf.size)'), 'size');
  assert.equal(normalizeFieldOptionKey('(struct_frame.max_size)'), 'max_size');
  assert.equal(normalizeFieldOptionKey('sf.size'), 'sf.size');
  assert.equal(normalizeDiscriminator('"off"'), 'none');
  assert.equal(isTrueValue('on'), true);
  assert.equal(isTrueValue('"yes"'), true);
  assert.equal(isTrueValue('maybe'), false);
});

test('the TextMate grammar highlights every primitive type and field option', () => {
  const grammar = readFileSync(resolve(EXTENSION_ROOT, 'syntaxes', 'sf.tmLanguage.json'), 'utf8');
  const alternations = [...grammar.matchAll(/\\\\b\(([a-z0-9_|]+)\)\\\\b/g)].map(match => match[1].split('|'));
  const highlighted = (name: string): boolean => alternations.some(words => words.includes(name));
  for (const type of PRIMITIVE_TYPES) assert.ok(highlighted(type), `grammar does not highlight primitive '${type}'`);
  for (const option of OPTION_NAMES.field) assert.ok(highlighted(option), `grammar does not highlight field option '${option}'`);
});
