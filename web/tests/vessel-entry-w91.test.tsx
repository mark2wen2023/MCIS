import { renderToStaticMarkup } from 'react-dom/server'
import { buildVessel, emptyVesselForm, fields, matchesVessel, parseVessels, canCreateVessel } from '../src/vessels/model'
let count=0
function check(v:unknown,msg:string){if(!v)throw Error(msg);count++}
const f=emptyVesselForm();f.vesselId='ship';f.values.name='<script>synthetic</script>'
const body=buildVessel(f,'CASE-A',true)
check(body.name===f.values.name,'literal name preserved')
check(Object.keys(body).length===3,'unknowns absent')
check(matchesVessel(body,body),'matches')
for(const x of [null,{},[],{...body,caseId:'CASE-B'},{...body,loaM:1}])check(!matchesVessel(x,body),'mismatch')
for(const key of ['loaM','beamM','draftForeM','draftAftM','displacementTons'] as const){
 for(const value of ['NaN','Infinity','1e400','-1','0x10','1,2','true']){f.values[key]=value;let bad=false;try{buildVessel(f,'CASE-A',true)}catch{bad=true}check(bad,'invalid '+key+value)}
 f.values[key]='0';let bad=false;try{buildVessel(f,'CASE-A',true)}catch{bad=true}check(bad===!key.startsWith('draft'),'zero semantics '+key);f.values[key]=''
}
for(const v of ['123','1234567890','12345678a']){f.values.mmsi=v;let bad=false;try{buildVessel(f,'CASE-A',true)}catch{bad=true}check(bad,'MMSI');}f.values.mmsi='001234567'
check(buildVessel(f,'CASE-A',true).mmsi==='001234567','MMSI leading zeros')
let bad=false;try{buildVessel(f,'CASE-A',false)}catch{bad=true}check(bad,'real requires sources')
f.sources.name={sourceLabel:'Synthetic report p1',kind:'Estimated'};f.sources.mmsi={sourceLabel:'Synthetic registry',kind:'Direct'}
const real=buildVessel(f,'CASE-A',false);check(real.parameterSources?.name.kind==='Estimated','source survives')
f.values.mmsi='';check(!buildVessel(f,'CASE-A',false).parameterSources?.mmsi,'removed parameter has no stale source')
for(const role of ['Public','ExternalExpert','InterestedState','AgentService','unknown'])check(!canCreateVessel(role),'write denied')
check(canCreateVessel('Investigator')&&canCreateVessel('LeadInvestigator'),'investigators')
check(parseVessels([], 'CASE-A').length===0,'empty list')
for(const x of [null,{},[body,body],[{...body,caseId:'CASE-B'}],[{...body,loaM:'10'}],[{...body,parameterSources:{name:{sourceLabel:'x',kind:'AI'}}}]]){let invalid=false;try{parseVessels(x,'CASE-A')}catch{invalid=true}check(invalid,'bad response')}
// Import after mock localStorage because api.ts reads it at module load.
;(globalThis as any).localStorage={getItem:()=>null,setItem:()=>{}}
const {VesselList}=await import('../src/pages/ShipsPage')
const html=renderToStaticMarkup(<VesselList vessels={[real]}/>)
check(!html.includes('<script>'),'escaped text')
check(html.includes('【估计】')&&html.includes('Synthetic report p1'),'source visible')
check(renderToStaticMarkup(<VesselList vessels={[]}/>).includes('本案尚无船舶参数'),'honest empty')
for(const [key] of fields)check(emptyVesselForm().values[key]==='','no defaults '+key)
console.log(`${count} W9.1 assertions passed`)
