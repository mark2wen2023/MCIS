"""Independent synthetic protocol tests; no model evaluation."""
import copy
import socket
import pytest
from sqlalchemy import select
from tests.test_knowledge_w19 import c, content, create, review, H, B
from mcis_service.knowledge.models import KnowledgeCardRow
from mcis_service.knowledge import duplicates

def call(c,b=None,role='LeadInvestigator'):
 return c.post(B+'/duplicates:preview',json=content() if b is None else b,headers=H(role))

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_denial_precedes_scan(c,monkeypatch,role):
 def deny(*a,**k):raise AssertionError('unauthorized database read')
 monkeypatch.setattr(c.app.state.db,'session',deny)
 assert call(c,role=role).status_code==403

def test_no_outbound_source_fetch(c,monkeypatch):
 b=content();b['source'].update(type='Public',url='https://example.com/fixture')
 create(c,b)
 def deny(*a,**k):raise AssertionError('outbound network')
 monkeypatch.setattr(socket,'create_connection',deny);monkeypatch.setattr(socket.socket,'connect',deny)
 d=call(c,b).json();assert len(d['matches'])==1 and d['modelUsed'] is False

def test_approval_actors_not_returned(c):
 card=create(c);assert review(c,card).status_code==200
 d=call(c).json();m=d['matches'][0]
 for key in ['source','createdBy','reviewedBy','reviewNote','approvals','body','excerpt','rightsNote']:
  assert key not in m
 assert m['status']=='Published' and d['reviewRequired'] is True

def test_whitespace_claims_not_silently_normalized(c):
 create(c);b=content();b['body']+=' '
 assert call(c,b).json()['matches'][0]['reasons']==['same_source_excerpt']

def test_scan_incomplete_without_matches(c,monkeypatch):
 monkeypatch.setattr(duplicates,'SCAN_LIMIT',2)
 for i in range(3):
  b=content();b['source']['excerpt']+=str(i);create(c,b)
 d=call(c).json();assert d['matches']==[] and d['scanIncomplete'] is True and d['resultsTruncated'] is False

def test_malformed_nonmatch_still_fails(c):
 b=content();b['source']['excerpt']='different';card=create(c,b)
 with c.app.state.db.session() as s:
  r=s.scalar(select(KnowledgeCardRow).where(KnowledgeCardRow.card_id==card['cardId']));d=copy.deepcopy(r.doc);d['content']['source']['type']='Secret';r.doc=d
 r=call(c);assert r.status_code==409 and 'Secret' not in r.text

def test_card_identifier_format_fail_closed(c):
 card=create(c)
 with c.app.state.db.session() as s:
  r=s.scalar(select(KnowledgeCardRow).where(KnowledgeCardRow.card_id==card['cardId']));d=copy.deepcopy(r.doc);d['cardId']='../../not-a-card';r.card_id=d['cardId'];r.doc=d
 r=call(c);assert r.status_code==409

def test_invalid_body_no_implicit_candidate(c):
 for b in [{}, {'approved':True}, []]:
  assert call(c,b).status_code==422
 assert c.get(B+'/cards?status=Candidate',headers=H()).json()['total']==0
