import assert from 'node:assert/strict';import {renderToStaticMarkup} from 'react-dom/server';import {SourceCoverage} from '../src/align/SourceCoverage';import type {RegisteredResult} from '../src/align/registered';
let n=0;const check=(f:()=>void)=>{f();n++};const p=(extractEvidenceId:string,evidenceId:string)=>({extractEvidenceId,evidenceId});
const render=(ids:string[],parents:any[])=>renderToStaticMarkup(<SourceCoverage value={{sourceSnapshots:ids.map(evidenceId=>({evidenceId})),reportSnapshots:parents} as RegisteredResult}/>);
let s=render(['EV-001','EV-002','EV-003','EV-004'],[p('EV-001','EV-010'),p('EV-002','EV-010'),p('EV-003','EV-020'),p('EV-004','EV-020')]);
check(()=>assert.equal((s.match(/共享报告来源/g)||[]).length,2));check(()=>assert(s.includes('EV-001、EV-002')));check(()=>assert(s.includes('EV-003、EV-004')));check(()=>assert(s.includes('未经核实的人工声明')));check(()=>assert(s.includes('实际导入情况和未校准提示')));
s=render(['EV-001','EV-002'],[p('EV-001','EV-010'),p('EV-001','EV-010')]);check(()=>assert(!s.includes('共享报告来源')));
s=render(['EV-001','EV-002','EV-003'],[p('EV-001','EV-010'),p('EV-002','EV-010')]);check(()=>assert.equal((s.match(/共享报告来源/g)||[]).length,1));check(()=>assert(s.includes('未关联父报告或关联不同文件')));
s=render(['EV-001','EV-002'],[p('<script>1</script>','EV-010'),p('EV-002','EV-010')]);check(()=>assert(!s.includes('<script>')));check(()=>assert(s.includes('&lt;script&gt;')));
console.log(n+' independent coverage grouping/render assertions passed');
