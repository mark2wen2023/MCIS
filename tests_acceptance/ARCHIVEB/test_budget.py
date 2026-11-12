"""Actual bounded package rejection with all manifest hashes recomputed."""
from helpers import *
import pytest
from mcis_service.package.mcase import manifest_json

def pack(files,version):
 files={k:v for k,v in files.items() if k!='manifest.json'}
 files['manifest.json']=manifest_json(CID,files,'2026-01-01T00:00:00Z',version).encode()
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for k,v in files.items():z.writestr(k,v)
 return out.getvalue()

def swap_artifact(outer,replacement):
 files=unzip(outer);d=json.loads(files[MEMBER]);assert len(d['historicalArtifacts'])==1
 old=d['historicalArtifacts'][0]['sha256'];new=sha(replacement);path='history/artifacts/'+new+'.bin'
 del files['history/artifacts/'+old+'.bin'];files[path]=replacement
 d['historicalArtifacts'][0].update(sha256=new,sizeBytes=len(replacement),relativePath=path)
 d['lineage']['nodes'][0]['artifactSha256']=new
 for h in d['importHistory']:
  if h['kind']=='package-intake' and h['key']==old:
   h['key']=new;h['sourceArtifactSha256']=new;h['metadata']['sourceSha256']=new;h['metadata']['byteLength']=len(replacement)
 files[MEMBER]=json.dumps(d,ensure_ascii=False).encode()
 return pack(files,'1.2.0')

@pytest.fixture
def history_package(tmp_path):
 with client(tmp_path/'A') as a:seed(a);populate(a);first=export(a)
 with client(tmp_path/'B') as b:assert intake(b,first,True).status_code==200;second=export(b)
 return first,second

@pytest.mark.parametrize('mode',['unknown-version','aggregate-members','wrong-case'])
def test_historical_inspection_is_bounded_and_structurally_bound(history_package,tmp_path,mode):
 first,outer=history_package;inside=unzip(first)
 if mode=='aggregate-members':
  # Each ZIP alone fits 2048; their combined inspected members do not.
  count=2040-len(inside)
  for i in range(count):inside[f'historical-padding/{i}.bin']=b'x'
  changed=pack(inside,'1.2.0')
 elif mode=='unknown-version':changed=pack(inside,'99.0.0')
 else:
  case=json.loads(inside['case.json']);case['caseId']='OTHER';inside['case.json']=json.dumps(case).encode();changed=pack(inside,'1.2.0')
 candidate=swap_artifact(outer,changed)
 with client(tmp_path/'target') as c:
  before=state(c)
  for commit in (False,True):
   r=intake(c,candidate,commit);assert r.status_code==(413 if mode=='aggregate-members' else 422),r.text
   if mode=='aggregate-members':assert r.json()['code']=='ARCHIVE_BUDGET'
   assert state(c)==before

def test_actual_default_64mib_aggregate_inspection_budget(history_package,tmp_path):
 first,outer=history_package;inside=unzip(first)
 outer_size=sum(map(len,unzip(outer).values()));inner_size=sum(map(len,inside.values()))
 # Materialize real bytes: inner remains below64MiB but outer+inner exceeds it.
 padding=64*1024*1024-inner_size-outer_size+4096
 assert padding>0
 for i in range(4):
  size=padding//4+(1 if i<padding%4 else 0)
  assert size<16*1024*1024
  inside[f'historical-large/{i}.bin']=b'0'*size
 changed=pack(inside,'1.2.0');candidate=swap_artifact(outer,changed)
 inner_bytes=sum(len(v) for v in unzip(changed).values());outer_bytes=sum(len(v) for v in unzip(candidate).values())
 assert inner_bytes<64*1024*1024 and outer_bytes<64*1024*1024
 assert inner_bytes+outer_bytes>64*1024*1024
 with client(tmp_path/'target') as c:
  before=state(c)
  r=intake(c,candidate);assert r.status_code==413 and r.json()['code']=='ARCHIVE_BUDGET',r.text
  assert state(c)==before

def fabricated_lineage(first,outer,count,chain):
 files=unzip(outer);d=json.loads(files[MEMBER]);original_package=next(x for x in d['importHistory'] if x['kind']=='package-intake')
 for a in d['historicalArtifacts']:del files[a['relativePath']]
 d['historicalArtifacts']=[];d['lineage']['nodes']=[];d['importHistory']=[h for h in d['importHistory'] if h['kind']!='package-intake']
 previous=None
 for i in range(count):
  import copy
  inside=unzip(first);inside['synthetic-history-marker.bin']=str(i).encode();raw=pack(inside,'1.2.0');h=sha(raw);path='history/artifacts/'+h+'.bin';files[path]=raw
  d['historicalArtifacts'].append({'sha256':h,'sizeBytes':len(raw),'relativePath':path,'mediaType':'application/octet-stream'})
  d['lineage']['nodes'].append({'artifactSha256':h,'parentArtifactSha256s':[previous] if chain and previous else []});previous=h
  history=copy.deepcopy(original_package);history['key']=h;history['sourceArtifactSha256']=h;history['metadata']['sourceSha256']=h;history['metadata']['byteLength']=len(raw);d['importHistory'].append(history)
 files[MEMBER]=json.dumps(d,ensure_ascii=False).encode();return pack(files,'1.2.0')

@pytest.mark.parametrize('count,chain,code',[(8,True,200),(9,True,413),(32,False,200),(33,False,413)])
def test_declared_lineage_and_artifact_count_boundaries(history_package,tmp_path,count,chain,code):
 first,outer=history_package;candidate=fabricated_lineage(first,outer,count,chain)
 with client(tmp_path/'target') as c:
  before=state(c);r=intake(c,candidate);assert r.status_code==code,r.text
  assert state(c)==before
