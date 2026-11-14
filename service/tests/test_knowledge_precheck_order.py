from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from .test_knowledge_w19 import c,content
from .test_knowledge_archive import counts
from mcis_service.knowledge import router

def test_both_guards_sequence_and_no_writes(c,monkeypatch):
 calls=[]
 for name in ('validate_actor','validate_content','validate_new_source_host'):
  original=getattr(router,name)
  def wrapper(*args,_n=name,_f=original):calls.append(_n);return _f(*args)
  monkeypatch.setattr(router,name,wrapper)
 body=content();body['source'].update(type='Public',url='https://.example.com/a')
 ctx=SimpleNamespace(db=c.app.state.db,operator='x'*161,role='Investigator');before=counts(c)
 with pytest.raises(HTTPException):router.create(body,ctx)
 assert calls==['validate_actor'] and counts(c)==before
 calls.clear();ctx.operator='valid'
 with pytest.raises(HTTPException):router.create(body,ctx)
 assert calls==['validate_actor','validate_content','validate_new_source_host'] and counts(c)==before
