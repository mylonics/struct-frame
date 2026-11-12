import assert = require('node:assert/strict');
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test = require('node:test');
import { EXTENSION_ROOT, startServer, Diagnostic } from './lspClient';

const example = (name: string): string => resolve(EXTENSION_ROOT, 'examples', name);

/** `// EXPECT: <text>` comments in a fixture: line number → expected message substring. */
function expectations(filePath: string): Map<number, string> {
  const expected = new Map<number, string>();
  readFileSync(filePath, 'utf8').split('\n').forEach((line, index) => {
    const match = line.match(/\/\/\s*EXPECT:\s*(.+?)\s*$/);
    if (match) expected.set(index, match[1]);
  });
  return expected;
}

test('publishes expected diagnostics for schema fixtures', async () => {
  const client = await startServer();
  try {
    const clean = await client.open(example('example.sf'));
    assert.deepEqual(clean.diagnostics.map(d => d.message), []);

    const fixture = example('validation-fixtures.sf');
    const { diagnostics } = await client.open(fixture);
    const onLine = (line: number): Diagnostic[] => diagnostics.filter(d => d.range.start.line === line);
    for (const [line, text] of expectations(fixture)) {
      assert.ok(onLine(line).some(d => d.message.includes(text)),
        `line ${line + 1}: expected a diagnostic containing '${text}', got ${JSON.stringify(onLine(line).map(d => d.message))}`);
    }

    const unknownOption = diagnostics.find(d => d.message.includes("Unknown field option 'defualt'"));
    assert.equal(unknownOption?.severity, 2);
    const repeatedDefault = diagnostics.find(d => d.message.includes('default is not supported on repeated field'));
    assert.deepEqual(repeatedDefault?.range, {
      start: { line: 12, character: 43 },
      end: { line: 12, character: 53 }
    });
  } finally {
    client.close();
  }
});

test('hover and option completion follow the compiler facts', async () => {
  const client = await startServer();
  try {
    const filePath = example('example.sf');
    const { uri } = await client.open(filePath);
    const lines = readFileSync(filePath, 'utf8').split('\n');

    // A message-scope `option ` offers every message option, including `discriminator`.
    const msgLine = lines.findIndex(line => line.includes('option msgid = 1;'));
    client.notify('textDocument/didChange', {
      textDocument: { uri, version: 2 },
      contentChanges: [{
        range: { start: { line: msgLine, character: 0 }, end: { line: msgLine, character: lines[msgLine].length } },
        text: '  option '
      }]
    });
    const messageCompletions = await client.request('textDocument/completion', {
      textDocument: { uri }, position: { line: msgLine, character: '  option '.length }
    });
    const messageLabels = (messageCompletions.result as Array<{ label: string }>).map(item => item.label);
    assert.ok(messageLabels.includes('discriminator'), `message options: ${messageLabels.join(', ')}`);
    assert.ok(!messageLabels.includes('pkgid'));

    // Inside an enum, `option ` offers the enum options.
    const enumLine = lines.findIndex(line => line.includes('OFFLINE = 0;'));
    const enumCompletions = await client.request('textDocument/completion', {
      textDocument: { uri }, position: { line: enumLine, character: 0 }
    });
    assert.ok(Array.isArray(enumCompletions.result));
    client.notify('textDocument/didChange', {
      textDocument: { uri, version: 3 },
      contentChanges: [{
        range: { start: { line: enumLine, character: 0 }, end: { line: enumLine, character: lines[enumLine].length } },
        text: '  option '
      }]
    });
    const enumOptions = await client.request('textDocument/completion', {
      textDocument: { uri }, position: { line: enumLine, character: '  option '.length }
    });
    assert.deepEqual((enumOptions.result as Array<{ label: string }>).map(item => item.label), ['extensions_start']);

    // `bytes` is a primitive (it was missing before the facts were shared).
    const bytesLine = lines.findIndex(line => line.includes('repeated uint8 data'));
    client.notify('textDocument/didChange', {
      textDocument: { uri, version: 4 },
      contentChanges: [{
        range: { start: { line: bytesLine, character: 0 }, end: { line: bytesLine, character: lines[bytesLine].length } },
        text: '  bytes data = 4 [max_size=200];'
      }]
    });
    const hover = await client.request('textDocument/hover', {
      textDocument: { uri }, position: { line: bytesLine, character: 3 }
    });
    const hoverText = (hover.result as { contents: { value: string } } | null)?.contents.value ?? '';
    assert.match(hoverText, /\*\*bytes\*\* \(primitive type\)/);
  } finally {
    client.close();
  }
});
