# Issue journal supplemental archive slice

Implemented actual export/restore/read/list service operations for a bounded JSON
bundle of all current local issue event histories and direct referenced source
bytes. Export refuses changed/missing historical sources instead of silently
omitting them. Restore is atomically stored only as untrusted/inactive historical
payload, with no activation of subjects, grants, sessions, source indexes, issue
operations or live Event rows. Same digest replay is authorized and scoped to the
target case incarnation and epoch. Source bytes remain within the inert record;
no file extraction or URL requests are performed.

Compatibility: separate versioned format and metadata initialization; old `.mcase`
and app routes unchanged. This is not a complete case/parent-evidence-chain backup,
production login or browser UI feature. Historical event epochs remain distinct
from exportCaseEpochUtc, and target epoch is separately bound.

Independent review reproduced version=True accepted as1; fixed with before-value
validator. Digest authenticity is explicitly not claimed. Per-source encoded-budget
precheck was added before base64 allocation. See independent report for final tests.
No merge or deployment.

Related combined regression:178/178 zero skips, including issue journal/domain,
HTTP/identity/catalog and previous web-demo service coverage. This ran before the
last pre-base64 allocation budget hardening; final archive-only acceptance is
reported separately and must not be called a new full-suite/CI run. Existing
Starlette/httpx deprecation warning persists.
Final frozen archive acceptance after the budget change:29/29 zero skips (9 primary,
20 independent). These are local tests, not browser/LLM/network or GitHub CI passes.
