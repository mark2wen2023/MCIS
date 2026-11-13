"""Runnable in-process nonproduction investigator client; trusted host only.

No CLI, login, network URL, browser storage, legacy app or token printing.
Host supplies an existing DB/settings and a pre-provisioned local session.
"""
import asyncio
import json
import re
import uuid
import httpx
from .http_trial import create_identity_trial_app
from ..timeline.evidence_preview import RegisteredPreview
from ..timeline.unreviewed_storage import selection_snapshot


class TrialClientError(Exception):
    def __init__(self,status):
        self.status=status
        super().__init__('试验请求未完成；请核对当前权限和来源版本')


class InvestigatorTrialClient:
    def __init__(self,*,db,settings,session_token):
        self.__closed=False
        self.__token=session_token
        self.__http=httpx.AsyncClient(transport=httpx.ASGITransport(app=create_identity_trial_app(db=db,settings=settings)),
            base_url='http://mcis-trial.invalid',follow_redirects=False,trust_env=False)
        self.__selection=None
        self.__case=None
        self.__request=None
        self.__operation=None
        self.__run=None
        self.phase='unselected'

    async def __aenter__(self):return self
    async def __aexit__(self,*_):
        self.__closed=True;self.__token=None
        self.__selection=None;self.__request=None;self.__case=None;self.__operation=None;self.__run=None
        self.phase='closed'
        await self.__http.aclose()

    def _ensure_open(self):
        if self.__closed:raise TrialClientError(409)

    def clear(self):
        self._ensure_open()
        if self.phase in ('closed','selecting','saving','reading'):raise TrialClientError(409)
        self.__selection=None;self.__request=None;self.__case=None
        self.__operation=None;self.__run=None;self.phase='unselected'

    @property
    def receipt(self):
        return {'phase':self.phase,'runId':self.__run,'operationId':self.__operation,
                'status':'unreviewed' if self.__run else None}

    async def _call(self,method,path,body=None):
        self._ensure_open()
        try:
            r=await self.__http.request(method,path,headers={'Authorization':'Bearer '+self.__token},json=body)
            self._ensure_open()
            if r.status_code!=200:raise TrialClientError(r.status_code)
            return r.json()
        except TrialClientError:raise
        except Exception:raise TrialClientError(503) from None

    async def cases(self):return await self._call('GET','/api/v1/trial/cases')

    async def sources(self,case_id):
        if not isinstance(case_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',case_id):raise TrialClientError(422)
        return await self._call('GET','/api/v1/trial/cases/'+case_id+'/sources')

    def _pins(self,catalog,body):
        rows={x['evidenceId']:x for x in catalog['items']}
        selected=set()
        for source in body['sources']:
            eid=source['evidenceId']
            if eid not in rows or rows[eid]['mediaKind']!='csv':raise TrialClientError(409)
            selected.add(eid)
            parent=source.get('parentReport')
            if parent:
                pid=parent['evidenceId']
                if pid not in rows or rows[pid]['mediaKind']!='pdf' or rows[pid]['sourceSha256']!=parent['sourceSha256']:raise TrialClientError(409)
                selected.add(pid)
        return {'caseId':catalog['caseId'],'caseIncarnation':catalog['caseIncarnation'],
            'caseEpochUtc':catalog['caseEpochUtc'],'sources':[
                {k:rows[eid][k] for k in ('evidenceId','sourceSha256','registrationDigest','sourceIncarnation')}
                for eid in sorted(selected)]}

    async def select(self,case_id,request):
        # Retain no caller-owned mutable request. Clear old result/operation first.
        if self.phase in ('closed','selecting','saving','reading'):raise TrialClientError(409)
        self.clear()
        try:body=RegisteredPreview.model_validate(request).model_dump(mode='json')
        except Exception:raise TrialClientError(422) from None
        self.phase='selecting'
        try:
            catalog=await self.sources(case_id)
            self._ensure_open()
            pins=self._pins(catalog,body)
        except BaseException:
            if not self.__closed:self.phase='unselected'
            raise
        self.__case=case_id;self.__request=json.dumps(body);self.__selection=json.dumps(pins)
        self.__operation=str(uuid.uuid4());self.phase='selected'
        return {'caseId':case_id,'operationId':self.__operation,'selection':json.loads(self.__selection)}

    async def execute(self):
        if self.phase not in ('selected','outcome-unknown'):raise TrialClientError(409)
        self.phase='saving'
        try:
            # UI refresh is not atomic. Server checks these pins within its initial
            # authorization transaction, then ordinary final-source capture protects
            # changes during computation. Client read check is defense in depth.
            result=await self._call('POST','/api/v1/cases/'+self.__case+'/timeline/unreviewed-runs',
                {'operationId':self.__operation,'request':json.loads(self.__request),
                 'expectedSelection':json.loads(self.__selection)})
            self._ensure_open()
            if result.get('saved') is not True or result.get('status')!='unreviewed':raise TrialClientError(503)
            run=result['runId']
            if str(uuid.UUID(run))!=run:raise TrialClientError(503)
            self.__run=run;self.phase='saved'
        except TrialClientError as error:
            if not self.__closed:self.phase='outcome-unknown' if error.status>=500 else 'rejected'
            raise
        except asyncio.CancelledError:
            if not self.__closed:self.phase='outcome-unknown'
            raise
        except Exception:
            if not self.__closed:self.phase='outcome-unknown'
            raise TrialClientError(503) from None
        return await self.read()

    async def read(self):
        if self.__run is None or self.phase not in ('saved','read','read-denied'):raise TrialClientError(409)
        self.phase='reading'
        try:
            value=await self._call('GET','/api/v1/cases/'+self.__case+'/timeline/unreviewed-runs/'+self.__run)
            self._ensure_open()
            if (value.get('runId')!=self.__run or value.get('caseId')!=self.__case
                    or value.get('status')!='unreviewed' or value.get('observationApproval')!='not_assessed'
                    or value.get('usableAsWriteCredential') is not False
                    or value.get('request')!=json.loads(self.__request)
                    or selection_snapshot(value['generationSnapshot'])!=json.loads(self.__selection)):
                raise TrialClientError(409)
            self.phase='read'
            return value
        except asyncio.CancelledError:
            if not self.__closed:self.phase='read-denied'
            raise
        except Exception as error:
            if not self.__closed:self.phase='read-denied'
            if isinstance(error,TrialClientError):raise
            raise TrialClientError(503) from None
