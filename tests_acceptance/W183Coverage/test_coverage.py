"""Independent synthetic observations: algorithm boundary disclosure, not legal adjudication."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('rest_accept',Path(__file__).parents[1]/'W183/test_rest.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
client=base.client
runtime=base.runtime

def body(end,rows):
    return {'recordStartUtc':base.stamp(0),'recordEndUtc':base.stamp(end),'intervals':[{'startUtc':base.stamp(a),'endUtc':base.stamp(b),'kind':kind} for a,b,kind in rows]}
CASES={
 'three':body(24,[(0,6,'Rest'),(6,10,'Watch'),(10,14,'Rest'),(14,18,'Watch'),(18,19,'Rest'),(19,24,'Watch')]),
 'short':body(5,[(0,5,'Rest')]),
 'gap':body(27,[(0,6,'Rest'),(6,21,'Watch'),(21,27,'Rest')]),
 'minute':body(27,[(0,6,'Rest'),(6,13,'Watch'),(13,13+1/60,'Rest'),(13+1/60,21,'Watch'),(21,27,'Rest')]),
}
@pytest.mark.parametrize('name',CASES)
def test_actual_cli_api_equal_no_conclusion(client,name):
    b=CASES[name];computed=base.cli(b)
    response=client.post(base.url(),json={**b,'sourceEvidenceIds':['EV-001']})
    assert response.status_code==200,response.text
    data=response.json();assert data['result']==computed
    assert data['assessment']=='technical-preview-only' and data['persisted'] is False
    assert 'isCompliant' not in computed
    warnings='\n'.join(data['limitations'])
    assert '休息段数未评估' in warnings
    assert '短暂' in warnings and 'Rest' in warnings
    assert 'assumptions' in warnings and '合规' in warnings
    if name=='short':
        assert computed['coverage']['has24hWindow'] is False
        assert computed['coverage']['has7dWindow'] is False
        assert not computed['findings']
    if name=='three':
        assert computed['totals']['restHours']==11
        assert not any(f['rule']=='RestSplit' for f in computed['findings'])

def test_one_minute_input_changes_interval_detection_not_rest_qualification():
    gap=base.cli(CASES['gap']);minute=base.cli(CASES['minute'])
    assert any(f['rule']=='RestInterval' for f in gap['findings'])
    assert not any(f['rule']=='RestInterval' for f in minute['findings'])
    assert minute['totals']['restHours']==pytest.approx(12+1/60)
