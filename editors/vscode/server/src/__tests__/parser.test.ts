import assert = require('node:assert/strict');
import test = require('node:test');
import {
  matchFieldDeclaration,
  matchFieldHead,
  parseDocument,
  parseFieldOptions,
  tokenizeFieldOptions
} from '../parser';

test('tokenizes commas inside quoted values', () => {
  const tokens = tokenizeFieldOptions('default = "a, b", size = 16', 10);
  assert.equal(tokens.length, 2);
  assert.equal(tokens[0].key, 'default');
  assert.equal(tokens[0].value, '"a, b"');
  assert.equal(tokens[1].key, 'size');
  assert.equal(tokens[1].value, '16');
});

test('keeps a closing bracket inside a quoted value', () => {
  const declaration = matchFieldDeclaration('string value = 1 [default = "a]b"];');
  assert.ok(declaration);
  assert.equal(declaration!.optionsRaw, 'default = "a]b"');
});

test('honors escaped quotes while scanning values', () => {
  const tokens = tokenizeFieldOptions('default = "a\\\"b, c", size = 8', 0);
  assert.equal(tokens.length, 2);
  assert.equal(tokens[0].value, '"a\\\"b, c"');
});

test('normalizes qualified option names like the compiler', () => {
  const options = parseFieldOptions('(sf.size)=4, (struct_frame.max_size) = 8');
  assert.deepEqual(options, { size: '4', max_size: '8' });
});

test('keeps bare sf.X names so they are reported as unknown (the compiler ignores them)', () => {
  const tokens = tokenizeFieldOptions('sf.size=4', 0);
  assert.equal(tokens[0].key, 'sf.size');
  assert.equal(tokens[0].malformed, false);
});

test('marks malformed option segments', () => {
  const tokens = tokenizeFieldOptions('size=16, broken, default=true', 0);
  assert.equal(tokens.length, 3);
  assert.equal(tokens[1].malformed, true);
  assert.equal(tokens[1].rawKey, 'broken');
});

test('returns no tokens for an empty option list', () => {
  assert.deepEqual(tokenizeFieldOptions('', 4), []);
});

test('reports exact key and value columns', () => {
  const tokens = tokenizeFieldOptions(' default = 16', 20);
  assert.deepEqual(tokens[0], {
    key: 'default',
    rawKey: 'default',
    value: '16',
    malformed: false,
    keyStart: 21,
    keyEnd: 28,
    valueStart: 31,
    valueEnd: 33,
    tokenStart: 20,
    tokenEnd: 33
  });
});

test('matches plain and repeated field heads with columns', () => {
  const plain = matchFieldHead('  uint32 count = 12');
  assert.ok(plain);
  assert.equal(plain!.repeated, false);
  assert.equal(plain!.typeStart, 2);
  assert.equal(plain!.nameStart, 9);
  assert.equal(plain!.tagStart, 17);

  const repeated = matchFieldHead('repeated string names = 3');
  assert.ok(repeated);
  assert.equal(repeated!.repeated, true);
  assert.equal(repeated!.type, 'string');
  assert.equal(repeated!.name, 'names');
});

test('requires a semicolon after field options', () => {
  assert.equal(matchFieldDeclaration('string value = 1 [size=4]'), null);
});

test('parses enum and oneof options', () => {
  const parsed = parseDocument('file:///fixture.sf', `
    enum State {
      option extensions_start = 2;
      READY = 1;
    }
    message Container {
      oneof payload {
        option variable = true;
        string value = 1 [size=8];
      }
    }
  `);
  assert.equal(parsed.enums[0].options.extensions_start, '2');
  assert.equal(parsed.messages[0].oneofs[0].options.variable, 'true');
  assert.equal(parsed.messages[0].oneofs[0].optionLines.variable, 7);
  assert.equal(parsed.messages[0].oneofs[0].fields[0].inOneof, true);
  assert.equal(parsed.messages[0].oneofs[0].fields[0].bracketStart, 25);
  assert.equal(parsed.messages[0].oneofs[0].fields[0].bracketEnd, 32);
});
