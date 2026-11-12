import {createRoot} from 'react-dom/client'
import {useState} from 'react'
import {TrackInputPanel} from '../src/trackInput/TrackInputPanel'
import {caseIdentity} from '../src/cases/identity'
import {setIdentity} from '../src/api'
function App(){const [caseId,setCase]=useState('A'),[who,setWho]=useState(caseIdentity);return <><button onClick={()=>setCase('B')}>Switch case</button><button onClick={()=>{setIdentity('Investigator','Other');setWho(caseIdentity())}}>Switch identity</button><TrackInputPanel key={caseId+who} who={who} snapshot={{case:{caseId,title:'Synthetic',isFictionalDemo:true,caseEpochUtc:'2026-01-01T00:00:00Z'},vessels:[{vesselId:'V',name:'Synthetic vessel'}],tracks:[]}}/></>}
createRoot(document.getElementById('root')!).render(<App/>);
