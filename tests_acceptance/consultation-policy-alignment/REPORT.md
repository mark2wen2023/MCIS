# Consultation input test policy alignment

Isolated branch fix/consultation-test-policy-alignment, direct baseline latest
fetched origin/main73fc8002868d9c6894b5fce6d03f7db690291bf6. This does not depend
on or incorporate audit-test candidate79c935d, archive7aa9b9f or HFACS1a9c802.

Fresh baseline: test_consultation_input_w73.py **15 failed,2 passed in4.91s**.
Existing Investigator requests cannot read or mutate protected consultation
originals. Some fixtures iterate403 error dictionaries; other assertions receive
FORBIDDEN instead of the expected input-domain errors. Snapshot helpers also
previously accepted error bodies without checking success, potentially comparing
two identical permission errors instead of actual state. Source route inspection
confirms require_content and report_draft write checks remain before business
validation. This is test precondition drift, not a service authorization defect.

Only service/tests/test_consultation_input_w73.py is changed among test/product
code. Allowed success/setup/input-validation paths explicitly use synthetic
LeadInvestigator. Original blank/duplicate/exact-ID/unchanged-text/whitespace and
error-precedence assertions remain; status checks added before successful JSON
consumption and alongside precedence codes. Snapshot reads actual rounds and
complete audit up to2000, asserts audit verify validity and count equality to
prevent silent truncation, and compares their full documents after invalid input.
The helper will fail if audit exceeds its limit, not silently omit later writes.

Added three restricted-role cases (Investigator/Public/InterestedState): actual
local HTTP list/open/waiver/close all403/FORBIDDEN/no-store; allowed before/after
rounds and audit snapshot unchanged. Existing Public/InterestedState malformed
request denials remain. No role grants, policy weakening, global fixture edits,
seed pruning, mocks, skipped assertions or production implementation changes.

Self-test: **20 passed in8.34s**, after.txt. Baseline evidence is baseline.txt
(only line-end whitespace normalized). Related permissions and independent
review results are saved separately. These are real TestClient service calls
with temporary seeded DBs and synthetic self-reported roles, not authenticated
SSO or production traffic. Snapshot equality covers exposed rounds/audit, not
an assertion of full filesystem/database transaction identity.

Whitespace assertions exercise existing Python parity checks, not actual C#.
No SDK installation, fabricated HFACS output or resolution of its two known
workflow failures. No claim of a passing full suite, real browser acceptance,
production identity, performance or aggregate memory guarantees. No push, merge,
deployment or protection bypass performed in this task.

Related service/tests/test_recommendation_content_access.py: **73 passed in
16.91s**, related.txt. These results are related coverage, not a full suite run.
