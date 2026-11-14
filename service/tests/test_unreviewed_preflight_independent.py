"""Independent acceptance: negative edges around the internal-only preflight."""
import pytest
from fastapi import HTTPException
from .conftest import C, CASE, H
from .test_source_incarnation import fresh
from .test_registered_align_preview import register, request
from .test_registered_parent_report import parent, body
from .test_unreviewed_preflight import ctx, result
from .test_binding_review_independent import snapshot
from mcis_service.timeline import align_preview, unreviewed_preflight as preflight
from mcis_service.timeline.evidence_preview import RegisteredPreview


def test_parent_bytes_mutated_during_compute_reject(client, empty_client, monkeypatch):
    target = fresh(client, empty_client)
    receipt, p = register(target), parent(target)
    def core(*args):
        path = target.app.state.settings.blob_dir / CASE / p['evidence']['relativePath']
        path.write_bytes(b'%PDF- changed')
        return result(args[2])
    monkeypatch.setattr(align_preview, 'core_run', core)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target), CASE, RegisteredPreview.model_validate(body(receipt, p)))
    assert error.value.status_code == 409


def test_source_permission_revoked_during_compute_reject(client, empty_client, monkeypatch):
    target = fresh(client, empty_client)
    receipt = register(target)
    def core(*args):
        from mcis_service.redaction.policy import default_policy
        policy = default_policy()
        policy['matrix']['Investigator']['evidence_meta'] = 'Deny'
        assert target.put(C + '/access-policy', headers=H('LeadInvestigator'), json=policy).status_code == 200
        return result(args[2])
    monkeypatch.setattr(align_preview, 'core_run', core)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target), CASE, RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code == 403


def test_no_timeline_write_permission_never_calls_core(client, empty_client, monkeypatch):
    target = fresh(client, empty_client)
    receipt = register(target)
    from mcis_service.redaction.policy import default_policy
    policy = default_policy()
    policy['matrix']['Investigator']['timeline'] = 'ReadOnly'
    assert target.put(C + '/access-policy', headers=H('LeadInvestigator'), json=policy).status_code == 200
    monkeypatch.setattr(align_preview, 'core_run', lambda *_: pytest.fail('must reject before core'))
    before = snapshot(target)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target), CASE, RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code == 403
    assert snapshot(target) == before


def test_core_failure_does_not_persist(client, empty_client, monkeypatch):
    target = fresh(client, empty_client)
    receipt = register(target)
    def core(*_):
        raise RuntimeError('injected core failure')
    monkeypatch.setattr(align_preview, 'core_run', core)
    before = snapshot(target)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target), CASE, RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code == 502
    assert snapshot(target) == before
