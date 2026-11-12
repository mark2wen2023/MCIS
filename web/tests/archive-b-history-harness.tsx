// Synthetic isolated component browser harness; not an application route.
import {useState,useSyncExternalStore} from 'react'
import {createRoot} from 'react-dom/client'
import {EvidenceIntakePanel} from '../src/evidenceIntake/EvidenceIntakePanel'
import {caseIdentity} from '../src/cases/identity'
import {onIdentityChange,setIdentity} from '../src/api'
function Harness(){const who=useSyncExternalStore(onIdentityChange,caseIdentity),[caseId,setCase]=useState('SYNTHETIC-A');return <><button onClick={()=>setCase('SYNTHETIC-B')}>Switch synthetic case</button><button onClick={()=>setIdentity('Investigator','different')}>Switch synthetic identity</button><EvidenceIntakePanel key={caseId+who} caseId={caseId} who={who} selectedEvidenceId="EV-001"/></>}
createRoot(document.getElementById('root')!).render(<Harness/>);
