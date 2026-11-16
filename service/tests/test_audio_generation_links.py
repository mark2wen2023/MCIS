"""New ordinary synthetic association checks; no worker, originals or refusal probes."""
import json
from copy import deepcopy
from types import SimpleNamespace
import pytest
from mcis_service.audio_review.generation_links import validate_rows, inspect_case
from mcis_service.common.csjson import sha256_utf8
from mcis_service.db import WRITE_LOCK
from mcis_service.reports.access import begin
from .test_audio_review_candidate import local, BASE, CID
from .test_audio_sensevoice_tasks import configured


def data():
    task={'taskId':'t','caseId':'c','source':{'registeredSha256':'a'*64},'status':'succeeded','runId':'r','operator':'synthetic','role':'LeadInvestigator'}
    ts=[dict(case_id='c',task_id='t',doc=task)]
    gs=[dict(case_id='c',generation_id='g',task_id='t',doc={'protocol':'audio-generation-observation/v1','source':deepcopy(task['source'])})]
    obs=[];audits=[]
    for n,(action,entity,label) in enumerate([('asr.task.start','t','registration-recorded-before-dispatch'),('asr.task.succeeded','r','result-converted-and-source-rechecked')]):
        e=dict(seq=n+1,action=action,command='t',entity_id=entity,category='Evidence',operator='synthetic',role='LeadInvestigator')
        e['line']=json.dumps(e);e['case_id']='c';audits.append(e)
        obs.append(dict(case_id='c',generation_id='g',ordinal=n,doc=dict(event=label,auditSeq=n+1,auditLineSha256=sha256_utf8(e['line']),writers='unknown',manifestStatus='not-captured',archiveReady=False)))
    return [ts,gs,obs,audits]


def test_same_transaction_native_task_links_stay_not_ready(configured):
    c,app,settings,b,calls=configured
    assert c.post(BASE+'/audio-asr-tasks',json=b).status_code==201
    ctx=SimpleNamespace(role='LeadInvestigator',operator='synthetic',settings=settings,db=app.state.db)
    with WRITE_LOCK,app.state.db.session() as s:
        begin(s);r=inspect_case(ctx,s,CID)
    assert len(r['links'])==2 and r['associationsConsistent'] is True
    assert r['archiveReady'] is False and r['historicalProof'] is False and r['writers']=='unknown'


def test_missing_generation_is_unknown_not_backfilled():
    d=data();d[1]=[];before=deepcopy(d)
    with pytest.raises(ValueError,match='legacy or lost history unknown'):validate_rows('c',*d)
    assert d==before


def test_orphan_and_duplicate_observations_rejected():
    d=data();d[2].append(deepcopy(d[2][0]))
    with pytest.raises(ValueError,match='duplicate'):validate_rows('c',*d)
    d=data();d[2][0]['generation_id']='absent'
    with pytest.raises(ValueError,match='orphan'):validate_rows('c',*d)


def test_incomplete_and_source_mismatch_rejected():
    d=data();d[2].pop()
    with pytest.raises(ValueError,match='missing'):validate_rows('c',*d)
    d=data();d[1][0]['doc']['source']={}
    with pytest.raises(ValueError,match='source binding'):validate_rows('c',*d)


def test_audit_reference_and_digest_must_agree():
    d=data();d[2][1]['doc']['auditSeq']=1
    with pytest.raises(ValueError):validate_rows('c',*d)
    d=data();d[2][1]['doc']['auditLineSha256']='b'*64
    with pytest.raises(ValueError,match='audit digest'):validate_rows('c',*d)


def test_running_observation_is_consistent_but_unresolved():
    d=data();d[0][0]['doc'].update(status='running_or_unknown',runId=None);d[2].pop();d[3].pop()
    r=validate_rows('c',*d)
    assert r['associationsConsistent'] is True and r['archiveReady'] is False
    assert len(r['links'])==1 and r['writers']=='unknown'


def test_duplicate_generation_and_case_disagreement_rejected():
    d=data();extra=deepcopy(d[1][0]);extra['generation_id']='g2';d[1].append(extra)
    with pytest.raises(ValueError,match='duplicate generation'):validate_rows('c',*d)
    d=data();d[2][0]['case_id']='other-synthetic-case'
    with pytest.raises(ValueError,match='orphan observation'):validate_rows('c',*d)


def test_incomplete_observation_matches_recorded_status_only():
    for status,label in [('failed','execution-or-conversion-exception-observed'),('interrupted_unknown','timeout-observed')]:
        d=data();d[0][0]['doc'].update(status=status,runId=None)
        e=d[3][1];e.update(action='asr.task.incomplete',entity_id='t')
        e['line']=json.dumps({k:v for k,v in e.items() if k not in ('case_id','line')})
        d[2][1]['doc'].update(event=label,auditLineSha256=sha256_utf8(e['line']))
        result=validate_rows('c',*d)
        assert result['archiveReady'] is False and result['writers']=='unknown'
        d[2][1]['doc']['event']='result-converted-and-source-rechecked'
        with pytest.raises(ValueError,match='observation claims'):validate_rows('c',*d)
