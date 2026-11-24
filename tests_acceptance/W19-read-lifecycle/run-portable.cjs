'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { pathToFileURL } = require('node:url');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');

async function run() {
  const checkout = path.resolve(process.argv[2] || path.join(__dirname, '../..'));
  const testPath = path.join(checkout, 'tests_acceptance/W19-read-lifecycle/check.tsx');
  const modules = path.resolve(process.env.MCIS_NODE_MODULES || path.join(checkout, 'web/node_modules'));
  const happy = process.env.MCIS_HAPPY_DOM_PATH;
  if (!happy) throw Error('Set MCIS_HAPPY_DOM_PATH to the existing happy-dom/lib/index.js path or file URL; no install is attempted');
  const happyURL = happy.startsWith('file:') ? happy : pathToFileURL(path.resolve(happy)).href;
  const pins = JSON.parse(fs.readFileSync(path.join(__dirname, 'frontend-pins.json'), 'utf8'));
  for (const [relative, pin] of Object.entries(pins)) {
    const raw = fs.readFileSync(path.join(checkout, relative));
    const digest = createHash('sha1').update('blob ' + raw.length + '\0').update(raw).digest('hex');
    if (digest !== pin) throw Error('W19 fixed source pin mismatch: ' + relative);
  }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mcis-w19-react-'));
  try {
    const output = path.join(tmp, 'check.mjs');
    await require(path.join(modules, 'esbuild')).build({
      entryPoints: [testPath], outfile: output, bundle: true,
      platform: 'node', format: 'esm', jsx: 'automatic', nodePaths: [modules],
      loader: {'.css': 'empty'},
      banner: {js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);"},
    });
    const result = spawnSync(process.execPath, [output], {
      encoding: 'utf8', timeout: 20000,
      env: {...process.env, MCIS_HAPPY_DOM_PATH: happyURL},
    });
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    if (result.error) throw result.error;
    if (result.status !== 0) throw Error('W19 React test exit: ' + result.status);
  } finally {
    fs.rmSync(tmp, {recursive: true, force: true});
  }
}
run().catch(error => {console.error(error.message); process.exitCode = 1;});
