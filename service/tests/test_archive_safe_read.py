"""Shared reader retains archive limits and historical-only authority boundary."""
import os
import pytest
from fastapi import HTTPException
from mcis_service.working_records_archive import service as archive
from mcis_service.common import safe_files


def source(tmp_path):
    p=tmp_path/'CASE-A'/'history'/'source.bin';p.parent.mkdir(parents=True);p.write_bytes(b'abc');return p


def test_archive_budget_and_no_mutation(tmp_path):
    p=source(tmp_path)
    assert archive.read_blob(tmp_path,'CASE-A','history/source.bin',3)==b'abc'
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin',2)
    assert e.value.status_code==413 and e.value.detail['code']=='ARCHIVE_BUDGET'
    assert p.read_bytes()==b'abc'


def test_archive_directory_rejects_without_fd_leak(tmp_path,monkeypatch):
    p=source(tmp_path);p.unlink();p.mkdir()
    real=os.open;seen=[]
    def opened(*a,**kw):
        fd=real(*a,**kw);seen.append(fd);return fd
    monkeypatch.setattr(os,'open',opened);monkeypatch.setattr(os,'supports_dir_fd',os.supports_dir_fd|{opened})
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin')
    assert e.value.status_code==409
    for fd in set(seen):
        with pytest.raises(OSError):os.fstat(fd)


def test_archive_parent_swap_after_open_pins_original(tmp_path,monkeypatch):
    p=source(tmp_path);outside=tmp_path/'outside';outside.mkdir();(outside/'source.bin').write_bytes(b'other')
    real=os.open
    def swapped(path,flags,*args,**kwargs):
        fd=real(path,flags,*args,**kwargs)
        if path=='history':
            p.parent.rename(tmp_path/'old-history');p.parent.symlink_to(outside,target_is_directory=True)
        return fd
    monkeypatch.setattr(os,'open',swapped);monkeypatch.setattr(os,'supports_dir_fd',os.supports_dir_fd|{swapped})
    assert archive.read_blob(tmp_path,'CASE-A','history/source.bin')==b'abc'


def test_archive_platform_failure_and_history_not_activation(tmp_path,monkeypatch):
    source(tmp_path);monkeypatch.delattr(os,'O_NOFOLLOW')
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin')
    assert e.value.status_code==503 and e.value.detail['code']=='ARCHIVE_SAFE_READ_UNAVAILABLE'
    with pytest.raises(HTTPException) as history:archive.historical_only()
    assert history.value.status_code==409 and history.value.detail['code']=='ARCHIVE_HISTORY_ONLY'


def test_archive_default_not_accidentally_limited_to_intake_eight_mib(tmp_path):
    p=source(tmp_path);raw=b'x'*(8*1024*1024+1);p.write_bytes(raw)
    assert archive.read_blob(tmp_path,'CASE-A','history/source.bin')==raw
