"""Synthetic offline parser tests with ordinary API-produced history. No restore wiring."""
from copy import deepcopy
import json
import pytest
from sqlalchemy import select
from mcis_service.timeline.models import ConflictRow
from mcis_service.timeline.revisions import ConflictRevision
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
from mcis_service.db import put_doc
from mcis_service.working_records_archive.conflicts import parse, ConflictArchiveInvalid
from mcis_service.working_records_archive.validation import canonical, digest
from .conflict_version_helpers import checked
from .test_working_record_archive import client_at,ROOT,CID,populate
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state


def bundle(c):
    with c.app.state.db.session() as s:
        records=[]
        for row in s.scalars(select(ConflictRow).where(ConflictRow.case_id==CID)):
            revisions=[r.doc for r in s.scalars(select(ConflictRevision).where(ConflictRevision.case_id==CID,ConflictRevision.conflict_id==row.key).order_by(ConflictRevision.revision))]
            records.append(dict(key=row.key,createdUtc=row.created_utc,updatedUtc=row.updated_utc,doc=row.doc,
                coverage=revisions[-1]['coverage'] if revisions else 'unknown-before-capture',revisions=revisions))
        context=dict(case_id=CID,evidence=[r.doc for r in s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CID))],
            audit_lines=[r.line for r in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq))],
            custody_lines=[r.line for r in s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==CID).order_by(CustodyEventRow.seq))],vessel_ids=set())
    return dict(format='MCIS-CONFLICT-ARCHIVE',version=1,caseId=CID,records=records),context


@pytest.fixture
def captured(tmp_path):
    with client_at(tmp_path/'source',True) as c:
        _,receipt,*_=populate(c)
        value=body('Synthetic original😀');value['a']['evidenceId']=receipt['evidenceId']
        checked(c,'post',ROOT+'/conflicts',value,201)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic explanation 中文 '*60})
        value['a']['valueText']='Synthetic next observation'
        checked(c,'post',ROOT+'/conflicts',value,201)
        yield c,*bundle(c)


def test_exact_parse_no_io_or_export_enabling(captured):
    c,data,context=captured
    before=state(c)
    result=parse(canonical(data),**context)
    assert result==data and canonical(result)==canonical(data)
    assert len(result['records'][0]['revisions'])==3
    assert result['records'][0]['revisions'][1]['afterSources']['a']['bytesVerified'] is False
    assert state(c)==before
    response=checked(c,'get',ROOT+'/export',status=409)
    assert response.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED' and state(c)==before


@pytest.mark.parametrize('edited',[False,True])
def test_legacy_unknown_exact_and_not_fabricated(tmp_path,edited):
    with client_at(tmp_path/'legacy',True) as c:
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        if edited:checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic new note'})
        data,ctx=bundle(c);result=parse(canonical(data),**ctx)
        assert result==data and result['records'][0]['coverage']=='unknown-before-capture'
        if edited:assert result['records'][0]['revisions'][0]['beforeSources'] is None
        else:assert result['records'][0]['revisions']==[]


@pytest.mark.parametrize('change',[
    lambda d:d.update(version=2),lambda d:d.update(version=True),
    lambda d:d.update(caseId='OTHER'),lambda d:d.update(extra=True),
    lambda d:d.update(records=[]),lambda d:d['records'].append(deepcopy(d['records'][0])),
    lambda d:d['records'][0].update(coverage='complete'),
    lambda d:d['records'][0].update(createdUtc='2026-01-01T00:00:00+00:60'),
    lambda d:d['records'][0].update(revisions=[]),
    lambda d:d['records'][0]['doc'].update(resolution='different terminal'),
    lambda d:d['records'][0]['doc'].update(vesselId='MISSING'),
    lambda d:d['records'][0]['revisions'].pop(1),
    lambda d:d['records'][0]['revisions'][0].pop('afterSources'),
    lambda d:d['records'][0]['revisions'][0]['afterSources']['a'].update(bytesVerified=True),
    lambda d:d['records'][0]['revisions'][0]['afterSources']['a'].update(extra='unknown'),
    lambda d:d['records'][0]['revisions'][0].update(beforeSources={}),
    lambda d:d['records'][0]['revisions'][0].update(identityMode='authenticated'),
    lambda d:d['records'][0]['revisions'][0].update(auditSeq=True),
    lambda d:d['records'][0]['revisions'][0].update(previousSha256='a'*64),
])
def test_reject_invalid_member(captured,change):
    _,data,ctx=captured;change(data)
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**ctx)


def rehash(data):
    previous=None
    for revision in data['records'][0]['revisions']:
        revision['previousSha256']=previous
        revision['sha256']=digest({k:v for k,v in revision.items() if k!='sha256'})
        previous=revision['sha256']


