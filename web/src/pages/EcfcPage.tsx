import {useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {CASE_ID,onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {EcfcPanel} from '../ecfcDrafts/Panel'
export function EcfcPage(){const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID;return <><Link to="/lobby">返回案件大厅</Link><EcfcPanel key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/></>}
