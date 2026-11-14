# Independent audit policy test alignment

Verdict: PASS for the local test-only alignment on parent73fc800. This is not a service permission change or a full-suite acceptance.

Read AGENTS.md and handoff; inspected the complete test diff and existing audit/router.py, audit/service.py and recommendations/access.py. Product service/contracts/web diff against HEAD is empty. The frozen implementation is only service/tests/test_audit.py; independent hash verification passed1/1.

Fresh independent command:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_audit.py
```

Result: **9 passed in2.28s**, independent-tests.txt. independent-hashes.txt records the frozen hash check. Coordinator baseline.txt retains **1 failed,7 passed**; that baseline was inspected, not rerun by this reviewer.

The existing list route applies full-content recommendation/interview/report gates in addition to audit-category permission. The verify route returns chain summary, not original lines, and does not apply those original-content gates. Thus selecting synthetic LeadInvestigator for the seeded audit-original success case aligns the test with current service policy; it does not grant Investigator access or bypass the service gate.

Original substantive assertions remain: valid nontrivial chain/count, contiguous sequence, zero initial hash, previous-line hash linkage, UTC ordering, canonical key order; audited-write count increase; append-only audit/custody trigger cases; tampering detection and ExternalExpert denial. New explicit HTTP200 assertions prevent parsing an error as successful data. A separate new Investigator case requires403/FORBIDDEN/no-store and absence of line/events fields, while verify remains200/valid and its complete response stays identical before/after denial (including count/headHash). No assertion was deleted, no fixture was sanitized and no skip/mock/fallback was introduced.

Limits: synthetic role headers test policy, not authenticated SSO. Top-level absence of line/events is not a general recursive leak audit, and matching verify summaries is not a full database-state snapshot; the report does not claim either. Existing write-test request statuses were not strengthened by this patch, although its three-event count assertion remains. Broader service failures and browser/HFACS issues are outside this narrow test adjustment.

No product/frozen implementation edits, commit, push, merge or deployment were performed by this reviewer.
