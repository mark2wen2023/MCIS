"""Synthetic multiline preservation; real existing routes, temporary test DB only."""
import pytest
from .test_knowledge_w19 import c,H,B,content
from .test_knowledge_archive import export,save,counts

def test_actual_newlines_tabs_preserved_in_card_and_archive(c):
 data=content();quote='第一行\n第二行\t限定条件'
 data['body']=quote;data['source']['excerpt']=quote
 r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==201,r.text
 assert r.json()['content']['body']==quote
 raw=export(c)
 import json
 archived=json.loads(raw)
 assert archived['cards'][0]['doc']['content']['source']['excerpt']==quote
 assert save(c,raw).status_code==201

@pytest.mark.parametrize('char',['\x00','\r','\x7f'])
def test_other_controls_remain_rejected_without_writes(c,char):
 data=content();data['body']='before'+char+'after';before=counts(c)
 r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==422 and counts(c)==before

def test_literal_slash_n_not_rewritten(c):
 data=content();data['body']=r'first\nsecond'
 r=c.post(B+'/cards',headers=H('Investigator'),json=data)
 assert r.status_code==201 and r.json()['content']['body']==r'first\nsecond'
