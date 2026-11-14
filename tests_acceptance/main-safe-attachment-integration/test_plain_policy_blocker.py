"""Independent expected-denial regressions. Current failure is an integration BLOCKER."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import pytest
import mcis_service
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H
from mcis_service.redaction.policy import default_policy

URL=f'/api/v1/cases/{CASE}'
RAW=b'independent synthetic plain evidence policy blocker'

@pytest.mark.parametrize('category',['evidence_meta','audit'])
def test_old_plain_export_must_respect_current_denial(local,category):
    client, app=local
    registered=client.post(URL+'/evidence',headers=H('LeadInvestigator'),json={
        'title':'Independent synthetic','source':'Synthetic','extractedBy':'Independent',
        'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.txt',
        'contentBase64':base64.b64encode(RAW).decode()})
    assert registered.status_code==201,registered.text
    policy=default_policy(); policy['matrix']['Investigator'][category]='Deny'
    changed=client.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=policy)
    assert changed.status_code==200,changed.text
    individual=client.get(URL+('/evidence/EV-001/content' if category=='evidence_meta' else '/audit'),headers=H())
    assert individual.status_code==403,individual.text
    response=client.get(URL+'/export',headers=H())
    evidence={'service_module':mcis_service.__file__,'category':category,'individual_status':individual.status_code,'export_status':response.status_code}
    if response.status_code==200:
        archive=zipfile.ZipFile(io.BytesIO(response.content))
        blob=archive.read('evidence/EV-001/source.txt')
        events=[json.loads(line) for line in archive.read('audit/audit.jsonl').decode().splitlines() if line]
        exported_policy=json.loads(archive.read('access-policy.json'))
        assert blob==RAW
        assert exported_policy['matrix']['Investigator'][category]=='Deny'
        actions=[row['action'] for row in events]
        assert 'custody.register' in actions and 'policy.update' in actions and 'package.export' in actions
        evidence.update(blob_matches=True,blob_sha256=hashlib.sha256(blob).hexdigest(),
                        audit_actions=actions,exported_policy='Deny')
    output=Path(os.environ.get('MCIS_BLOCKER_OUTPUT','/tmp/mcis-plain-policy-blocker.jsonl'))
    with output.open('a') as f:f.write(json.dumps(evidence,sort_keys=True)+'\n')
    assert response.status_code==403, f'BLOCKER: {evidence}'
