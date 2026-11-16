"""Ordinary synthetic native HTTP setup plus read-only SQLite inventory.
No real files/model execution in scanner, no permissions or security probes.
Omission/ambiguity fixtures are fresh bare SQLite schemas, NOT modified product stores.
"""
import copy
import json
import sqlite3
import hashlib
import subprocess
from contextlib import contextmanager
import pytest
from research.media_archive.preflight import scan
from .test_audio_review_candidate import local, attach, revision, BASE, CID
from .test_audio_sensevoice_tasks import configured
from mcis_service.audio_review import tasks


@contextmanager
def readonly(settings):
    c=sqlite3.connect('file:'+str(settings.data_dir/'test.db')+'?mode=ro',uri=True)
    c.execute('BEGIN')
    try: yield c
    finally:c.rollback();c.close()


def setup(local):
    client,app,settings=local
    _,_,_,run=attach(client)
    r=client.post(BASE+'/audio-reviews/'+run['runId']+'/revisions',json=revision())
    assert r.status_code==200,r.text
    return client,settings,run


def test_native_two_revisions_inventory_is_read_only(local):
    _,settings,run=setup(local)
    with readonly(settings) as c:
        result=scan(c,CID)
        assert c.total_changes==0 and c.in_transaction
        assert len(result['rows']['audio_review_revisions'])==2
        assert [r['revision'] for r in result['revisionAuditLinks']]==[0,1]
        assert len(result['registrations'])==2
        assert result['export_allowed'] is False and result['restore_ready'] is False
        assert result['bytes_verified'] is False
        assert all(r['runId']==run['runId'] for r in result['revisionAuditLinks'])
        with pytest.raises(sqlite3.OperationalError):c.execute('CREATE TABLE forbidden_write(x)')


@pytest.mark.parametrize('status',['succeeded','failed','interrupted_unknown'])
def test_native_task_actions_and_run_association(configured,monkeypatch,status):
    client,_,settings,body,calls=configured
    if status!='succeeded':
        def stop(*args):
            if status=='failed':raise ValueError('synthetic failure')
            raise subprocess.TimeoutExpired('synthetic',120)
        monkeypatch.setattr(tasks,'execute',stop)
    response=client.post(BASE+'/audio-asr-tasks',json=body)
    assert response.status_code==(201 if status=='succeeded' else 409)
    with readonly(settings) as c:
        result=scan(c,CID)
        assert c.total_changes==0
        assert len(result['revisionAuditLinks'])==(1 if status=='succeeded' else 0)
        assert json.loads(result['rows']['audio_asr_tasks'][0]['doc'])['status']==status
        assert result['export_allowed'] is False


def bare_inventory(rows):
    """New fabricated SQLite schema: no product triggers, migrations, or writes to source."""
    c=sqlite3.connect(':memory:')
    for name,values in rows.items():
        # Empty tables still need the native columns used for detection.
        columns=list(values[0]) if values else ['case_id']
        quoted='"'+name.replace('"','""')+'"'
        c.execute('CREATE TABLE '+quoted+' ('+','.join('"'+k+'"' for k in columns)+')')
        for row in values:
            c.execute('INSERT INTO '+quoted+' VALUES('+','.join('?' for _ in columns)+')',tuple(row[k] for k in columns))
    c.commit();c.execute('BEGIN')
    return c


@pytest.mark.parametrize('omit',['initial','revision','audit','registration','evidence','task-table'])
def test_missing_native_dependency_rejects_fresh_fixture(local,omit):
    _,settings,_=setup(local)
    with readonly(settings) as c:rows=scan(c,CID)['rows']
    if omit=='initial':rows['audio_review_revisions']=rows['audio_review_revisions'][1:]
    if omit=='revision':rows['audio_review_revisions']=rows['audio_review_revisions'][:1]
    if omit=='audit':rows['audit_events']=rows['audit_events'][:-1]
    if omit=='registration':rows['custody_events']=[]
    if omit=='evidence':rows['evidence_items']=[]
    if omit=='task-table':del rows['audio_asr_tasks']
    c=bare_inventory(rows)
    try:
        with pytest.raises(ValueError):scan(c,CID)
        assert c.total_changes==sum(len(v) for v in rows.values()) # inserts only, no scan writes
    finally:c.close()


