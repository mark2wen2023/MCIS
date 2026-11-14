"""Fixed-scope trusted-host RPC adapter. No credentials, provider or paths in RPC."""
import asyncio
import copy
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from starlette.concurrency import run_in_threadpool
from .persistent_extraction_review_host import PersistentExtractionReviewHost,PROFILE
from .extraction_review_host import Decision,bounded
from .extraction import digest
from ..investigation.journal import canonical_id

class Request(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    profile:Literal['mcis-extraction-review-persistent-trial-v1']
    contextId:str
    caseId:str
    recordId:str
    requestId:str
    action:Literal['generate','list','read','review']
    operationId:str|None=None
    proposalId:str|None=None
    expectedRevision:int|None=Field(default=None,ge=0,lt=100)
    decisions:list[Decision]|None=Field(default=None,max_length=20)

class PersistentExtractionRPC:
    def __init__(self,host):
        if type(host) is not PersistentExtractionReviewHost:raise ValueError('trusted fixed host required')
        self.__host=host;self.__scope=host.scope;self.__closed=False;self.__busy=False;self.__seen={}
    @property
    def scope(self):return dict(self.__scope)
    def close(self):
        self.__closed=True;self.__seen.clear();self.__host.close()
    async def __aenter__(self):
        if self.__closed:raise ValueError('closed')
        return self
    async def __aexit__(self,*args):self.close()
    async def dispatch(self,value):
        rid=None;acquired=False;write_started=False
        try:
            req=Request.model_validate(bounded(value,65536));canonical_id(req.requestId);rid=req.requestId
            if self.__closed or self.__busy or any(getattr(req,k)!=self.scope[k] for k in ('contextId','caseId','recordId')):raise ValueError()
            allowed={'generate':{'operationId'},'list':set(),'read':{'proposalId'},'review':{'operationId','proposalId','expectedRevision','decisions'}}[req.action]
            supplied=req.model_fields_set & {'operationId','proposalId','expectedRevision','decisions'}
            if supplied!=allowed:raise ValueError()
            if req.action in ('generate','review'):canonical_id(req.operationId)
            if req.action in ('read','review'):canonical_id(req.proposalId)
            if req.action=='review' and (req.decisions is None or req.expectedRevision is None):raise ValueError()
            fingerprint=digest(req.model_dump())
            if rid in self.__seen and self.__seen[rid]!=fingerprint:raise ValueError()
            if rid not in self.__seen and len(self.__seen)>=128:raise ValueError()
            self.__seen[rid]=fingerprint;self.__busy=True;acquired=True
            write_started=req.action in ('generate','review')
            if req.action=='generate':result=await run_in_threadpool(self.__host.generate,req.operationId)
            elif req.action=='list':result=await run_in_threadpool(self.__host.list)
            elif req.action=='read':result=await run_in_threadpool(self.__host.read,req.proposalId)
            else:result=await run_in_threadpool(self.__host.review,req.proposalId,req.operationId,req.expectedRevision,[d.model_dump() for d in req.decisions])
            if self.__closed:raise ValueError()
            self.__host._check()
            if 'proposal' in result:
                body={k:copy.deepcopy(result[k]) for k in ('proposalId','recordId','revision','status','saved','persistence','factActivated')}
                if 'replayed' in result:body['replayed']=result['replayed']
                p=result['proposal'];body['proposal']={k:copy.deepcopy(p[k]) for k in ('result','bindingDigest','storedUtc')}
                body['reviews']=[{**{k:copy.deepcopy(e[k]) for k in ('revision','recordedUtc','decisions','reviewedAsWorkingOnly','factVerified')},'authorRef':e['authorSubjectId'],**({'reviewOrigin':e['reviewOrigin']} if 'reviewOrigin' in e else {})} for e in result['reviews']]
            elif req.action=='list':
                body={k:result[k] for k in ('caseId','persistence','factActivated')}
                body['items']=[{k:e[k] for k in ('proposalId','recordId','revision','status')} for e in result['items']]
            else:
                body={k:result[k] for k in ('status','inferencePerformed','proposals','sourceScope')}
            return bounded({**self.scope,'requestId':rid,'ok':True,'body':body},4*1024*1024+1024)
        except asyncio.CancelledError:raise
        except HTTPException as e:
            status=e.status_code if e.status_code in (403,404,409,413,422) else 503
            return {**self.scope,'requestId':rid,'ok':False,'code':'WORKING_RPC_REJECTED' if status!=503 else 'WORKING_RPC_UNCONFIRMED','status':status}
        except ValueError:
            return {**self.scope,'requestId':rid,'ok':False,'code':'WORKING_RPC_UNCONFIRMED' if write_started else 'WORKING_RPC_REJECTED','status':503 if write_started else 409}
        except Exception:
            return {**self.scope,'requestId':rid,'ok':False,'code':'WORKING_RPC_UNCONFIRMED','status':503}
        finally:
            if acquired:self.__busy=False
