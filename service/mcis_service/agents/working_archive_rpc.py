"""Explicit trusted-host supplemental archive bridge, not a production IPC endpoint."""
import asyncio
import base64
import uuid
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool
from . import working_history_archive as a
from .extraction_review_host import bounded
from .extraction import digest
from ..investigation import journal as j

PROFILE='mcis-working-history-archive-trial-v1'
RPC_LIMIT=12*1024*1024
ENCODED_LIMIT=4*((a.MAX_BYTES+2)//3)
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    profile:Literal['mcis-working-history-archive-trial-v1']
    contextId:str
    caseId:str
    requestId:str
    action:Literal['export','import','list','read']
    bundleBase64:str|None=None
    sha256:str|None=None

class WorkingArchiveRPC:
    def __init__(self,*,db,settings,session_token,case_id):
        self.__args=(db,settings,session_token,case_id)
        self.__closed=False;self.__busy=False;self.__seen={}
        self.__binding=self._scope_check(initial=True)
        self.__scope={'profile':PROFILE,'contextId':str(uuid.uuid4()),'caseId':case_id,'productionLogin':False}
    @property
    def scope(self):return dict(self.__scope)
    def _scope_check(self,initial=False):
        if self.__closed:raise ValueError()
        db,_,token,case=self.__args
        with db.session() as s:
            before=j.auth(s,token,case)
            epoch=j.load_case(s,case)['caseEpochUtc']
            if j.auth(s,token,case)!=before:raise ValueError()
            result=(before,epoch)
        if not initial and result!=self.__binding:raise ValueError()
        return result
    def _permission(self,action):
        self._scope_check()
        if action!='export':
            db,_,token,case=self.__args
            with db.session() as s:a._auth(s,token,case,'import' if action=='import' else 'read')
        self._scope_check()
    def close(self):
        self.__closed=True;self.__args=None;self.__seen.clear()
    async def __aenter__(self):
        if self.__closed:raise ValueError()
        return self
    async def __aexit__(self,*args):self.close()
    async def dispatch(self,value):
        rid=None;acquired=False;write_started=False
        try:
            if type(value) is not dict or len(value)>7:raise ValueError()
            for key,item in value.items():
                if type(key) is not str or key not in Request.model_fields or type(item) is not str:raise ValueError()
                if len(item)>(ENCODED_LIMIT if key=='bundleBase64' else 200):raise ValueError()
            req=Request.model_validate(bounded(value,RPC_LIMIT));j.canonical_id(req.requestId);rid=req.requestId
            if self.__closed or self.__busy or any(getattr(req,k)!=self.scope[k] for k in ('caseId','contextId')):raise ValueError()
            allowed={'import':{'bundleBase64'},'read':{'sha256'},'export':set(),'list':set()}[req.action]
            if req.model_fields_set & {'bundleBase64','sha256'}!=allowed:raise ValueError()
            raw=None
            if req.action=='import':
                if not isinstance(req.bundleBase64,str) or len(req.bundleBase64)>ENCODED_LIMIT:raise ValueError()
                raw=base64.b64decode(req.bundleBase64,validate=True)
                if len(raw)>a.MAX_BYTES or base64.b64encode(raw).decode('ascii')!=req.bundleBase64:raise ValueError()
            if req.action=='read':a.hash_value(req.sha256)
            fingerprint=digest(req.model_dump())
            if rid in self.__seen and self.__seen[rid]!=fingerprint:raise ValueError()
            if rid not in self.__seen and len(self.__seen)>=64:raise ValueError()
            self.__seen[rid]=fingerprint;self.__busy=True;acquired=True
            self._permission(req.action)
            db,settings,token,case=self.__args
            if req.action=='export':
                exported=await run_in_threadpool(a.export_bundle,db,settings,token,case)
                if self.__closed:raise ValueError()
                # Revalidate live bindings after the worker. No stale bundle is cached.
                if a.export_bundle(db,settings,token,case)!=exported:raise ValueError()
                checksum,_=a.validate(exported)
                body={'encoding':'base64','bundleBase64':base64.b64encode(exported).decode('ascii'),'sha256':checksum,'format':a.FORMAT,'completeBackup':False}
            elif req.action=='import':
                write_started=True
                body=await run_in_threadpool(a.restore_bundle,db,token,case,raw)
            elif req.action=='read':body=await run_in_threadpool(a.read_imported,db,token,case,req.sha256)
            else:body=await run_in_threadpool(a.list_imported,db,token,case)
            response=bounded({**self.scope,'requestId':rid,'ok':True,'body':body},RPC_LIMIT)
            self._permission(req.action)
            # Export body materialization and terminal scope checks may themselves
            # span source changes. The last content operation revalidates every
            # live binding; never release the previously encoded stale bundle.
            if req.action=='export':
                if a.export_bundle(db,settings,token,case)!=exported:raise ValueError()
                if self.__closed:raise ValueError()
            return response
        except asyncio.CancelledError:raise
        except Exception as e:
            status=e.status_code if isinstance(e,HTTPException) and e.status_code in (403,404,409,413,422) else 409 if isinstance(e,ValueError) else 503
            if write_started:status=503
            return {**self.scope,'requestId':rid,'ok':False,'status':status,'code':'WORKING_ARCHIVE_RPC_UNCONFIRMED' if status==503 else 'WORKING_ARCHIVE_RPC_REJECTED'}
        finally:
            if acquired:self.__busy=False
