"""Complete versioned HFACS backup; restored receipts are inert history."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
import uuid
from types import SimpleNamespace
from sqlalchemy import select
from ..common.context import problem
from ..db import list_docs,get_doc
from ..evidence.models import EvidenceRow
from ..redaction.policy import default_policy
from ..redaction.models import AccessPolicyRow
from .models import HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow,HfacsArchivedRequestRow
from . import router as hf

PATH='hfacs/backup.v1.json'
MAX_REVISIONS=256
MAX_RECEIPTS=256
DOC_KEYS={'caseId','revision','digest','draft','sources','classification','status','strength','origin','savedBy','savedRole','savedUtc'}
EVENT_KEYS={'caseId','revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','before','after','prevHash','hash'}
RECEIPT_KEYS={'case_id','request_id','request_digest','operator','response'}


def bad(message='HFACS备份结构、版本、来源或完整性无效'):
    raise problem(422,'HFACS_ARCHIVE_INVALID',message)


def exact(value,keys):
    if not isinstance(value,dict) or set(value)!=keys: bad()


def digest(value): return hashlib.sha256(hf.canonical(value)).hexdigest()


def hexhash(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-f0-9]{64}',value): bad()


def request_id(value):
    if not isinstance(value,str): bad()
    try: normalized=str(uuid.UUID(value))
    except ValueError: bad()
    if value!=normalized: bad()


def stamp(value):
    if not isinstance(value,str) or not value.endswith('Z'): bad()
    try: datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: bad()


@dataclass(frozen=True)
class ValidatedArchive:
    data: dict
    raw: bytes

    @property
    def summary(self):
        return {'version':'MCIS-HFACS-PACKAGE-1','draftCount':int(self.data['currentDocument'] is not None),
                'revisionCount':len(self.data['revisionAudit']),'receiptCount':len(self.data['requestReceipts']),
                'receiptMode':'archive-only','identityMode':'unverified-self-reported'}


def validate(raw,case_id,evidence_ids):
    if len(raw)>16*1024*1024: bad('HFACS成员超过16 MiB工程上限；不会截断历史')
    if raw.startswith(b'\xef\xbb\xbf'): bad()
    try: data=hf.strict_json(raw)
    except hf.PreviewError: bad()
    exact(data,{'format','version','caseId','receiptPolicy','currentDocument','revisionAudit','requestReceipts'})
    if data['format']!='MCIS-HFACS-BACKUP' or type(data['version']) is not int or data['version']!=1 or data['caseId']!=case_id or data['receiptPolicy']!='archive-only-on-import': bad()
    events,receipts=data['revisionAudit'],data['requestReceipts']
    if not isinstance(events,list) or not isinstance(receipts,list): bad()
    if len(events)>MAX_REVISIONS or len(receipts)>MAX_RECEIPTS: bad('HFACS备份超过256个完整修订/回执工程上限；不会截断历史')
    if len(events)!=len(receipts): bad()
    cache={}
    def document(doc,revision):
        exact(doc,DOC_KEYS)
        if doc['caseId']!=case_id or type(doc['revision']) is not int or doc['revision']!=revision: bad()
        if doc['status']!='Draft' or doc['strength']!='ToBeVerified' or doc['origin']!='Investigator' or doc['savedRole'] not in ('Investigator','LeadInvestigator') or not isinstance(doc['savedBy'],str) or not doc['savedBy']: bad()
        stamp(doc['savedUtc']);hexhash(doc['digest'])
        try: _,sources=hf.validate_body({'requestId':'00000000-0000-0000-0000-000000000001','expectedDigest':None,'draft':doc['draft'],'expectedSources':doc['sources']})
        except hf.PreviewError: bad()
        if sources!=doc['sources'] or any(s['evidenceId'] not in evidence_ids for s in sources): bad()
        if digest({k:doc[k] for k in ('caseId','revision','draft','sources','classification')})!=doc['digest']: bad()
        classification=doc['classification']
        if not isinstance(classification,dict) or classification.get('coreVersion')!='mcis-hfacs/1' or classification.get('taxonomyVersion')!=hf.TAXONOMY: bad()
        key=digest(doc['draft'])
        if key not in cache:
            try: cache[key]=hf.run_core({'action':'validate','draft':doc['draft']})
            except hf.PreviewError as exc: raise problem(exc.status,'HFACS_ARCHIVE_CORE',exc.message)
        if hf.canonical(classification)!=hf.canonical(cache[key]): bad()
    previous=None;prev_hash='0'*64;by_request={}
    for index,event in enumerate(events,1):
        exact(event,EVENT_KEYS)
        if event['caseId']!=case_id or type(event['revision']) is not int or event['revision']!=index or event['action']!='hfacs.draft.save': bad()
        request_id(event['requestId'])
        if event['requestId'] in by_request: bad()
        document(event['after'],index)
        if hf.canonical(event['before'])!=hf.canonical(previous) or event['beforeDigest']!=(previous['digest'] if previous else None) or event['afterDigest']!=event['after']['digest']: bad()
        if any(event[k]!=event['after'][v] for k,v in (('operator','savedBy'),('role','savedRole'),('utc','savedUtc'))): bad()
        hexhash(event['hash'])
        if event['prevHash']!=prev_hash or event['hash']!=digest({k:v for k,v in event.items() if k!='hash'}): bad()
        previous=event['after'];prev_hash=event['hash'];by_request[event['requestId']]=event
    if hf.canonical(data['currentDocument'])!=hf.canonical(previous): bad()
    seen=set();order=[]
    for receipt in receipts:
        exact(receipt,RECEIPT_KEYS);request_id(receipt['request_id']);hexhash(receipt['request_digest'])
        rid=receipt['request_id'];order.append(rid)
        if receipt['case_id']!=case_id or rid in seen or rid not in by_request: bad()
        seen.add(rid);event=by_request[rid]
        if receipt['operator']!=event['operator'] or hf.canonical(receipt['response'])!=hf.canonical(hf.response_doc(case_id,event['after'],'unchanged')): bad()
    if order!=sorted(order): bad()
    return ValidatedArchive(data,raw)


def build(session,case_id,role):
    current=session.get(HfacsWorksheetRow,case_id)
    events=[r.doc for r in session.scalars(select(HfacsAuditRow).where(HfacsAuditRow.case_id==case_id).order_by(HfacsAuditRow.revision))]
    receipts=[]
    for model in (HfacsRequestRow,HfacsArchivedRequestRow):
        for row in session.scalars(select(model).where(model.case_id==case_id)):
            receipts.append({key:getattr(row,key) for key in RECEIPT_KEYS})
    if current is None and not events and not receipts: return None
    ctx=SimpleNamespace(role=role)
    hf.snapshot(session,ctx,case_id,[],audit=True)
    documents=([current.doc] if current else [])+[e.get(k) for e in events for k in ('before','after')]+[r['response'].get('document') for r in receipts]
    for doc in documents:
        if doc is not None: hf.check_document_sources(session,ctx,case_id,doc,audit=True)
    saved=get_doc(session,AccessPolicyRow,case_id,'policy')
    if saved is not None and saved!=default_policy(): raise problem(422,'HFACS_ARCHIVE_POLICY','HFACS受限恢复只支持默认权限；不会导出不可恢复的策略')
    data={'format':'MCIS-HFACS-BACKUP','version':1,'caseId':case_id,'receiptPolicy':'archive-only-on-import',
          'currentDocument':current.doc if current else None,'revisionAudit':events,'requestReceipts':sorted(receipts,key=lambda r:r['request_id'])}
    return validate(hf.canonical(data),case_id,{d['evidenceId'] for d in list_docs(session,EvidenceRow,case_id)})


def restore(session,archive):
    data=archive.data;case_id=data['caseId']
    if any(session.scalars(select(model).where(model.case_id==case_id).limit(1)).first() is not None for model in (HfacsWorksheetRow,HfacsAuditRow,HfacsRequestRow,HfacsArchivedRequestRow)): bad('HFACS恢复不覆盖已有记录')
    if data['currentDocument'] is not None: session.add(HfacsWorksheetRow(case_id=case_id,doc=data['currentDocument']))
    for event in data['revisionAudit']: session.add(HfacsAuditRow(case_id=case_id,revision=event['revision'],doc=event))
    for receipt in data['requestReceipts']: session.add(HfacsArchivedRequestRow(**receipt))
    session.flush()
