import assert from 'node:assert/strict'
import { renderToStaticMarkup as render } from 'react-dom/server'
// Test-only storage prerequisite; no identity or request is exercised.
Object.defineProperty(globalThis, 'localStorage', {value: {getItem: () => null}})
globalThis.fetch = async () => { throw Error('Network forbidden in SSR test') }
const { ConflictPanel } = require('../src/pages/EvidencePage') as typeof import('../src/pages/EvidencePage')
import { ConflictMetric, ConflictReadNotice, conflictReadState, timedConflicts } from '../src/evidenceIntake/ConflictReadState'
import type { Conflict } from '../src/types'
const row: Conflict = {conflictId:'SYN-C',summary:'合成差异',trackKind:'synthetic',timeSec:null,a:{sourceLabel:'合成甲',valueText:'甲'},b:{sourceLabel:'合成乙',valueText:'乙'},deltaUnit:'s',status:'Open',resolution:'',detectedBy:'fixture'}
let checks = 0
function check(ok: unknown) { assert.ok(ok); checks++ }
const panel = (state: ReturnType<typeof conflictReadState>) => render(<ConflictPanel caseId="SYN" state={state} offsetMinutes={0} onChanged={()=>{throw Error('no writes')}}/>)
for (const [data,error,label] of [[null,null,'待载入'],[null,'DENIED-PRIVATE','不可用'],[[row],'','不可用']] as const) {
  const state = conflictReadState(data === null ? null : [...data],error)
  const metric = render(<ConflictMetric state={state}/> )
  const table = panel(state)
  const notice = render(<ConflictReadNotice state={state}/> )
  check(metric.includes(label) && !metric.includes('green') && !metric.includes('<small>'))
  check(table.includes(label) && !table.includes('>无冲突<') && !table.includes('合成差异') && !table.includes('<select'))
  check(notice.includes(label) && !notice.includes('DENIED-PRIVATE'))
}
const empty = conflictReadState([],null)
check(render(<ConflictMetric state={empty}/>).includes('0<small>/ 0</small>'))
check(panel(empty).includes('无冲突'))
check(render(<ConflictReadNotice state={empty}/>) === '')
const rows: Conflict[] = [row,{...row,conflictId:'SYN-ZERO',timeSec:0,status:'Resolved'}]
const populated = conflictReadState(rows,null)
check(render(<ConflictMetric state={populated}/>).includes('1<small>/ 2</small>'))
const table = panel(populated)
check(table.includes('合成差异') && table.includes('待处理') && table.includes('已解决') && !table.includes('>无冲突<'))
check(timedConflicts(rows).length === 1 && timedConflicts(rows)[0].timeSec === 0)
check(conflictReadState(rows,null).kind === 'success')
console.log(`PASS ${checks} synthetic assertions: actual conflict table/metric/notice SSR and chart time filter; no mounted effects or browser`)
