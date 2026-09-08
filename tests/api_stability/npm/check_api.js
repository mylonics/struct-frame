const fs = require('fs');
const path = require('path');

const baseline = path.join(__dirname, 'baseline.d.ts');
const generatedDir = path.join(__dirname, '..', '..', 'generated', 'ts');

// Collect all .ts files from the generated directory, excluding test files
function collectGeneratedDeclarations(dir) {
  const lines = [];
  if (!fs.existsSync(dir)) {
    console.error(`Generated directory not found: ${dir}`);
    process.exit(1);
  }
  for (const file of fs.readdirSync(dir).sort()) {
    if (file.endsWith('.structframe.ts') || file === 'index.ts') {
      const content = fs.readFileSync(path.join(dir, file), 'utf8');
      // Extract exported names (types, interfaces, classes, enums, const, functions)
      const exportMatches = content.matchAll(
        /export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)/g
      );
      for (const m of exportMatches) {
        lines.push(`${file}:${m[1]}`);
      }
    }
  }
  return lines.sort();
}

const args = process.argv.slice(2);
const update = args.includes('--update');
const allowMissingBaseline = args.includes('--allow-missing-baseline');

const current = collectGeneratedDeclarations(generatedDir);

if (update) {
  const header = '# npm API stability baseline — regenerate with `node check_api.js --update`\n';
  fs.writeFileSync(baseline, header + current.join('\n') + '\n');
  console.log(`npm API stability: updated baseline ${baseline} (${current.length} exports).`);
  process.exit(0);
}

if (!fs.existsSync(baseline)) {
  const msg = 'npm API stability: missing baseline.d.ts.';
  if (allowMissingBaseline) {
    console.log(msg + ' (allowed; skipping)');
    process.exit(0);
  }
  console.error(msg);
  console.error('Create tests/api_stability/npm/baseline.d.ts or run with --allow-missing-baseline.');
  process.exit(1);
}

// Split on \r?\n, not \n: the baseline is stored with LF but git checks it out
// with CRLF on Windows (core.autocrlf), and a trailing \r on every entry made
// each one compare unequal — reporting the whole baseline as REMOVED.
const expected = fs.readFileSync(baseline, 'utf8')
  .split(/\r?\n/)
  .map(l => l.trim())
  .filter(l => l && !l.startsWith('#'));

const removed = expected.filter(e => !current.includes(e));
const added = current.filter(e => !expected.includes(e));

if (removed.length > 0) {
  console.error('npm API stability: BREAKING CHANGES detected:');
  for (const r of removed) console.error(`  REMOVED: ${r}`);
  process.exit(1);
}

if (added.length > 0) {
  console.log('npm API stability: new exports added (non-breaking):');
  for (const a of added) console.log(`  ADDED: ${a}`);
}

console.log(`npm API stability: compatible (${current.length} exports checked).`);
process.exit(0);
