// Isolated synthetic browser harness, not an application route.
import {useState} from 'react'
import {createRoot} from 'react-dom/client'
import {ArchiveProvenance} from '../src/archiveProvenance/Provenance'
import {setIdentity} from '../src/api'
function Harness(){const [caseId,setCase]=useState('SYNTHETIC-A'),[id,setId]=useState('IR-01'),[revision,setRevision]=useState({}),[denied,setDenied]=useState(false);return <><button onClick={()=>setCase('SYNTHETIC-B')}>Switch case</button><button onClick={()=>setId('IR-02')}>Switch record</button><button onClick={()=>setIdentity('Investigator','different')}>Switch identity</button><button onClick={()=>setRevision({})}>Advance content revision</button>{denied?<p>Parent protected content cleared</p>:<><p>PROTECTED-PARENT-TEXT</p><ArchiveProvenance revision={revision} onDenied={()=>setDenied(true)} caseId={caseId} kind="interview" recordId={id}/></>}</>}
createRoot(document.getElementById('root')!).render(<Harness/>);
