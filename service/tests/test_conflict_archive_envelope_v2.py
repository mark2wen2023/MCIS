"""Synthetic offline ZIP tests; no product restore or protected read operations."""
import base64
from copy import deepcopy
import hashlib
import json
import pytest
from sqlalchemy import select
from fastapi import HTTPException
from research.conflict_source_intent import archive_envelope_v2 as envelope
from research.conflict_source_intent.archive_receipts_v2 import ConflictArchiveInvalid
from mcis_service.working_records_archive.validation import canonical
from mcis_service.package_intake.parser import read_bounded,parse_package
from mcis_service.package.mcase import manifest_json
from mcis_service.db import list_docs
from mcis_service.timeline.models import ConflictRow
from mcis_service.timeline.revisions import ConflictRevision
from mcis_service.timeline.source_receipts import ConflictSourceReceipt
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from .test_working_record_archive import client_at,ROOT,HEAD,CID
from .test_conflict_archive_readiness import body
from .test_package_intake_parser import base,pack

DATE='2026-01-01T00:00:00Z'
def inspect(raw):return envelope.inspect_envelope(raw,expected_sha256=hashlib.sha256(raw).hexdigest())
def unchecked(files,version=envelope.VERSION,mutate=None):
    m=json.loads(manifest_json(CID,files,DATE,version))
    if mutate:mutate(m)
    return pack(files,json.dumps(m))

@pytest.fixture
def archives(tmp_path):
    with client_at(tmp_path/'case',True) as c:
        original=b'Synthetic original bytes only\n'
        r=c.post(ROOT+'/evidence',headers=HEAD,json={'title':'Synthetic','source':'Synthetic','extractedBy':'Synthetic','extractedUtc':DATE,'relativePath':'raw/source.txt','contentBase64':base64.b64encode(original).decode()})
        assert r.status_code==201,r.text
        v=body();v['a']['evidenceId']=r.json()['evidenceId']
        r=c.post(ROOT+'/conflicts',headers=HEAD,json=v);assert r.status_code==201;v=r.json()
        def collect(version):
            with c.app.state.db.session() as s:
                row=s.scalars(select(ConflictRow).where(ConflictRow.case_id==CID)).one()
                revisions=[r.doc for r in s.scalars(select(ConflictRevision).order_by(ConflictRevision.revision))]
                data={'format':'MCIS-CONFLICT-ARCHIVE','version':version,'caseId':CID,'records':[{'key':row.key,'createdUtc':row.created_utc,'updatedUtc':row.updated_utc,'doc':row.doc,'coverage':revisions[-1]['coverage'],'revisions':revisions}]}
                if version==2:data['receipts']=[{'receiptId':r.id,'caseId':r.case_id,'conflictId':r.conflict_id,'consumedRevision':r.consumed_revision,'authorization':'inactive-history','doc':r.doc} for r in s.scalars(select(ConflictSourceReceipt))]
                files=base();files.update({f'conflicts/records.v{version}.json':canonical(data),envelope.MIRROR:canonical({'conflicts':[row.doc]}),'evidence/index.json':canonical(list_docs(s,EvidenceRow,CID)),'raw/source.txt':original})
                for name,model in [('audit',AuditEventRow),('custody',CustodyEventRow)]:files[f'audit/{name}.jsonl']=('\n'.join(r.line for r in s.scalars(select(model).order_by(model.seq)))+'\n').encode()
                return files
        old=collect(1)
        version=c.get(ROOT+'/conflicts:editable',headers=HEAD).json()[0]['version'];v['a']['valueText']='Synthetic edited observation'
        receipt=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':version,'observations':{k:v[k] for k in ('a','b')}})
        assert receipt.status_code==201,receipt.text
        r=c.post(ROOT+'/conflicts',headers=HEAD,json={**v,'expectedVersion':version,'sourceReceiptId':receipt.json()['receiptId']});assert r.status_code==201,r.text
        version=c.get(ROOT+'/conflicts:editable',headers=HEAD).json()[0]['version'];v['a']['valueText']='Synthetic unused proposal'
        receipt=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':version,'observations':{k:v[k] for k in ('a','b')}})
        assert receipt.status_code==201,receipt.text
        yield old,collect(2)

