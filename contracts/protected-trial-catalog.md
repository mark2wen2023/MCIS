# Minimal authorized trial discovery

Explicit nonproduction TrialIdentityApp only:
- GET /api/v1/trial/cases
- GET /api/v1/trial/cases/{caseId}/sources

These are new trial paths, not mounts of legacy cases/evidence APIs. Default
protected factory remains deny-all. No browser/IdP/login/config switch/deployment.
Bearer session validated in same reserved SQLite transaction. Case discovery starts
from that subject's enabled memberships only, verifies current case incarnation and
conservative full-content policy, omits missing/stale/denied cases. No titles,
unauthorized totals or per-case exclusion reasons. Source lookup authenticates case
before lookup; unknown and unauthorized cases both403. Role/operator headers confer
no authority. Origin/Cookie/encoded bodies/query strings/declared GET body refused.

Source list uses current local source-incarnation indexes only; restored historical
markers never make candidates. Current bytes/registration/audit/permissions/review
flags checked; one invalid current source fails whole list instead of returning
partial results. Only CSV or Document PDF candidates returned. This does not validate
CSV mappings, PDF semantics, relationship claims, or guarantee later save succeeds.
Sources unsupported by this narrow selection purpose are omitted. This is not a
complete general evidence catalog and does not list raw historical archives.

Minimal projection: case ID/incarnation/epoch; source ID/SHA/registration digest/
size/registered time/incarnation/media kind/not_assessed. No filenames, paths,
titles, uploader/operator, metadata body, contents or credentials returned. Current
save/read routes reauthorize independently; catalog output is not a write credential.
No mutations/audit/custody/LLM/core calls for listing. Budget100 case memberships and
100 current sources, overflow413 without partial list/count. No pagination yet.
SQLite writer reservation serializes concurrent DB policy/membership edits; final
session/authority check happens after response materialization. Mutable disk and
revocation after response decision remain limits, not immutable-store guarantees.

Tests: actual temporary SQLite and ASGI fixtures; expanded actual-W2 test exercises
catalog -> POST -> GET/replay/revocation, but case creation and original intake still
use legacy test preparation and trusted-host identity provisioning. Not entire
workbench authentication, network/browser/IdP/LLM/deployment or production capacity.
