"""Independent adversarial contract tests; synthetic temporary DB, no seed imports."""
import sys, math, copy
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'service'))
import pytest
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow,VesselRow,TrackPointRow
from mcis_service.current_analysis import router as mod
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
CID='INDEPENDENT-SYNTHETIC'; E=datetime(2026,1,1,tzinfo=timezone.utc)

def point(v,t,**kw):
    return dict(vesselId=v,timeSec=t,utc=(E+timedelta(seconds=t)).isoformat(timespec='milliseconds').replace('+00:00','Z'),latDeg=0,lonDeg=.01 if v=='b' else 0,sogKn=0 if v=='b' else 10,cogDeg=90,**kw)

def put(c,ps):
    with c.app.state.db.session() as s:
        s.query(TrackPointRow).delete()
        for p in ps:s.add(TrackPointRow(case_id=CID,vessel_id=p['vesselId'],time_sec=p['timeSec'],doc=p))

@pytest.fixture
def c(tmp_path):
    st=Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/a.db',seed_demo=False)
    with TestClient(create_app(st)) as client:
        with client.app.state.db.session() as s:
            put_doc(s,CaseRow,CID,CID,dict(caseId=CID,title='Synthetic inputs, non-demo flag test',isFictionalDemo=False,caseEpochUtc='2026-01-01T00:00:00Z',incidentLocation={'latDeg':0,'lonDeg':0}))
            for v in ('a','b'):put_doc(s,VesselRow,CID,v,dict(caseId=CID,vesselId=v,name=v))
        put(client,[point('a',0),point('b',0)])
        yield client

def req(c,**kw):
    r=c.get(f'/api/v1/cases/{CID}/analysis/current',params={'ownVesselId':'a','targetVesselId':'b',**kw},headers={'X-MCIS-Role':'LeadInvestigator'})
    assert r.headers.get('cache-control')=='no-store'
    return r

def good(ctx,command,payload):
    return dict(ok=True,command='cpa',coreVersion='independent-stub',result={'results':[dict(pairId=p['pairId'],timeSec=p['timeSec'],ownVesselId=p['own']['vesselId'],targetVesselId=p['target']['vesselId'],currentDistanceNm=.6,dcpaNm=0.,tcpaMin=3.6,isDegenerate=False,isDiverging=False,riskLevel='Danger',thresholds={'hidden':True}) for p in payload['pairs']]})

@pytest.fixture
def stub(monkeypatch):monkeypatch.setattr(mod,'_core',good)

def test_all_sources_exact_and_read_only(c,stub):
    ps=[point(v,t,**({'provenance':p,'source':'声明 <not verified> '+v} if p else {})) for t,p in enumerate(['Measured','Interpolated','ManualDrawn','Simulated',None]) for v in ('a','b')]
    put(c,list(reversed(ps)))
    with c.app.state.db.engine.connect() as conn:before=list(conn.exec_driver_sql('select * from track_points'))
    r=req(c);assert r.status_code==200,r.text
    data=r.json();assert data['isFictionalDemo'] is False and data['counts']['matched']==5
    for row in data['rows']:
        for key,v in [('own','a'),('target','b')]:assert row[key]==next(p for p in ps if p['vesselId']==v and p['timeSec']==row['timeSec'])
    assert 'riskLevel' not in r.text and 'thresholds' not in r.text
    with c.app.state.db.engine.connect() as conn:assert before==list(conn.exec_driver_sql('select * from track_points'))

@pytest.mark.parametrize('t',[1e-7,-1e-7,1e-6,-1e-6])
def test_close_not_equal_never_pairs(c,monkeypatch,t):
    b=point('b',t);b['utc']='2026-01-01T00:00:00.000Z'
    put(c,[point('a',0),b]);monkeypatch.setattr(mod,'_core',lambda *a:pytest.fail('No shared timestamp'))
    r=req(c);assert r.status_code==200,r.text
    assert r.json()['counts']==dict(own=1,target=1,matched=0,unmatchedOwn=1,unmatchedTarget=1)

@pytest.mark.parametrize('utc',['2026-01-01T00:00:00.0000Z','2026-01-01T00:00:00+00:00','2026-01-01','2026-01-01T00:00:60Z'])
def test_utc_strict(c,utc):
    p=point('a',0);p['utc']=utc;put(c,[p,point('b',0)]);assert req(c).status_code==422

