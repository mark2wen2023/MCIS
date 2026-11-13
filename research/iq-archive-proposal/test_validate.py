from copy import deepcopy
import hashlib
from uuid import uuid4
import pytest
from mcis_service.investigation_issues.domain import transition,digest
from validate import validate,InvalidSnapshot


def example(raw=b'old evidence'):
    cid='case-1'; iid=str(uuid4()); h1=str(uuid4());h2=str(uuid4());sha=hashlib.sha256(raw).hexdigest();r=[{'evidenceId':'EV-001','sha256':sha}]
    ev={'sequence':1,'type':'Create','payload':{'title':'question','description':'description','sourceRefs':r},'actor':'a','role':'LeadInvestigator','utc':'2026-01-01T00:00:00Z','resultingStage':'Observed'}
    state={'issueId':iid,'caseId':cid,'title':'question','description':'description','initialSources':r,'revision':1,'stage':'Observed','round':0,'hypotheses':{},'currentVerifications':{},'packet':None,'createdBy':'a','createdUtc':ev['utc']}
    events=[(iid,1,ev)]; rid=str(uuid4()); req={'requestId':rid,'title':'question','description':'description','sourceRefs':r,'acknowledgeArchiveUnsupported':True}
    receipts=[('a','LeadInvestigator',rid,digest(req),iid,{'issueId':iid,'revision':1,'event':ev})]
    actions=[('RecordHypothesis',{'hypothesisId':h1,'text':'h1','reason':'r','expectedVersion':0,'sourceRefs':r}),('RecordHypothesis',{'hypothesisId':h2,'text':'h2','reason':'r','expectedVersion':0,'sourceRefs':[]}),('BeginVerification',{'question':'q','method':'m'}),('RecordVerification',{'hypothesisId':h1,'hypothesisVersion':1,'activity':'a','result':'r','outcome':'Supported','sourceRefs':r}),('RecordVerification',{'hypothesisId':h2,'hypothesisVersion':1,'activity':'a','result':'r','outcome':'Inconclusive','sourceRefs':[]}),('SubmitDiscussion',{'agenda':'a','unresolved':[]}),('RecordDiscussion',{'packetRevision':7,'summary':'s','dissent':[],'participantsRecorded':['x'],'outcome':'MoreVerification'})]
    for kind,p in actions:
        n=state['revision']+1; prior=state;state=transition(state,kind,p,n)
        ev={'sequence':n,'type':kind,'payload':p,'actor':'a','role':'LeadInvestigator','utc':'2026-01-01T00:00:00Z','resultingStage':state['stage'],'round':state['round']}
        if kind=='SubmitDiscussion':ev['packet']=deepcopy(state['packet'])
        if kind=='RecordDiscussion':ev['packet']=deepcopy(prior['packet'])
        rid=str(uuid4()); req={'requestId':rid,'expectedRevision':n-1,'type':kind,'payload':p,'issueId':iid}
        events.append((iid,n,ev));receipts.append(('a','LeadInvestigator',rid,digest(req),iid,{'issueId':iid,'revision':n,'event':deepcopy(ev)}))
    return cid,[state],events,receipts,raw

def run(x,access=True,raw=None):
    cid,issues,events,receipts,source=x
    return validate(cid,issues,events,receipts,lambda i,h: source if raw is None else raw,lambda i,h: access)

def test_multiple_hypotheses_and_historical_source():
    x=example(); assert len(run(x))==1

def test_bad_evidence_or_authorization_rejected():
    x=example()
    for kw in ({'raw':b'changed'}, {'access':False}):
        with pytest.raises(InvalidSnapshot):run(x,**kw)

@pytest.mark.parametrize('mutation', ['missing_event','missing_receipt','extra_receipt','changed_digest','changed_state','gap','receipt_actor','bad_packet'])
def test_inconsistent_snapshots_rejected(mutation):
    x=example();cid,issues,events,receipts,raw=x
    if mutation=='missing_event':events.pop(2)
    elif mutation=='missing_receipt':receipts.pop(2)
    elif mutation=='extra_receipt':receipts.append(deepcopy(receipts[0]))
    elif mutation=='changed_digest':
        a=list(receipts[1]);a[3]='0'*64;receipts[1]=tuple(a)
    elif mutation=='changed_state':issues[0]['stage']='Observed'
    elif mutation=='gap':events[1]=(events[1][0],99,events[1][2])
    elif mutation=='receipt_actor':
        a=list(receipts[1]);a[0]='other';receipts[1]=tuple(a)
    elif mutation=='bad_packet': events[-1][2]['packet']['agenda']='changed'
    with pytest.raises(InvalidSnapshot):run(x)

def test_orphan_rows_rejected():
    x=example(); x[1].clear()
    with pytest.raises(InvalidSnapshot):run(x)

def test_create_digest_may_not_be_reconstructible():
    x=example(); row=list(x[3][0]); row[3]='f'*64; x[3][0]=tuple(row)
    # Original create source ordering isn't retained. Treat digest as opaque.
    assert run(x)


def test_boolean_integer_cannot_masquerade_as_sequence_or_state():
    x=example(); x[2][0][2]['sequence']=True
    with pytest.raises(InvalidSnapshot):run(x)
    x=example(); x[1][0]['round']=True
    with pytest.raises(InvalidSnapshot):run(x)

def test_same_id_two_historical_hashes_both_required():
    a=example(b'old');b=example(b'new')
    issues=a[1]+b[1]; events=a[2]+b[2]; receipts=a[3]+b[3]
    versions={hashlib.sha256(z).hexdigest():z for z in (b'old',b'new')}
    found=validate('case-1',issues,events,receipts,lambda i,h:versions[h],lambda i,h:True)
    assert len(found)==2
    versions.pop(hashlib.sha256(b'old').hexdigest())
    with pytest.raises(InvalidSnapshot):
        validate('case-1',issues,events,receipts,lambda i,h:versions[h],lambda i,h:True)
