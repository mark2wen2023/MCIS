"""Main-only PR64 + PR61 chain; synthetic case, real ZIP/intake/archive bytes."""
import hashlib
from urllib.parse import quote
import pytest
from .test_working_record_archive import client_at, checked, exported, imported, ROOT, HEAD
from .test_restored_attachment_filename import attach, accesses


@pytest.mark.parametrize('fmt', ['pdf', 'docx'])
def test_zip_permission_and_unicode_name_survive_repeated_restore(tmp_path, fmt):
    name = '调查报告 “副本” 😀 100%.zip'
    limited = {**HEAD, 'X-MCIS-Role': 'Investigator'}
    with client_at(tmp_path/'origin', True) as client:
        report = checked(client, 'post', ROOT+'/reports', {'templateId': 'imo-cic', 'lang': 'zh'}, 201).json()
        path = ROOT+'/reports/'+report['reportId']+'/output-bundle'
        digest = checked(client, 'get', path+':preview').json()['reportDocumentSha256']
        bundle = checked(client, 'post', path, {'format': fmt, 'lang': 'zh', 'expectedReportDigest': digest})
        raw = bundle.content
        receipt = attach(client, raw, name)
        routes = [('get', ROOT+'/evidence/'+receipt['evidenceId']+'/content', None),
                  ('post', ROOT+'/evidence-intakes/'+receipt['requestDigest']+':download', {'purpose': 'Synthetic integration check'})]
        for method, url, body in routes:
            before = accesses(client)
            denied = checked(client, method, url, body, headers=limited, status=403)
            assert accesses(client) == before
            assert 'content-disposition' not in denied.headers
            assert denied.headers['cache-control'] == 'no-store'
            allowed = checked(client, method, url, body)
            assert allowed.content == raw and accesses(client) == before+1
        package = exported(client)
    for turn in range(2):
        with client_at(tmp_path/f'restored-{turn}') as client:
            imported(client, package)
            url = ROOT+'/archive-history/evidence/'+receipt['evidenceId']+'/content'
            before = accesses(client)
            denied = checked(client, 'get', url, headers=limited, status=403)
            assert accesses(client) == before and 'content-disposition' not in denied.headers
            response = checked(client, 'get', url)
            assert response.content == raw
            assert response.headers['x-sha256'] == hashlib.sha256(raw).hexdigest()
            assert response.headers['content-disposition'] == 'attachment; filename="historical-source.bin"; filename*=UTF-8\'\'' + quote(name, safe='')
            assert response.headers['cache-control'] == 'no-store'
            assert accesses(client) == before+1
            checked(client, 'get', ROOT+'/evidence-intakes/'+receipt['requestDigest'], status=409)
            package = exported(client)