@pytest.mark.parametrize('value',[1e12,-1e12])
def test_extreme_valid_window_empty(c,value,stub):
    r=req(c,fromSec=value,toSec=value);assert r.status_code==200,r.text;assert not r.json()['rows']

@pytest.mark.parametrize('field,value',[('timeSec',True),('vesselId','b'),('cogDeg',None)])
def test_corrupt_doc_index_and_no_hdg_substitute(c,field,value):
    with c.app.state.db.session() as s:
        r=s.query(TrackPointRow).filter_by(vessel_id='a').one();r.doc={**r.doc,field:value,'hdgDeg':90}
    assert req(c).status_code==422

@pytest.mark.parametrize('v',['a','b'])
def test_budget_each_ship(c,stub,v):
    put(c,[point(v,i) for i in range(5001)]+[point('b' if v=='a' else 'a',0)])
    assert req(c).status_code==422
    r=req(c,toSec=4999);assert r.status_code==200,r.text;assert r.json()['counts']['matched']==1

@pytest.mark.parametrize('mutation',['reverse','wrong_target','nonfinite','bool_number','false_degenerate'])
def test_core_attack(c,monkeypatch,mutation):
    put(c,[point(v,t) for t in [0,1] for v in ['a','b']])
    def malicious(*a):
        out=good(*a);rows=out['result']['results']
        if mutation=='reverse':rows.reverse()
        elif mutation=='wrong_target':rows[0]['targetVesselId']='a'
        elif mutation=='nonfinite':rows[0]['currentDistanceNm']=float('inf')
        elif mutation=='bool_number':rows[0]['dcpaNm']=False
        elif mutation=='false_degenerate':rows[0].update(isDegenerate=True,tcpaMin=None)
        return out
    monkeypatch.setattr(mod,'_core',malicious);r=req(c);assert r.status_code==502,r.text

@pytest.mark.parametrize('mutation',['invalid_point','deleted_vessel','permission'])
def test_midflight_change_discard_status(c,monkeypatch,mutation):
    def delayed(*a):
        result=good(*a)
        with c.app.state.db.session() as s:
            if mutation=='invalid_point':
                p=s.query(TrackPointRow).filter_by(vessel_id='a').one();p.doc={**p.doc,'cogDeg':None}
            elif mutation=='deleted_vessel':s.query(VesselRow).filter_by(key='b').delete()
            else:
                p=default_policy();p['matrix']['LeadInvestigator']['ais_sim']='Deny';put_doc(s,AccessPolicyRow,CID,'policy',p)
        return result
    monkeypatch.setattr(mod,'_core',delayed);r=req(c);assert r.status_code==(403 if mutation=='permission' else 409),r.text
    assert 'rows' not in r.json()

def test_real_core_geometry_rounding_and_degenerate(c):
    r=req(c);assert r.status_code==200,r.text
    row=r.json()['rows'][0];d=6378137*math.sin(math.radians(.01))/1852
    assert abs(row['currentDistanceNm']-d)<1e-6 and abs(row['tcpaMin']-6*d)<1e-6
    a,b=point('a',0),point('b',0);a['sogKn']=b['sogKn']=0;put(c,[a,b]);row=req(c).json()['rows'][0]
    assert row['isDegenerate'] and row['tcpaMin'] is None
    a['sogKn']=10;a['cogDeg']=270;b['lonDeg']=1e-12;put(c,[a,b]);row=req(c).json()['rows'][0]
    assert row['tcpaMin']==0 and row['isDiverging'] and not row['isDegenerate']

def test_real_core_random_vectors_independent(c):
    import random
    rng=random.Random(122);ps=[];expected=[]
    for t in range(40):
        a,b=point('a',t),point('b',t)
        for p in [a,b]:p.update(lonDeg=rng.uniform(-.02,.02),sogKn=rng.uniform(0,25),cogDeg=rng.uniform(0,360))
        rx=6378137*(math.sin(math.radians(b['lonDeg']))-math.sin(math.radians(a['lonDeg'])))
        vx=(b['sogKn']*math.sin(math.radians(b['cogDeg']))-a['sogKn']*math.sin(math.radians(a['cogDeg'])))*1852/3600
        vy=(b['sogKn']*math.cos(math.radians(b['cogDeg']))-a['sogKn']*math.cos(math.radians(a['cogDeg'])))*1852/3600
        seconds=-rx*vx/(vx*vx+vy*vy)
        expected.append((abs(rx)/1852,math.hypot(rx+vx*seconds,vy*seconds)/1852,seconds/60))
        ps.extend([a,b])
    put(c,ps);r=req(c);assert r.status_code==200,r.text
    for row,ex in zip(r.json()['rows'],expected):
        for k,val in zip(['currentDistanceNm','dcpaNm','tcpaMin'],ex):assert row[k]==pytest.approx(val,abs=1e-6)

