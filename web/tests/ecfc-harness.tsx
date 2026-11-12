import '../src/styles.css'
import {createRoot} from 'react-dom/client'
import {useState,useSyncExternalStore} from 'react'
import {EcfcPanel} from '../src/ecfcDrafts/Panel'
import {onIdentityChange,setIdentity} from '../src/api'
import {caseIdentity} from '../src/cases/identity'
function App(){const [caseId,setCase]=useState('SYNTHETIC-A'),[open,setOpen]=useState(true),who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity);return <><button onClick={()=>setCase(c=>c==='SYNTHETIC-A'?'SYNTHETIC-B':'SYNTHETIC-A')}>Switch case</button><button onClick={()=>setIdentity('Investigator','Other')}>Switch identity</button><button onClick={()=>setOpen(o=>!o)}>Close or reopen</button>{open&&<EcfcPanel key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>}</>}
createRoot(document.getElementById('root')!).render(<App/>);
