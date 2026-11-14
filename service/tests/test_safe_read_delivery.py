"""Synthetic real API checks; no claim of hostile endpoint exfiltration."""
from pathlib import Path
import os
import pytest
from sqlalchemy import select
from tests.test_working_record_archive import origin,client_at,imported,checked,ROOT,HEAD
from mcis_service.evidence.models import CustodyEventRow


def accesses(client):
 with client.app.state.db.session() as s:
  return len(s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind=='Access')).all())


def test_restore_stays_historical(origin):
 c,details,raw,path=origin
 original,receipt,*_=details
 with client_at(path/'target-safe') as d:
  imported(d,raw)
  response=checked(d,'get',ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content')
  assert response.content==original
  checked(d,'get',ROOT+'/evidence-intakes/'+receipt['requestDigest'],status=409)
  checked(d,'get',ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content',headers={**HEAD,'X-MCIS-Role':'Public'},status=403)


@pytest.mark.parametrize('capability',['O_NOFOLLOW','O_DIRECTORY','dir_fd'])
def test_historical_unsupported_capability_no_success_access(origin,monkeypatch,capability):
 _,details,raw,path=origin
 _,receipt,*_=details
 with client_at(path/'target-capability') as d:
  imported(d,raw);before=accesses(d)
  if capability=='dir_fd':monkeypatch.setattr(os,'supports_dir_fd',set())
  else:monkeypatch.delattr(os,capability)
  r=checked(d,'get',ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content',status=503)
  assert r.json()['code']=='ARCHIVE_SAFE_READ_UNAVAILABLE'
  assert accesses(d)==before


def test_historical_directory_swap_refuses_without_access(origin,monkeypatch):
 _,details,raw,path=origin
 _,receipt,*_=details
 with client_at(path/'target-swap') as d:
  imported(d,raw);before=accesses(d)
  leaf=d.app.state.settings.blob_dir/'CASE-INTAKE'/receipt['evidence']['relativePath']
  outside=path/'outside-synthetic';outside.mkdir();(outside/'source.bin').write_bytes(b'different synthetic marker')
  old_is_symlink=Path.is_symlink;swaps=[]
  def swapped(p):
   result=old_is_symlink(p)
   if p==leaf and not swaps:
    leaf.parent.rename(leaf.parent.with_name('old-parent'))
    leaf.parent.symlink_to(outside,target_is_directory=True);swaps.append(True)
   return result
  monkeypatch.setattr(Path,'is_symlink',swapped)
  r=checked(d,'get',ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content',status=409)
  assert swaps==[True]
  assert b'different synthetic marker' not in r.content
  assert accesses(d)==before
