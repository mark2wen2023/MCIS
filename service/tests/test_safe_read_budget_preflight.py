"""Synthetic local files; retain descriptor security and existing limit semantics."""
import os
import pytest
from mcis_service.common import safe_files


def test_oversize_rejects_before_any_read_and_closes_fd(tmp_path,monkeypatch):
    path=tmp_path/'oversize.bin'
    with path.open('wb') as f:f.truncate(32*1024*1024)
    observed=[];original=os.fstat
    def stat(fd):observed.append(fd);return original(fd)
    def forbidden(*a):raise AssertionError('oversize body read before rejection')
    monkeypatch.setattr(os,'fstat',stat);monkeypatch.setattr(os,'read',forbidden)
    with pytest.raises(safe_files.ReadBudgetExceeded):safe_files.read_regular_no_symlinks(path,8*1024*1024)
    assert observed
    with pytest.raises(OSError):original(observed[-1])


def test_growth_after_stat_still_rejected_and_closed(tmp_path,monkeypatch):
    path=tmp_path/'growing.bin';path.write_bytes(b'abc')
    original=os.fstat;observed=[]
    def grow(fd):
        info=original(fd);observed.append(fd)
        with path.open('ab') as f:f.write(b'd')
        return info
    monkeypatch.setattr(os,'fstat',grow)
    with pytest.raises(safe_files.ReadBudgetExceeded):safe_files.read_regular_no_symlinks(path,3)
    with pytest.raises(OSError):original(observed[-1])


@pytest.mark.parametrize('raw,limit',[(b'',0),(b'a',1),(b'abc',3),(b'\x00\xff',3)])
def test_existing_allowed_boundaries(tmp_path,raw,limit):
    p=tmp_path/'allowed.bin';p.write_bytes(raw)
    assert safe_files.read_regular_no_symlinks(p,limit)==raw


@pytest.mark.parametrize('limit',[True,False,-1,None,1.5,'8'])
def test_invalid_limit_rejected(tmp_path,limit):
    p=tmp_path/'file';p.write_bytes(b'x')
    with pytest.raises(ValueError):safe_files.read_regular_no_symlinks(p,limit)
