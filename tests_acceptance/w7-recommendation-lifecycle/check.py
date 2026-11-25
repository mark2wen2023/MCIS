"""Pure-synthetic HTTP/SQLite acceptance; no network and no production identity."""
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


CASE = 'SYN-W7-LIFECYCLE'
ROOT = '/api/v1/cases/' + CASE
REC = ROOT + '/recommendations/SR-2099-77'
ROUND = ROOT + '/consultation/rounds'
BODY = '合成复核后正文：仅测试本地建议记录。'
LEAD = {'X-MCIS-Role': 'LeadInvestigator', 'X-MCIS-Operator': 'Synthetic%20local%20reviewer'}
DOC = {
    'caseId': CASE, 'title': 'Fictional W7 lifecycle only', 'schemaVersion': '1.0.0',
    'accidentType': 'Collision', 'incidentTimeUtc': '2026-01-01T00:00:00Z',
    'caseEpochUtc': '2026-01-01T00:00:00Z',
    'incidentLocation': {'latDeg': 0, 'lonDeg': 0}, 'displayTimeZoneOffsetMinutes': 0,
    'isFictionalDemo': True,
}

def req(c, method, path, expected=200, body=None, headers=LEAD):
    extra = {'json': body} if body is not None else {}
    r = c.request(method, path, headers=headers, **extra)
    assert r.status_code == expected, (method, path, r.status_code, r.text)
    return r.json()

def no_network(*args, **kwargs):
    raise AssertionError('outbound sockets are disabled')

def phase1(c):
    req(c, 'POST', '/api/v1/cases', 201, DOC)
    new = req(c, 'POST', ROOT + '/recommendations', 201, dict(
        id='SR-2099-77', title='Synthetic prevention recommendation',
        body='合成待复核正文。', addressee='Invented party A',
        causeNodeIds=['SYN-CAUSE-ONLY'], dueUtc='2099-01-01T00:00:00Z'))
    assert new['status'] == 'Draft'
    draft = req(c, 'PATCH', REC, body={'body': BODY})
    assert draft['status'] == 'Draft' and draft['body'] == BODY
    req(c, 'POST', REC + ':transition', 409, {'to': 'Closed'})
    draft_sha = hashlib.sha256(BODY.encode()).hexdigest()
    rnd = req(c, 'POST', ROUND, 201, {'draftVersion':new['id']+'-synthetic-reviewed',
        'draftSha256':draft_sha,'days':45,'isAgreedDeadline':True,
        'parties':[{'partyId':'A','name':'Invented party A'},
                   {'partyId':'B','name':'Invented party B'}]})
    assert rnd['draftSha256'] == draft_sha and rnd['isAgreedDeadline'] is True
    instant = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))
    assert instant(rnd['deadlineUtc'])-instant(rnd['openedUtc']) == timedelta(days=45)
    rpath = ROUND + '/' + str(rnd['roundNo'])
    req(c, 'POST', rpath+':close', 409)
    reply = req(c, 'POST', rpath+'/replies', 201, {'partyId':'A',
        'text':'Synthetic consultation acknowledgement', 'comments':['Synthetic review comment']})
    cid = reply['comments'][0]['commentId']
    req(c, 'PATCH', rpath+'/comments/'+cid, 422, {'decision':'PartiallyAdopted'})
    req(c, 'PATCH', rpath+'/comments/'+cid, body={'decision':'PartiallyAdopted','feedback':'Synthetic review rationale'})
    req(c, 'POST', rpath+'/waivers', 201, {'partyId':'B','reason':'Synthetic recorded waiver only'})
    closed = req(c, 'POST', rpath+':close')
    assert closed['isClosed'] and closed['comments'][0]['decision']=='PartiallyAdopted'
    assert req(c, 'GET', REC)['status']=='Draft'
    issued = req(c, 'POST', REC+':transition', body={'to':'Issued','note':'Synthetic local issuance after human review; never delivered'})
    assert issued['status']=='Issued' and issued['body']==BODY
    req(c, 'PATCH', REC, 409, {'body':'Do not rewrite issued body.'})
    h = req(c,'GET', REC+'/history')
    return issued, closed, h

