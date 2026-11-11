"""W12.1 independent regression: historical numeric identity and explicit derivation labels.

The numeric fingerprint was computed from the pre-W12.1 seed at upstream commit
 ddb9dffaa7e2d0e2c7ee82ff28b95c45cd4224d8, not from the implementation under test.
This proves no numeric drift; it is NOT a substitute for independent CPA computation.
"""
import hashlib
import json

from conftest import H, LILY, ROOT, YANGZE, get_analysis


def numeric_leaves(value, path=''):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield [path, value]
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from numeric_leaves(value[key], path + '/' + key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from numeric_leaves(item, path + '/' + str(index))


def test_w121_numeric_values_unchanged_from_pre_fix_commit():
    data = json.loads((ROOT / 'service/mcis_service/analysis/data/w12-analysis-seed.json').read_text())
    values = list(numeric_leaves(data))
    assert len(values) == 14539
    digest = hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    assert digest == 'b1d98497ef4c5cf7181557d0481f49d484d56242b9198a5b12ae67dec723fd0e'


def test_w121_each_heading_assumption_is_explicitly_marked_derived(client):
    for case_id in (LILY, YANGZE):
        data = get_analysis(client, case_id)
        assert '【推算】' in data['whatif']['curveNote']
        assumptions = [x for x in data['whatif']['assumptions'] if 'COG=船首向' in x]
        assert assumptions and all('【推算】' in x for x in assumptions)
    assert '航向作对地航向【推算】' in get_analysis(client, YANGZE)['baseline']['label']


def test_w121_analysis_routes_are_in_runtime_openapi(client):
    paths = client.get('/openapi.json', headers=H()).json()['paths']
    assert '/api/v1/analysis/cases' in paths
    # FastAPI uses the implementation's parameter spelling, rather than the YAML alias.
    assert any(path.startswith('/api/v1/cases/{') and path.endswith('}/analysis') for path in paths)
