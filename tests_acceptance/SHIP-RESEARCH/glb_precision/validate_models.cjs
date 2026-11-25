const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('gltf-validator');

async function main() {
  const [source, destination] = process.argv.slice(2);
  const rows = [];
  for (const name of fs.readdirSync(source).filter(n => n.endsWith('.glb')).sort()) {
    const bytes = fs.readFileSync(path.join(source, name));
    const report = await validator.validateBytes(new Uint8Array(bytes), {uri: name});
    rows.push({name, sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
      errors: report.issues.numErrors, warnings: report.issues.numWarnings,
      infos: report.issues.numInfos, messages: report.issues.messages});
  }
  if (!rows.length) throw Error('No GLB inputs');
  fs.writeFileSync(destination, JSON.stringify({validator: validator.version(), rows}, null, 2) + '\n');
  if (rows.some(row => row.errors > 0)) process.exitCode = 1;
}

main().catch(error => { console.error(error.message); process.exitCode = 2; });
