"""Ordinary synthetic schema compatibility, not runtime restore/security probes."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from mcis_service.common.contracts import registry
from .test_working_record_archive import client_at,ROOT,HEAD
from .test_conflict_source_receipt_submit import seed,prepare

REPO=Path(__file__).resolve().parents[2]
FROZEN=REPO/'research/conflict_source_intent/fixtures/a812d38-conflict-archive.schema.json'


def old_revision_validator():
    archive=json.loads(FROZEN.read_text())
    revision=archive['properties']['records']['items']['properties']['revisions']['items']
    # Same relative conflict schema resolution as the old archive contract.
    revision={**revision,'$id':archive['$id']}
    return Draft202012Validator(revision,registry=registry())


def test_old_schema_accepts_creation_but_rejects_receipted_revision(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);request,receipt=prepare(c,v)
        result=c.post(ROOT+'/conflicts',headers=HEAD,json=request)
        assert result.status_code==201,result.text
        h=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert h.status_code==200,h.text
        creation,edited=h.json()['revisions']
        validator=old_revision_validator()
        assert not list(validator.iter_errors(creation))
        errors=list(validator.iter_errors(edited))
        assert errors and all(e.validator=='additionalProperties' for e in errors)
        assert any('sourceReceiptId' in e.message for e in errors)
        assert edited['sourceReceiptId']==receipt['receiptId']
        # Never strip the field or recompute history to force acceptance.
        again=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert again.status_code==200 and again.json()==h.json()
