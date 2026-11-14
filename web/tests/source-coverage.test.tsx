import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {SourceCoverage} from '../src/align/SourceCoverage'
import type {RegisteredResult} from '../src/align/registered'
const value=(ids:string[],parents:any[]=[])=>({sourceSnapshots:ids.map(evidenceId=>({evidenceId})),reportSnapshots:parents}) as RegisteredResult
const p=(extractEvidenceId:string,evidenceId:string)=>({extractEvidenceId,evidenceId})
let n=0;const check=(f:()=>void)=>{f();n++};const render=(v:RegisteredResult)=>renderToStaticMarkup(<SourceCoverage value={v}/>);
let s=render(value(['EV-001']));check(()=>assert(s.includes('只有一份登记来源')));check(()=>assert(s.includes('不能完成跨来源比对')));check(()=>assert(s.includes('不能据此认为两份证据一致')));
s=render(value(['EV-001','EV-002']));check(()=>assert(!s.includes('只有一份登记来源')));check(()=>assert(s.includes('文件数量不等于独立证据数量')));check(()=>assert(s.includes('不代表来源相互独立')));
s=render(value(['EV-001','EV-002'],[p('EV-001','EV-003'),p('EV-002','EV-003')]));check(()=>assert(s.includes('共享报告来源')));check(()=>assert(s.includes('EV-001、EV-002')));check(()=>assert(s.includes('未经核实的人工声明')));
s=render(value(['EV-001','EV-002'],[p('EV-001','EV-003'),p('EV-002','EV-004')]));check(()=>assert(!s.includes('共享报告来源')));check(()=>assert(s.includes('关联不同文件，也不代表来源相互独立')));
console.log(n+' source coverage static-render assertions passed; not browser or backend');
