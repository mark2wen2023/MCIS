// Actual page SSR with injected hook result and View boundary, no seed/API.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),esbuild=require('esbuild'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
let state={snapshot:null,error:null,reload(){}};
const moduleBox={exports:{}};
const mocks={'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYN-A'),()=>{}]},'../api':{CASE_ID:'SYN-DEFAULT'},'../analysis/AnalysisView':{AnalysisView:({data})=>React.createElement('div',{'data-analysis':true},data.caseId)},'../analysis/derive':{BASELINE:'baseline'},'../components/Toast':{useToast:()=>({show(){}})},'../config':{SERVICE_ADDR:'synthetic'},'../analysis/useAnalysisSnapshot':{useAnalysisSnapshot:()=>state}};
vm.runInNewContext(esbuild.transformSync(fs.readFileSync('src/pages/AnalysisPage.tsx','utf8'),{loader:'tsx',format:'cjs',jsx:'automatic'}).code,{module:moduleBox,exports:moduleBox.exports,require:n=>n.endsWith('.css')?{}:mocks[n]??require(n)});
const render=()=>renderToStaticMarkup(React.createElement(moduleBox.exports.AnalysisPage));
assert.match(render(),/旧分析已停用/);assert(!render().includes('data-analysis'));
state={...state,error:'合成失败'};assert.match(render(),/合成失败/);assert(!render().includes('data-analysis'));
state={...state,error:null,snapshot:{data:{caseId:'SYN-A',meta:{seedSha256:'a'.repeat(64)}},list:{cases:[]}}};assert.match(render(),/data-analysis/);assert.match(render(),/未确认登记轨迹实时版本/);assert.match(render(),/重新读取分析快照/);
console.log('PASS actual AnalysisPage SSR loading/error/current boundary (View replaced), no effects or browser');
