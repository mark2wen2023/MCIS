# Conservative existing-conflict observation guard

Same-ID POST retains timeline write policy and expectedVersion comparison first.
Within the same reserved SQLite transaction, before any put/audit/capture, compare
both complete a/b observation documents with current. ANY difference returns409
CONFLICT_SOURCE_REVIEW_REQUIRED: preserve draft and original record, source-version
review is unavailable, edit handling note/status separately. No replacement receipt,
caller digest or permission fallback. Refuse even if current registry digest happens
to match; digest coincidence is not proof of the version the user saw. Unknown or
unregistered observation changes also refuse, rather than silently assigning meaning.

Unchanged a/b POST can still update other allowed existing fields. PATCH accepts only
existing status/resolution/expectedVersion and keeps current timeline permission.
Unchanged observations retain captured source association without querying newer
registry values. Legacy row with no prior revision: afterSources stays unresolved
for an evidence ID, unregistered for absent ID, bytesVerified=false and no digest;
beforeSources=null and coverage=unknown-before-capture. Subsequent note edits retain
that unknown association. No previous history/author/source version is invented.
This applies to forward captures only, not rewriting existing journals.

Compatibility is intentionally tightened, not transparent: old source-changing POST
clients now receive409 even with valid conflict token; missing token still428, stale
still412. No automatic new ID creation, refresh-and-retry or lost-draft workaround.
Existing workbench only PATCHes handling note/status and retains its draft behavior;
no new client observation editor is claimed. API cannot guarantee third-party clients
retain their drafts. New-record POST remains existing declared registration behavior,
not a source-read receipt/human confirmation. This change does not establish same-read
original bytes, authenticity of actor, complete source review or generic A→B prevention
across all modules. Existing archive refusal and visibility policies are unchanged.
