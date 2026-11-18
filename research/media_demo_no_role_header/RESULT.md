# Isolated preparation without an elevated role header
Base6bd0bd87271ad7aa2ff073b42f51dc6ce345e400. Local candidate/media-demo-no-role-header only.

Static evidence: common/context.py defaults to Investigator without a role header; cases/router.py permits that role to create a case; redaction/policy.py gives it evidence_meta/testimony ReadWrite and does not remove Restricted evidence; image/audio review use the unchanged intake authorization gate. Therefore LeadInvestigator injection in prepare.py was unnecessary. Remove only that header, retaining an explicitly synthetic operator label. No trustworthy identity or production authentication was implemented or claimed. Default Investigator remains the existing unauthenticated local role, not SSO. No policy/dependency overrides, changed confidentiality, direct fixture DB seeding or new privilege grant.

New ordinary node statically reviewed before execution:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_media_demo_no_role_header.py::test_synthetic_prepare_and_readback_without_role_header --tb=short
```
Result1 passed in0.77s,exit0. The request observer delegates to the real TestClient implementation; it checks absence of the role header, not fake responses. Fresh synthetic case and six generated materials prepared through existing APIs; manifest preflight passed; saved image/audio runs re-read; generated PNG/tone downloaded through ordinary authorization with expected digest headers; fresh temporary audit roles all Investigator. Both models stayed disabled. Only this new node ran, no old paused/write-refusal/security tests.

This is developer in-process HTTP testing, not a listening service/browser/playback/manual review or independent acceptance. No real audio, model, credential or production database was used. No public optional-input branch validation this turn. Existing legacy-role limitations and formal archive/restore refusal remain. No push/merge/deployment. This removes the preparation-specific elevated-header blocker; it does not prove general page usability or production identity security.
