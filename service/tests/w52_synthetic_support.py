"""Synthetic fixture support: seed=False; no real report files."""
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.interviews import router as ir, service as ins
from mcis_service.audit.models import AuditEventRow
from .conftest import make_settings, H

CASE='CASE-SYNTHETIC-W52'
BASE='/api/v1/cases/'+CASE
MARK='SYNTHETIC_PRIVATE_MARKER'

@pytest.fixture
def client(tmp_path):
    app=create_app(make_settings(tmp_path, seed=False))
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic','isFictionalDemo':True})
    with TestClient(app) as c: yield c


def doc():
    return {'recordId':'IR-01','caseId':CASE,'interviewee':{'intervieweeId':'P1','name':'SYNTHETIC_NAME','role':'Synthetic witness','affiliation':'Synthetic'},
            'startUtc':'2026-01-01T00:00:00Z','turns':[{'round':1,'question':'Synthetic question','answer':MARK,'sensitiveFragments':[MARK]}],
            'statements':[], 'crossChecks':[{'statementId':'IR-01-S01','recordId':'IR-01','outcome':'Unverifiable',
             'claimedText':MARK,'observedText':MARK,'sourceLabel':'synthetic','state':'Confirmed','note':MARK}],
            'signed':True,'evidenceId':'EV-NOT-REGISTERED','sourceSha256':'client-supplied-unvalidated-hash'}

