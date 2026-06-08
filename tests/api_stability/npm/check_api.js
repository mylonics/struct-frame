const fs = require('fs');
const path = require('path');

const baseline = path.join(__dirname, 'baseline.d.ts');
const generatedDir = path.join(__dirname, '..', '..', 'generated', 'ts');

if (!fs.existsSync(baseline)) {
  console.log('npm API stability: no baseline.d.ts yet; skipping.');
  process.exit(0);
}

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

const current = collectGeneratedDeclarations(generatedDir);
const expected = fs.readFileSync(baseline, 'utf8')
  .split('\n')
  .filter(l => l.trim() && !l.startsWith('#'));

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
