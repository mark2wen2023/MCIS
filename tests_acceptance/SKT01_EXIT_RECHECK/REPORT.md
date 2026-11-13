# Existing align-preview exit recheck acceptance

Implementation base: 6f6959377b6c63294f589761ff1b7cd56116051b.
Executor: native implementation subtask + separate native acceptance subtask.
Scope: real service route, real fresh SQLite sessions, FastAPI TestClient.

## Results
- Existing service/tests/test_align_preview_w41.py:30 passed, no skips.
- New service/tests/test_align_preview_recheck.py:6 passed, no skips.
- Existing tests_acceptance/W4/test_align_preview_independent.py:31 passed.
- New independently authored test_align_preview_recheck_independent.py:3 passed.
Total70 local targeted tests across these runs. No CI/full-repository claim.
A pre-existing Starlette/httpx deprecation warning is unrelated to the change.

The36-test service run was independently rerun. It includes the existing
real-core success test and2 new real-core cases (success and access revoked
after actual computation). Other core responses are controlled test doubles.
All cases use temporary real SQLite databases and actual service handlers;
none uses an externally deployed server or browser.

New failure paths: current timeline access denial returns403 with no result;
case epoch changed in a second database transaction returns409;
case removed returns404. Same instant in another timezone expression and
unrelated case-title edits remain allowed. Independent checks also cover
role removal and denial before core call. Persistence regressions keep
existing conflict/timeline/audit records unchanged except intentional test
changes of case/policy state.

## Reproduction
Use installed service dependencies (service/.venv). Set MCIS_CORE and
MCIS_ACCEPTANCE_CORE to a trusted executable wrapper that forwards arguments
to a real built mcis-core.dll; MCIS_DOTNET points to the installed dotnet.
The original CLI script must be present for existing HAS_DOTNET detection.
No binary or machine-specific wrapper is committed.

Run pytest on the four named files (include service and tests_acceptance/W4
on PYTHONPATH). Our DLL used the earlier verified package-free direct-Roslyn
build; see research/skills_timeline/REVIEW_REAL_W2.md. This is not a standard
MSBuild/CI build. No NuGet access or permission bypass.

## Boundaries
The old role/operator HTTP headers are not authentication. This uses existing
access policy, adds no new privileges, and does not make production security
claims. The final check is not atomic with response delivery. Temporary
revocation/reinstatement or delete/recreate with identical epoch is outside
the guarantee. No evidence IDs, blob hashes, reviewed observations, original
AIS/VDR, manual approval, LLM or UI workflow is added. Legacy /core/align
and global subprocess resource limits remain unchanged. No merge/deploy.

Final combined rerun of all four files:70 passed, zero skipped,23.82s.