@pytest.mark.parametrize('change',['delete_case','invalid_epoch','over_budget'])
def test_other_midflight_changes(c,monkeypatch,change):
    def delayed(*args):
        result=good(*args)
        with c.app.state.db.session() as s:
            if change=='delete_case':s.query(CaseRow).filter_by(case_id=CID).delete()
            elif change=='invalid_epoch':
                row=s.query(CaseRow).filter_by(case_id=CID).one();row.doc={**row.doc,'caseEpochUtc':'broken'}
            else:
                for i in range(1,5001):s.add(TrackPointRow(case_id=CID,vessel_id='a',time_sec=i,doc=point('a',i)))
        return result
    monkeypatch.setattr(mod,'_core',delayed);r=req(c);assert r.status_code==409,r.text;assert 'rows' not in r.json()

@pytest.mark.parametrize('mutation',['degenerate_wrong_distance','degenerate_marked_regular'])
def test_equal_velocity_core_semantics(c,monkeypatch,mutation):
    a,b=point('a',0),point('b',0);b['sogKn']=a['sogKn'];put(c,[a,b])
    def wrong(*args):
        env=good(*args)
        if mutation=='degenerate_wrong_distance':env['result']['results'][0].update(isDegenerate=True,tcpaMin=None,dcpaNm=.1)
        return env
    monkeypatch.setattr(mod,'_core',wrong);r=req(c);assert r.status_code==502,r.text

@pytest.mark.parametrize('level',[None,'','Allow','readwrite',False])
def test_invalid_permission_denies(c,monkeypatch,level):
    with c.app.state.db.session() as s:
        policy=default_policy();policy['matrix']['LeadInvestigator']['ais_sim']=level;put_doc(s,AccessPolicyRow,CID,'policy',policy)
    monkeypatch.setattr(mod,'_core',lambda *args:pytest.fail('Unauthorized core call'))
    assert req(c).status_code==403

def test_entire_database_unchanged_on_repeated_read(c,stub):
    def snapshot():
        with c.app.state.db.engine.connect() as conn:
            names=[r[0] for r in conn.exec_driver_sql("select name from sqlite_master where type='table' order by name")]
            return {n:list(conn.exec_driver_sql('SELECT * FROM "'+n+'"')) for n in names}
    before=snapshot();first=req(c);second=req(c)
    assert first.status_code==second.status_code==200 and first.json()==second.json()
    assert before==snapshot()

@pytest.mark.parametrize('origin,coordinate,status',[((85,0),(85,0),200),((85.00001,0),(85.00001,0),422),((0,179.99),(0,-179.99),200),((0,0),(0,1),422)])
def test_local_geometry_domain(c,stub,origin,coordinate,status):
    with c.app.state.db.session() as s:
        row=s.query(CaseRow).one();row.doc={**row.doc,'incidentLocation':dict(zip(['latDeg','lonDeg'],origin))}
    ps=[point(v,0) for v in ['a','b']]
    for p in ps:p.update(dict(zip(['latDeg','lonDeg'],coordinate)))
    put(c,ps);assert req(c).status_code==status

def test_missing_points_no_common_duplicates(c,monkeypatch):
    monkeypatch.setattr(mod,'_core',lambda *args:pytest.fail('Core must not run'))
    for ps in ([],[point('a',0)],[point('a',0),point('b',1)]):
        put(c,ps);r=req(c);assert r.status_code==200 and r.json()['rows']==[] and r.json()['coreVersion'] is None
    put(c,[point('a',0),point('a',0),point('b',0)]);assert req(c).status_code==422

@pytest.mark.parametrize('field',['sogKn','cogDeg','latDeg','rotDegPerMin'])
def test_oversized_json_integer_is_validation_error(c,field):
    a=point('a',0);a[field]=10**400;put(c,[a,point('b',0)])
    r=req(c);assert r.status_code==422,r.text

def test_oversized_core_integer_is_bad_gateway(c,monkeypatch):
    def malicious(*args):
        env=good(*args);env['result']['results'][0]['dcpaNm']=10**400;return env
    monkeypatch.setattr(mod,'_core',malicious);r=req(c);assert r.status_code==502,r.text
