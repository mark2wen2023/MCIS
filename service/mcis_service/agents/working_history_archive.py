"""Supplemental untrusted working-history archive. Never restore live authority."""
import copy
import json
import re
from datetime import datetime
from types import SimpleNamespace
from sqlalchemy import Column,String,Boolean,JSON,select,text
from sqlalchemy.orm import DeclarativeBase
from . import extraction,extraction_working_store as w
from .extraction_review_host import Decision
from ..investigation import journal as j
from ..redaction.gateway import require
from ..common import contracts
from ..common.context import problem
from ..interviews.service import utf16_len

MAX_BYTES=8*1024*1024
FORMAT='extraction-working-supplement-v2'
LEGACY_FORMAT='extraction-working-supplement-v1'
AUTHORITY='historical-untrusted-no-activation'
COVERAGE='proposals-reviews-citations-only-no-originals-no-identities-no-permissions'
class ArchiveBase(DeclarativeBase):pass
class ArchiveGrant(ArchiveBase):
    __tablename__='extraction_archive_grants'
    subject_id=Column(String(36),primary_key=True)
    incarnation=Column(String(36),primary_key=True)
    can_import=Column(Boolean,nullable=False)
    can_read=Column(Boolean,nullable=False)
class ImportedWorkingArchive(ArchiveBase):
    __tablename__='extraction_imported_working_archives'
    incarnation=Column(String(36),primary_key=True)
    digest=Column(String(64),primary_key=True)
    target_epoch=Column(String(64),nullable=False)
    doc=Column(JSON,nullable=False)
    imported_by=Column(String(36),nullable=False)

def initialize(db):
    if db.engine.dialect.name!='sqlite':raise ValueError('SQLite required')
    ArchiveBase.metadata.create_all(db.engine)
    with db.engine.begin() as c:
        for op in ('UPDATE','DELETE'):
            c.execute(text(f"CREATE TRIGGER IF NOT EXISTS extraction_imported_no_{op.lower()} BEFORE {op} ON extraction_imported_working_archives BEGIN SELECT RAISE(ABORT,'imported working history append-only'); END;"))

def grant(s,subject_id,case_id,*,can_import,can_read):
    j.begin(s)
    if type(can_import) is not bool or type(can_read) is not bool or s.get(j.Subject,subject_id) is None:raise ValueError()
    key=(subject_id,j.case_current(s,case_id));row=s.get(ArchiveGrant,key)
    if row is None:s.add(ArchiveGrant(subject_id=key[0],incarnation=key[1],can_import=can_import,can_read=can_read))
    else:row.can_import=can_import;row.can_read=can_read
    s.flush()

def _auth(s,token,case_id,mode):
    before,generation=j.auth(s,token,case_id)
    def permission():
        require(SimpleNamespace(role=before.role),s,case_id,'testimony')
        require(SimpleNamespace(role='AgentService'),s,case_id,'testimony')
        row=s.get(ArchiveGrant,(before.subject_id,generation),populate_existing=True)
        if row is None or not (row.can_import if mode=='import' else row.can_read):raise problem(403,'WORKING_ARCHIVE_DENIED','未授予历史归档内容访问权限')
    permission()
    epoch=j.load_case(s,case_id)['caseEpochUtc']
    # Metadata reads precede the terminal permission/session check, including expiry.
    permission()
    if j.auth(s,token,case_id)!=(before,generation):raise problem(403,'WORKING_ARCHIVE_ACCESS_CHANGED','归档授权变化')
    return before,generation,epoch

def _final(s,token,case_id,mode,before):
    if _auth(s,token,case_id,mode)!=before:raise problem(403,'WORKING_ARCHIVE_ACCESS_CHANGED','归档授权或目标时基变化')

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def reject():raise problem(422,'WORKING_ARCHIVE_INVALID','历史补充包格式无效')
def keys(value,expected):
    if not isinstance(value,dict) or set(value)!=set(expected.split()):reject()
def seq(value,minimum,maximum):
    if not isinstance(value,list) or not minimum<=len(value)<=maximum:reject()
def hash_value(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):reject()
def utc(value):
    if not isinstance(value,str) or len(value)>64 or datetime.fromisoformat(value.replace('Z','+00:00')).utcoffset() is None:reject()
def pairs(values):
    out={}
    for k,v in values:
        if k in out:reject()
        out[k]=v
    return out

