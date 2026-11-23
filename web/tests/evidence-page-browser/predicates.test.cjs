const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scope = {};
vm.runInNewContext(fs.readFileSync(__dirname + '/predicates.js', 'utf8'), scope);
let count = 0;
const check = (a,b) => { assert.equal(a,b); count++; };
const row = (id,caseId='SYN-B',op='SYNTHETIC-TWO') => ({id,url:`/api/v1/cases/${caseId}/evidence`,operator:encodeURIComponent(op)});
const match = rows => scope.matchingRequest(rows,4,'SYN-B','SYNTHETIC-TWO');
check(match([row(4)]),null); // Old pending cannot satisfy a new wait.
check(match([row(5,'SYN-A')]),null);
check(match([row(5,'SYN-B','SYNTHETIC-ONE')]),null);
check(match([row(4),row(5)]),5);
check(match([row(5),row(6)]),null); // Ambiguity is not silently newest-wins.
check(match([]),null);
check(match([{...row(5),url:'/api/v1/cases/SYN-B/evidence/EV-001'}]),null);
check(scope.matchingRequest([row(5,'SYN-B','合成身份')],4,'SYN-B','合成身份'),5);
check(scope.fourMetrics([],'不可用'),false);
check(scope.fourMetrics(Array(3).fill('不可用'),'不可用'),false);
check(scope.fourMetrics(Array(5).fill('不可用'),'不可用'),false);
check(scope.fourMetrics(['不可用','不可用','不可用','0条'],'不可用'),false);
check(scope.fourMetrics(Array(4).fill('不可用'),'不可用'),true);
console.log(`${count} shared browser predicate checks passed; no browser executed`);
