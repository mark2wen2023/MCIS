"""Synthetic case, real report renderer/intake/archive APIs and independent SQLite stores."""
import base64
import copy
import hashlib
from urllib.parse import quote
import pytest
from sqlalchemy import select
from mcis_service.evidence.models import CustodyEventRow
from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
from .test_working_record_archive import client_at, checked, exported, imported, CID, ROOT, HEAD


def attach(c, raw, name):
    body = {'profile': 'mcis-evidence-intake-v1', 'fileName': name,
            'contentBase64': base64.b64encode(raw).decode(), 'title': 'Synthetic report copy',
            'source': 'Explicit synthetic report export', 'extractedBy': 'Synthetic recorder',
            'extractedUtc': '2026-01-01T00:00:00Z', 'category': 'Document',
            'confidentiality': 'Restricted', 'note': 'Fixture; no authentic report claim'}
    preview = checked(c, 'post', ROOT+'/evidence-intakes:preview', body).json()
    return checked(c, 'post', ROOT+'/evidence-intakes:commit',
                   {**body, 'confirmed': True, 'requestDigest': preview['requestDigest']}).json()


def accesses(c):
    with c.app.state.db.session() as s:
        return len(s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind == 'Access')).all())


@pytest.mark.parametrize('fmt', ['pdf', 'docx'])
def test_real_report_attachment_two_restores(tmp_path, fmt):
    name = '调查报告 “副本” 😀.' + fmt
    with client_at(tmp_path/'origin', True) as c:
        report = checked(c, 'post', ROOT+'/reports', {'templateId': 'imo-cic', 'lang': 'zh'}, 201).json()
        path = ROOT+'/reports/'+report['reportId']+'/output-bundle'
        digest = checked(c, 'get', path+':preview').json()['reportDocumentSha256']
        bundle = checked(c, 'post', path, {'format': fmt, 'lang': 'zh', 'expectedReportDigest': digest})
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(bundle.content)) as z:
            raw = z.read('report.'+fmt)
        receipt = attach(c, raw, name)
        archive = exported(c)
    for turn in range(2):
        with client_at(tmp_path/str(turn)) as c:
            imported(c, archive)
            before = accesses(c)
            response = checked(c, 'get', ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content')
            assert response.content == raw
            assert response.headers['x-sha256'] == hashlib.sha256(raw).hexdigest()
            assert response.headers['content-disposition'] == 'attachment; filename="historical-source.bin"; filename*=UTF-8\'\'' + quote(name, safe='')
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['content-type'] == 'application/octet-stream'
            assert accesses(c) == before+1
            checked(c, 'get', ROOT+'/evidence-intakes/'+receipt['requestDigest'], status=409)
            archive = exported(c)


@pytest.mark.parametrize('name', ['report";evil=.pdf', "report'%.docx", '报告\t.pdf', '../report.pdf'])
def test_header_names_and_rejected_controls(tmp_path, name):
    with client_at(tmp_path/'origin', True) as c:
        if '\t' in name or '/' in name:
            # Existing intake boundary must reject before any archival naming operation.
            from fastapi import HTTPException
            from mcis_service.evidence_intake.parser import metadata
            with pytest.raises(HTTPException):
                metadata({'profile':'mcis-evidence-intake-v1', 'fileName':name})
            return
        receipt = attach(c, b'synthetic opaque report', name)
        archive = exported(c)
    with client_at(tmp_path/'dest') as c:
        imported(c, archive)
        response = checked(c, 'get', ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content')
        assert response.headers['content-disposition'].endswith(quote(name, safe=''))
        assert len(response.headers.get_list('content-disposition')) == 1


@pytest.mark.parametrize('change', ['filename', 'digest', 'binding', 'missing', 'bytes'])
def test_corrupt_history_refuses_without_access(tmp_path, change, monkeypatch):
    with client_at(tmp_path/'origin', True) as c:
        receipt = attach(c, b'synthetic report bytes', 'report.pdf')
        archive = exported(c)
    with client_at(tmp_path/'dest') as c:
        imported(c, archive)
        with c.app.state.db.session() as s:
            row = s.scalars(select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.kind=='evidence-intake')).one()
            doc = copy.deepcopy(row.doc)
            if change == 'filename': doc['metadata']['binding']['fileName'] = 'different.pdf'
            elif change == 'digest': doc['metadata']['requestDigest'] = '0'*64
            elif change == 'binding': doc['metadata']['binding'] = []
            elif change == 'missing': del doc['metadata']['binding']['fileName']
            else:
                path = c.app.state.settings.blob_dir/CID/doc['metadata']['relativePath']
                path.write_bytes(b'changed bytes')
            history_key = row.key
        if change != 'bytes':
            # Simulated corrupt read result; leave append-only database protections intact.
            from types import SimpleNamespace
            from mcis_service.working_records_archive import router as history_router
            monkeypatch.setattr(history_router, 'archived_evidence',
                                lambda *a, **kw: SimpleNamespace(key=history_key, doc=doc))
        before = accesses(c)
        checked(c, 'get', ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content', status=409)
        assert accesses(c) == before


def test_denied_before_filename_disclosure(tmp_path):
    with client_at(tmp_path/'origin', True) as c:
        receipt = attach(c, b'synthetic report bytes', 'restricted-report.pdf')
        archive = exported(c)
    with client_at(tmp_path/'dest') as c:
        imported(c, archive)
        before = accesses(c)
        r = checked(c, 'get', ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content',
                    headers={**HEAD, 'X-MCIS-Role':'Public'}, status=403)
        assert 'restricted-report' not in r.text
        assert 'content-disposition' not in r.headers
        assert accesses(c) == before
