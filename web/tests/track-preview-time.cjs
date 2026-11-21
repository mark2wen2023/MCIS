// Actual response parser; synthetic values only, no CSV read or request.
const fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process'),assert=require('node:assert/strict'),es=require('esbuild');
function load(source,imports={}){const module={exports:{}};vm.runInNewContext(es.transformSync(source,{loader:'ts',format:'cjs'}).code,{module,exports:module.exports,require:n=>{if(!(n in imports))throw Error('Unexpected import');return imports[n];}});return module.exports;}
const base='94d5e38c926fda232bb987b60fa9145e4bcf01a7';
const old=load(cp.execFileSync('git',['show',base+':web/src/trackInput/model.ts'],{encoding:'utf8'}));
const tracks=load(fs.readFileSync('src/tracks/model.ts','utf8'));
const current=load(fs.readFileSync('src/trackInput/model.ts','utf8'),{'../tracks/model':tracks});
const body={profile:'mcis-utc-v1',vesselId:'SYN-V',fileName:'synthetic.csv',source:'Synthetic',timeBasis:'Synthetic UTC',contentBase64:'eA=='};
const point=(utc,t)=>({vesselId:body.vesselId,utc,timeSec:t,latDeg:0,lonDeg:0,sogKn:10,cogDeg:90,hdgDeg:null});
const p={...body,caseId:'SYN-A',caseEpochUtc:'2026-01-01T00:00:00Z',previewDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),rowCount:2,canCommit:true,issues:[],issuesTotal:0,issuesTruncated:false,existingTrackCount:0,warnings:[],samplePoints:[point('2026-01-01T00:00:00Z',0),point('2026-01-01T00:00:01.250Z',1.25)],timeRange:{firstUtc:'2026-01-01T00:00:00Z',lastUtc:'2026-01-01T00:00:01.250Z',fromSec:0,toSec:1.25}};
let n=0;const parse=x=>current.parsePreview(x,'SYN-A',body),bad=x=>{assert.throws(()=>parse(x));n++;};
const duplicate={...p,samplePoints:[p.samplePoints[0],p.samplePoints[0]]};assert.equal(old.parsePreview(duplicate,'SYN-A',body).canCommit,true);bad(duplicate);console.log('REPRO fixed old parser accepts duplicate UTC as committable preview');
const copy=()=>JSON.parse(JSON.stringify(p));
assert.equal(parse(p).samplePoints[0].hdgDeg,null);assert.equal(parse(p).samplePoints[0].cogDeg,90);n++;
for(const utc of ['01/02/2026','2026-01-01T00:00:00','2026-02-30T00:00:00Z','2026-01-01T00:00:00+00:00']){const q=copy();q.samplePoints[0].utc=utc;bad(q);}
for(const delta of [0.01,0.0000011]){const q=copy();q.samplePoints[1].timeSec+=delta;bad(q);}
let q=copy();q.samplePoints[1].timeSec+=0.0000009;parse(q);n++;
q=copy();q.samplePoints[0].hdgDeg=0;assert.equal(parse(q).samplePoints[0].hdgDeg,0);n++;
q=copy();q.samplePoints[1]=point('2026-01-01T00:00:00.000Z',0);bad(q);
q=copy();q.caseEpochUtc='2026-02-30T00:00:00Z';bad(q);
q=copy();q.caseEpochUtc='2026-01-02T00:00:00Z';bad(q);
q=copy();q.timeRange.toSec=2;bad(q);
q=copy();q.timeRange.lastUtc='2026-01-01T00:00:02Z';q.timeRange.toSec=2;bad(q);
q=copy();q.samplePoints.reverse();bad(q);
q=copy();q.samplePoints=[point('2025-12-31T23:59:59Z',-1),p.samplePoints[1]];q.timeRange.firstUtc=q.samplePoints[0].utc;q.timeRange.fromSec=-1;parse(q);n++;
q=copy();q.canCommit=false;q.issuesTotal=1;q.issues=[{row:2,field:'utc',code:'TIME_ORDER',message:'Synthetic repeated time'}];q.samplePoints=[p.samplePoints[0]];q.timeRange={firstUtc:p.samplePoints[0].utc,lastUtc:p.samplePoints[0].utc,fromSec:0,toSec:0};assert.equal(parse(q).canCommit,false);n++;
q=copy();q.canCommit=false;q.issuesTotal=1;q.samplePoints=[];q.timeRange=null;assert.equal(parse(q).canCommit,false);n++;
q=copy();q.rowCount=101;q.samplePoints=Array.from({length:100},(_,i)=>point(new Date(Date.UTC(2026,0,1,0,0,i)).toISOString(),i));q.timeRange.lastUtc=new Date(Date.UTC(2026,0,1,0,0,100)).toISOString();q.timeRange.toSec=100;parse(q);n++;
console.log(`PASS ${n} synthetic response time checks; zero/null HDG preserved, diagnostic preview retained, first100 not full-file proof`);