@pytest.mark.parametrize('field,value',[
    ('auditLineSha256','f'*64),('auditSeq',999999),('operator','Different declaration'),
    ('role','Different role'),('utc','2000-01-01T00:00:00Z'),('operation','conflict.update'),
])
def test_rehashed_revision_still_requires_original_audit(captured,field,value):
    _,data,ctx=captured;data['records'][0]['revisions'][0][field]=value;rehash(data)
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**ctx)


@pytest.mark.parametrize('field,value',[
    ('custodyHeadSeq',999999),('custodyHeadSha256','f'*64),('sha256','f'*64),
    ('registrationSha256','f'*64),('evidenceId','EV-MISSING'),('status','unresolved'),
])
def test_rehashed_source_binding_requires_dependency(captured,field,value):
    _,data,ctx=captured
    for r in data['records'][0]['revisions']:
        r['afterSources']['a'][field]=value
        if r['beforeSources']:r['beforeSources']['a'][field]=value
    rehash(data)
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**ctx)


def test_omitted_last_revision_detected_from_original_audit(captured):
    _,data,ctx=captured;record=data['records'][0]
    record['revisions'].pop();record['doc']=deepcopy(record['revisions'][-1]['after'])
    with pytest.raises(ConflictArchiveInvalid,match='omitted captured'):parse(canonical(data),**ctx)


def test_dependency_case_and_missing_source(captured):
    _,data,ctx=captured
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**{**ctx,'case_id':'OTHER'})
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**{**ctx,'evidence':[]})
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**{**ctx,'audit_lines':[]})
    with pytest.raises(ConflictArchiveInvalid):parse(canonical(data),**{**ctx,'custody_lines':[]})


@pytest.mark.parametrize('raw',[b'{"version":1,"version":1}',b'{"x":NaN}',b'\xff',b'[]',b'null',b'{}',b'{',b' '* (16*1024*1024+1)])
def test_malformed_input(raw):
    with pytest.raises(ConflictArchiveInvalid):parse(raw,case_id=CID,evidence=[],audit_lines=[],custody_lines=[],vessel_ids=set())


def test_two_registered_version_declarations_preserved(tmp_path):
    from mcis_service.evidence.service import append_custody
    with client_at(tmp_path/'versions',True) as c:
        _,receipt,*_=populate(c)
        value=body();value['a']['evidenceId']=receipt['evidenceId']
        checked(c,'post',ROOT+'/conflicts',value,201)
        original=bundle(c)[0]['records'][0]['revisions'][0]['afterSources']['a']['sha256']
        # Synthetic registry-only version evolution. No bytes are replaced or verified.
        with c.app.state.db.session() as s:
            append_custody(s,case_id=CID,evidence_id=receipt['evidenceId'],kind='Change',operator='Synthetic',role='LeadInvestigator',sha256='b'*64,previous_sha256=original,detail='Synthetic version declaration only')
        value['a']['valueText']='Synthetic changed observation'
        checked(c,'post',ROOT+'/conflicts',value,201)
        data,ctx=bundle(c);result=parse(canonical(data),**ctx)
        first,last=result['records'][0]['revisions']
        assert first['afterSources']['a']['sha256']==original
        assert last['afterSources']['a']['sha256']=='b'*64
        assert last['beforeSources']==first['afterSources']
        assert result==data
        checked(c,'get',ROOT+'/export',status=409)


def test_historical_registry_digest_not_asserted_current_or_bytes(captured):
    _,data,ctx=captured
    # A supplied historical digest has no available preimage here. Do not silently
    # replace it with the current registry digest or label it file verification.
    for r in data['records'][0]['revisions']:
        r['afterSources']['a']['registryDocSha256']='c'*64
        if r['beforeSources']:r['beforeSources']['a']['registryDocSha256']='c'*64
    rehash(data)
    result=parse(canonical(data),**ctx)
    assert result==data
    assert result['records'][0]['revisions'][0]['afterSources']['a']['bytesVerified'] is False


@pytest.mark.parametrize('encoding',['utf-16','utf-32'])
def test_only_utf8(captured,encoding):
    _,data,ctx=captured
    with pytest.raises(ConflictArchiveInvalid):parse(json.dumps(data).encode(encoding),**ctx)


def test_revision_budget_rejects_without_truncation(captured,monkeypatch):
    from mcis_service.working_records_archive import conflicts
    _,data,ctx=captured;monkeypatch.setattr(conflicts,'MAX_REVISIONS',2)
    with pytest.raises(ConflictArchiveInvalid,match='total revision budget'):parse(canonical(data),**ctx)


def test_update_cannot_describe_an_observation_replacement(captured):
    _,data,ctx=captured
    data['records'][0]['revisions'][1]['after']['a']['valueText']='not a patch field'
    rehash(data)
    with pytest.raises(ConflictArchiveInvalid,match='patch changes observation'):parse(canonical(data),**ctx)
