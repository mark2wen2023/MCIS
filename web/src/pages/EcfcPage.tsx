import {useRef,useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {CASE_ID,onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {EcfcPanel} from '../ecfcDrafts/Panel'
export function EcfcPage(){const heading=useRef<HTMLHeadingElement|null>(null);const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID;return <><Link to="/lobby">返回案件大厅</Link><h1 ref={heading} tabIndex={-1}>ECFC 事件与条件草稿</h1><EcfcPanel key={JSON.stringify([caseId,who])} focusTarget={heading} caseId={caseId} who={who}/></>}
