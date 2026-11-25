import React from 'react';
import {createRoot} from 'react-dom/client';
import {IssueWorkspace} from 'w3-fixed/IssueWorkspace';
import {createIssueHostPort} from 'w3-fixed/hostPort';
declare global {
 interface Window { w3Scope: any; w3Send: (m:unknown)=>Promise<unknown>; }
}
const info=window.w3Scope;
createRoot(document.getElementById('root')!).render(<IssueWorkspace caseId={info.scope.caseId} contextKey={info.scope.contextId}
 issueId={info.id} port={createIssueHostPort(info.scope,window.w3Send)}/>);
