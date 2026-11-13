"""Public report excerpts over real HTTP/W2; never original telemetry or approval."""
import base64
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import threading
import time
import httpx
import pytest
import uvicorn
from .conftest import H
from .test_binding_review_independent import snapshot

ROOT=Path(__file__).resolve().parents[2]
CASE='CJK-2024-1230-YangZe22-VegaDream'
REPORT_SHA='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
TITLE='长江口深水航道“12·30”“YANGZE 22”轮与“VEGA DREAM”轮碰撞事故'


def test_public_report_registered_scope_real_http(client):
    wrapper=os.environ.get('MCIS_ACCEPTANCE_CORE')
    if not wrapper:pytest.skip('requires actual built core wrapper')
    review=json.loads((ROOT/'research/skills_timeline/public_report_visual_review.json').read_text())
    pdf=(ROOT/'reports/yangze22/report.pdf').read_bytes()
    assert hashlib.sha256(pdf).hexdigest()==REPORT_SHA==review['report']['sha256']
    assert review['report']['sourceFamily']=='single_published_investigation_report'
    assert review['investigatorApproval']=='pending'
    assert review['originalTelemetryVerified'] is False
    observations=review['observations'];assert len(observations)==2
    assert [o['headingDeg'] for o in observations]==[47.0,48.0]
    assert [o['headingReference'] for o in observations]==['not_explicit_in_crop','true']
    assert [o['pdfPage'] for o in observations]==[17,41]
    assert [o['imo'] for o in observations]==['9958212','9958212']
    app=client.app;app.state.settings.core_cmd=wrapper
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started and time.monotonic()<deadline:time.sleep(.02)
        assert server.started
        with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1/cases/{CASE}',headers=H(),trust_env=False,timeout=60) as h:
            from .test_registered_parent_report import parent
            report_receipt=parent(h,pdf,'yangze22-public-report.pdf',case='')
            sources=[]
            for o in observations:
                raw=f"utc,heading\n{o['interpretationUtc']},{o['headingDeg']}\n".encode()
                b={'profile':'mcis-evidence-intake-v1','fileName':o['id']+'-report-extract.csv',
                   'contentBase64':base64.b64encode(raw).decode(),'title':o['figure']+'报告摘录，非原始遥测',
                   'source':TITLE+'；单一公开报告家族','extractedBy':'assistant acceptance transcription, not investigator approval',
                   'extractedUtc':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),'category':'Document','confidentiality':'Restricted',
                   'note':'测试重建CSV；提取时间是本次CSV重建时刻，不是原始设备记录或事实批准；PDF SHA256 '+REPORT_SHA}
                p=h.post('/evidence-intakes:preview',json=b);assert p.status_code==200,p.text
                r=h.post('/evidence-intakes:commit',json={**b,'confirmed':True,'requestDigest':p.json()['requestDigest']});assert r.status_code==200,r.text
                receipt=r.json();assert receipt['sourceSha256']==hashlib.sha256(raw).hexdigest()
                sources.append({'evidenceId':receipt['evidenceId'],
                  'parentReport':{'evidenceId':report_receipt['evidenceId'],'sourceSha256':REPORT_SHA},
                  'csvMapping':{'timeColumn':'utc','columns':[{'column':'heading','kind':'Heading'}]},
                  'comparisonContext':{'vesselLabel':'YANGZE 22 / IMO 9958212','sourceNature':'report_extract','sourceTitle':TITLE,
                    'citation':f"PDF p{o['pdfPage']} / 正文p{o['bodyPage']} / {o['figure']} / SHA256 {REPORT_SHA}",
                    'timeBasis':o['interpretationBasis'], 'headingReference':'true' if o['headingReference']=='true' else 'unknown'}})
            before=snapshot(client)
            rejected=h.post('/timeline/registered-align-preview',json={'sources':sources})
            assert rejected.status_code==422,rejected.text
            assert snapshot(client)==before
            # Do not alter AIS unknown->true or downgrade to unscoped to get a comparison.
            accepted=h.post('/timeline/registered-align-preview',json={'sources':[sources[1]]})
            assert accepted.status_code==200,accepted.text
            data=accepted.json()
            assert data['comparisonScope']['status']=='user_declared_not_verified'
            assert data['comparisonScope']['sources'][0]['context']==sources[1]['comparisonContext']
            assert data['sourceSnapshots'][0]['evidenceId']==sources[1]['evidenceId']
            assert data['reportSnapshots'][0]['evidenceId']==report_receipt['evidenceId']
            assert data['reportSnapshots'][0]['sourceSha256']==REPORT_SHA
            assert data['reportSnapshots'][0]['relationshipStatus']=='user_declared_not_verified'
            assert data['result']['stats']['sourcesImported']==1
            assert data['result']['conflicts']==[] # single source; not corroboration
            assert data['result']['calibration']['allCalibrated'] is False
            assert data['observationApproval']=='not_assessed' and data['persisted'] is False
            assert snapshot(client)==before
    finally:
        server.should_exit=True;thread.join(10);sock.close()
        assert not thread.is_alive()
