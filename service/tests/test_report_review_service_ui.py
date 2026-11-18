"""One normal PATCH/GET with synthetic stored fixture, then captured-response UI replay.
No generation, seed, original evidence, core, model, denied operation or live server.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.common import contracts
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.reports.models import ReportRow
from .conftest import make_settings, H


def test_synthetic_sentence_patch_response_reaches_parent_view(tmp_path):
    cid, rid = 'CASE-SYNTHETIC-REVIEW', 'RPT-SYNTHETIC-REVIEW'
    case = dict(schemaVersion='1.0.0', caseId=cid, title='Synthetic review fixture',
                accidentType='Collision', caseEpochUtc='2026-01-01T00:00:00Z',
                incidentTimeUtc='2026-01-01T00:00:00Z',
                incidentLocation=dict(lonDeg=0.0, latDeg=0.0, heightM=0.0),
                isFictionalDemo=True, displayTimeZoneOffsetMinutes=0)
    text = dict(textZh='合成原文，不是实际事故资料。', textEn='Synthetic original, not case evidence.')
    sentence = dict(sentenceId='SYNTHETIC-S', status='Draft', source='Generated',
                    sourceStatus='CaseFields', **text, generatedText=deepcopy(text),
                    reviewedBy=None, reviewedAt=None, reviews=[], missing=True,
                    citations=[dict(kind='evidence', id='SYNTHETIC-E',
                        href=f'#/evidence?case={cid}&id=SYNTHETIC-E',
                        registration='unregistered', unregistered=True, needsReview=True)])
    section = dict(sectionId='analysis', titleZh='合成章节', titleEn='Synthetic section',
                   dataSources=['synthetic-fixture'], status='Draft', source='Generated',
                   **text, generatedText=deepcopy(text), reviewedBy=None, reviewedAt=None,
                   reviews=[], missing=True, sentences=[sentence])
    report = dict(reportId=rid, familyId=rid, parentReportId=None, caseId=cid,
                  templateId='imo-cic', lang='bilingual', version=1, status='Draft',
                  isFictionalDemo=True, realDataStatus='fictional', createdBy='Synthetic fixture',
                  createdUtc='2026-01-01T00:00:00Z', sections=[section],
                  disclaimerZh='不作责任认定', disclaimerEn='Synthetic fixture only',
                  reportHref=f'#/report?case={cid}&report={rid}')
    contracts.validate('case', case)
    contracts.validate('report', report)
    app = create_app(make_settings(tmp_path, seed=False))
    # Explicit setup only; no access policy/dependency overrides or invented generation audit.
    with app.state.db.session() as s:
        put_doc(s, CaseRow, cid, cid, case)
        put_doc(s, ReportRow, cid, rid, report)
    headers = H('LeadInvestigator', operator='Synthetic reviewer')
    path = f'/api/v1/cases/{cid}/reports/{rid}'
    body = dict(action='modify', sentenceId=sentence['sentenceId'],
                textZh='合成人工修改，仅用于普通回归。', reason='Synthetic normal review')
    with TestClient(app) as client:
        initial = client.get(path, headers=headers)
        assert initial.status_code == 200, initial.text
        response = client.patch(path+'/sections/analysis', headers=headers, json=body)
        assert response.status_code == 200, response.text
        returned = response.json()
        saved = client.get(path, headers=headers)
        assert saved.status_code == 200, saved.text
        events = client.get(path+'/audit', headers=headers)
        assert events.status_code == 200, events.text
    current = returned['sentences'][0]
    assert current['source'] == current['sourceStatus'] == 'Investigator'
    assert current['generatedText'] == sentence['generatedText']
    assert current['citations'] == sentence['citations']
    assert current['textEn'] == sentence['textEn'] and current['textZh'] == body['textZh']
    assert saved.json()['sections'][0] == returned
    event = next(e for e in events.json() if e['auditEvent']['action'] == 'report.review.modify')
    assert event['beforeValue']['source'] == 'Generated'
    assert event['afterValue']['sourceStatus'] == 'Investigator'
    assert current['reviews'][-1]['beforeValue'] == event['beforeValue']
    assert current['reviews'][-1]['afterValue'] == event['afterValue']
    capture = dict(case=case, initial=initial.json(), body=body, returned=returned, saved=saved.json())
    web = Path(__file__).resolve().parents[2] / 'web'
    run = subprocess.run(['node', 'tests/report-review-service-response.test.cjs'], cwd=web,
                         input=json.dumps(capture), text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'captured service response' in run.stdout
