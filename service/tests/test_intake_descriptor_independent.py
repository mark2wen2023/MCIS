"""Independent Linux fd safety checks, not write safety or Windows support."""
import os
from pathlib import Path
import pytest
from mcis_service.evidence_intake import router as intake


def track(monkeypatch):
    original=os.open;seen=[]
    def opened(*args,**kwargs):
        fd=original(*args,**kwargs);seen.append(fd);return fd
    monkeypatch.setattr(os,'open',opened)
    monkeypatch.setattr(os,'supports_dir_fd',os.supports_dir_fd|{opened})
    return seen


def closed(seen):
    for fd in set(seen):
        with pytest.raises(OSError):os.fstat(fd)


@pytest.mark.parametrize('kind',['directory','fifo','missing','parent-file'])
def test_rejected_objects_release_all_fds(tmp_path,monkeypatch,kind):
    leaf=tmp_path/'source.bin'
    if kind=='directory':leaf.mkdir()
    elif kind=='fifo':os.mkfifo(leaf)
    elif kind=='parent-file':
        leaf.write_bytes(b'x');leaf=leaf/'source.bin'
    seen=track(monkeypatch)
    with pytest.raises((OSError,ValueError)):intake.read_file(leaf)
    closed(seen)


def test_read_failure_releases_leaf(tmp_path,monkeypatch):
    leaf=tmp_path/'source.bin';leaf.write_bytes(b'x');seen=track(monkeypatch)
    def unavailable(*args,**kwargs):raise OSError('read failed')
    monkeypatch.setattr(os,'read',unavailable)
    with pytest.raises(OSError,match='read failed'):intake.read_file(leaf)
    closed(seen)


def test_parent_swap_before_open_rejects_symlink(tmp_path,monkeypatch):
    parent=tmp_path/'input';parent.mkdir();(parent/'source.bin').write_bytes(b'original')
    outside=tmp_path/'outside';outside.mkdir();(outside/'source.bin').write_bytes(b'private')
    original=os.open;seen=[]
    def swap(path,flags,*args,**kwargs):
        if path=='input':
            parent.rename(tmp_path/'old');parent.symlink_to(outside,target_is_directory=True)
        fd=original(path,flags,*args,**kwargs);seen.append(fd);return fd
    monkeypatch.setattr(os,'open',swap);monkeypatch.setattr(os,'supports_dir_fd',os.supports_dir_fd|{swap})
    with pytest.raises(OSError):intake.read_file(parent/'source.bin')
    closed(seen)


@pytest.mark.parametrize('path',[Path('relative/source.bin'),Path('/tmp/../source.bin')])
def test_unbounded_path_rejected_without_open(path,monkeypatch):
    seen=track(monkeypatch)
    with pytest.raises(ValueError):intake.read_file(path)
    assert seen==[]


def test_fstat_failure_releases_leaf(tmp_path,monkeypatch):
    leaf=tmp_path/'source.bin';leaf.write_bytes(b'x');seen=track(monkeypatch)
    original=os.fstat
    def unavailable(fd):raise OSError('stat failed')
    monkeypatch.setattr(os,'fstat',unavailable)
    with pytest.raises(OSError,match='stat failed'):intake.read_file(leaf)
    monkeypatch.setattr(os,'fstat',original)
    closed(seen)