def test_ambiguous_revision_audit_rejects_fresh_fixture(local):
    _,settings,_=setup(local)
    with readonly(settings) as c:rows=scan(c,CID)['rows']
    last=rows['audit_events'][-1]; duplicate=copy.deepcopy(last)
    duplicate['id']+=1;duplicate['seq']+=1
    duplicate['prev_hash']=hashlib.sha256(last['line'].encode()).hexdigest()
    line=json.loads(duplicate['line']);line.update(seq=duplicate['seq'],prev=duplicate['prev_hash'])
    duplicate['line']=json.dumps(line,separators=(',',':'))
    rows['audit_events'].append(duplicate)
    c=bare_inventory(rows)
    try:
        with pytest.raises(ValueError,match='ambiguous'):scan(c,CID)
    finally:c.close()


def test_other_case_not_enumerated_and_explicit_transaction_required(local):
    _,settings,_=setup(local)
    with readonly(settings) as c:
        with pytest.raises(ValueError,match='case absent'):scan(c,'OTHER-SYNTHETIC')
        c.rollback()
        with pytest.raises(ValueError,match='explicit snapshot'):scan(c,CID)


def test_two_runs_same_actor_and_revision_number_remain_distinct(local):
    _,settings,first=setup(local)
    _,_,second=setup(local)
    with readonly(settings) as c:
        result=scan(c,CID); links=result['revisionAuditLinks']
        assert len(links)==4 and len({v['auditSeq'] for v in links})==4
        assert {v['runId'] for v in links}=={first['runId'],second['runId']}


def test_image_native_shape_in_fresh_synthetic_store(local):
    _,settings,_=setup(local)
    with readonly(settings) as c:rows=scan(c,CID)['rows']
    media=rows.pop('audio_review_revisions');rows['image_ocr_review_records']=media
    rows['image_ocr_tasks']=rows.pop('audio_asr_tasks')
    first=json.loads(media[0]['doc'])
    first['bindings']={'pdf':first['audioReceipt'],'image':first['draftReceipt'],
                       'candidate':first['draftReceipt'],'raw':first['audioReceipt']}
    media[0]['doc']=json.dumps(first)
    human=json.loads(media[1]['doc']);human['lineIndex']=0;media[1]['doc']=json.dumps(human)
    previous='0'*64
    for event in rows['audit_events']:
        if event['action']=='audio.draft.attach':
            event['action']='ocr.import';event['after']=str({'revision':0})
        if event['action']=='audio.human.revise':
            event['action']='ocr.review';event['after']=str({'revision':1,'lineIndex':0})
        event['prev_hash']=previous
        line=json.loads(event['line']);line.update(action=event['action'],after=event['after'],prev=previous)
        event['line']=json.dumps(line,separators=(',',':'));previous=hashlib.sha256(event['line'].encode()).hexdigest()
    c=bare_inventory(rows)
    try:
        result=scan(c,CID)
        assert len(result['revisionAuditLinks'])==2
        assert all(v['kind']=='image' for v in result['revisionAuditLinks'])
        assert result['restore_ready'] is False
    finally:c.close()


def test_future_media_state_is_not_silently_excluded(local):
    _,settings,_=setup(local)
    with readonly(settings) as c:rows=scan(c,CID)['rows']
    rows['audio_future_records']=[{'case_id':CID,'doc':'{}'}]
    c=bare_inventory(rows)
    try:
        with pytest.raises(ValueError,match='unknown media table'):scan(c,CID)
    finally:c.close()
