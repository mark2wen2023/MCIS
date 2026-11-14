"""Ephemeral trusted-host review; decisions never activate statements or facts."""
import asyncio
import copy
import json
import uuid
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from starlette.concurrency import run_in_threadpool
from . import host_extraction as h,extraction
from ..investigation.journal import canonical_id

PROFILE='mcis-extraction-review-trial-v1'
MAX_REQUEST=65536
MAX_RESPONSE=512*1024
class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    index:int=Field(ge=1,le=20)
    decision:Literal['adopted_working','rejected','needs_verification']
    note:str=Field(min_length=1,max_length=1000)
    @field_validator('note')
    @classmethod
    def nonblank(cls,v):
        if not v.strip() or '\x00' in v:raise ValueError()
        return v
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    profile:Literal['mcis-extraction-review-trial-v1']
    contextId:str
    caseId:str
    recordId:str
    requestId:str
    action:Literal['generate','review']
    proposalId:str|None=None
    decisions:list[Decision]|None=Field(default=None,max_length=20)


def bounded(value,limit):
    encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    if len(encoded)>limit:raise ValueError()
    return copy.deepcopy(value)

class ExtractionReviewHost:
    def __init__(self,*,db,settings,session_token,case_id,record_id,provider=None):
        if provider is not None and type(provider) not in (h.FixtureProvider,h.LocalProvider):raise ValueError('explicit provider required')
        binding=h.describe(db,settings,session_token,case_id,record_id)['bindingDigest']
        self.__args=(db,settings,session_token,case_id,record_id)
        self.__binding=binding;self.__provider=provider
        self.__context=str(uuid.uuid4());self.__case=case_id;self.__record=record_id
        self.__closed=False;self.__busy=False;self.__active=None;self.__seen={};self.__cache={}
    @property
    def scope(self):return {'profile':PROFILE,'contextId':self.__context,'caseId':self.__case,'recordId':self.__record,'productionLogin':False}
    def close(self):
        self.__closed=True;self.__active=None;self.__args=None;self.__provider=None;self.__seen.clear();self.__cache.clear()
    async def __aenter__(self):
        if self.__closed:raise ValueError('closed')
        return self
    async def __aexit__(self,*args):self.close()
    def _check(self):
        if self.__closed or self.__args is None:raise ValueError()
        if h.describe(*self.__args)['bindingDigest']!=self.__binding:raise ValueError()
    async def dispatch(self,value):
        request_id=None;acquired=False
        try:
            req=Request.model_validate(bounded(value,MAX_REQUEST));canonical_id(req.requestId);request_id=req.requestId
            if self.__closed or self.__busy or any(getattr(req,k)!=self.scope[k] for k in ('contextId','caseId','recordId')):raise ValueError()
            if req.action=='generate' and req.model_fields_set & {'proposalId','decisions'}:raise ValueError()
            if req.action=='review':
                canonical_id(req.proposalId)
                if req.decisions is None:raise ValueError()
            self.__busy=True;acquired=True
            self._check()
            digest=extraction.digest(req.model_dump())
            if request_id in self.__seen:
                if self.__seen[request_id]!=digest or request_id not in self.__cache:raise ValueError()
                if req.action=='generate' and self.__active is None and self.__cache[request_id]['body']['status']!='not_connected':raise ValueError()
                response=bounded(self.__cache[request_id],MAX_RESPONSE);self._check();return response
            if len(self.__seen)>=32:raise ValueError()
            self.__seen[request_id]=digest
            if req.action=='generate':
                self.__active=None;self.__cache.clear()
                args=self.__args;provider=self.__provider
                result=await run_in_threadpool(h.run,*args,self.__binding,provider)
                self._check()
                frozen=bounded(result,MAX_RESPONSE-4096)
                proposal_id=str(uuid.uuid4()) if frozen['status']=='PendingReview' else None
                response=bounded({**self.scope,'requestId':request_id,'ok':True,'body':{**frozen,'proposalId':proposal_id}},MAX_RESPONSE)
                if proposal_id:self.__active=(proposal_id,copy.deepcopy(frozen))
                self.__cache[request_id]=copy.deepcopy(response)
                return response
            if self.__active is None or self.__active[0]!=req.proposalId:raise ValueError()
            proposal_id,original=self.__active
            decisions=[x.model_dump() for x in req.decisions]
            indexes=[x['index'] for x in decisions]
            if len(set(indexes))!=len(indexes) or set(indexes)!=set(range(1,len(original['proposals'])+1)):raise ValueError()
            decisions.sort(key=lambda x:x['index'])
            receipt={**copy.deepcopy(original['receipt']),'reviewChecksum':extraction.digest({'proposalId':proposal_id,'originalChecksum':original['receipt']['runChecksum'],'decisions':decisions})}
            response=bounded({**self.scope,'requestId':request_id,'ok':True,'body':{'proposalId':proposal_id,'decisions':decisions,
                'reviewedAsWorkingOnly':True,'saved':False,'factVerified':False,'status':'ReviewedWorking','receipt':receipt}},MAX_RESPONSE)
            self._check();self.__active=None;self.__cache={request_id:copy.deepcopy(response)}
            return response
        except asyncio.CancelledError:
            self.__active=None
            raise
        except Exception:
            return {**self.scope,'requestId':request_id,'ok':False,'code':'EXTRACTION_REVIEW_REJECTED','status':409}
        finally:
            if acquired:self.__busy=False
