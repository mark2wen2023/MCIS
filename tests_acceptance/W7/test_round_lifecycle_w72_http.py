"""W7.2 real-HTTP acceptance, independent disposable DB per test; no outreach.
Reuses only the unchanged W7.1 loopback fixture, not its test functions.
"""
from datetime import datetime, timedelta
import pytest
from test_consultation_http import server, audit, unchanged_failure, OTHER

BASE='/consultation/rounds'
NEW={'draftVersion':'v-independent-72','parties':[{'partyId':'P-A','name':'Synthetic A'},{'partyId':'P-B','name':'Synthetic B'}], 'days':30,'isAgreedDeadline':False}

def finish_seed_round(call):
    for party in ['FLAG-B','CO-MARY']:
        assert call('POST',BASE+'/2/waivers',{'partyId':party,'reason':'Previously confirmed waiver (synthetic)'})[0]==201
    status,closed=call('POST',BASE+'/2:close',{})
    assert status==200 and closed['isClosed']
    return closed

def test_default_thirty_day_open_waive_close_persists_without_cross_case_changes(server):
    call=server; other=call('GET',BASE,case=OTHER)
    finish_seed_round(call)
    n=len(audit(call)); status,r=call('POST',BASE,NEW)
    assert status==201 and r['roundNo']==3
    assert datetime.fromisoformat(r['deadlineUtc'])-datetime.fromisoformat(r['openedUtc'])==timedelta(days=30)
    assert r['isAgreedDeadline'] is False and r['daysRemaining']==30
    assert len(audit(call))==n+1 and audit(call)[-1]['action']=='consultation.open'
    unchanged_failure(call,'POST',BASE,NEW,409)
    unchanged_failure(call,'POST',BASE+'/3:close',{},409)
    for party in ['P-A','P-B']:
        n=len(audit(call)); status,r=call('POST',BASE+'/3/waivers',{'partyId':party,'reason':'Confirmed written waiver (synthetic)'})
        assert status==201 and len(audit(call))==n+1
        assert audit(call)[-1]['action']=='consultation.waive'
        unchanged_failure(call,'POST',BASE+'/3/waivers',{'partyId':party,'reason':'duplicate'},409)
    n=len(audit(call)); status,r=call('POST',BASE+'/3:close',{})
    assert status==200 and r['isClosed'] and r['closedUtc'] and r['allReplied']
    assert len(audit(call))==n+1 and audit(call)[-1]['action']=='consultation.close'
    unchanged_failure(call,'POST',BASE+'/3:close',{},409)
    persisted=next(x for x in call('GET',BASE)[1] if x['roundNo']==3)
    assert persisted['isClosed'] and len(persisted['waivers'])==2
    assert all(x['status']=='Waived' for x in persisted['partyStatus'])
    assert call('GET',BASE,case=OTHER)==other
    assert call('GET','/audit:verify')[1]['valid']

def test_close_does_not_require_pending_comments_to_be_decided(server):
    call=server; closed=finish_seed_round(call)
    pending=next(c for c in closed['comments'] if c['decision']=='Pending')
    unchanged_failure(call,'POST',BASE+'/2/waivers',{'partyId':'FLAG-B','reason':'again'},409)
    n=len(audit(call))
    assert call('PATCH',f"{BASE}/2/comments/{pending['commentId']}",{'decision':'Adopted'})[0]==200
    assert len(audit(call))==n+1
    assert call('GET','/audit:verify')[1]['valid']

@pytest.mark.parametrize('role',['InterestedState','ExternalExpert','Public'])
def test_lifecycle_mutations_reject_readonly_and_deny_without_audit(server,role):
    call=server
    unchanged_failure(call,'POST',BASE,NEW,403,role)
    unchanged_failure(call,'POST',BASE+'/2/waivers',{'partyId':'FLAG-B','reason':'confirmed'},403,role)
    unchanged_failure(call,'POST',BASE+'/2:close',{},403,role)

def test_invalid_lifecycle_requests_no_audit(server):
    call=server
    unchanged_failure(call,'POST',BASE+'/2/waivers',{'partyId':'UNKNOWN','reason':'confirmed'},404)
    unchanged_failure(call,'POST',BASE+'/2/waivers',{'partyId':'FLAG-B','reason':''},422)
    unchanged_failure(call,'POST',BASE+'/2:close',{},409)
    finish_seed_round(call)
    for body in [{**NEW,'parties':[]},{**NEW,'days':0},{**NEW,'days':181}]:
        unchanged_failure(call,'POST',BASE,body,422)
    assert call('GET','/audit:verify')[1]['valid']
