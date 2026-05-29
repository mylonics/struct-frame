const fs = require('fs');
const path = require('path');
const baseline = path.join(__dirname, 'baseline.d.ts');
if (!fs.existsSync(baseline)) {
  console.log('npm API stability scaffold: no baseline.d.ts yet; skipping.');
  process.exit(0);
}
console.log('npm API stability scaffold: compare generated declarations to baseline.d.ts here.');
