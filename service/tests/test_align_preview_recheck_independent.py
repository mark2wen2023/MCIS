"""Independent fresh-database recheck regression; core responses are doubles."""
from mcis_service.timeline import align_preview as module
from mcis_service.db import get_doc, put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import CASE, H
from .test_align_preview_w41 import BODY, URL, result
from .test_align_preview_recheck import change_case, deny


def test_equivalent_utc_epoch_representation_does_not_false_conflict(client, monkeypatch):
    def run(*args):
        # Seed epoch is 2026-05-18T06:15:00Z; +08 rendering is same instant.
        change_case(client, caseEpochUtc='2026-05-18T14:15:00+08:00')
        return result(args[2])
    monkeypatch.setattr(module, 'core_run', run)
    response = client.post(URL, json=BODY, headers=H())
    assert response.status_code == 200, response.text
    assert response.json()['persisted'] is False


def test_role_removed_during_compute_fails_closed(client, monkeypatch):
    def run(*args):
        with client.app.state.db.session() as s:
            policy = get_doc(s, AccessPolicyRow, CASE, 'policy') or default_policy()
            policy['matrix'].pop('Investigator')
            put_doc(s, AccessPolicyRow, CASE, 'policy', policy)
        return result(args[2])
    monkeypatch.setattr(module, 'core_run', run)
    response = client.post(URL, json=BODY, headers=H())
    assert response.status_code == 403, response.text
    assert 'result' not in response.json()


def test_denied_before_compute_does_not_invoke_core(client, monkeypatch):
    deny(client)
    def unexpected(*args):
        raise AssertionError('core must not run')
    monkeypatch.setattr(module, 'core_run', unexpected)
    response = client.post(URL, json=BODY, headers=H())
    assert response.status_code == 403
    assert 'result' not in response.json()
