# Archive-compatible actor text validation on existing writers

Verified actual main remains3aba2bf. Isolated copy from285 hash-checked main service/contracts blobs.
Only knowledge/router.py runtime change: validate_actor checks actual str, nonblank, <=160 Python
Unicode codepoints, valid UTF8/no disallowed controls; called after existing role gate, before create
or review transaction. Reuses existing strings rules. Does not trim, truncate, normalize or authenticate.

Existing defect:161-character actor could create/review successfully but archive subsequently rejects
createdBy/reviewedBy/audit.operator. The precheck prevents new invalid rows. Existing archival validation,
format, history and actor values are untouched. Already-invalid archives require explicit remediation,
not silently rewriting append-only history. Valid historical data remains readable as before.

27 focused tests: rejected create/review leaves candidate/status/audit/epoch/snapshot unchanged and
archive identical except export clock;160 ASCII/Chinese/emoji,80 decomposed character pairs, spaces,
LF/TAB retain exact text and archive. Untrusted-but-syntactically-valid actor still accepted, proving
this is NOT authentication. Real SSO/org/case authorization remains unsolved. Local DB/functions only,
no real user identity, network/API or model test in these cases.

Integration note: independent hostname fix also edits knowledge/router.py create line. Preserve both
prechecks before writes when coordinating; this branch intentionally contains no hostname patch.
No other runtime files changed. No source authorization, deployment, merge or push.
