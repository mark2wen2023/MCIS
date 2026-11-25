"""Audited in-process research execution; not an HTTP or authentication layer.

Trusted service code supplies authorize and persist_event callbacks. The latter
must durably commit before returning. Neither callback may come from model input.
No database transactions or artifact publication are implemented here.
"""
from copy import deepcopy
from uuid import uuid4
import re

from .skill_runtime import execute_local_skill


def run_audited_ship_skill(*, case_id, operator, evidence_id, expected_drawing_sha256,
                           reviewed_arguments, authorize, persist_event):
    if not all(isinstance(v, str) and v.strip() for v in (case_id, operator, evidence_id)):
        raise ValueError('trusted execution context required')
    if not isinstance(expected_drawing_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_drawing_sha256):
        raise ValueError('expected drawing digest required')
    if not callable(authorize) or not callable(persist_event):
        raise ValueError('trusted service callbacks required')
    context = dict(run_id=uuid4().hex, case_id=case_id, operator=operator,
                   evidence_id=evidence_id, drawing_sha256=expected_drawing_sha256,
                   skill='ship-reconstruction', research_only=True, lofting_authorized=False)

    def emit(status, reason=None, **details):
        persist_event(dict(context, status=status, reason=reason, **details))

    def permitted(phase):
        try:
            allowed = authorize(dict(context), phase) is True
        except Exception:
            emit('failed', 'authorization_check_failed')
            raise
        if not allowed:
            emit('rejected', 'authorization_denied_' + phase)
            raise PermissionError('research execution not authorized')

    emit('started')
    permitted('before_execution')
    try:
        args = deepcopy(reviewed_arguments)
        if args['parsed']['document']['sha256'] != expected_drawing_sha256:
            raise ValueError('drawing scope mismatch')
        result = execute_local_skill('ships', 'ship-reconstruction', reviewed_arguments=args)
        manifest = result['manifest']
        details = dict(glb_sha256=manifest['glb_sha256'], evidence_sha256=manifest['evidence_sha256'],
                       algorithm_version=manifest['algorithm_version'])
    except (ValueError, KeyError, TypeError):
        emit('rejected', 'invalid_research_input')
        raise
    except Exception:
        emit('failed', 'execution_failed')
        raise
    permitted('before_release')
    # If this write fails, no result is returned. A caller must reconcile started
    # runs without terminal events; no automatic retry is attempted here.
    emit('succeeded', **details)
    return result