@pytest.mark.parametrize('version',[envelope.LEGACY_VERSION,envelope.VERSION])
def test_complete_envelopes_preserve_members_without_restore(archives,version):
    files=archives[0 if version==envelope.LEGACY_VERSION else 1]
    raw=envelope.build_envelope(files,case_id=CID,created_utc=DATE,version=version)
    result=inspect(raw)
    assert not result.restore_ready and result.receipt_authorization=='inactive-history'
    assert result.member_version==(1 if version==envelope.LEGACY_VERSION else 2)
    assert result.receipt_count==(0 if result.member_version==1 else 2)
    decoded=read_bounded(raw);decoded.pop('manifest.json');assert decoded==files
    again=envelope.build_envelope(decoded,case_id=CID,created_utc=DATE,version=version)
    assert inspect(again).revision_count==result.revision_count
    assert {k:v for k,v in read_bounded(again).items()if k!='manifest.json'}==files
    with pytest.raises(HTTPException):parse_package(raw) # production profile remains unsupported

@pytest.mark.parametrize('change',[
 lambda m:m.update(packageVersion='1.5.0'),lambda m:m.update(packageFormat='other'),
 lambda m:m.update(caseId='OTHER'),lambda m:m['files'].pop(),
 lambda m:m['files'].append(deepcopy(m['files'][0])),
 lambda m:m['files'][0].update(sizeBytes=True),lambda m:m['files'][0].update(sha256='0'*64),
 lambda m:m['files'][0].update(role='Other'),lambda m:m.update(extra=True)])
def test_manifest_conflicts_rejected(archives,change):
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(archives[1],mutate=change))

@pytest.mark.parametrize('path,data',[
 (envelope.MIRROR,b'{"conflicts":[]}'),(envelope.PATH,b'{}'),
 ('raw/source.txt',b'wrong synthetic bytes'),('evidence/index.json',b'[]'),
 ('audit/audit.jsonl',b''),('audit/custody.jsonl',b''),('access-policy.json',b'{}'),
 ('recommendations.json',b'[{}]'),('analysis/timeline.json',b'{"events":[{}]}'),
 ('working-records/backup.v1.json',b'{}'),('unknown.json',b'{}')])
def test_valid_manifest_cannot_hide_bad_associations(archives,path,data):
    files={**archives[1],path:data}
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(files))
    with pytest.raises(ConflictArchiveInvalid):envelope.build_envelope(files,case_id=CID,created_utc=DATE)

def test_versions_cannot_be_mixed_or_downgraded(archives):
    old,new=archives
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(new,envelope.LEGACY_VERSION))
    files={**new,'conflicts/records.v1.json':old['conflicts/records.v1.json']}
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(files))
    member=json.loads(new[envelope.PATH]);member['version']=1
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked({**new,envelope.PATH:canonical(member)}))

def test_missing_receipt_or_active_label_rejected(archives):
    for mode in ('missing','active'):
        files=dict(archives[1]);member=json.loads(files[envelope.PATH])
        if mode=='missing':member['receipts']=[]
        else:member['receipts'][0]['authorization']='active'
        files[envelope.PATH]=canonical(member)
        with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(files))

def test_missing_member_and_wrong_outer_digest(archives):
    files=dict(archives[1]);raw=unchecked(files)
    with pytest.raises(ConflictArchiveInvalid):envelope.inspect_envelope(raw,expected_sha256='0'*64)
    del files[envelope.PATH]
    with pytest.raises(ConflictArchiveInvalid):inspect(unchecked(files))

@pytest.mark.parametrize('version',[envelope.LEGACY_VERSION,envelope.VERSION])
def test_constructed_legacy_unknown_has_no_invented_history(version):
    member_version,path=envelope.PROFILES[version]
    doc={**body(),'caseId':CID}
    member={'format':'MCIS-CONFLICT-ARCHIVE','version':member_version,'caseId':CID,
        'records':[{'key':'C-01','createdUtc':DATE,'updatedUtc':DATE,'doc':doc,
                    'coverage':'unknown-before-capture','revisions':[]}]}
    if member_version==2:member['receipts']=[]
    files=base();files[path]=canonical(member);files[envelope.MIRROR]=canonical({'conflicts':[doc]})
    raw=envelope.build_envelope(files,case_id=CID,created_utc=DATE,version=version)
    result=inspect(raw)
    assert result.unknown_history_count==1 and result.revision_count==0 and result.receipt_count==0
    assert read_bounded(raw)[path]==canonical(member)
