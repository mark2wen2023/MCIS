"""Experimental read-only IQ-1A snapshot validator. Not an archive parser or restore.

All inputs must be from one consistent DB snapshot. The caller supplies exact
historical evidence bytes and independently authorizes access. No production hook.
"""
from copy import deepcopy
import hashlib
import re
from mcis_service.investigation_issues.domain import transition, digest, refs, uid, txt, canonical

class InvalidSnapshot(ValueError): pass

def equal(a, b):
    return canonical(a) == canonical(b)

def need(ok):
    if not ok: raise InvalidSnapshot('inconsistent or unsupported IQ snapshot')

def validate(case_id, issues, events, receipts, evidence_bytes, authorize_ref):
    """Return unique (evidenceId, hash) references. Does not mutate inputs.

    events: [(issue_id, seq, event_doc)]
    receipts: [(operator, role, request_id, digest, issue_id, response)]
    evidence_bytes(id, hash) -> exact bytes; authorize_ref(id, hash) -> bool.
    Raises on absent, ambiguous, unauthorized, or invalid input.
    """
    try:
        need(len(issues)<=200 and len(events)<=100000 and len(receipts)<=100000)
        by_issue={}
        for d in issues:
            iid=d['issueId']; uid(iid); need(iid not in by_issue and d['caseId']==case_id)
            by_issue[iid]=deepcopy(d)
        indexed={}
        for iid, seq, ev in events:
            need(iid in by_issue and type(seq) is int and 1<=seq<=500 and type(ev['sequence']) is int and ev['sequence']==seq)
            need((iid,seq) not in indexed); indexed[iid,seq]=deepcopy(ev)
        rec_index={}; keys=set()
        for op,role,rid,dh,iid,response in receipts:
            txt(op,128); txt(role,32); uid(rid)
            # A recognized self-reported role is not authentication or proof
            # that authorization existed at the time of the original write.
            need(role in ('Investigator','LeadInvestigator'))
            need((op,role,rid) not in keys);keys.add((op,role,rid))
            need(iid in by_issue and response['issueId']==iid and type(response['revision']) is int)
            need(isinstance(dh,str) and re.fullmatch(r'[a-f0-9]{64}',dh) is not None)
            key=(iid,response['revision']);need(key not in rec_index);rec_index[key]=(op,role,rid,dh,deepcopy(response))
        need(set(indexed)==set(rec_index))
        all_refs=set()
        for iid, current in by_issue.items():
            revision=current['revision'];need(type(revision) is int and 1<=revision<=500)
            need({n for i,n in indexed if i==iid}==set(range(1,revision+1)))
            state=None
            for n in range(1,revision+1):
                ev=indexed[iid,n];op,role,rid,dh,response=rec_index[iid,n]
                need(equal(response,{'issueId':iid,'revision':n,'event':ev}))
                need(ev['actor']==op and ev['role']==role);txt(ev['utc'],128)
                payload=ev['payload']; kind=ev['type']
                if n==1:
                    need(set(ev)=={'sequence','type','payload','actor','role','utc','resultingStage'} and kind=='Create')
                    need(set(payload)=={'title','description','sourceRefs'} and ev['resultingStage']=='Observed')
                    txt(payload['title'],200);txt(payload['description']); sources=refs(payload['sourceRefs'])
                    need(sources==payload['sourceRefs'])
                    state={'issueId':iid,'caseId':case_id,'title':payload['title'],'description':payload['description'],'initialSources':sources,'revision':1,'stage':'Observed','round':0,'hypotheses':{},'currentVerifications':{},'packet':None,'createdBy':op,'createdUtc':ev['utc']}
                    request={'requestId':rid,'title':payload['title'],'description':payload['description'],'sourceRefs':sources,'acknowledgeArchiveUnsupported':True}
                else:
                    need(kind!='Create')
                    fields={'sequence','type','payload','actor','role','utc','resultingStage','round'}
                    if kind in ('SubmitDiscussion','RecordDiscussion'):fields.add('packet')
                    need(set(ev)==fields)
                    prior=state;state=transition(state,kind,payload,n)
                    need(ev['resultingStage']==state['stage'] and type(ev['round']) is int and ev['round']==state['round'])
                    if kind=='SubmitDiscussion':need(equal(ev['packet'],state['packet']))
                    if kind=='RecordDiscussion':need(equal(ev['packet'],prior['packet']))
                    request={'requestId':rid,'expectedRevision':n-1,'type':kind,'payload':payload,'issueId':iid}
                # Create normalizes the event's source order but hashes the raw
                # request; its original order is not retained. Preserve opaque.
                if n>1: need(digest(request)==dh)
                for ref in refs(payload.get('sourceRefs',[])):
                    all_refs.add((ref['evidenceId'],ref['sha256']))
            need(equal(state,current))
        for eid,sha in all_refs:
            need(authorize_ref(eid,sha) is True)
            raw=evidence_bytes(eid,sha)
            need(type(raw) is bytes and hashlib.sha256(raw).hexdigest()==sha)
        return all_refs
    except InvalidSnapshot: raise
    except Exception as exc: raise InvalidSnapshot('inconsistent or unsupported IQ snapshot') from exc
