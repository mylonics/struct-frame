// Parity check against the compiler: every schema in the struct-frame repo that the
// compiler accepts (tests/test_language_facts.py validates the same set with
// `struct-frame --validate`) must produce zero error diagnostics in the language server.
import assert = require('node:assert/strict');
import { existsSync, readdirSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import test = require('node:test');
import { EXTENSION_ROOT, REPO_ROOT, startServer } from './lspClient';

// Keep in sync with VALID_SCHEMA_DIRS in tests/test_language_facts.py.
const CORPUS: Array<{ dir: string; recursive: boolean }> = [
  { dir: join(REPO_ROOT, 'tests', 'proto'), recursive: false },
  { dir: join(REPO_ROOT, 'examples'), recursive: true },
  { dir: join(REPO_ROOT, 'tests', 'benchmarks', 'schema'), recursive: false },
  { dir: join(REPO_ROOT, 'tests', 'docs', 'schemas'), recursive: false },
];
const EXTENSION_EXAMPLES = ['example.sf', 'fixture-imports.sf'].map(name => resolve(EXTENSION_ROOT, 'examples', name));

function schemaFiles(dir: string, recursive: boolean): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory() && recursive) files.push(...schemaFiles(full, true));
    else if (entry.isFile() && entry.name.endsWith('.sf')) files.push(full);
  }
  return files.sort();
}

test('reports no errors on any compiler-valid schema in the repo', async () => {
  assert.ok(existsSync(join(REPO_ROOT, 'pyproject.toml')), `struct-frame repo not found at ${REPO_ROOT}`);
  const files = [...CORPUS.flatMap(({ dir, recursive }) => schemaFiles(dir, recursive)), ...EXTENSION_EXAMPLES];
  assert.ok(files.length >= 28, `expected the schema corpus, found only ${files.length} files`);

  const client = await startServer(REPO_ROOT);
  const failures: string[] = [];
  try {
    for (const file of files) {
      const { diagnostics } = await client.open(file);
      for (const d of diagnostics.filter(d => d.severity === 1)) {
        failures.push(`${relative(REPO_ROOT, file)}:${d.range.start.line + 1}: ${d.message}`);
      }
    }
  } finally {
    client.close();
  }
  assert.deepEqual(failures, [], `the language server rejects schemas the compiler accepts:\n${failures.join('\n')}`);
});
