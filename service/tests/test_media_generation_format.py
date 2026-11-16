"""New ordinary fabricated member tests, no I/O/model/security probes."""
import json
from copy import deepcopy
import pytest
from research.media_archive.test_contract import fixture as legacy_fixture
from research.media_archive.contract import digest
from research.media_archive.generation_format import FORMAT, validate


def fixture():
    base,blobs,_=legacy_fixture()
    def put(name,value):
        raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode();blobs[name]=raw
        base['members'][name]={'size':len(raw),'sha256':digest(raw)}
    src=base['sources'][0]
    source={k:src[k] for k in ('caseId','evidenceId','registeredSha256','currentSha256')}
    task=json.loads(blobs['task']);task.update(source=source,operator='Synthetic',role='LeadInvestigator');put('task',task)
    previous='0'*64
    for ref in base['audit']:
        name=ref['member'];e=json.loads(blobs[name]);e.update(prev=previous,category='Evidence',entity_id='TASK' if e['action']=='asr.task.start' else 'RUN')
        put(name,e);previous=digest(blobs[name])
    index=dict(format=FORMAT,caseId='SYN',archiveReady=False,base=deepcopy(base),members=deepcopy(base['members']),generations=['generation'],observations=['observation-0','observation-1'])
    def extra(name,value):
        raw=json.dumps(value,separators=(',',':')).encode();blobs[name]=raw;index['members'][name]={'size':len(raw),'sha256':digest(raw)}
    extra('generation',dict(case_id='SYN',generation_id='g',task_id='TASK',doc={'protocol':'audio-generation-observation/v1','source':source}))
    for n,label in enumerate(('registration-recorded-before-dispatch','result-converted-and-source-rechecked')):
        extra('observation-'+str(n),dict(case_id='SYN',generation_id='g',ordinal=n,doc=dict(event=label,auditSeq=n+1,auditLineSha256=digest(blobs['audit-'+str(n+1)]),writers='unknown',manifestStatus='not-captured',archiveReady=False)))
    return index,blobs


def test_v2_all_history_retained_without_readiness():
    i,b=fixture();before=deepcopy((i,b));r=validate(i,b)
    assert r['generationCount']==1 and r['observationCount']==2
    assert r['archiveReady'] is False and r['restore_ready'] is False and r['execution_allowed'] is False
    assert (i,b)==before


def test_v1_keeps_original_meaning_without_history_upgrade():
    i,b,_=legacy_fixture();r=validate(i,b)
    assert r['generationHistory']=='unknown-not-upgraded' and r['archiveReady'] is False


def test_missing_observation_member_rejected():
    i,b=fixture();b.pop('observation-1')
    with pytest.raises(ValueError):validate(i,b)


def test_missing_generation_history_rejected():
    i,b=fixture();i['generations']=[];i['members'].pop('generation');b.pop('generation')
    with pytest.raises(ValueError,match='history unknown'):validate(i,b)


def test_duplicate_reference_and_unreferenced_member_rejected():
    i,b=fixture();i['observations'].append('observation-0')
    with pytest.raises(ValueError,match='duplicate'):validate(i,b)
    i,b=fixture();i['observations'].pop()
    with pytest.raises(ValueError,match='unreferenced'):validate(i,b)


def test_inconsistent_audit_association_rejected():
    i,b=fixture();o=json.loads(b['observation-1']);o['doc']['auditSeq']=1
    raw=json.dumps(o).encode();b['observation-1']=raw;i['members']['observation-1']={'size':len(raw),'sha256':digest(raw)}
    with pytest.raises(ValueError):validate(i,b)


def test_unknown_version_and_case_disagreement_rejected():
    i,b=fixture();i['format']='unknown'
    with pytest.raises(ValueError):validate(i,b)
    i,b=fixture();i['caseId']='other-synthetic'
    with pytest.raises(ValueError,match='case'):validate(i,b)


def test_member_bytes_mismatch_and_source_disagreement_rejected():
    i,b=fixture();b['generation']+=b' '
    with pytest.raises(ValueError,match='digest'):validate(i,b)
    i,b=fixture();task=json.loads(b['task']);task['source']['currentSha256']='b'*64
    raw=json.dumps(task).encode();b['task']=raw;desc={'size':len(raw),'sha256':digest(raw)}
    i['members']['task']=desc;i['base']['members']['task']=deepcopy(desc)
    with pytest.raises(ValueError,match='source binding'):validate(i,b)


def test_serialized_envelope_preserves_all_members_and_links():
    i,b=fixture();encoded=json.dumps(i);decoded=json.loads(encoded)
    r=validate(decoded,dict(b))
    assert r['observationCount']==2 and len(r['links'])==2
    assert decoded==i and set(decoded['members'])==set(b)
