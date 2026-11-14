# Existing timeline align-preview: response-boundary recheck

Endpoint: POST /api/v1/cases/{case_id}/timeline/align-preview.
Existing request/response schemas and no-persistence behavior are unchanged.

After core execution and output validation, a new database session:
1. Loads the case again (missing case: existing404 CASE_NOT_FOUND).
2. Applies existing timeline access policy again (revoked access:403 FORBIDDEN).
3. Compares current caseEpochUtc with the original instant, timezone-normalized.
   Changed instant:409 ALIGN_PREVIEW_CASE_CHANGED; no computed result is returned.
4. Returns the validated preview only if these checks succeed.

An unrelated title edit or an equivalent timezone spelling does not change
the time origin. This check neither writes business data nor approves evidence.
Core failures retain their existing error behavior; they never return previews.

This improves the real case-service boundary, NOT the research adapter alone.
It is NOT an atomic lease: a subsequent policy change after recheck, temporary
revocation followed by reinstatement, or case deletion/recreation with an
identical epoch is not certified by this check. No evidence-ID/hash binding,
reviewed extraction record or original-media comparison is introduced.
The existing local role/operator headers remain unauthenticated. Do not describe
this as production identity/security readiness. The legacy /core/align route
and global core-process output-budget limitations remain outside this patch.
