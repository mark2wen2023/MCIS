"""Synthetic protocol tests only; no model evaluation."""
import copy
import importlib.util
import sys
from pathlib import Path
import pytest
from fastapi import HTTPException
# In repository runs the service package resolves normally.
path=Path(__file__).parents[1]/'mcis_service/knowledge/review_worksheet.py'
spec=importlib.util.spec_from_file_location('mcis_service.knowledge.review_worksheet',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from mcis_service.knowledge.router import digest

def content():
 return dict(kind='Case',title='合成审核样本',summary='非真实案件',body='合成正文',
 tags=['合成'],applicability='仅协议测试',source=dict(type='Synthetic',title='合成源',
 locator='第1段',excerpt='合成摘录',rightsNote='合成测试'))
def payload():
 c=content();return dict(content=c,expectedDigest=digest(c))
def test_default_all_pending():
 p=payload();before=copy.deepcopy(p);r=m.build(p)
 assert p==before
 assert len(r['checks'])==6 and all(x['status']=='pending' for x in r['checks'])
 assert all(x['status']=='pending' for x in r['requiredReleaseApprovals'])
 assert r['reviewRequired'] and not r['approvalGranted']
 for key in ('persisted','networkUsed','modelUsed'):assert r[key] is False
 assert r['distribution']=='internal_review_only'
def test_output_copy_does_not_mutate_input():
 p=payload();r=m.build(p);r['content']['source']['excerpt']='changed'
 assert p['content']['source']['excerpt']=='合成摘录'
def test_version_conflict():
 p=payload();p['content']['body']+='new'
 with pytest.raises(HTTPException) as e:m.build(p)
 assert e.value.status_code==409
@pytest.mark.parametrize('field',['reviewedBy','approvals','status','releaseApproved','reviewNote'])
def test_no_approval_or_operator_inputs(field):
 p=payload();p[field]=True
 with pytest.raises(HTTPException):m.build(p)
@pytest.mark.parametrize('field',['kind','title','summary','body','tags','applicability','source'])
def test_missing_content_fields(field):
 p=payload();del p['content'][field];p['expectedDigest']=digest(p['content'])
 with pytest.raises(HTTPException):m.build(p)
@pytest.mark.parametrize('value',[None,True,'abc','A'*64])
def test_bad_digest(value):
 p=payload();p['expectedDigest']=value
 with pytest.raises(HTTPException):m.build(p)
def test_public_is_still_pending():
 p=payload();p['content']['source'].update(type='Public',url='https://example.com/synthetic-fixture')
 p['expectedDigest']=digest(p['content']);r=m.build(p)
 assert r['sourceClassification']=='Public' and not r['approvalGranted']
 assert all(x['status']=='pending' for x in r['requiredReleaseApprovals'])
def test_missing_rights_cannot_export():
 p=payload();del p['content']['source']['rightsNote'];p['expectedDigest']=digest(p['content'])
 with pytest.raises(HTTPException):m.build(p)

def test_json_roundtrip_html_metacharacters_escaped():
 import json
 p=payload();p['content']['body']='<script>alert("test")</script>&'
 p['expectedDigest']=digest(p['content'])
 raw=m.export_json(p)
 assert '<' not in raw and '>' not in raw and '&' not in raw
 assert json.loads(raw)['content']==p['content']
 assert not json.loads(raw)['approvalGranted']
