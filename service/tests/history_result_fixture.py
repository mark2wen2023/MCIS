"""Deliberately self-reported historical claims, not verified computation."""
import json
from .conftest import CASE
from .test_align_preview_w41 import result
from mcis_service.timeline.evidence_preview import RegisteredPreview
from mcis_service.audit import service as audit
from mcis_service.timeline.unreviewed_history import PREFIX

STAMP='2026-01-01T00:00:00Z'
RUN='10000000-0000-4000-8000-000000000001'
CASE_UUID='20000000-0000-4000-8000-000000000001'
SOURCE_UUID='30000000-0000-4000-8000-000000000001'

def value():
    request=RegisteredPreview.model_validate({'sources':[{'evidenceId':'EV-900','csvMapping':{'timeColumn':'utc','columns':[{'column':'heading','kind':'Heading'}]}}]}).model_dump(mode='json')
    core=result({'caseId':CASE})['result'];core['calibration']['uncalibratedSources']=['EV-900']
    return {'version':1,'runId':RUN,'caseId':CASE,'createdUtc':STAMP,'status':'unreviewed','request':request,
            'generationSnapshot':{'caseId':CASE,'caseIncarnation':CASE_UUID,'caseEpochUtc':STAMP,
                'sourceIdentities':[{'version':1,'caseId':CASE,'evidenceId':'EV-900','incarnation':SOURCE_UUID,'caseIncarnation':CASE_UUID,'requestDigest':'a'*64,'sourceSha256':'b'*64,'registeredSeq':1,'registeredUtc':STAMP}],
                'sourceSnapshots':[{'evidenceId':'EV-900','registrationDigest':'a'*64,'sourceSha256':'b'*64,'byteLength':1,'registeredUtc':STAMP}], 'reportSnapshots':[]},
            'serverPreview':{'previewOnly':True,'persisted':False,'caseId':CASE,'caseEpochUtc':STAMP,'result':core}}

def marker(d=None):return PREFIX+json.dumps(value() if d is None else d,ensure_ascii=True,sort_keys=True,separators=(',',':'))

def inject_valid_history(client):
    with client.app.state.db.session() as s:
        audit.append(s,case_id=CASE,operator='self-reported historical fixture',role='LeadInvestigator',action='timeline.unreviewed.save',category='TimelineUnreviewed',command='synthetic historical declaration',entity_type='timeline-unreviewed-result',entity_id=RUN,utc=STAMP,snapshot_ref=marker())