def _validate_result(result,record_id,binding,allow_pi=False):
    if allow_pi and type(result) is dict and result.get('providerMode')=='remote-deepseek':
        from .pi_working_result import validate_shape
        validate_shape(result,record_id,binding)
        return
    keys(result,'status inferencePerformed fixture proposals citations receipt saved citationMeaning')
    if result['status']!='PendingReview' or result['saved'] is not False or result['citationMeaning']!='exact_quote_match_only_not_fact_verification':reject()
    receipt=result['receipt'];keys(receipt,'bindingDigest promptDigest outputDigest providerMode modelIdentityVerified configuredModel persistentAudit signature sourceScope runChecksum')
    for name in ('bindingDigest','promptDigest','outputDigest','runChecksum'):hash_value(receipt[name])
    if receipt['bindingDigest']!=binding or receipt['providerMode'] not in ('fixture','local') or receipt['sourceScope'] not in ('interview_document_only','registered_original_bytes'):reject()
    if any(receipt[k] is not False for k in ('modelIdentityVerified','persistentAudit','signature')):reject()
    fixture=receipt['providerMode']=='fixture'
    if result['fixture'] is not fixture or result['inferencePerformed'] is not (not fixture):reject()
    model=receipt['configuredModel']
    if fixture and model is not None:reject()
    if not fixture and (not isinstance(model,str) or not model.strip() or len(model)>200 or any(ord(c)<32 for c in model)):reject()
    if receipt['runChecksum']!=extraction.digest({k:v for k,v in receipt.items() if k!='runChecksum'}):reject()
    seq(result['proposals'],1,20);seq(result['citations'],1,20);expected=[];seen=set()
    for st in result['proposals']:
        keys(st,'kind subject summary claim quote recordId statementId span reviewStatus revision extractedBy')
        contracts.validate('interview#/$defs/statement',st)
        if st['recordId']!=record_id or st['statementId']!='pending' or st['reviewStatus']!='Draft' or type(st['revision']) is not int or st['revision']!=1 or st['extractedBy']!='Agent':reject()
        span=st['span'];keys(span,'round field start length')
        if type(span['round']) is not int or span['round']<1 or span['field'] not in ('Question','Answer') or type(span['start']) is not int or span['start']<0 or type(span['length']) is not int or span['length']!=utf16_len(st['quote']) or not st['quote'].strip():reject()
        key=(span['round'],span['field'],st['quote'])
        if key in seen:reject()
        seen.add(key);expected.append({'recordId':record_id,'round':span['round'],'quote':st['quote']})
    if result['citations']!=expected:reject()
    for item in result['citations']:
        keys(item,'recordId round quote')
        if type(item['round']) is not int:reject()

