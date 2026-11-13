import sys
from pathlib import Path
sys.path.insert(0,str(Path('iq-impl-0930/tree/service/tests').resolve()))
from test_investigation_issues import c,new,event,hypo,begin,verify,submit,get,H,BASE,ROOT,counts,rid
from sqlalchemy import select
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.db import put_doc

def test_readonly_role_cannot_mutate(c):
 i,_=new(c)
 with c.app.state.db.session()as s:
  p=default_policy();p['matrix']['LeadInvestigator']['report_draft']='ReadOnly';put_doc(s,AccessPolicyRow,'IQ-SYNTHETIC','policy',p)
 assert c.get(BASE+'/'+i,headers=H).status_code==200
 r=c.post(BASE+'/'+i+'/events',headers=H,json={'requestId':rid(),'expectedRevision':1,'type':'RecordHypothesis','payload':{}});assert r.status_code==403

def test_export_blocks_receipt_without_current_issue_or_events(c):
 from mcis_service.investigation_issues.models import IssueRow,EventRow
 from sqlalchemy import text
 i,_=new(c)
 with c.app.state.db.session()as s:
  # Explicit corruption fixture: bypass append trigger only in isolated test DB.
  s.execute(text('DROP TRIGGER investigation_issue_events_no_delete'))
  s.execute(text('DELETE FROM investigation_issue_events'))
  s.delete(s.scalar(select(IssueRow)))
 r=c.get(ROOT+'/export',headers=H);assert r.status_code==409;assert r.json()['code']=='ISSUE_ARCHIVE_UNSUPPORTED'

def test_new_hypothesis_invalidates_previous_discussion(c):
 i,_=new(c);h=hypo(c,i);begin(c,i);verify(c,i,h);submit(c,i);old=get(c,i)['packet']['revision']
 hypo(c,i)
 event(c,i,'RecordDiscussion',{'packetRevision':old,'summary':'stale','dissent':[],'participantsRecorded':['x'],'outcome':'OpinionRecorded'},409)
