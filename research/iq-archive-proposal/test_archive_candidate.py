import base64, hashlib, json
import pytest
from test_validate import example
from archive_candidate import preflight, InvalidArchive, VERSION

def bundle():
    cid,issues,events,receipts,raw=example();sha=hashlib.sha256(raw).hexdigest()
    return {'version':VERSION,'sourceCaseId':cid,'issues':issues,
      'events':[dict(issueId=i,sequence=n,event=e) for i,n,e in events],
      'receipts':[dict(zip(('operator','role','requestId','digest','issueId','response'),r)) for r in receipts],
      'evidence':[{'evidenceId':'EV-001','sha256':sha,'descriptor':{'evidenceId':'EV-001','sha256':sha},'bytesBase64':base64.b64encode(raw).decode()}]}

def encoded(d):return json.dumps(d,ensure_ascii=False,separators=(',',':')).encode()
def check(d,allow=True):return preflight(encoded(d),lambda c,e,h:allow)

def test_round_trip_preflight():
    d=bundle();assert check(d)==d

def test_missing_original_evidence_fails_closed():
    d=bundle();d['evidence']=[]
    with pytest.raises(InvalidArchive):check(d)

def test_inaccessible_evidence_fails_closed():
    with pytest.raises(InvalidArchive):check(bundle(),False)

@pytest.mark.parametrize('damage',['wrong_bytes','duplicate_evidence','extra_version','wrong_descriptor','extra_field','unknown_version','orphan_event','missing_receipt','noncanonical_b64'])
def test_damaged_bundle_rejected(damage):
    d=bundle();e=d['evidence'][0]
    if damage=='wrong_bytes':e['bytesBase64']=base64.b64encode(b'altered').decode()
    elif damage=='duplicate_evidence':d['evidence'].append(e.copy())
    elif damage=='extra_version':
        data=b'another';h=hashlib.sha256(data).hexdigest();d['evidence'].append({'evidenceId':'EV-001','sha256':h,'descriptor':{'evidenceId':'EV-001','sha256':h},'bytesBase64':base64.b64encode(data).decode()})
    elif damage=='wrong_descriptor':e['descriptor']['sha256']='0'*64
    elif damage=='extra_field':d['other']=1
    elif damage=='unknown_version':d['version']='future'
    elif damage=='orphan_event':d['issues']=[]
    elif damage=='missing_receipt':d['receipts'].pop()
    elif damage=='noncanonical_b64':e['bytesBase64']+='\n'
    with pytest.raises(InvalidArchive):check(d)

def test_duplicate_keys_and_nonfinite_rejected():
    for data in (b'{"version":"a","version":"b"}',b'{"n":NaN}'):
        with pytest.raises(InvalidArchive):preflight(data,lambda *args:True)

def test_unknown_descriptor_field_rejected():
    d=bundle(); d['evidence'][0]['descriptor']['unvalidated']='unsafe'
    with pytest.raises(InvalidArchive):check(d)

def test_cross_operator_repeated_request_id_fails_closed():
    # The underlying current data model allows this. Keep both histories
    # otherwise valid so rejection tests the proposed stricter profile.
    from validate import validate
    d=bundle();other=bundle();other['issues'][0]['createdBy']='another'
    other['events'][0]['event']['actor']='another'
    other['receipts'][0]['operator']='another'
    other['receipts'][0]['response']['event']['actor']='another'
    other['receipts'][0]['requestId']=d['receipts'][0]['requestId']
    d['issues']+=other['issues'];d['events']+=other['events'];d['receipts']+=other['receipts']
    events=[(r['issueId'],r['sequence'],r['event']) for r in d['events']]
    keys=('operator','role','requestId','digest','issueId','response')
    receipts=[tuple(r[k] for k in keys) for r in d['receipts']]
    raw=b'old evidence'
    assert validate(d['sourceCaseId'],d['issues'],events,receipts,lambda *_:raw,lambda *_:True)
    with pytest.raises(InvalidArchive):check(d)

def test_unknown_role_consistent_across_event_and_receipt_rejected():
    d=bundle()
    for event in d['events']:event['event']['role']='InventedRole'
    for receipt in d['receipts']:
        receipt['role']='InventedRole';receipt['response']['event']['role']='InventedRole'
    with pytest.raises(InvalidArchive):check(d)
