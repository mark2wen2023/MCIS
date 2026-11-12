"""Synthetic test data only. No changes to real case data; real-core test is explicit."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import math
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow,VesselRow,TrackPointRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.current_analysis import router as ar
from .conftest import make_settings
C='SYNTHETIC-W122';BASE=f'/api/v1/cases/{C}/analysis/current';E='2026-01-01T00:00:00Z'
H={'X-MCIS-Role':'LeadInvestigator'}

def point(vid,t,**kw):
    return dict(vesselId=vid,timeSec=t,utc=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=t)).isoformat(timespec='milliseconds').replace('+00:00','Z'),latDeg=0,lonDeg=0 if vid=='A' else .01,sogKn=10 if vid=='A' else 0,cogDeg=90,**kw)

def points(c,ps):
    with c.app.state.db.session() as s:
        s.query(TrackPointRow).filter_by(case_id=C).delete()
        for p in ps:s.add(TrackPointRow(case_id=C,vessel_id=p['vesselId'],time_sec=p['timeSec'],doc=p))

@pytest.fixture
def client(tmp_path):
    settings=make_settings(tmp_path,False)
    with TestClient(create_app(settings)) as c:
        with c.app.state.db.session() as s:
            put_doc(s,CaseRow,C,C,dict(caseId=C,title='Synthetic only',isFictionalDemo=True,caseEpochUtc=E,incidentLocation={'latDeg':0,'lonDeg':0}))
            for v in ('A','B'):put_doc(s,VesselRow,C,v,dict(caseId=C,vesselId=v,name=v))
        points(c,[point('A',0,provenance='Measured',source='unverified declared source'),point('B',0,provenance='Interpolated'),point('A',2),point('B',3)])
        yield c

def request(c,**params):return c.get(BASE,params={'ownVesselId':'A','targetVesselId':'B',**params},headers=H)

def core(_ctx,command,payload):
    assert command=='cpa'
    return {'ok':True,'command':'cpa','coreVersion':'test-double','result':{'results':[dict(pairId=p['pairId'],ownVesselId=p['own']['vesselId'],targetVesselId=p['target']['vesselId'],timeSec=p['timeSec'],currentDistanceNm=1.,dcpaNm=.2,tcpaMin=6.,isDegenerate=False,isDiverging=False,riskLevel='Danger') for p in payload['pairs']]}}

@pytest.fixture
def stub(monkeypatch):monkeypatch.setattr(ar,'_core',core)

def test_exact_pairs_provenance_no_interpolation_repeat_no_write(client,stub):
    def snapshot():
        with client.app.state.db.engine.connect() as conn:return {t:conn.exec_driver_sql('SELECT COUNT(*) FROM '+t).scalar() for t in ('track_points','audit_events','cases','vessels')}
    before=snapshot();a=request(client);b=request(client)
    assert a.status_code==200,a.text
    assert a.json()==b.json();r=a.json();assert r['counts']==dict(own=2,target=2,matched=1,unmatchedOwn=1,unmatchedTarget=1)
    assert len(r['rows'])==1 and r['rows'][0]['own']['provenance']=='Measured' and r['rows'][0]['target']['provenance']=='Interpolated'
    assert 'riskLevel' not in a.text and 'thresholds' not in a.text and before==snapshot()
    assert a.headers['cache-control']=='no-store'

def test_empty_and_no_common_do_not_call_core(client,monkeypatch):
    monkeypatch.setattr(ar,'_core',lambda *_:pytest.fail('core should not run'))
    for ps in ([],[point('A',0),point('B',1)],[point('A',0)]):
        points(client,ps);r=request(client);assert r.status_code==200,r.text;assert r.json()['rows']==[] and r.json()['coreVersion'] is None

@pytest.mark.parametrize('p',[{'ownVesselId':''},{'targetVesselId':'A'},{'targetVesselId':'missing'},{'fromSec':2,'toSec':1},{'fromSec':'NaN'},{'fromSec':'inf'},{'toSec':'oops'},{'fromSec':1e13}])
def test_bad_request(client,p):
    r=request(client,**p);assert r.status_code==422,r.text;assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('changes',[{'latDeg':91},{'lonDeg':181},{'sogKn':-1},{'sogKn':True},{'cogDeg':361},{'utc':'2026-02-30T00:00:00Z'},{'utc':'2026-01-01T00:00:01Z'},{'provenance':'Unknown'},{'source':None},{'source':'x'*4097},{'hdgDeg':361},{'rotDegPerMin':False},{'extraPrivate':'never disclose'}])
def test_bad_stored_point(client,changes):
    ps=[point('A',0),point('B',0)];ps[0].update(changes);points(client,ps)
    r=request(client);assert r.status_code==422,r.text;assert 'never disclose' not in r.text

def test_duplicate_and_row_doc_index(client):
    points(client,[point('A',0),point('A',0),point('B',0)]);assert request(client).json()['code']=='ANALYSIS_DUPLICATE_TIME'
    points(client,[point('A',0),point('B',0)])
    with client.app.state.db.session() as s:
        row=s.query(TrackPointRow).filter_by(case_id=C,vessel_id='A').first();row.doc={**row.doc,'timeSec':1}
    assert request(client).status_code==422

def test_local_domain_and_dateline(client,stub):
    ps=[point('A',0),point('B',0)];ps[0]['lonDeg']=2;points(client,ps);assert request(client).json()['code']=='ANALYSIS_LOCAL_DOMAIN'
    with client.app.state.db.session() as s:
        row=s.query(CaseRow).filter_by(case_id=C).first();row.doc={**row.doc,'incidentLocation':{'latDeg':0,'lonDeg':179.99}}
    ps[0]['lonDeg']=179.99;ps[1]['lonDeg']=-179.99;points(client,ps);assert request(client).status_code==200

def test_window_negative_fractional_and_unmatched_unknown(client,stub):
    points(client,[point(v,t) for v in ('A','B') for t in (-.5,0,1)])
    r=request(client,fromSec=-.5,toSec=0);assert r.status_code==200,r.text
    assert [p['timeSec'] for p in r.json()['rows']]==[-.5,0] and r.json()['counts']['own']==2
    assert 'provenance' not in r.json()['rows'][0]['own']

def test_limit(client,stub):
    points(client,[point('A',t) for t in range(5001)]+[point('B',0)])
    assert request(client).json()['code']=='ANALYSIS_POINT_LIMIT'
    r=request(client,toSec=4999);assert r.status_code==200 and r.json()['counts']['own']==5000

@pytest.mark.parametrize('field,value',[('pairId','wrong'),('ownVesselId','B'),('timeSec',1),('timeSec',False),('dcpaNm',None),('dcpaNm',-1),('dcpaNm',float('nan')),('tcpaMin',None),('isDegenerate',True),('isDiverging',True)])
def test_core_malformed(client,monkeypatch,field,value):
    def bad(*args):
        env=core(*args);env['result']['results'][0][field]=value;return env
    monkeypatch.setattr(ar,'_core',bad);r=request(client);assert r.status_code==502,r.text;assert r.headers['cache-control']=='no-store'

def test_core_missing_and_extra_rows(client,monkeypatch):
    for mode in ('missing','empty','extra'):
        def bad(*args):
            env=core(*args);rows=env['result']['results']
            if mode=='missing':del rows[0]['tcpaMin']
            elif mode=='empty':rows.clear()
            else:rows.append(deepcopy(rows[0]))
            return env
        monkeypatch.setattr(ar,'_core',bad);assert request(client).status_code==502

@pytest.mark.parametrize('mode',['data','source','epoch','policy'])
def test_change_during_core_discards(client,monkeypatch,mode):
    def changed(*args):
        env=core(*args)
        with client.app.state.db.session() as s:
            if mode=='policy':
                p=default_policy();p['matrix']['LeadInvestigator']['ais_sim']='Deny';put_doc(s,AccessPolicyRow,C,'policy',p)
            elif mode=='epoch':
                r=s.query(CaseRow).filter_by(case_id=C).first();r.doc={**r.doc,'title':'changed'}
            else:
                r=s.query(TrackPointRow).filter_by(case_id=C,vessel_id='A').first();r.doc={**r.doc,('sogKn' if mode=='data' else 'source'):20 if mode=='data' else 'updated'}
        return env
    monkeypatch.setattr(ar,'_core',changed);r=request(client);assert r.status_code==(403 if mode=='policy' else 409),r.text
    assert 'rows' not in r.json()

def test_unauthorized_and_missing(client,monkeypatch):
    with client.app.state.db.session() as s:
        p=default_policy();p['matrix']['Public']['ais_sim']='Deny';put_doc(s,AccessPolicyRow,C,'policy',p)
    monkeypatch.setattr(ar,'_core',lambda *_:pytest.fail('core should not run'))
    r=client.get(BASE,params={'ownVesselId':'A','targetVesselId':'B'},headers={'X-MCIS-Role':'Public'});assert r.status_code==403
    r=client.get(BASE.replace(C,'MISSING'),params={'ownVesselId':'A','targetVesselId':'B'},headers=H);assert r.status_code==404

def test_real_core_independent_analytic_geometry(client):
    # At latitude zero ENU east from origin equals WGS84 a*sin(lon), independently.
    points(client,[point('A',0),point('B',0)])
    r=request(client);assert r.status_code==200,r.text;row=r.json()['rows'][0]
    distance=6378137*math.sin(math.radians(.01))/1852
    assert row['currentDistanceNm']==pytest.approx(distance,abs=1e-6)
    assert row['dcpaNm']==pytest.approx(0,abs=1e-6)
    assert row['tcpaMin']==pytest.approx(distance/10*60,abs=1e-6)
    # Equal velocities: signed time is undefined; it must not become zero/safe.
    ps=[point('A',0),point('B',0)];ps[1]['sogKn']=10;points(client,ps)
    row=request(client).json()['rows'][0];assert row['isDegenerate'] and row['tcpaMin'] is None
    ps[0]['cogDeg']=270;ps[1]['sogKn']=0;points(client,ps)
    row=request(client).json()['rows'][0];assert row['tcpaMin']<0 and row['isDiverging']
