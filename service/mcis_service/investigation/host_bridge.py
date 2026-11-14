"""Trusted-host-only in-process bridge. No URL, browser token or legacy app."""
import uuid
from typing import Literal
import httpx
from pydantic import BaseModel,ConfigDict,Field
from ..identity.http_trial import create_identity_trial_app
from .journal import Entry,SourcePin,canonical_id,auth,load_case

PROFILE='mcis-issue-host-trial-v1'
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    profile:Literal['mcis-issue-host-trial-v1']
    contextId:str
    requestId:str
    action:Literal['save','read','sources']
    caseId:str
    issueId:str|None=None
    operationId:str|None=None
    expectedRevision:int|None=Field(default=None,ge=0,lt=200)
    entry:Entry|None=None
    sourcePins:list[SourcePin]|None=Field(default=None,max_length=20)

class SourceItem(BaseModel):
    model_config=ConfigDict(extra='ignore',strict=True)
    evidenceId:str=Field(min_length=1,max_length=64)
    sourceSha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    sourceIncarnation:str
    mediaKind:Literal['csv','pdf']
    byteLength:int=Field(ge=0)
    registeredUtc:str

class IssueHostClient:
    def __init__(self,*,db,settings,session_token,case_id):
        import re
        if not isinstance(case_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',case_id):raise ValueError('case scope required')
        with db.session() as s:
            _,generation=auth(s,session_token,case_id)
            self.__epoch=load_case(s,case_id)['caseEpochUtc']
        self.__db=db;self.__generation=generation
        self.__case=case_id;self.__context=str(uuid.uuid4());self.__token=session_token;self.__closed=False
        self.__http=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_identity_trial_app(db=db,settings=settings)),base_url='http://mcis-host.invalid',follow_redirects=False,trust_env=False)
    @property
    def scope(self):return {'profile':PROFILE,'contextId':self.__context,'caseId':self.__case,'productionLogin':False}
    async def __aenter__(self):return self
    async def __aexit__(self,*_):
        self.__closed=True;self.__token=None
        await self.__http.aclose()
    def _check_scope(self):
        if self.__closed:raise ValueError()
        with self.__db.session() as s:
            _,generation=auth(s,self.__token,self.__case)
            if generation!=self.__generation or load_case(s,self.__case)['caseEpochUtc']!=self.__epoch:raise ValueError()
    async def dispatch(self,value):
        request_id=None
        try:
            req=Request.model_validate(value);canonical_id(req.requestId);request_id=req.requestId
            if req.action=='sources':
                if req.model_fields_set & {'issueId','operationId','expectedRevision','entry','sourcePins'}:raise ValueError()
            else:canonical_id(req.issueId)
            if self.__closed or req.contextId!=self.__context or req.caseId!=self.__case:raise ValueError()
            self._check_scope()
            path=f'/api/v1/trial/cases/{self.__case}/issues'
            if req.action=='sources':
                response=await self.__http.get(f'/api/v1/trial/cases/{self.__case}/sources',headers={'Authorization':'Bearer '+self.__token})
            elif req.action=='save':
                canonical_id(req.operationId)
                if req.entry is None or req.expectedRevision is None:raise ValueError()
                if req.entry.sourceIds and req.sourcePins is None:raise ValueError()
                body={'operationId':req.operationId,'entry':req.entry.model_dump()}
                if req.sourcePins is not None:body['sourcePins']=[p.model_dump() for p in req.sourcePins]
                if req.expectedRevision==0:body['issueId']=req.issueId
                else:path+='/'+req.issueId+'/events';body['expectedRevision']=req.expectedRevision
                response=await self.__http.post(path,headers={'Authorization':'Bearer '+self.__token},json=body)
            else:
                if req.operationId is not None or req.entry is not None or req.expectedRevision is not None or 'sourcePins' in req.model_fields_set:raise ValueError()
                response=await self.__http.get(path+'/'+req.issueId,headers={'Authorization':'Bearer '+self.__token})
            self._check_scope()
            if response.status_code not in (200,201):
                code='ISSUE_HOST_REJECTED'
                if response.status_code==409 and response.json().get('code')=='SOURCE_SELECTION_CHANGED':code='ISSUE_SOURCE_SELECTION_CHANGED'
                return {**self.scope,'requestId':request_id,'ok':False,'code':code,'status':response.status_code}
            raw=response.json()
            if req.action=='sources':
                if (response.status_code!=200 or raw.get('profile')!='trial-current-sources-v1'
                    or raw.get('caseId')!=self.__case or raw.get('caseIncarnation')!=self.__generation
                    or raw.get('caseEpochUtc')!=self.__epoch
                    or raw.get('scope')!='current-local-supported-candidates-only'):raise ValueError()
                items=raw.get('items')
                if not isinstance(items,list) or len(items)>100:raise ValueError()
                projected=[SourceItem.model_validate(item).model_dump() for item in items]
                if len({x['evidenceId'] for x in projected})!=len(projected):raise ValueError()
                from datetime import datetime
                for item in projected:
                    canonical_id(item['sourceIncarnation'])
                    if datetime.fromisoformat(item['registeredUtc'].replace('Z','+00:00')).utcoffset() is None:raise ValueError()
                body={'profile':'trial-issue-sources-v1','caseId':self.__case,'items':projected,'scope':'current-local-supported-candidates-only',
                    'selectionSnapshotPinned':False,'observationApproval':'not_assessed'}
                return {**self.scope,'requestId':request_id,'ok':True,'body':body}
            if raw['caseId']!=self.__case or raw['issueId']!=req.issueId or raw['status']!='working_unreviewed':raise ValueError()
            # Only the UI's fields; no identity table, raw source bytes or author IDs.
            fields=('kind','note','sourceIds','outcome','againstJudgment','seq','recordedUtc','status')
            body={'caseId':raw['caseId'],'issueId':raw['issueId'],'revision':raw['revision'],'status':raw['status'],
                  'events':[{k:e[k] for k in fields} for e in raw['events']]}
            return {**self.scope,'requestId':request_id,'ok':True,'body':body}
        except Exception:
            return {**self.scope,'requestId':request_id,'ok':False,'code':'ISSUE_HOST_UNCONFIRMED','status':503}
