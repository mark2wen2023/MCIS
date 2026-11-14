"""Existing writers, temporary test DB; synthetic principals are not authentication."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from .test_knowledge_w19 import c,content
from .test_knowledge_archive import counts
from mcis_service.knowledge.router import create,review
from mcis_service.knowledge_archive.service import envelope
from mcis_service.knowledge_archive.validation import validate,encode

def context(c,operator,role='Investigator'):
 return SimpleNamespace(db=c.app.state.db,operator=operator,role=role)
def archive(c):
 with c.app.state.db.session() as s:return validate(encode(envelope(s)))[0]
def decision(card):return {'decision':'Rejected','expectedDigest':card['contentDigest'],'note':'synthetic rejection, not real expert decision'}

@pytest.mark.parametrize('actor',['x'*161,'海'*161,'🙂'*161,'','  ',None,12,'x\x00y','x\x7fy','\ud800'])
@pytest.mark.parametrize('stage',['create','review'])
def test_reject_before_any_state_change(c,actor,stage):
 card=create(content(),context(c,'original'))
 before=counts(c);history=archive(c)
 with pytest.raises(HTTPException) as error:
  if stage=='create':create(content(),context(c,actor))
  else:review(card['cardId'],decision(card),context(c,actor,'LeadInvestigator'))
 assert error.value.status_code==422 and counts(c)==before
 after=archive(c);history.pop('exportedUtc');after.pop('exportedUtc');assert history==after

@pytest.mark.parametrize('actor',['x'*160,'海'*160,'🙂'*160,'e\u0301'*80,'保留 空格 ','a\nb\tc'])
def test_exact_unicode_preserved_and_archivable(c,actor):
 card=create(content(),context(c,actor));assert card['createdBy']==actor
 out=review(card['cardId'],decision(card),context(c,actor,'LeadInvestigator'))
 assert out['createdBy']==out['reviewedBy']==actor
 d=archive(c);assert d['cards'][0]['doc']['createdBy']==actor
 assert d['cards'][0]['doc']['reviewedBy']==actor

def test_no_fake_actor_authentication(c):
 # A syntactically valid caller-provided name is still accepted, NOT verified identity.
 card=create(content(),context(c,'synthetic unverified caller'))
 assert card['status']=='Candidate' and card['createdBy']=='synthetic unverified caller'
