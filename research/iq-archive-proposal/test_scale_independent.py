# Independent research checks; no production .mcase export/import support.
# Tested against draft parent d466432806dc3f9627463c2baa9de3fdc7b97772.
# Run from repo root with existing service dependencies:
# PYTHONPATH=service:research/iq-archive-proposal python -m pytest -q research/iq-archive-proposal/test_validate.py research/iq-archive-proposal/test_archive_candidate.py research/iq-archive-proposal/test_scale_independent.py
# 38 synthetic tests passed locally; independent reviewer reran 38. Fixtures
# reuse domain transition/digest, so shared semantic bugs may be missed. These
# tests do not establish historical authenticity, completeness, permission
# provenance, crash safety, atomic restore, integration or browser acceptance.
# The existing export refusal guard remains mandatory.

"""Independent synthetic stress and fail-closed checks, research preflight only."""
import base64
from copy import deepcopy
import hashlib
import json
import pytest
from archive_candidate import preflight, InvalidArchive, VERSION
from test_validate import example


def sample():
    issues=[]; events=[]; receipts=[]; evidence=[]
    keys=('operator','role','requestId','digest','issueId','response')
    for i in range(8):
        raw=f'historical version {i}'.encode()
        cid,iss,ev,rec,_=example(raw)
        issues.extend(iss)
        events.extend(dict(issueId=a,sequence=n,event=e) for a,n,e in ev)
        receipts.extend(dict(zip(keys,r)) for r in rec)
        sha=hashlib.sha256(raw).hexdigest()
        evidence.append(dict(evidenceId='EV-001',sha256=sha,descriptor=dict(evidenceId='EV-001',sha256=sha),bytesBase64=base64.b64encode(raw).decode()))
    return dict(version=VERSION,sourceCaseId=cid,issues=issues,events=events,receipts=receipts,evidence=evidence)

def wire(d): return json.dumps(d,separators=(',',':')).encode()

def test_many_issues_and_versions_all_checked_without_mutation():
    d=sample(); original=deepcopy(d); seen=set()
    def auth(case,eid,sha):
        assert case=='case-1'; seen.add((eid,sha)); return True
    assert len(d['events'])==64
    assert preflight(wire(d),auth)==d
    assert d==original
    assert seen=={(e['evidenceId'],e['sha256']) for e in d['evidence']}

@pytest.mark.parametrize('failure',['restricted','missing_version','corrupt_version','missing_receipt','digest','event_and_response'])
def test_multihistory_damage_rejected(failure):
    d=sample(); old=d['evidence'][0]['sha256']
    if failure=='missing_version': d['evidence'].pop(0)
    elif failure=='corrupt_version': d['evidence'][0]['bytesBase64']=base64.b64encode(b'altered').decode()
    elif failure=='missing_receipt': d['receipts'].pop(20)
    elif failure=='digest': d['receipts'][20]['digest']='0'*64
    elif failure=='event_and_response':
        # Tamper a non-create event and its mirrored response consistently,
        # leaving its original digest and final state untouched.
        event=d['events'][17]['event']; event['payload']['text']='altered'
        d['receipts'][17]['response']['event']['payload']['text']='altered'
    with pytest.raises(InvalidArchive):
        preflight(wire(d),lambda c,e,h: not(failure=='restricted' and h==old))

def test_one_issue_more_than_fifty_events():
    from uuid import uuid4
    from mcis_service.investigation_issues.domain import transition, digest
    cid, issues, events, receipts, raw=example()
    state=issues[0]; iid=state['issueId']; hypothesis=next(iter(state['hypotheses']))
    for _ in range(52):
        n=state['revision']+1
        payload={'hypothesisId':hypothesis,'hypothesisVersion':1,'activity':'repeat check',
                 'result':'recorded','outcome':'Inconclusive','sourceRefs':[]}
        state=transition(state,'RecordVerification',payload,n)
        event={'sequence':n,'type':'RecordVerification','payload':payload,'actor':'a',
               'role':'LeadInvestigator','utc':'2026-01-01T00:00:00Z',
               'resultingStage':state['stage'],'round':state['round']}
        request_id=str(uuid4())
        request={'requestId':request_id,'expectedRevision':n-1,'type':event['type'],
                 'payload':payload,'issueId':iid}
        events.append((iid,n,event))
        receipts.append(('a','LeadInvestigator',request_id,digest(request),iid,
                         {'issueId':iid,'revision':n,'event':deepcopy(event)}))
    from validate import validate, InvalidSnapshot
    assert len(events)==60
    args=(cid,[state],events,receipts,lambda *_:raw,lambda *_:True)
    assert len(validate(*args))==1
    # Tail records must not be silently ignored or truncated.
    altered=deepcopy(receipts); row=list(altered[-1]); row[3]='0'*64; altered[-1]=tuple(row)
    with pytest.raises(InvalidSnapshot):
        validate(cid,[state],events,altered,lambda *_:raw,lambda *_:True)
