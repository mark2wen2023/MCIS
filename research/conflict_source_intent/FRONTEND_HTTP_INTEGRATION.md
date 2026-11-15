# Registry receipt controller / backend HTTP integration

Base: 6102b0b15cc9d0fa9bf65816298e28655b51aa02, direct parent
fd4708bb2f9886c20963619ef3d00f8de99f1e41, backend dependency
58720e6028de2dc02fc62e3fa99bde07f0cd84e9. These remain an unmerged
candidate stack, not main product acceptance. No implementation or policy changes.

Two ordinary synthetic integration tests, with actual FastAPI routes and SQLite
in pytest temporary directories. TestClient initializes lifecycle and synthetic
CASE-INTAKE registry/conflict; uvicorn serves that app on 127.0.0.1 ephemeral port.
Node executes bundled production ObservationEditing and api.ts, using actual fetch
HTTP; only the relative URL is prefixed with the loopback origin. localStorage is
an in-memory adapter because Node has no browser storage. No response mocks.
Existing LeadInvestigator role/operator headers are used, not trusted SSO.

1. Unchanged registry: real receipt with SHA A, actual POST returns 201, controller
   confirms saved; history GET contains two revisions, prior value preserved, new
   value and sourceReceiptId bound, bytesVerified=false; SQLite receipt consumed=2.
2. A -> B: after the frontend receives real receipt, harness appends synthetic
   custody Change to EV-A in SQLite. Controller POST returns 412, retains draft,
   clears receipt, reports refusal and makes no automatic retry. History remains
   one revision; document/audit state unchanged by rejected submission; receipt
   remains unconsumed. No real source file exists or is accessed.

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_observation_receipt_http_integration.py

Uses installed uvicorn, node and web/node_modules/.bin/esbuild; missing prerequisites
fail rather than skip. Bundle and databases are created only in temporary dirs.
Two invocations from repository root failed because .venv/bin/pytest is under
service/; corrected working directory. First actual run: 2 passed in 1.15s.
Final results recorded in REQUESTS.md after explicit rejection-state assertion.

Limits: no real browser, DOM event or React mounting lifecycle test. No real case,
original-byte reading, OCR, LLM or production identity verification. No restricted
permission/security/ECFC tests rerun. Existing source gate may be stricter than
receipt issuance. Registry receipt is not human-reading proof. This limited live
HTTP integration does not validate all error/concurrency/expiry conditions or
production deployment. No production API enabled, merge or deployment performed.
