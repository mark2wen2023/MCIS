"""Additional synthetic CPA boundary checks; all core calls are stubbed."""
import pytest
from .test_current_analysis_w122 import client, point, points, request, core, ar

@pytest.mark.parametrize('mutation',['null','wrong_command','empty_version','wrong_result','negative_distance','nonfinite_tcpa','degenerate_nonnull','equal_velocity_diverging'])
def test_additional_core_fail_closed(client,monkeypatch,mutation):
    if mutation=='equal_velocity_diverging':
        a,b=point('A',0),point('B',0);b['sogKn']=a['sogKn'];points(client,[a,b])
    def altered(*args):
        env=core(*args)
        if mutation=='null':return None
        if mutation=='wrong_command':env['command']='other'
        elif mutation=='empty_version':env['coreVersion']=''
        elif mutation=='wrong_result':env['result']=[]
        else:
            row=env['result']['results'][0]
            if mutation=='negative_distance':row['currentDistanceNm']=-1
            elif mutation=='nonfinite_tcpa':row['tcpaMin']=float('inf')
            elif mutation=='degenerate_nonnull':row.update(isDegenerate=True,tcpaMin=1)
            elif mutation=='equal_velocity_diverging':row.update(isDegenerate=True,tcpaMin=None,dcpaNm=1,isDiverging=True)
        return env
    monkeypatch.setattr(ar,'_core',altered)
    response=request(client)
    assert response.status_code==502,response.text
    assert response.json()['code']=='ANALYSIS_CORE_OUTPUT'
    assert 'rows' not in response.json()
    assert response.headers['cache-control']=='no-store'

@pytest.mark.parametrize('field,value',[('timeSec',None),('utc','2026-01-01T00:00:00.0001Z'),('sogKn',float('inf')),('cogDeg',float('nan')),('hdgDeg',True)])
def test_reject_before_core(client,monkeypatch,field,value):
    a,b=point('A',0),point('B',0)
    if field=='timeSec':
        from .test_current_analysis_w122 import TrackPointRow,C
        with client.app.state.db.session() as s:
            row=s.query(TrackPointRow).filter_by(case_id=C,vessel_id='A').first();row.doc={**row.doc,field:value}
    else:
        a[field]=value;points(client,[a,b])
    monkeypatch.setattr(ar,'_core',lambda *args:pytest.fail('Invalid inputs must not reach core'))
    response=request(client)
    assert response.status_code==422,response.text
    assert 'rows' not in response.json()
    assert response.headers['cache-control']=='no-store'
