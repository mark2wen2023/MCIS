import assert from 'node:assert/strict';
import {allowedRequest} from './request-policy.mjs';
let count = 0;
const check = (url, method, expected) => {assert.equal(allowedRequest(url, method), expected); count++;};
for (const c of ['SYN-A','SYN-B']) {
 for (const s of ['', '/evidence', '/custody:verify-chain', '/timeline', '/conflicts', '/tracks', '/access-policy', '/evidence/EV-001/custody'])
  check(`/api/v1/cases/${c}${s}`, 'GET', true);
 for (const s of ['/unknown', '/conflicts/extra', '/conflicts?extra=1', '/evidence/EV-002/custody', '/cpa?stepSec=15', '/archive-history', '/timeline/align-preview'])
  check(`/api/v1/cases/${c}${s}`, 'GET', false);
}
for (const method of ['POST','PATCH','PUT','DELETE']) check('/api/v1/cases/SYN-A/conflicts',method,false);
check('/api/v1/cases/SYN-C/conflicts','GET',false);
check('https://external.invalid/api/v1/cases/SYN-A/conflicts','GET',false);
check('/api/v1/cases/SYN-A/conflicts/','GET',false);
console.log(`${count} fixture endpoint allowlist checks passed; no browser executed`);
