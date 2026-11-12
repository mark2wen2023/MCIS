"""Actual simultaneous requests and controlled transaction failures."""
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from helpers import *
from test_provenance import restored,prov


def test_historical_content_commit_failure_sends_no_bytes_or_access(restored,monkeypatch):
 from sqlalchemy.orm import Session
 c,f,_=restored;before=state(c)
 def fail(*a,**k):raise RuntimeError('Synthetic commit failure')
 with monkeypatch.context() as patch:
  patch.setattr(Session,'commit',fail)
  with TestClient(c.app,raise_server_exceptions=False) as raw:
   r=raw.get(BASE+'/archive-history/evidence/'+f['evidenceId']+'/content',headers=H)
  assert r.status_code==500 and f['raw'] not in r.content and 'Synthetic commit failure' not in r.text
 assert state(c)==before


def test_historical_download_vs_export_no_lock_inversion(restored,monkeypatch):
 from mcis_service.evidence import service
 c,f,_=restored;original=service.append_custody;ready=threading.Event();release=threading.Event()
 def pause(*a,**k):
  if k.get('kind')=='Access':ready.set();assert release.wait(10)
  return original(*a,**k)
 monkeypatch.setattr(service,'append_custody',pause)
 with ThreadPoolExecutor(2) as pool:
  download=pool.submit(c.get,BASE+'/archive-history/evidence/'+f['evidenceId']+'/content',headers=H)
  assert ready.wait(10);package=pool.submit(c.get,BASE+'/export',headers=H)
  assert not package.done();release.set()
  assert download.result(timeout=4).content==f['raw']
  r=package.result(timeout=4);assert r.status_code==200,r.text


def test_provenance_and_old_writer_linearized_consistent_snapshot(restored,monkeypatch):
 from mcis_service.working_records_archive import router
 c,f,_=restored;original=router.read_blob;ready=threading.Event();release=threading.Event()
 def pause(*a,**k):
  raw=original(*a,**k);ready.set();assert release.wait(10);return raw
 monkeypatch.setattr(router,'read_blob',pause)
 with ThreadPoolExecutor(2) as pool:
  read=pool.submit(prov,c,'interview',f['recordId']);assert ready.wait(10)
  write=pool.submit(c.post,BASE+'/interviews/'+f['recordId']+'/turns',headers=H,json={'question':'Synthetic concurrent','answer':'Synthetic new state'})
  assert not write.done();release.set()
  r=read.result(timeout=4);assert r.status_code==200 and r.json()['provenance']['changedSinceImport'] is False,r.text
  assert write.result(timeout=4).status_code==201
 assert prov(c,'interview',f['recordId']).json()['provenance']['changedSinceImport'] is True
