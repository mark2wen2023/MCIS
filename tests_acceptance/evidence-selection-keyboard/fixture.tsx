/** Synthetic component fixture only; no app/router/API imports. */
import {useState} from 'react'
import {createRoot} from 'react-dom/client'
import {EvidenceSelectionButton} from '../../web/src/evidenceIntake/EvidenceSelectionButton'
function Fixture(){
  const [selected,setSelected]=useState('SYN-E-A')
  const [calls,setCalls]=useState(0)
  const [bubbled,setBubbled]=useState(0)
  return <main><h1>合成证据选择 · 组件键盘验收</h1><p>不连接业务服务，不读取原件。</p>
    <button type="button">开始定位</button>
    <div onClick={()=>setBubbled(n=>n+1)}>
      {['SYN-E-A','SYN-E-B'].map(id=><EvidenceSelectionButton key={id} evidenceId={id} title="同名合成记录" selected={selected===id} onSelect={value=>{setSelected(value);setCalls(n=>n+1)}}/>)}
    </div>
    <button type="button">结束定位</button>
    <output data-testid="calls">{calls}</output><output data-testid="bubbled">{bubbled}</output>
  </main>
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
