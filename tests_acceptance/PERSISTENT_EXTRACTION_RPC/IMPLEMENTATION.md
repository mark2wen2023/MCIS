# Persistent working-review trial RPC and fictional stdio fixture

New `agents/persistent_extraction_rpc.py` adapts exact trusted PersistentExtractionReviewHost objects; only fixed context/case/record allowed. Distinct persistent profile keeps existing ephemeral UI unchanged. Caller supplies no credentials, provider, database path, model output or author identity. Strict generate/list/read/review schemas reject unknown fields and explicit null extras. requestId identifies transport request, operationId identifies durable mutation; changing payload under a seen requestId is rejected. Same operation can be retried with its original payload after an unknown result. Seen request IDs capped128; inputs64KiB, outputs4MiB+1024. Busy and closed state prevent overlapping commands/late successful publication. Worker-return authorization/source binding rechecked before projection.

Projection includes original immutable proposal content and review decisions. Generated actor identity omitted; review authorSubjectId is projected as authorRef, an internal investigator identifier, not verified human name. Original raw sources/session secrets and arbitrary internal fields are not projected. Working storage remains working_record_only, factActivated=false. A stored pending proposal is distinct from later stored review revisions.

`agents/persistent_extraction_fixture.py` rejects all CLI arguments, provisions only fixed fictional documents/provider in its own TemporaryDirectory SQLite, and uses bounded JSON lines with duplicate/nonfinite rejection. Ready explicitly states temporary-sqlite-deleted-on-process-exit and crossProcessRetention=false. Same-process UI remount can recover via list/read; this demo makes no claim of cross-process retention. Reads have30-second idle/300-second waiting deadline, not a hard wall-clock bound on blocked stdout/whole process. SIGKILL cleanup not promised. No socket listener, old HTTP login, real model or real input.

Main tests16/16 passed, zero skips,12.12s, one known deprecation warning. Includes actual subprocess generation/list/read/review/re-read, anonymous author projection, same-op replay and changed request conflict, stale revision, strict forbidden fields, busy/close late response, temporary directory clean exit, invalid CLI/JSON/oversized input. Initial4 fixture failures were ordering error: attempted first authority check after put_doc had already started an unproven transaction. Fixed fixture to authorize/reserve writer before inserting the fictional interview or granting dedicated working access; product authorization not weakened.

Independent review is performed separately. No push, merge, deployment, production browser IPC or durable user-facing application rollout by implementer.

Final error-classification hardening: ValueError after starting generate/review is WORKING_RPC_UNCONFIRMED503, not a rejection implying no save. Added actual committed generation with injected response-projection failure, then same-operation replay proving the durable effect appears exactly once. Final main **17/17 passed, zero skipped,12.95s**. Product files frozen and independent reviewer notified for combined rerun.

SHA256:
- persistent_extraction_rpc.py `cb7bdb9b4b72d6fb3f016e5d49491ff1c7183eda66957af9bc8dcb4a5372e8d1`
- persistent_extraction_fixture.py `ee9c4cec82aa8e301e873671f7615036918b9537f465bb0f20cebb50c08d7cd6`
