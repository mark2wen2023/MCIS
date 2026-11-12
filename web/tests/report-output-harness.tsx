import {createRoot} from 'react-dom/client'
import {useState} from 'react'
import {ReportOutputPanel} from '../src/reportOutput/Panel'
import {identity} from '../src/reportOutput/api'
import {setIdentity} from '../src/api'
import {unzipStored} from '../src/reportOutput/zip'
import {fixtures} from './report-output-fixtures'
import type {Report} from '../src/reports/types'
const bytes=Uint8Array.from(atob(fixtures.pdf.zipBase64),c=>c.charCodeAt(0));const original=JSON.parse(new TextDecoder().decode(unzipStored(bytes,'pdf').get('report.json'))) as Report
function App(){const [report,setReport]=useState(original),[who,setWho]=useState(identity),[denied,setDenied]=useState(false);return <><button onClick={()=>setReport({...original,caseId:'OTHER'})}>Switch case</button><button onClick={()=>{setIdentity('Investigator','Other');setWho(identity())}}>Switch identity</button>{denied?<p>Parent protected text cleared</p>:<><p>PROTECTED-REPORT-TEXT</p><ReportOutputPanel report={report} who={who} onDenied={()=>setDenied(true)}/></>}</>}
createRoot(document.getElementById('root')!).render(<App/>);