def phase2(c, issued, closed, issued_history):
    assert req(c,'GET',REC)==issued and req(c,'GET',ROUND)==[closed]
    assert req(c,'GET',REC+'/history')==issued_history
    req(c,'GET',REC,403,headers={'X-MCIS-Role': 'ExternalExpert', 'X-MCIS-Operator': 'Invented%20observer'})
    req(c,'POST',REC+':transition',409,{'to':'Responded'})
    responded=req(c,'POST',REC+'/responses',201,{'party':'Invented party A','text':'Synthetic local reply'})
    assert responded['status']=='Responded'
    assert req(c,'PATCH',REC,body={'progressPct':60,'note':'Synthetic progress'})['progressPct']==60
    assert req(c,'POST',REC+':transition',body={'to':'Implemented','note':'Synthetic local verification'})['progressPct']==100
    final=req(c,'POST',REC+':transition',body={'to':'Closed','note':'Synthetic local close'})
    assert final['status']=='Closed' and final['body']==BODY and final['responses'][0]['text']=='Synthetic local reply'
    return final

BASE = '7dfb3261522ff6241b9f5b44f809dd405b28ffde'


def materialize(checkout: Path, dest: Path):
    def git(*args):
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env['GIT_NO_REPLACE_OBJECTS'] = '1'
        return subprocess.check_output(['git', '--no-optional-locks', '-C', str(checkout), *args], env=env)
    if Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve() != checkout:
        raise ValueError('--base-checkout must be a Git worktree root')
    if git('rev-parse', 'HEAD').decode().strip() != BASE:
        raise ValueError(f'--base-checkout must be at fixed commit {BASE}')
    tree = git('rev-parse', BASE + '^{tree}').decode().strip()
    pins = json.loads(Path(__file__).with_name('pins.json').read_text())
    for name, expected in pins.items():
        if not name.startswith(('service/', 'contracts/')) or '..' in Path(name).parts:
            raise ValueError('invalid pinned path')
        record = git('ls-tree', BASE, '--', name).decode().rstrip('\n')
        metadata, sep, key = record.partition('\t')
        fields = metadata.split()
        if not sep or key != name or fields not in (['100644', 'blob', expected], ['100755', 'blob', expected]):
            raise ValueError(f'Git tree pin mismatch: {name}')
        raw = git('cat-file', 'blob', expected)
        if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != expected:
            raise ValueError(f'Git blob bytes mismatch: {name}')
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    print(f'Pinned {len(pins)} Git tree entries from {BASE} tree {tree}')


def exercise(exact):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(exact / 'service'))
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    from tests.conftest import make_settings
    import mcis_service
    if not Path(mcis_service.__file__).resolve().is_relative_to(exact):
        raise ValueError('unexpected service import')
    with tempfile.TemporaryDirectory(prefix='w7-lifecycle-') as d, patch.object(socket.socket,'connect',no_network), patch.object(socket.socket,'connect_ex',no_network), patch.object(socket.socket,'sendto',no_network), patch.object(socket,'getaddrinfo',no_network):
        data=Path(d)
        def reopen():
            return create_app(make_settings(data,seed=False))
        a=reopen()
        with TestClient(a) as c: started=phase1(c)
        a.state.db.engine.dispose()
        b=reopen()
        with TestClient(b) as c: complete=phase2(c,*started)
        b.state.db.engine.dispose()
        e=reopen()
        with TestClient(e) as c:
            assert req(c,'GET',REC)==complete
            assert req(c,'GET',ROUND)==[started[1]]
            hist=req(c,'GET',REC+'/history')
            exp=['create','update','transition','response','progress','transition','transition']
            assert [a['action'] for a in hist]==['safetyrec.'+action for action in exp]
            assert [(x['from'],x['to']) for x in complete['history']]==[
                ('Draft','Issued'),('Issued','Responded'),('Responded','Implemented'),('Implemented','Closed')]
            audit=req(c,'GET',ROOT+'/audit')
            assert [a['action'] for a in audit if a['action'].startswith('consultation.')]==[
                'consultation.open','consultation.reply','consultation.decide','consultation.waive','consultation.close']
            assert req(c,'GET',ROOT+'/audit:verify')['valid'] is True
        e.state.db.engine.dispose()
    print('PASS W7 synthetic API lifecycle; 3 SQLite app instances, 7 recommendation + 5 consultation audit entries, verified chain; 0 outbound calls')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-checkout', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='w7-pinned-src-') as tmp:
        exact = Path(tmp)
        materialize(args.base_checkout.resolve(), exact)
        exercise(exact)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
