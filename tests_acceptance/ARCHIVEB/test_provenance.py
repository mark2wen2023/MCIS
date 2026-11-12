"""Latest-import provenance is canonical state comparison, not authentication."""
import json
import pytest
from helpers import *
from mcis_service.interviews.models import InterviewRow
from mcis_service.reports.models import ReportRow

def prov(c,kind,key):return c.get(BASE+'/archive-history/provenance/'+kind+'/'+key,headers=H)
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
@pytest.fixture
def restored(tmp_path):
 with client(tmp_path/'A') as a:seed(a);f=populate(a);raw=export(a)
 with client(tmp_path/'B') as b:
  r=intake(b,raw,True);assert r.status_code==200,r.text
  yield b,f,raw

@pytest.mark.parametrize('kind',['interview','report'])
def test_same_document_then_changed_and_new_not_auto_restored(restored,kind):
 c,f,raw=restored;key=f['recordId'] if kind=='interview' else f['reportId'];coll='interviews' if kind=='interview' else 'reports'
 old=next(x['doc'] for x in archive(raw)[coll] if x['key']==key);before=state(c);r=prov(c,kind,key)
 assert r.status_code==200 and r.headers['cache-control']=='no-store',r.text
 p=r.json()['provenance'];assert p['sourceArchiveSha256']==sha(raw) and p['originalDocumentSha256']==sha(canonical(old))
 assert p['currentDocumentSha256']==p['originalDocumentSha256'] and p['changedSinceImport'] is False
 assert state(c)==before
 if kind=='interview':
  r=c.post(BASE+'/interviews/'+key+'/turns',headers=H,json={'question':'Synthetic post-restore','answer':'Not an imported answer'});assert r.status_code==201,r.text
  r=c.get(BASE+'/interviews/'+key,headers=H);now=r.json()
 else:
  section=old['sections'][0]['sectionId'];r=c.patch(BASE+'/reports/'+key+'/sections/'+section,headers=H,json={'action':'modify','textZh':'Synthetic post-restore revision','reason':'Synthetic test'});assert r.status_code==200,r.text
  now=c.get(BASE+'/reports/'+key,headers=H).json()
 r=prov(c,kind,key);assert r.status_code==200,r.text
 p=r.json()['provenance'];assert p['changedSinceImport'] is True and p['currentDocumentSha256']==sha(canonical(now))
 assert p['originalDocumentSha256']==sha(canonical(old))

def test_no_active_intake_and_new_id_null(tmp_path):
 with client(tmp_path/'A') as a:
  seed(a);f=populate(a);assert prov(a,'interview',f['recordId']).json()['provenance'] is None
  raw=export(a)
 with client(tmp_path/'B') as b:
  assert intake(b,raw,True).status_code==200
  r=b.post(BASE+'/interviews',headers=H,json={'interviewee':{'intervieweeId':'NEW','name':'Synthetic new','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z'});assert r.status_code==201,r.text
  r=prov(b,'interview',r.json()['recordId']);assert r.status_code==200 and r.json()['provenance'] is None,r.text

@pytest.mark.parametrize('damage',['missing','bytes','symlink'])
def test_bad_source_never_null_or_path_leak(restored,damage,tmp_path):
 c,f,_=restored;path=c.app.state.settings.blob_dir/CID/'_package_intake/source.mcase'
 if damage=='bytes':path.write_bytes(b'SYNTHETIC damaged bytes')
 else:
  path.unlink()
  if damage=='symlink':other=tmp_path/'synthetic-other';other.write_bytes(b'Synthetic');path.symlink_to(other)
 r=prov(c,'interview',f['recordId']);assert r.status_code==409,r.text
 assert str(tmp_path) not in r.text and 'provenance' not in r.json()
 assert r.headers['cache-control']=='no-store'

def test_permission_before_missing_object(restored):
 c,f,_=restored
 r=c.get(BASE+'/archive-history/provenance/report/RPT-MISSING',headers={'X-MCIS-Role':'Investigator'})
 assert r.status_code==403 and 'HISTORY_NOT_FOUND' not in r.text
 r=prov(c,'report','RPT-MISSING');assert r.status_code==404

def test_original_source_change_still_blocks_after_current_unbound(restored):
 from mcis_service.evidence.models import EvidenceRow
 c,f,_=restored
 with c.app.state.db.session() as s:
  row=s.query(InterviewRow).filter_by(case_id=CID,key=f['recordId']).one();d=dict(row.doc);d.pop('evidenceId');d.pop('sourceSha256');put_doc(s,InterviewRow,CID,f['recordId'],d)
  er=s.query(EvidenceRow).filter_by(case_id=CID,key=f['evidenceId']).one();e=dict(er.doc);e['sha256']='e'*64;put_doc(s,EvidenceRow,CID,f['evidenceId'],e)
 before=state(c);r=prov(c,'interview',f['recordId']);assert r.status_code==409 and state(c)==before,r.text

@pytest.mark.parametrize('change',['denied','bytes','metadata','missing'])
def test_history_content_source_failure_no_access_or_file_side_effect(restored,change):
 from mcis_service.evidence.models import EvidenceRow
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.redaction.policy import default_policy
 c,f,_=restored
 with c.app.state.db.session() as s:
  item=dict(s.query(EvidenceRow).filter_by(case_id=CID,key=f['evidenceId']).one().doc)
  if change=='metadata':item['sha256']='f'*64;put_doc(s,EvidenceRow,CID,f['evidenceId'],item)
  elif change=='denied':
   p=default_policy();p['matrix']['LeadInvestigator']['audit']='Deny';put_doc(s,AccessPolicyRow,CID,'policy',p)
 path=c.app.state.settings.blob_dir/CID/item['relativePath']
 if change=='bytes':path.write_bytes(b'Synthetic damaged bytes')
 elif change=='missing':path.unlink()
 before=state(c);r=c.get(BASE+'/archive-history/evidence/'+f['evidenceId']+'/content',headers=H)
 assert r.status_code==(403 if change=='denied' else 409),r.text
 assert f['raw'] not in r.content and r.headers['cache-control']=='no-store'
 assert state(c)==before
