"""Expected-denial workflow regression. Synthetic API/SQLite, no SSO claim."""
import base64
from contextlib import nullcontext
import json
import os
from pathlib import Path

import mcis_service
import pytest
from fastapi.testclient import TestClient
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H, make_settings
from mcis_service.main import create_app
from mcis_service.redaction.policy import default_policy
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow

URL=f'/api/v1/cases/{CASE}'
RAW=b'independent synthetic restricted field-rule evidence'


def access_counts(client):
    with client.app.state.db.session() as s:
        return s.query(AuditEventRow).filter_by(action='custody.access').count(),s.query(CustodyEventRow).filter_by(kind='Access').count()


@pytest.mark.parametrize('stage',['source','restored'])
def test_restricted_remove_must_also_deny_original_content(local,tmp_path,stage):
    source,_=local
    r=source.post(URL+'/evidence',headers=H('LeadInvestigator'),json={
        'title':'Synthetic restricted','source':'Synthetic','extractedBy':'Independent',
        'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/independent.txt',
        'confidentiality':'Restricted','category':'Other','contentBase64':base64.b64encode(RAW).decode()})
    assert r.status_code==201,r.text
    policy=default_policy()
    next(rule for rule in policy['fieldRules'] if rule['field']=='evidence.restricted')['appliesTo'].append('Investigator')
    assert source.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
    if stage=='restored':
        package=source.get(URL+'/export',headers=H('LeadInvestigator'))
        assert package.status_code==200,package.text
        manager=TestClient(create_app(make_settings(tmp_path/'restore-independent',False)))
    else:manager=nullcontext(source)
    with manager as client:
        if stage=='restored':
            verified=client.post('/api/v1/packages:verify',content=package.content,headers=H('LeadInvestigator'))
            assert verified.status_code==200 and verified.json()['isValid']
            imported=client.post('/api/v1/cases:import',content=package.content,headers=H('LeadInvestigator'))
            assert imported.status_code==201,imported.text
        assert client.get(URL+'/access-policy',headers=H('LeadInvestigator')).json()==policy
        listing=client.get(URL+'/evidence',headers=H())
        metadata=client.get(URL+'/evidence/EV-001',headers=H())
        export=client.get(URL+'/export',headers=H())
        assert listing.status_code==200 and listing.json()==[]
        assert metadata.status_code==403
        before=access_counts(client)
        content=client.get(URL+'/evidence/EV-001/content',headers=H())
        after=access_counts(client)
        result={'module':mcis_service.__file__,'stage':stage,'list_hidden':True,
            'metadata_status':metadata.status_code,'export_status':export.status_code,
            'content_status':content.status_code,'exact_synthetic_bytes':content.content==RAW,
            'access_audit_delta':after[0]-before[0],'custody_access_delta':after[1]-before[1],
            'stored_policy_preserved':True}
        out=Path(os.environ.get('MCIS_FIELD_RULE_OUTPUT','/tmp/field-rule-content-independent.jsonl'))
        with out.open('a') as f:f.write(json.dumps(result,sort_keys=True)+'\n')
        assert content.status_code==403 and RAW not in content.content, str(result)
        assert after==before
