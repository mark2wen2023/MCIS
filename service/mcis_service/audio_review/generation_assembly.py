"""Strict generation internal entry; no product export/restore authority."""
from ..evidence_intake.router import load_receipt
from ._assembly import _build


def build_candidate(ctx, session, case_id):
    return _build(ctx, session, case_id, 'generation', load_receipt)
