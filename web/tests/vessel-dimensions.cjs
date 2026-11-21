// Actual old/new VesselList SSR; only synthetic records, no API/browser.
const fs=require('node:fs'),cp=require('node:child_process'),vm=require('node:vm'),es=require('esbuild'),assert=require('node:assert/strict'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
function load(source,mocks={}){const module={exports:{}};vm.runInNewContext(es.transformSync(source,{loader:'tsx',format:'cjs',jsx:'automatic'}).code,{module,exports:module.exports,require:n=>n.endsWith('.css')?{}:n in mocks?mocks[n]:n.startsWith('.')?{}:require(n)});return module.exports;}
const model=load(fs.readFileSync('src/vessels/model.ts','utf8'));
const dims=load(fs.readFileSync('src/vessels/Dimensions.tsx','utf8'),{'./model':model});
const mocks={'../vessels/model':model,'../vessels/Dimensions':dims};
const old=load(cp.execFileSync('git',['show','94d5e38c926fda232bb987b60fa9145e4bcf01a7:web/src/pages/ShipsPage.tsx'],{encoding:'utf8'}),mocks);
const now=load(fs.readFileSync('src/pages/ShipsPage.tsx','utf8'),mocks);
const vessel={caseId:'SYN-A',vesselId:'SYN-V',name:'Synthetic'};
const render=(m,v)=>renderToStaticMarkup(React.createElement(m.VesselList,{vessels:v}));
assert(!render(old,[vessel]).includes('总长'));console.log('REPRO old real VesselList silently omits unknown dimensions');
let h=render(now,[vessel]);for(const k of ['总长','型宽','首吃水','尾吃水','未登记','不填默认值','未提供模型比例'])assert(h.includes(k));
let v={...vessel,loaM:123,beamM:20,draftForeM:0,draftAftM:4,parameterSources:{loaM:{kind:'Direct',sourceLabel:'<script>synthetic</script>'},beamM:{kind:'Estimated',sourceLabel:'Synthetic estimate'},draftAftM:{kind:'Derived',sourceLabel:'Synthetic calculation'}}};
const before=JSON.stringify(v);h=render(now,[v]);assert(h.includes('123 · 已登记值'));assert(h.includes('0 · 已登记值'));assert(h.includes('【估计】'));assert(h.includes('【推算】'));assert(h.includes('尚未核验'));assert(h.includes('来源未登记'));assert(!h.includes('<script>'));assert.equal(JSON.stringify(v),before);
h=render(now,[{...vessel,loaM:0,beamM:-1,draftForeM:-1,draftAftM:0}]);assert.equal((h.match(/登记值异常/g)||[]).length,3);assert(h.includes('0 · 已登记值'));
h=render(now,[{...vessel,parameterSources:{loaM:{kind:'Direct',sourceLabel:'orphan-source'}}}]);assert(!h.includes('orphan-source'));assert(h.includes('不能据来源标签推定数值'));
h=render(now,[{...vessel,loaM:10,parameterSources:{loaM:{kind:'Direct',sourceLabel:'   '}}}]);assert(h.includes('来源未登记'));
h=render(now,[{...vessel,loaM:null}]);assert(h.includes('未登记 · 不填默认值'));
assert(render(now,[]).includes('尚无船舶参数'));assert(!render(now,[]).includes('已登记值'));
console.log('PASS real old/new SSR: missing, known/unverified, null/zero policy, abnormal values, orphan/blank sources, escaping, no mutation, empty list');
