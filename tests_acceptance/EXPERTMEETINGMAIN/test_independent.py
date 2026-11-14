import hashlib,json,subprocess,sys
from pathlib import Path
from copy import deepcopy
import pytest
from research.expert_group.packet import ROLES,_packet,load_packet,GroupError
from research.expert_meeting.machine import Meeting,MeetingError,verify_snapshot

def reviews():return [{'itemId':i['itemId'],'label':'insufficient','quote':i['citation']['quote'],'rationale':'Independent synthetic declaration','uncertainty':'Not verified'} for i in _packet(load_packet())['items']]
def issue(m,role):return m.act({'type':'issue_turn','roleId':role})['activeTurn']
def submit(t,remote=False):return {'type':'submit_provider_response' if remote else 'submit_simulated','ticketId':t['ticketId'],'contextDigest':t['contextDigest'],'reviews':reviews()}
@pytest.mark.parametrize('remote',[False,True])
def test_complete_previous_round_only_and_false_execution_flags(remote):
    m=Meeting(provider_mode='remote' if remote else 'scripted');m.act({'type':'start_round'})
    for role in ROLES:
        t=issue(m,role);assert t['context']['previousRoundOpinions']=={}
        m.act(submit(t,remote))
    previous=m.snapshot()['rounds'][0]['responses'];m.act({'type':'start_round'});contexts=[]
    for role in ROLES:
        t=issue(m,role);contexts.append(t['context']);assert t['context']['previousRoundOpinions']==previous
        m.act(submit(t,remote))
    assert contexts[0]==contexts[1]
    s=m.snapshot();assert s['phase']=='completed_unverified'
    for field in ['modelExecuted','piExecuted','identityAuthenticated','factActivated','consensusComputed']:assert s[field] is False
    assert all(x['relationship']=='same_labels_not_consensus' for x in s['rounds'][-1]['comparison'])
    assert verify_snapshot(m.export())['factActivated'] is False

@pytest.mark.parametrize('outcome',['stop','failed','unknown'])
def test_stop_preserves_partial_and_rejects_late(outcome):
    m=Meeting();m.act({'type':'start_round'});m.act(submit(issue(m,ROLES[0])));t=issue(m,ROLES[1]);old=m.snapshot()['rounds'][0]['responses']
    m.act({'type':'stop'} if outcome=='stop' else {'type':'fail_turn','ticketId':t['ticketId'],'outcome':outcome})
    assert m.snapshot()['rounds'][0]['responses']==old
    assert m.snapshot()['phase']==('stopped_by_operator' if outcome=='stop' else 'stopped_'+outcome)
    with pytest.raises(MeetingError):m.act(submit(t))
    assert verify_snapshot(m.export())['phase']==m.snapshot()['phase']

def test_deadline_old_exact_replay_does_not_keep_next_slot_alive():
    clock=[0];m=Meeting(clock=lambda:clock[0]);m.act({'type':'start_round'});a=submit(issue(m,ROLES[0]));m.act(a);issue(m,ROLES[1]);clock[0]=600
    assert m.act(a)['phase']=='timed_out'

def test_repeated_issue_submit_and_mutation_are_local_safe():
    m=Meeting();m.act({'type':'start_round'});t=issue(m,ROLES[0]);assert issue(m,ROLES[0])==t
    a=submit(t);m.act(a);before=m.export();m.act(a);assert m.export()==before
    a['reviews'][0]['rationale']='mutated'
    with pytest.raises(MeetingError):m.act(a)
    assert m.export()==before

def test_bad_context_and_mode_atomic():
    m=Meeting();m.act({'type':'start_round'});t=issue(m,ROLES[0]);before=m.export()
    for a in [submit(t,True),{**submit(t),'contextDigest':'0'*64}]:
        with pytest.raises(MeetingError):m.act(a)
        assert m.export()==before

def test_public_pin_and_shared_source():
    raw=load_packet();assert hashlib.sha256(raw).hexdigest()=='1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e'
    p=_packet(raw);assert len({json.dumps(i['sourceLocator'],sort_keys=True) for i in p['items']})==1
    assert all(set(i)=={'itemId','claim','sourceText','sourceSha256','sourceLocator','citation'} for i in p['items'])
    with pytest.raises(GroupError):_packet(raw+b' ')

def test_isolated_four_file_stdlib_closure(tmp_path):
    names=['research/expert_group/packet.py','research/expert_group/public-packet.json','research/expert_meeting/machine.py','research/expert_meeting/demo.py']
    for name in names:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path(name).read_bytes())
    code="import socket; socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network')); from research.expert_meeting.machine import Meeting,verify_snapshot; m=Meeting(); m.act({'type':'stop'}); assert verify_snapshot(m.export())['phase']=='stopped_by_operator'; import sys; assert not any(x in sys.modules for x in ['research.expert_group.engine','httpx','research.expert_remote.transport']); print('stdlib closure passed')"
    r=subprocess.run([sys.executable,'-S','-c',code],cwd=tmp_path,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True)
    assert r.returncode==0,r.stderr

@pytest.mark.parametrize('field',['modelExecuted','piExecuted','identityAuthenticated'])
def test_remote_snapshot_cannot_upgrade_execution_claim(field):
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'});m.act(submit(issue(m,ROLES[0]),True))
    data=json.loads(m.export());data['state'][field]=True
    with pytest.raises(MeetingError):verify_snapshot(json.dumps(data).encode())
