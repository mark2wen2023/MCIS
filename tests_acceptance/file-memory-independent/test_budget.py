"""Independent synthetic bounded-read and unchanged caller HTTP error semantics."""
import os
import pytest
from mcis_service.common import safe_files
from tests.test_evidence_intake_w42 import local,save,URL,CASE,counts


def test_growth_with_short_reads_stops_at_limit_plus_one(tmp_path,monkeypatch):
    p=tmp_path/'growing';p.write_bytes(b'a');original_stat=os.fstat;original_read=os.read;seen=[];reads=[]
    def stat(fd):
        info=original_stat(fd);seen.append(fd)
        with p.open('ab') as f:f.write(b'bcdefgh')
        return info
    def read(fd,n):
        data=original_read(fd,min(n,1));reads.append(data);return data
    monkeypatch.setattr(os,'fstat',stat);monkeypatch.setattr(os,'read',read)
    with pytest.raises(safe_files.ReadBudgetExceeded):safe_files.read_regular_no_symlinks(p,3)
    assert b''.join(reads)==b'abcd'
    with pytest.raises(OSError):original_stat(seen[-1])


def test_sparse_oversize_no_body_read_and_fd_closed(tmp_path,monkeypatch):
    p=tmp_path/'oversize';p.touch()
    with p.open('r+b') as f:f.truncate(128*1024*1024)
    original=os.fstat;seen=[]
    def stat(fd):seen.append(fd);return original(fd)
    def read(*args):raise AssertionError('over-budget body was read')
    monkeypatch.setattr(os,'fstat',stat);monkeypatch.setattr(os,'read',read)
    with pytest.raises(safe_files.ReadBudgetExceeded):safe_files.read_regular_no_symlinks(p,1024)
    assert len(seen)==1
    with pytest.raises(OSError):original(seen[0])


def test_directory_still_invalid_regular_file_not_budget_error(tmp_path):
    with pytest.raises(ValueError) as error:safe_files.read_regular_no_symlinks(tmp_path,0)
    assert type(error.value) is ValueError


def block_target_reads(monkeypatch,path):
    identity=path.stat();original=os.read;stat=os.fstat
    def read(fd,n):
        found=stat(fd)
        assert (found.st_dev,found.st_ino)!=(identity.st_dev,identity.st_ino),'oversized source body was read'
        return original(fd,n)
    monkeypatch.setattr(os,'read',read)


def test_intake_oversized_blob_still_integrity409_no_success_audit(local,monkeypatch):
    c,app=local;_,receipt=save(c)
    path=app.state.settings.blob_dir/CASE/'raw'/'evidence-intakes'/receipt['requestDigest']/'source.bin'
    assert path.is_file()
    with path.open('r+b') as f:f.truncate(8*1024*1024+1)
    block_target_reads(monkeypatch,path);before=counts(app)
    r=c.post(URL+'/'+receipt['requestDigest']+':download',json={'purpose':'independent synthetic budget'})
    assert r.status_code==409 and r.json()['code']=='INTAKE_INTEGRITY',r.text
    assert counts(app)==before


def test_historical_oversized_blob_still_budget413_no_success_audit(tmp_path,monkeypatch):
    from sqlalchemy import select
    from tests.test_working_record_archive import client_at,exported,imported,ROOT,CID,HEAD
    from tests.test_restored_attachment_filename import attach
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    with client_at(tmp_path/'source',True) as c:
        receipt=attach(c,b'synthetic original','source.bin');archive=exported(c)
    with client_at(tmp_path/'restore') as c:
        imported(c,archive)
        with c.app.state.db.session() as s:
            row=s.scalars(select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.kind=='evidence-intake')).one()
            path=c.app.state.settings.blob_dir/CID/row.doc['metadata']['relativePath']
        with path.open('r+b') as f:f.truncate(16*1024*1024+1)
        block_target_reads(monkeypatch,path);before=counts(c.app)
        r=c.get(ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content',headers=HEAD)
        assert r.status_code==413 and r.json()['code']=='ARCHIVE_BUDGET',r.text
        assert counts(c.app)==before
