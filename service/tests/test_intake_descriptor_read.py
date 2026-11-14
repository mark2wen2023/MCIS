"""Local reader safety only; does not certify immutable storage or write races."""
import os
import pytest
from mcis_service.evidence_intake import router as intake
from .test_evidence_intake_w42 import local,save,URL,counts


def test_regular_and_size_limit(tmp_path,monkeypatch):
    path=tmp_path/'parent'/'source.bin';path.parent.mkdir();path.write_bytes(b'abc')
    monkeypatch.setattr(intake,'MAX_BYTES',3)
    assert intake.read_file(path)==b'abc'
    path.write_bytes(b'abcd')
    with pytest.raises(ValueError,match='budget'):intake.read_file(path)

@pytest.mark.parametrize('link_kind',['parent','leaf'])
def test_symlinks_never_followed(tmp_path,link_kind):
    outside=tmp_path/'outside';outside.mkdir();(outside/'source.bin').write_bytes(b'private')
    if link_kind=='parent':
        (tmp_path/'input').symlink_to(outside,target_is_directory=True);path=tmp_path/'input'/'source.bin'
    else:
        path=tmp_path/'source.bin';path.symlink_to(outside/'source.bin')
    with pytest.raises(OSError):intake.read_file(path)


def test_parent_replaced_after_open_stays_pinned(tmp_path,monkeypatch):
    parent=tmp_path/'input';parent.mkdir();(parent/'source.bin').write_bytes(b'original')
    outside=tmp_path/'outside';outside.mkdir();(outside/'source.bin').write_bytes(b'private')
    original=os.open;seen=[]
    def swap(path,flags,*args,**kwargs):
        fd=original(path,flags,*args,**kwargs);seen.append(fd)
        if path=='input':
            parent.rename(tmp_path/'old-input');parent.symlink_to(outside,target_is_directory=True)
        return fd
    monkeypatch.setattr(os,'open',swap);monkeypatch.setattr(os,'supports_dir_fd',os.supports_dir_fd|{swap})
    assert intake.read_file(parent/'source.bin')==b'original'
    for fd in seen:
        with pytest.raises(OSError):os.fstat(fd)


def test_unsupported_platform_returns_503_not_unsafe_fallback(local,monkeypatch):
    client,app=local
    _,receipt=save(client)
    before=counts(app)
    monkeypatch.delattr(os,'O_NOFOLLOW')
    r=client.get(URL+'/'+receipt['requestDigest'])
    assert r.status_code==503,r.text
    assert r.json()['code']=='INTAKE_SAFE_READ_UNAVAILABLE'
    r=client.post(URL+'/'+receipt['requestDigest']+':download',json={'purpose':'synthetic'})
    assert r.status_code==503,r.text
    assert counts(app)==before
