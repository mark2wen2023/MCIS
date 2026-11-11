"""W6.2新增验收：废弃字段确实拒绝、页面地址沿用注入配置。"""

import pytest

from conftest import H, LILY, ROOT


@pytest.mark.parametrize('body', [
    {'reviewStatus': 'Confirmed'},
    {'action': 'dismiss', 'reason': '已给合同理由', 'note': '旧字段仍须拒绝'},
])
def test_legacy_fields_rejected_without_mutation(client, body):
    prefix = f'/api/v1/cases/{LILY}'
    before = client.get(prefix + '/colreg', headers=H()).json()
    events = client.get(prefix + '/audit', headers=H()).json()
    result = client.patch(prefix + '/colreg/checks/CK-05', headers=H(), json=body)
    assert result.status_code == 422
    assert result.json()['code'] == 'VALIDATION_ERROR'
    assert 'Deprecation' not in result.headers
    assert client.get(prefix + '/colreg', headers=H()).json() == before
    assert client.get(prefix + '/audit', headers=H()).json() == events


@pytest.mark.parametrize('page', ['EvidencePage.tsx', 'RecommendationsPage.tsx'])
def test_remaining_page_headers_use_service_configuration(page):
    text = (ROOT / 'web/src/pages' / page).read_text()
    assert "import { SERVICE_ADDR } from '../config'" in text
    assert 'LIVE · {SERVICE_ADDR}' in text
    assert 'LIVE · 127.0.0.1:8765' not in text
