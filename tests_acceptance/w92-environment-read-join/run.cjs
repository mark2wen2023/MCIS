'use strict';

const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

const revision = 'a928e5e4db6d0bd669a41b80a8f5d39a707cab98';
const flags = ['--source', '--python', '--web-modules', '--happy-dom-entry'];
const args = process.argv.slice(2);
const options = {};
if (args.length !== flags.length * 2) {
  console.error('Usage: node run.cjs --source FIXED_CHECKOUT --python PYTHON --web-modules NODE_MODULES --happy-dom-entry ENTRY_JS');
  process.exit(2);
}
for (let i = 0; i < args.length; i += 2) {
  assert(flags.includes(args[i]) && !(args[i] in options) && !args[i+1].startsWith('--'), 'invalid arguments');
  options[args[i]] = path.resolve(args[i+1]);
}

function stage(temp) {
  const pins = JSON.parse(fs.readFileSync(path.join(__dirname, 'pins.json'), 'utf8'));
  for (const [name, expected] of Object.entries(pins)) {
    assert(/^(service|web|contracts)\/[a-zA-Z0-9_./-]+$/.test(name) && !name.split('/').includes('..'), name);
    assert(/^[0-9a-f]{40}$/.test(expected), name);
    const bytes = fs.readFileSync(path.join(options['--source'], name));
    const actual = createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex');
    assert.equal(actual, expected, 'pinned source mismatch: '+name);
    const copy = path.join(temp, name);
    fs.mkdirSync(path.dirname(copy), {recursive:true});
    fs.writeFileSync(copy, bytes, {flag:'wx'});
  }
  return Object.keys(pins).length;
}

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'mcis-w92-offline-'));
try {
  const n = stage(temp);
  fs.copyFileSync(path.join(__dirname,'pins.json'), path.join(temp,'pins.json'), fs.constants.COPYFILE_EXCL);
  const modules = options['--web-modules'];
  const esbuild = require(path.join(modules, 'esbuild'));
  console.log('Verified '+n+' input Git blobs at '+revision);
  const entry = path.join(temp, 'check.tsx');
  const output = path.join(temp, 'check.mjs');
  fs.copyFileSync(path.join(__dirname, 'check.tsx'), entry, fs.constants.COPYFILE_EXCL);
  esbuild.buildSync({
    entryPoints:[entry], outfile:output, bundle:true, platform:'node', format:'esm',
    jsx:'automatic', nodePaths:[modules], loader:{'.css':'empty'},
    banner:{js:"import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);"},
  });
  const result = spawnSync(process.execPath,[output], {
    encoding:'utf8', timeout:30000,
    env:{...process.env,PYTHON:options['--python'],HOST:path.join(__dirname, 'host.py'),MCIS_PINNED_SOURCE:temp,
      MCIS_HAPPY_DOM_PATH:pathToFileURL(options['--happy-dom-entry']).href},
  });
  process.stdout.write(result.stdout || '');
  process.stderr.write(result.stderr || '');
  if (result.error) throw result.error;
  assert.equal(result.status,0,'joined check did not pass');
} finally {
  fs.rmSync(temp,{recursive:true,force:true});
}
