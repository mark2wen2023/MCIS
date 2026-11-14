"""Synthetic protocol/data tests, not model or expert evaluation."""
import copy
import pytest
from sqlalchemy import select, func
from tests.test_knowledge_w19 import c, content, create, review, H, B
from mcis_service.knowledge.models import KnowledgeCardRow, KnowledgeAuditRow

def preview(c, body=None, role='Investigator'):
 return c.post(B+'/duplicates:preview',json=body or content(),headers=H(role))

def test_empty_and_no_write(c):
 r=preview(c);assert r.status_code==200,r.text
 d=r.json();assert d['matches']==[] and d['scanned']==0 and not d['scanIncomplete']
 assert not d['persisted'] and not d['modelUsed'] and d['reviewRequired']
 assert c.get(B+'/audit',headers=H()).json()==[]

def test_exact_match(c):
 card=create(c); before=c.get(B+'/audit',headers=H()).json()
 d=preview(c).json();m=d['matches'][0]
 assert m['cardId']==card['cardId'] and m['reasons']==['exact_content','same_source_excerpt']
 assert m['contentDigest']==d['inputDigest']
 assert set(m)=={'cardId','status','kind','title','contentDigest','reasons'}
 assert c.get(B+'/audit',headers=H()).json()==before

@pytest.mark.parametrize('field',['title','summary','body','applicability'])
def test_same_excerpt_not_content(c,field):
 create(c);b=content();b[field]='changed synthetic value'
 assert preview(c,b).json()['matches'][0]['reasons']==['same_source_excerpt']

@pytest.mark.parametrize('field',['locator','excerpt'])
def test_source_exact_no_normalization(c,field):
 create(c);b=content();b['source'][field]+=' '
 assert preview(c,b).json()['matches']==[]

def test_rights_and_title_not_identity(c):
 create(c);b=content();b['source']['rightsNote']='different assertion';b['source']['title']='different title'
 assert preview(c,b).json()['matches'][0]['reasons']==['same_source_excerpt']

def test_type_url_separate(c):
 create(c);b=content();b['source'].update(type='Public',url='https://example.com/fixture-not-a-report')
 assert preview(c,b).json()['matches']==[]
 create(c,b);b['source']['url']+='?a=1';assert preview(c,b).json()['matches']==[]

@pytest.mark.parametrize('role',['Public','ExternalExpert','InterestedState','AgentService'])
def test_denies_read(c,role):
 create(c);assert preview(c,role=role).status_code==403

@pytest.mark.parametrize('status',['Published','Rejected','Withdrawn'])
def test_all_statuses_kept(c,status):
 d=create(c)
 if status=='Withdrawn':assert review(c,d).status_code==200
 assert review(c,d,status).status_code==200
 assert preview(c).json()['matches'][0]['status']==status

def test_limits(c,monkeypatch):
 from mcis_service.knowledge import duplicates
 monkeypatch.setattr(duplicates,'SCAN_LIMIT',3);monkeypatch.setattr(duplicates,'RESULT_LIMIT',2)
 cards=[create(c) for _ in range(4)];r=preview(c).json()
 assert r['scanned']==3 and r['scanIncomplete'] and r['resultsTruncated']
 assert [m['cardId'] for m in r['matches']]==[d['cardId'] for d in cards[::-1][:2]]

def test_bad_input_no_write(c):
 b=content();b['approved']=True;assert preview(c,b).status_code==422
 assert c.get(B+'/audit',headers=H()).json()==[]

def test_corrupt_row_no_partial(c):
 create(c);d=create(c)
 with c.app.state.db.session() as s:
  row=s.scalar(select(KnowledgeCardRow).where(KnowledgeCardRow.card_id==d['cardId']));v=copy.deepcopy(row.doc);v['contentDigest']='0'*64;row.doc=v
 r=preview(c);assert r.status_code==409 and r.json()['code']=='INVALID_STORED_CARD'
 assert '合成正文' not in r.text
