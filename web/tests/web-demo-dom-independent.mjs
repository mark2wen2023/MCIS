import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Window} from 'happy-dom';
const assets=new URL('../../service/mcis_service/identity/demo_assets/',import.meta.url);
const html=fs.readFileSync(new URL('index.html',assets),'utf8').replace('__DEMO_CSRF__','fake-csrf');
const js=fs.readFileSync(new URL('demo.js',assets),'utf8');
const base={fixture:'fictional',caseId:'CASE-TRIAL-FICTIONAL',saved:true,read:true,status:'unreviewed',observationApproval:'not_assessed',temporaryDataCleaned:true,productionLogin:false,networkListener:false,sourceRelationship:'not_verified',coreImplementationVersionStatus:'not_attested',sourcesImported:2,selectedSourceIds:['EV-001','EV-002'],runId:'00000000-0000-0000-0000-000000000001',conflicts:[{delta:5,deltaUnit:'deg'}]};
const flush=()=>new Promise(r=>setTimeout(r,0));
const w=new Window({url:'http://127.0.0.1:34567'});w.document.write(html);let jobs=[];
w.fetch=(_p,opts)=>new Promise(resolve=>jobs.push({resolve,opts}));w.eval(js);
const d=w.document,button=d.querySelector('#run'),visible=()=>!d.querySelector('#result').hidden;
const deliver=(job,data,ok=true)=>job.resolve({ok,status:503,json:async()=>data});
const mutations=[{caseId:'other'},{saved:false},{read:false},{fixture:'real'},{productionLogin:true},{temporaryDataCleaned:false},{networkListener:true},{selectedSourceIds:['EV-002','EV-001']},{sourcesImported:1},{observationApproval:'approved'},{sourceRelationship:'verified'},{coreImplementationVersionStatus:'attested'},{runId:'<img src=x onerror=alert(1)>'},{conflicts:[{delta:NaN,deltaUnit:'deg'}]},{conflicts:[{delta:5,deltaUnit:'m'}]},{conflicts:Array(129).fill({delta:5,deltaUnit:'deg'})},{conflicts:[null]}];
for(const mutation of mutations){button.click();deliver(jobs.at(-1),{...base,...mutation});await flush();assert(!visible());assert(!button.disabled);assert(d.querySelector('#status').textContent.includes('未确认完成'));}
// A page restoration permits a new request, but the old result must not clear its lock or paint.
button.click();const old=jobs.at(-1);w.dispatchEvent(new w.Event('pagehide'));
button.click();const newer=jobs.at(-1);deliver(old,base);await flush();assert(button.disabled);assert(!visible());
deliver(newer,base);await flush();assert(visible());assert(!button.disabled);
// A new selection clears a successful old value, and mismatched returned sources cannot paint.
d.querySelector('input[value="1"]').click();assert(!visible());button.click();deliver(jobs.at(-1),base);await flush();assert(!visible());
button.click();deliver(jobs.at(-1),{...base,sourcesImported:1,selectedSourceIds:['EV-001'],conflicts:[]});await flush();assert(visible());assert(d.querySelector('#metric').textContent.includes('未列出'));
assert.equal(d.querySelectorAll('#result img').length,0);assert.equal(w.localStorage.length,0);assert.equal(w.sessionStorage.length,0);
w.happyDOM.abort();console.log('Independent DOM: 17 rejected summary mutations; overlapping late response lock; selection mismatch; valid single source; no injected markup/storage.');
