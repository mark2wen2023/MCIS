"""Offline synthetic history validation. No product intake/export/security probes."""
from copy import deepcopy
import json
from sqlalchemy import select
import pytest
from research.conflict_source_intent.archive_receipts_v2 import parse,ConflictArchiveInvalid
from mcis_service.db import list_docs
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.timeline.models import ConflictRow
from mcis_service.timeline.revisions import ConflictRevision
from mcis_service.timeline.source_receipts import ConflictSourceReceipt
from .test_working_record_archive import client_at,ROOT,HEAD,CID
from .test_conflict_archive_readiness import body

@pytest.fixture
def sample(tmp_path):
    with client_at(tmp_path/'case',True) as c:
        for _ in range(2):
            r=c.post(ROOT+'/evidence',headers=HEAD,json={'title':'Synthetic registry','source':'Synthetic','extractedBy':'Synthetic','sha256':'a'*64})
            assert r.status_code==201,r.text
        v=body();v['a']['evidenceId']='EV-001';v['b']['evidenceId']='EV-002'
        r=c.post(ROOT+'/conflicts',headers=HEAD,json=v);assert r.status_code==201
        v=r.json()
        def collect(version):
            with c.app.state.db.session() as s:
                record=s.scalars(select(ConflictRow).where(ConflictRow.case_id==CID)).one()
                revisions=[r.doc for r in s.scalars(select(ConflictRevision).where(ConflictRevision.case_id==CID).order_by(ConflictRevision.revision))]
                data={'format':'MCIS-CONFLICT-ARCHIVE','version':version,'caseId':CID,'records':[{'key':record.key,'createdUtc':record.created_utc,'updatedUtc':record.updated_utc,'doc':record.doc,'coverage':revisions[-1]['coverage'],'revisions':revisions}]}
                if version==2:data['receipts']=[{'receiptId':r.id,'caseId':r.case_id,'conflictId':r.conflict_id,'consumedRevision':r.consumed_revision,'authorization':'inactive-history','doc':r.doc}for r in s.scalars(select(ConflictSourceReceipt))]
                deps={'case_id':CID,'evidence':list_docs(s,EvidenceRow,CID),'audit_lines':[r.line for r in s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq))],'custody_lines':[r.line for r in s.scalars(select(CustodyEventRow).order_by(CustodyEventRow.seq))],'vessel_ids':set()}
                return deepcopy(data),deps
        legacy=collect(1)
        version=c.get(ROOT+'/conflicts:editable',headers=HEAD).json()[0]['version']
        v['a']['valueText']='Synthetic changed observation'
        receipt=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':version,'observations':{k:v[k]for k in ('a','b')}})
        assert receipt.status_code==201,receipt.text
        r=c.post(ROOT+'/conflicts',headers=HEAD,json={**v,'expectedVersion':version,'sourceReceiptId':receipt.json()['receiptId']});assert r.status_code==201,r.text
        # Preserve an unused issued receipt too; not an active restored capability.
        version=c.get(ROOT+'/conflicts:editable',headers=HEAD).json()[0]['version'];v['a']['valueText']='Synthetic unused proposal'
        r=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':version,'observations':{k:v[k]for k in ('a','b')}});assert r.status_code==201
        yield legacy,collect(2)

def decode(pair):
    data,deps=pair
    return parse(json.dumps(data,ensure_ascii=False).encode(),**deps)

def test_v1_and_v2_preserve_exact_history_without_activation(sample):
    legacy,current=sample
    assert decode(legacy)==legacy[0]
    assert decode(current)==current[0]
    assert all(r['authorization']=='inactive-history'for r in decode(current)['receipts'])
    assert sorted(str(r['consumedRevision'])for r in current[0]['receipts'])==['2','None']
    # JSON transport reserialization does not alter any recorded history digest.
    assert decode((json.loads(json.dumps(current[0])),current[1]))==current[0]

@pytest.mark.parametrize('mutation',[
 'missing','extra','active','wrong-case','wrong-conflict','wrong-revision','wrong-version',
 'wrong-observations','wrong-source','wrong-custody','wrong-registry','wrong-actor',
 'wrong-expiry','duplicate','unused-consumed','missing-field','unknown-version'])
def test_v2_rejects_incomplete_or_inconsistent_declarations(sample,mutation):
    _,pair=sample;data=deepcopy(pair[0]);r=next(r for r in data['receipts'] if r['consumedRevision']==2);d=r['doc']
    if mutation=='missing':data['receipts'].remove(r)
    elif mutation=='extra':data['receipts'].append({**deepcopy(r),'receiptId':'12345678-1234-4234-9234-123456789012'})
    elif mutation=='active':r['authorization']='active'
    elif mutation=='wrong-case':d['caseId']='OTHER'
    elif mutation=='wrong-conflict':r['conflictId']='C-02'
    elif mutation=='wrong-revision':r['consumedRevision']=1
    elif mutation=='wrong-version':d['conflictVersion']='f'*64
    elif mutation=='wrong-observations':d['observationsSha256']='f'*64
    elif mutation=='wrong-source':d['sources']['EV-002']=d['sources'].pop('EV-001')
    elif mutation=='wrong-custody':d['sources']['EV-001']['custodyHeadSeq']=999
    elif mutation=='wrong-registry':d['sources']['EV-001']['registryDocSha256']='f'*64
    elif mutation=='wrong-actor':d['operator']='Other'
    elif mutation=='wrong-expiry':d['expiresUtc']=d['issuedUtc']
    elif mutation=='duplicate':data['receipts'].append(deepcopy(r))
    elif mutation=='unused-consumed':next(x for x in data['receipts']if x['consumedRevision']is None)['consumedRevision']=3
    elif mutation=='missing-field':del r['doc']['humanReadVerified']
    elif mutation=='unknown-version':data['version']=3
    with pytest.raises(ConflictArchiveInvalid):decode((data,pair[1]))
    assert decode(pair)==pair[0] # original synthetic history unchanged

def test_new_member_is_not_silently_downgraded(sample):
    _,pair=sample;d=deepcopy(pair[0]);d['version']=1
    with pytest.raises(ConflictArchiveInvalid):decode((d,pair[1]))

def test_synthetic_legacy_unknown_is_not_filled_in(sample):
    legacy,_=sample
    # Separate constructed pre-capture record, not migration of captured history.
    old=legacy[0]['records'][0]
    record={k:deepcopy(old[k]) for k in ('key','createdUtc','updatedUtc','doc')}
    record.update(coverage='unknown-before-capture',revisions=[])
    deps={**legacy[1],'audit_lines':[]}
    for version in (1,2):
        data={'format':'MCIS-CONFLICT-ARCHIVE','version':version,'caseId':CID,'records':[record]}
        if version==2:data['receipts']=[]
        parsed=decode((data,deps))
        assert parsed==data and parsed['records'][0]['revisions']==[]

def test_all_issuance_audit_entries_must_be_represented(sample):
    _,pair=sample;data=deepcopy(pair[0])
    data['receipts']=[r for r in data['receipts'] if r['consumedRevision'] is not None]
    with pytest.raises(ConflictArchiveInvalid,match='omitted historical receipts'):decode((data,pair[1]))