def validate(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:reject()
    try:
        wrapper=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda _:reject())
        keys(wrapper,'sha256 payload');hash_value(wrapper['sha256']);p=wrapper['payload']
        if extraction.digest(p)!=wrapper['sha256']:reject()
        keys(p,'format caseId originCaseIncarnation exportCaseEpochUtc authority coverage proposals')
        if p['format'] not in (FORMAT,LEGACY_FORMAT) or p['authority']!=AUTHORITY or p['coverage']!=COVERAGE or not isinstance(p['caseId'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',p['caseId']):reject()
        j.canonical_id(p['originCaseIncarnation']);utc(p['exportCaseEpochUtc']);seq(p['proposals'],0,50);ids=set()
        for item in p['proposals']:
            keys(item,'proposalId recordId bindingDigest generatedBySubjectId storedUtc result reviews sourceDeclaration')
            j.canonical_id(item['proposalId']);j.canonical_id(item['generatedBySubjectId']);utc(item['storedUtc']);hash_value(item['bindingDigest'])
            if not isinstance(item['recordId'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',item['recordId']) or item['proposalId'] in ids:reject()
            ids.add(item['proposalId']);_validate_result(item['result'],item['recordId'],item['bindingDigest'],p['format']==FORMAT);seq(item['reviews'],0,100)
            source=item['sourceDeclaration']
            if (item['result']['sourceScope'] if item['result'].get('providerMode')=='remote-deepseek' else item['result']['receipt']['sourceScope'])=='interview_document_only':
                if source is not None:reject()
            else:
                keys(source,'evidenceId sourceIncarnation sourceSha256')
                if not isinstance(source['evidenceId'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',source['evidenceId']):reject()
                j.canonical_id(source['sourceIncarnation']);hash_value(source['sourceSha256'])
            for index,review in enumerate(item['reviews'],1):
                keys(review,'revision authorSubjectId recordedUtc decisions reviewedAsWorkingOnly factVerified'+(' reviewOrigin' if p['format']==FORMAT and 'reviewOrigin' in review else ''))
                if 'reviewOrigin' in review and review['reviewOrigin'] not in ('user_submission_unverified','scripted_test'):reject()
                if type(review['revision']) is not int or review['revision']!=index or review['reviewedAsWorkingOnly'] is not True or review['factVerified'] is not False:reject()
                j.canonical_id(review['authorSubjectId']);utc(review['recordedUtc']);seq(review['decisions'],1,20)
                decisions=[Decision.model_validate(d).model_dump() for d in review['decisions']]
                if [d['index'] for d in decisions]!=list(range(1,len(item['result']['proposals'])+1)):reject()
        return wrapper['sha256'],p
    except Exception:reject()

def export_bundle(db,settings,token,case_id):
    with db.session() as s:
        before=w._auth(s,token,case_id);epoch=j.load_case(s,case_id)['caseEpochUtc']
        rows=list(s.scalars(select(w.WorkingProposal).where(w.WorkingProposal.incarnation==before[1]).order_by(w.WorkingProposal.proposal_id).limit(51)))
        if len(rows)>50:raise problem(413,'WORKING_ARCHIVE_LIMIT','补充归档超出预算')
        p={'format':FORMAT,'caseId':case_id,'originCaseIncarnation':before[1],'exportCaseEpochUtc':epoch,'authority':AUTHORITY,'coverage':COVERAGE,'proposals':[]}
        for row in rows:
            snap=w._snapshot(s,db,settings,token,case_id,row.record_id,row.binding)
            if row.doc['result'].get('providerMode')=='remote-deepseek':
                from .pi_working_result import validate_current
                validate_current(row.doc['result'],snap,row.record_id)
            else:w._validate_generated(row.doc['result'],snap,row.record_id)
            declaration=None
            if snap[1].get('evidenceId'):
                ctx=SimpleNamespace(db=db,settings=settings,role=before[0].role,operator=before[0].subject_id)
                current=j.source_current(ctx,s,case_id,snap[1]['evidenceId'])
                declaration={'evidenceId':current['evidenceId'],'sourceIncarnation':current['incarnation'],'sourceSha256':current['sourceSha256']}
            item={'sourceDeclaration':declaration,'proposalId':row.proposal_id,'recordId':row.record_id,'bindingDigest':row.binding,
                'generatedBySubjectId':row.doc['generatedBySubjectId'],'storedUtc':row.doc['storedUtc'],'result':copy.deepcopy(row.doc['result']),
                'reviews':[copy.deepcopy(e.doc) for e in w._history(s,before[1],row.proposal_id)]}
            p['proposals'].append(item)
            if len(canonical(p))>MAX_BYTES-128:raise problem(413,'WORKING_ARCHIVE_LIMIT','补充归档超出预算')
        raw=canonical({'sha256':extraction.digest(p),'payload':p});validate(raw)
        for row in rows:w._final(s,db,settings,token,case_id,row.record_id,row.binding,before,False)
        if j.load_case(s,case_id)['caseEpochUtc']!=epoch or w._auth(s,token,case_id)!=before:raise problem(403,'WORKING_ARCHIVE_ACCESS_CHANGED','导出授权或时基变化')
        return raw

def restore_bundle(db,token,case_id,raw):
    with db.session() as s:
        before=_auth(s,token,case_id,'import');checksum,p=validate(raw)
        if p['caseId']!=case_id:reject()
        row=s.get(ImportedWorkingArchive,(before[1],checksum));replayed=row is not None
        if row is not None and row.target_epoch!=before[2]:raise problem(409,'WORKING_ARCHIVE_TARGET_CHANGED','目标时基变化')
        if row is None:
            if len(list(s.scalars(select(ImportedWorkingArchive.digest).where(ImportedWorkingArchive.incarnation==before[1]).limit(20))))>=20:raise problem(413,'WORKING_ARCHIVE_LIMIT','历史补充包数量达到预算')
            s.add(ImportedWorkingArchive(incarnation=before[1],digest=checksum,target_epoch=before[2],doc=p,imported_by=before[0].subject_id));s.flush()
        result={'sha256':checksum,'replayed':replayed,'status':'imported_untrusted_history','activated':False,'proposals':len(p['proposals'])}
        _final(s,token,case_id,'import',before);return result

def read_imported(db,token,case_id,checksum):
    hash_value(checksum)
    with db.session() as s:
        before=_auth(s,token,case_id,'read');row=s.get(ImportedWorkingArchive,(before[1],checksum))
        if row is None:raise problem(404,'WORKING_ARCHIVE_NOT_FOUND','历史补充包不存在')
        if row.target_epoch!=before[2]:raise problem(409,'WORKING_ARCHIVE_TARGET_CHANGED','目标时基变化')
        result={'sha256':checksum,'status':'imported_untrusted_history','activated':False,'targetCaseEpochUtc':row.target_epoch,'historicalClaimsVerified':False,'payload':copy.deepcopy(row.doc)}
        _final(s,token,case_id,'read',before);return result

def list_imported(db,token,case_id):
    with db.session() as s:
        before=_auth(s,token,case_id,'read')
        rows=list(s.scalars(select(ImportedWorkingArchive).where(ImportedWorkingArchive.incarnation==before[1],ImportedWorkingArchive.target_epoch==before[2]).order_by(ImportedWorkingArchive.digest).limit(21)))
        if len(rows)>20:raise problem(413,'WORKING_ARCHIVE_LIMIT','历史清单超出预算')
        result={'caseId':case_id,'items':[]}
        result['items']=[{'sha256':r.digest,'proposals':len(r.doc['proposals']),'status':'imported_untrusted_history','activated':False} for r in rows]
        _final(s,token,case_id,'read',before);return result
