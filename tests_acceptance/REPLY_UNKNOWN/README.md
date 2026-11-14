# Recommendation reply unknown-result guard

Only existing Detail reply handler, not create/progress/status or backend idempotency. In-flight synchronous lock; unknown transport/server result preserves draft and blocks current component retry. Explicit known 4xx releases on first attempt. Late unmount/identity callbacks discarded. Successful POST plus refresh callback error remains recorded, not unknown.

Component-local lock is lost on navigation/reload/new tab; UI warns against submitting a new request to compensate. No persistent draft/receipt or authentication added.

Tests: `node tests_acceptance/REPLY_UNKNOWN/fixed-handler.test.cjs`, `node tests_acceptance/REPLY_UNKNOWN/independent.test.cjs` run 15+10 extracted actual source handler cases, synthetic hooks/transport, not React DOM/browser. `PYTHONPATH=service python -m pytest -q tests_acceptance/REPLY_UNKNOWN/test_backend.py` reproduces 3 actual-app SQLite behaviors on synthetic cases: duplicated create/reply after discarded success, and retry409 following successful transition. These are documented existing backend limitations, not fixed tests. Test uses existing LeadInvestigator role header, not real identity.

Original independent red: a successful POST followed by onChanged throwing used to enter the submit catch with cleared draft/unlocked state. Original assertion retained and extended to onCancel, now passes. Local tsc/vite build passed with existing chunk warning; CI/browser not run.

Based on actual main3aba2bf. PR67 Detail hunks apply but import hunk conflicts: preserve its BodyEditor import/bodyRevision/CAS mount while adding useEffect/useRef/ApiError. Do not replace PR67 file wholesale. No deployment/merge, no production auth claim.
