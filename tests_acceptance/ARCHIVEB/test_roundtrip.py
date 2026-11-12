"""Prepared before freeze. Real API and three independent synthetic databases."""
from helpers import *

def test_three_databases_exact_records_chains_and_artifacts(tmp_path):
 with client(tmp_path/'A') as a:
  seed(a);fixture=populate(a);first=export(a);original=archive(first);files1=unzip(first)
  assert json.loads(files1['manifest.json'])['packageVersion']=='1.2.0'
  assert len(original['interviews'])==1 and len(original['reports'])==2 and len(original['manualReceipts'])==3
 with client(tmp_path/'B') as b:
  preview=intake(b,first);assert preview.status_code==200,preview.text
  assert preview.json()['workingRecordsExtension']['receiptMode']=='archive-only'
  restored=intake(b,first,True);assert restored.status_code==200,restored.text
  before=state(b);again=intake(b,first,True);assert again.status_code==200 and state(b)==before
  inert(b,fixture)
  r=b.get(BASE+'/archive-history/evidence/'+fixture['evidenceId']+'/content',headers=H)
  assert r.status_code==200 and r.content==fixture['raw'] and r.headers['cache-control']=='no-store'
  second=export(b);middle=archive(second);files2=unzip(second);originals_equal(original,middle)
  for chain in ('audit/audit.jsonl','audit/custody.jsonl'):assert files2[chain].startswith(files1[chain])
  assert files2['history/artifacts/'+sha(first)+'.bin']==first
 with client(tmp_path/'C') as c:
  restored=intake(c,second,True);assert restored.status_code==200,restored.text
  inert(c,fixture)
  old=c.get('/api/v1/packages/intakes/'+sha(first),headers=H);assert old.status_code==409,old.text
  active=c.get('/api/v1/packages/intakes/'+sha(second),headers=H);assert active.status_code==200,active.text
  third=export(c);final=archive(third);files3=unzip(third);originals_equal(original,final)
  for chain in ('audit/audit.jsonl','audit/custody.jsonl'):assert files3[chain].startswith(files2[chain])
  assert files3['history/artifacts/'+sha(first)+'.bin']==first
  assert files3['history/artifacts/'+sha(second)+'.bin']==second
  assert len(final['historicalArtifacts'])==2
  for entry in middle['importHistory']:assert entry in final['importHistory']

def test_optional_real_hfacs_cli_coexists_and_receipt_inert(tmp_path):
 with client(tmp_path/'A') as a:
  seed(a);populate(a)
  request={'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic archive combination','entries':[{'id':'entry','categoryCode':'UA-ERR-DEC','description':'Synthetic hypothesis','rationale':'Not a verified fact'}]},'expectedSources':[]}
  r=a.post(BASE+'/human-factors/hfacs:save',headers=H,json=request);assert r.status_code==200,r.text
  original=r.json()['document'];raw=export(a)
  assert 'hfacs/backup.v1.json' in unzip(raw)
 with client(tmp_path/'B') as b:
  r=intake(b,raw,True);assert r.status_code==200,r.text
  assert b.get(BASE+'/human-factors/hfacs:draft',headers=H).json()['document']==original
  r=b.post(BASE+'/human-factors/hfacs:save',headers=H,json=request);assert r.status_code==409 and r.json()['code']=='REQUEST_ARCHIVED',r.text
  again=export(b);assert json.loads(unzip(again)['hfacs/backup.v1.json'])==json.loads(unzip(raw)['hfacs/backup.v1.json'])

def test_more_than_50_full_report_snapshots_not_paginated(tmp_path):
 with client(tmp_path/'A') as a:
  seed(a);f=populate(a);rpt=f['reportId'];d=a.get(BASE+'/reports/'+rpt,headers=H).json();sid=d['sections'][0]['sectionId']
  for i in range(51):
   r=a.patch(BASE+'/reports/'+rpt+'/sections/'+sid,headers=H,json={'action':'confirm','reason':f'Synthetic history check {i}'});assert r.status_code==200,r.text
  raw=export(a);original=archive(raw);assert len(original['reportSnapshots'])>50
 with client(tmp_path/'B') as b:
  r=intake(b,raw,True);assert r.status_code==200,r.text
  again=archive(export(b));assert again['reportSnapshots']==original['reportSnapshots'];assert again['reports']==original['reports']
