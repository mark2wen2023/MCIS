"""Independent exact-sample regression, synthetic tracks and real tracks route."""
from copy import deepcopy
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.cases.service import state_at
from mcis_service.cases.router import router
from mcis_service.cases.models import CaseRow,TrackPointRow
from mcis_service.db import Database,put_doc
from test_exact_sample import samples


def test_duplicate_final_sample_first_record_wins():
    p=samples();first=deepcopy(p[-1]);p.append({**first,'source':'conflicting-final','latDeg':88})
    assert state_at(p,3600)==first
    # Existing after-end behavior still returns final listed point, not conflict resolution.
    assert state_at(p,3601)==p[-1]


def test_exact_sample_does_not_need_missing_interpolation_fields():
    p=samples();p[1]={'timeSec':60,'source':'recorded-minimal','vesselId':'V'}
    assert state_at(p,60)==p[1]


def test_top_level_result_modification_does_not_change_sample():
    p=samples();before=deepcopy(p);out=state_at(p,60)
    out['source']='modified';out['hdgDeg']=90
    assert p==before
    # dict copy is intentionally shallow, not a newly guaranteed deep-copy API.
    assert out['extra'] is p[1]['extra']


def test_actual_get_tracks_exact_resampling_metadata_and_existing_utc_rule(tmp_path):
    app=FastAPI();app.state.db=Database(f'sqlite:///{tmp_path}/track.db');app.state.db.create_all();app.include_router(router)
    p=samples()
    with app.state.db.session() as s:
        put_doc(s,CaseRow,'synthetic','synthetic',{'caseId':'synthetic','caseEpochUtc':'2026-01-01T00:00:00Z'})
        for item in p:s.add(TrackPointRow(case_id='synthetic',vessel_id='V',time_sec=item['timeSec'],doc=item))
    try:
        with TestClient(app) as client:
            for i,t in enumerate([0,60,3600]):
                response=client.get('/api/v1/cases/synthetic/tracks',params={'fromSec':t,'toSec':t,'stepSec':60},headers={'X-MCIS-Role':'Investigator'})
                assert response.status_code==200,response.text
                point=response.json()['tracks'][0]['points'][0]
                assert {k:v for k,v in point.items() if k!='utc'}=={k:v for k,v in p[i].items() if k!='utc'}
                assert point['utc']!='recorded-'+str(i) # existing route recomputes UTC
            middle=client.get('/api/v1/cases/synthetic/tracks',params={'fromSec':30,'toSec':30,'stepSec':60}).json()['tracks'][0]['points'][0]
            assert middle['provenance']=='Interpolated'
        with app.state.db.session() as s:
            stored=[r.doc for r in s.scalars(select(TrackPointRow).order_by(TrackPointRow.time_sec))]
            assert stored==p
    finally:app.state.db.engine.dispose()
