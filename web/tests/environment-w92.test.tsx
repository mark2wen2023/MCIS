import {renderToStaticMarkup} from 'react-dom/server'
import {buildObservation,emptyForm,parseObservations,matchesObservation,validUtc,canCreate,fields,quantity} from '../src/environment/model'
import {navigationForCase,supportsCaseContext} from '../src/caseContext'
let checks=0
const ok=(v:unknown,m:string)=>{if(!v)throw Error(m);checks++}
const bad=(fn:()=>unknown,m:string)=>{let rejected=false;try{fn()}catch{rejected=true}ok(rejected,m)}
const f=emptyForm();f.valueOrigin='Direct';f.observationId='OBS-1';f.sourceLabel='Synthetic source p.1';f.description=' 东北风4级，能见度良好\n保留原文 '
const r=buildObservation(f,'CASE-A');ok(r.description===f.description,'verbatim');ok(r.observedAtUtc===null&&r.locationDescription===null,'unknown context null');ok(fields.every(([k])=>!(k in r)),'unknown quantities absent')
ok(matchesObservation(r,r),'exact match');ok(quantity(0,'nm')==='0 nm','zero visible');ok(quantity(null,'kn')==='未知'&&quantity(undefined,'m/s')==='未知','null missing unknown')
for(const role of ['Public','AgentService','ExternalExpert','InterestedState','other'])ok(!canCreate(role),'readonly '+role)
ok(canCreate('Investigator')&&canCreate('LeadInvestigator'),'investigators')
for(const x of ['2024-02-29T12:34:56Z','0001-01-01T00:00:00Z','9999-12-31T23:59:59Z'])ok(validUtc(x),'valid '+x)
for(const x of ['0000-01-01T00:00:00Z','2023-02-29T00:00:00Z','2024-02-30T00:00:00Z','2024-13-01T00:00:00Z','2024-01-01T24:00:00Z','2024-01-01T23:59:60Z','2024-01-01T00:00:00+00:00','2024-01-01','2024-01-01T00:00:00.000Z'])ok(!validUtc(x),'invalid '+x)
for(const [key] of fields){
 for(const v of ['NaN','Infinity','1e400','-1','0x10','2,3','true']){f.values[key]=v;bad(()=>buildObservation(f,'CASE-A'),'invalid numeric '+v)}
 f.values[key]='0';ok(buildObservation(f,'CASE-A')[key]===0,'zero '+key)
 f.values[key]='0.0000001';ok(buildObservation(f,'CASE-A')[key]===1e-7,'small positive')
 if(key.endsWith('Deg')){f.values[key]='360';ok(buildObservation(f,'CASE-A')[key]===360,'360 accepted');f.values[key]='360.0000001';bad(()=>buildObservation(f,'CASE-A'),'outside bearing')}
 f.values[key]=''
}
for(const key of ['sourceLabel','description'] as const){const prev=f[key];f[key]=' \t ';bad(()=>buildObservation(f,'CASE-A'),'blank '+key);f[key]=prev}
for(const id of ['','-bad','with space','a'.repeat(65),'中文']){f.observationId=id;bad(()=>buildObservation(f,'CASE-A'),'bad id')};f.observationId='OBS-1'
for(const raw of [null,{},[r,r],[{...r,caseId:'OTHER'}],[{...r,observedAtUtc:undefined}],[{...r,locationDescription:undefined}],[{...r,sourceLabel:''}],[{...r,valueOrigin:'AI'}],[{...r,extra:1}],[{...r,windSpeedMps:NaN}],[{...r,visibilityNm:-1}],[{...r,currentToDirDeg:361}]])bad(()=>parseObservations(raw,'CASE-A'),'reject response')
ok(parseObservations([{...r,windSpeedMps:null}],'CASE-A')[0]?.windSpeedMps===null,'explicit null retained')
ok(!matchesObservation({...r,visibilityNm:0},r),'additional field mismatch');ok(!matchesObservation({...r,description:'other'},r),'text mismatch')
ok(supportsCaseContext('/env'),'env context');ok(navigationForCase('env','CASE-A','DEFAULT')==='/env?case=CASE-A','case link')
;(globalThis as any).localStorage={getItem:()=>null,setItem:()=>{}}
const {ObservationList}=await import('../src/pages/EnvironmentPage')
const html=renderToStaticMarkup(<ObservationList records={[{...r,description:'<img src=x onerror=alert(1)>',windFromDirDeg:90,currentToDirDeg:180,visibilityNm:0}]}/> )
ok(!html.includes('<img'),'escaped source');ok(html.includes('风的来向')&&html.includes('水流去向'),'direction labels');ok(html.includes('从该方向吹来')&&html.includes('向该方向流去'),'direction semantics');ok(html.includes('0 nm')&&html.includes('未知'),'zero vs unknown');ok(html.includes('Synthetic source p.1'),'source displayed');ok(renderToStaticMarkup(<ObservationList records={[]}/>).includes('不会自动补值'),'empty no fabrication')
console.log(`${checks} W9.2 model/render assertions passed`)
