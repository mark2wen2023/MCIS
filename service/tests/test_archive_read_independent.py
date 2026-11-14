"""Independent shared-reader/archive boundary verification, Linux only."""
import os
import pytest
from fastapi import HTTPException
from mcis_service.working_records_archive import service as archive
from mcis_service.common import safe_files
from .test_intake_descriptor_independent import track,closed


def source(tmp_path):
    p=tmp_path/'CASE-A'/'history'/'source.bin';p.parent.mkdir(parents=True);return p

@pytest.mark.parametrize('limit',[256*1024,1024*1024,16*1024*1024,32*1024*1024])
def test_caller_limit_exact_and_plus_one(tmp_path,limit):
    p=source(tmp_path)
    with p.open('wb') as f:f.truncate(limit)
    assert len(archive.read_blob(tmp_path,'CASE-A','history/source.bin',limit))==limit
    with p.open('ab') as f:f.write(b'x')
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin',limit)
    assert e.value.status_code==413 and e.value.detail['code']=='ARCHIVE_BUDGET'
    assert p.stat().st_size==limit+1

@pytest.mark.parametrize('missing',['directory','dir_fd'])
def test_other_missing_capabilities_no_fallback(tmp_path,monkeypatch,missing):
    p=source(tmp_path);p.write_bytes(b'x')
    if missing=='directory':monkeypatch.delattr(os,'O_DIRECTORY')
    else:monkeypatch.setattr(os,'supports_dir_fd',set())
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin')
    assert e.value.status_code==503 and e.value.detail['code']=='ARCHIVE_SAFE_READ_UNAVAILABLE'

@pytest.mark.parametrize('mode',['fifo','read-error'])
def test_unreadable_archive_releases_descriptors(tmp_path,monkeypatch,mode):
    p=source(tmp_path)
    if mode=='fifo':os.mkfifo(p)
    else:p.write_bytes(b'x')
    seen=track(monkeypatch)
    if mode=='read-error':
        def bad(*args):raise OSError('read failed')
        monkeypatch.setattr(os,'read',bad)
    with pytest.raises(HTTPException) as e:archive.read_blob(tmp_path,'CASE-A','history/source.bin')
    assert e.value.status_code==409 and e.value.detail['code']=='ARCHIVE_HISTORY_INTEGRITY'
    closed(seen)


def test_zero_budget_and_short_reads(tmp_path,monkeypatch):
    p=source(tmp_path);p.write_bytes(b'')
    assert safe_files.read_regular_no_symlinks(p,0)==b''
    p.write_bytes(b'abc')
    with pytest.raises(safe_files.ReadBudgetExceeded):safe_files.read_regular_no_symlinks(p,0)
    original=os.read;monkeypatch.setattr(os,'read',lambda fd,n:original(fd,min(n,1)))
    assert safe_files.read_regular_no_symlinks(p,3)==b'abc'

@pytest.mark.parametrize('rel',['../source.bin','history/../../source.bin','history\\source.bin'])
def test_path_escape_rejected(tmp_path,rel):
    with pytest.raises(HTTPException):archive.read_blob(tmp_path,'CASE-A',rel)
