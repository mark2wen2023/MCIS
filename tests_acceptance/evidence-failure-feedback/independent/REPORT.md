# Evidence failure feedback — independent review

Reviewed isolated `/workspace/mcis-evidence-failure-feedback`, baseline `3aba2bf`, repository rules/handoff and the two changed frontend product files. Reviewer did not modify product, run a browser, push, merge or deploy. Independent artifacts are outside the product tree in this directory.

## Actual tests

* Bundled `classifier.ts` against this tree's actual ApiError and commitFailure using the existing esbuild, then ran Node: **80 independent assertions passed** (`classifier-results.txt`). These are synthetic error inputs, not 80 HTTP requests/UI scenarios. Checks cover all 14 allowed code/status pairs, prior-unknown dominance, mismatched status, case-sensitive codes, integrity/path/history conflicts, missing receipt, cleanup/server failure, malformed receipt/network exceptions and unrecognized values.
* From service: `PYTHONPATH=. .venv/bin/python -m pytest -q --import-mode=importlib /workspace/mcis-local-followup-results/evidence-failure-feedback/independent/test_backend.py`: **5 passed, one dependency deprecation warning, 1.94 seconds** (`backend-results.txt`). Real TestClient/SQLite/temp files with synthetic content. Four cases establish INTAKE_METADATA/CONFIRM/BASE64/STALE rejection before evidence/custody/audit/file creation. Fifth registers successfully, mutates the synthetic source file, then observes repeat commit **409 INTAKE_INTEGRITY** and recovery **409 INTAKE_INTEGRITY**, while evidence/custody/audit stay **1/1/1** and existing bytes are not overwritten. Thus this 409 truly cannot imply noncommit.

Coordinator's 19 classifier checks, prior 88 tests and Chromium runs are separate evidence; this report does not claim to have independently rerun them. No browser interaction/state rendering acceptance is claimed from Node classifier assertions.

## Error-code provenance review

| Allowed first-attempt code | Actual source / ordering on this endpoint |
|---|---|
| INTAKE_FIELDS, INTAKE_METADATA, INTAKE_CONFIRM, INTAKE_BASE64, INTAKE_FILE_LIMIT | parser.inputs/metadata invoked before registration session writes |
| CONTENT_TYPE, INTAKE_REQUEST_LIMIT, INTAKE_JSON | body_bounded before commit parsing/registration |
| INTAKE_OPERATOR | preview/binding computation before load_receipt and new registration writes |
| INTAKE_STALE | requestDigest mismatch immediately before receipt lookup/new ID/write |
| CASE_ID, CASE_NOT_FOUND | authorization and case lookup before new registration writes |
| FORBIDDEN, READ_ONLY | initial/final authorize or existing receipt visibility checks before new registration writes |

Source inspection supports the precise claim **this attempt was rejected before creating a registration**, for the exact endpoint/error contracts reviewed. It does not prove absence of earlier same-content/history registration: receipt visibility rejection can occur for already stored evidence, and a separate earlier request may have committed. The added message explicitly preserves that distinction. Wrong code/status combinations remain locked instead of extrapolating from status alone. No claim that the frontend independently proves database noncommit under arbitrary proxy/error spoofing or future server-contract changes.

Unknown result always dominates the recognized rejection classification when `previouslyUncertain=true`; no later recognized rejection can clear it. INTAKE_INTEGRITY/BLOB_EXISTS/PATH, archive-history conflicts and unrecognized errors stay locked. Read-only receipt 404 is not used as proof of absence/noncommit and no longer recommends resubmission.

## Panel code review

On locked commit failure, panel retains body/preview/confirmation for read-only lookup and disables editable input/preview via uncertain state. On exact pre-registration rejection with no prior uncertainty, it clears those fields so another explicit preview is required. Removed uncertain-state retry button means the rendered unknown-state controls expose only read-only recovery; no new automatic retry/delete/repair is introduced. Successful recovery must still pass existing parseReceipt binding checks before accept.

Important scope limit: uncertain is React component state, not durable cross-session idempotency protection. Existing close/navigation/identity-reset/unmount behavior can discard it, and the existing UI warns that closing does not cancel server handling. This patch does not provide a persistent lock across reloads, windows or processes. It also does not fix backend filesystem/DB commit ambiguity, cleanup behavior, source tampering, authentication or atomic retry. A frontend lock is conservative guidance, not server-side duplicate prevention.

## Disposition

No new blocker found in the reviewed classifier/code path. The independently reproduced committed-content integrity conflict is correctly retained as uncertain/locked, and the 14 permitted first-attempt rejection codes were traced to prewrite locations. Browser interaction acceptance remains the coordinator's separate test evidence. This is a focused frontend feedback improvement, not a guarantee that all failed requests were rolled back or that closing/reopening cannot produce duplicate submissions.
