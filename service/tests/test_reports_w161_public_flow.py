"""Public Haili report HTTP lifecycle: source draft, review, version, exports and audit."""
import hashlib
import json
import pytest

from .conftest import H
from mcis_service.common import contracts


@pytest.mark.parametrize('template', ['imo-cic', 'maib', 'cn-msa'])
def test_haili_public_report_full_lifecycle(client, template):
    prefix = '/api/v1/cases/CASE-2025-HAILI5-WANA17'
    created = client.post(prefix + '/reports', headers=H(), json={'templateId': template, 'lang': 'bilingual'})
    assert created.status_code == 201, created.text
    report = created.json()
    assert report['isFictionalDemo'] is False and report['realDataStatus'] == 'authorized-public'
    assert report['status'] == 'Draft' and not contracts.errors('report', report)
    text = json.dumps(report, ensure_ascii=False)
    assert '海力5' in text and 'WAN HAI A17' in text
    assert '不作责任认定' in text and 'W14 推演对比表未提供' in text
    rid = report['reportId']
    assert client.get(prefix + '/reports/' + rid, headers=H()).json() == report
    assert client.get(prefix + '/reports', headers=H()).json()['reports'][0]['reportId'] == rid
    sid = report['sections'][0]['sectionId']
    reviewed = client.patch(prefix + f'/reports/{rid}/sections/{sid}', headers=H(),
                            json={'action': 'modify', 'textZh': '人工复核记录', 'reason': '逐项核对公开来源'})
    assert reviewed.status_code == 200, reviewed.text
    audit = client.get(prefix + f'/reports/{rid}/audit', headers=H()).json()
    snapshot = audit[-1]['snapshotRef'].split(':', 1)[1]
    assert client.get(prefix + '/report-snapshots/' + snapshot, headers=H()).json()['reason'] == '逐项核对公开来源'
    regenerated = client.post(prefix + f'/reports/{rid}:generate', headers=H())
    assert regenerated.status_code == 201, regenerated.text
    assert regenerated.json()['version'] == 2 and regenerated.json()['parentReportId'] == rid
    for fmt in ('pdf', 'docx'):
        exported = client.get(prefix + f'/reports/{rid}/export?format={fmt}&lang=bilingual', headers=H())
        assert exported.status_code == 200, exported.text[:200] if exported.status_code != 200 else ''
        assert exported.content.startswith(b'%PDF' if fmt == 'pdf' else b'PK')
        assert exported.headers['x-sha256'] == hashlib.sha256(exported.content).hexdigest()
    gisis = client.get(prefix + '/gisis', headers=H())
    assert gisis.status_code == 200 and gisis.json()['realDataStatus'] == 'authorized-public'
    assert not contracts.errors('report#/$defs/gisis', gisis.json())
    for fmt in ('json', 'csv'):
        response = client.get(prefix + '/gisis/export?format=' + fmt, headers=H())
        assert response.status_code == 200
    draft = client.post(prefix + '/reports/sections/colreg:draft', headers=H(), json={})
    assert draft.status_code == 201 and draft.json()['report']['isFictionalDemo'] is False


def test_haili_cn_template_contains_official_headings_without_generated_conclusions(client):
    prefix = '/api/v1/cases/CASE-2025-HAILI5-WANA17'
    response = client.post(prefix + '/reports', headers=H(),
                           json={'templateId': 'cn-msa', 'lang': 'zh'})
    assert response.status_code == 201, response.text
    report = response.json()
    assert not contracts.errors('report', report)
    liability = next(section for section in report['sections'] if section['sectionId'] == 'official-conclusions')
    assert liability['missing'] is True
    assert all(sentence['missing'] for sentence in liability['sentences'])
    assert report['isFictionalDemo'] is False
