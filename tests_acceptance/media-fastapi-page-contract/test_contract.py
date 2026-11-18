"""Normal synthetic workflows only: real ASGI API + actual page JS, fake DOM.
No socket server/browser/model; no role header, refusal or paused probes.
"""
import json
import selectors
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from tools.media_review_demo.prepare import prepare
from tools.media_review_demo.launch import settings_for, check_manifest
from mcis_service.media_review_demo import create_media_review_demo
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit.service import verify_chain


def workflow(tmp_path, kind):
    manifest = prepare(tmp_path)
    root = Path(manifest['dataDir'])
    assert check_manifest(root/'demo-manifest.json', root) == manifest
    assert manifest['modelExecuted'] is False and manifest['archiveSupported'] is False
    settings = settings_for(manifest)
    app = create_media_review_demo(settings)
    assert app.state.image_ocr_runtime is None and app.state.audio_asr_runtime is None
    with TestClient(app) as client:
        page = client.get('/'+kind+'-review-lab')
        assert page.status_code == 200
        proc = subprocess.Popen(['node', str(Path(__file__).with_name('page.cjs'))],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            proc.stdin.write(json.dumps({'kind':kind, 'html':page.text, 'manifest':manifest})+'\n');proc.stdin.flush()
            watched = selectors.DefaultSelector();watched.register(proc.stdout, selectors.EVENT_READ)
            result = None
            calls = []
            while True:
                assert watched.select(15), 'fixed synthetic page runner timed out'
                line = proc.stdout.readline()
                assert line, 'page runner exited before workflow completion: '+proc.stderr.read()
                msg = json.loads(line)
                if msg['type'] == 'done':
                    result = msg;break
                assert msg['type'] == 'request'
                opts = msg['options'];headers = opts.get('headers', {})
                assert set(headers) <= {'Content-Type'}
                path = msg['url'];assert path.startswith('/api/v1/cases/'+manifest['caseId']+'/'+kind+'-reviews')
                response = client.request(opts.get('method','GET'), path, headers=headers, content=opts.get('body'))
                # Stop immediately on any unexpected status; no retries/role changes.
                assert response.status_code in (200,201), (path,response.status_code)
                calls.append((opts.get('method','GET'),path,response.status_code))
                proc.stdin.write(json.dumps({'status':response.status_code,'body':response.json()})+'\n');proc.stdin.flush()
            proc.wait(timeout=5);assert proc.returncode == 0, proc.stderr.read()
            assert len(calls) == result['requests'] == 6
        finally:
            if proc.poll() is None:
                proc.terminate();proc.wait(timeout=5)
    doc = result['doc']
    assert doc['revision'] == 2
    history = doc['reviews'] if kind == 'image' else doc['humanRevisions']
    assert [r['text'] for r in history] == ['SYNTHETIC correction 1','SYNTHETIC correction 2']
    if kind == 'audio':
        assert all(r['startMs'] is None and r['endMs'] is None and r['factVerified'] is False for r in history)
    with TestClient(create_media_review_demo(settings)) as reopened:
        response = reopened.get('/api/v1/cases/'+manifest['caseId']+'/'+kind+'-reviews/'+doc['runId'])
        assert response.status_code == 200 and response.json() == doc
    with app.state.db.session() as session:
        audit = session.scalars(select(AuditEventRow).where(AuditEventRow.case_id==manifest['caseId']).order_by(AuditEventRow.seq)).all()
        assert verify_chain([r.line for r in audit])['valid']
        edits = [r for r in audit if r.entity_id == doc['runId'] and r.action == ('ocr.review' if kind=='image' else 'audio.human.revise')]
        assert len(edits) == 2


def test_image_prepare_create_edit_twice_and_reopen(tmp_path):
    workflow(tmp_path, 'image')


def test_audio_prepare_create_edit_twice_and_reopen(tmp_path):
    workflow(tmp_path, 'audio')
