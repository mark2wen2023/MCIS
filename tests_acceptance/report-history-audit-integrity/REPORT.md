# Historical report audit integrity follow-up

Isolated follow-up on ac0dfe173bad84e967e829d4ba30d0d797997ccc, still depends on
PR95 0c182570107079794af048bfaf4e19a64b70dd63. No production/policy changes.

Independent review demonstrated tampered ReportAuditRow historical fields could be returned
by audit-list and report-snapshots GET while live GET rejected transplanted history. The
review also confirmed tightened permissions still denied both audit paths: integrity flaw,
NOT demonstrated permission bypass.

Both paths now check event snapshot_ref/entity ownership and recursively validate before/
after history with persisted case/report/time context. Generation and review are bound to
the owner; regeneration before-value is bound to its parent. Live report reads also validate
nested review history. No current-register lookups/reconstruction. Legacy no-history reads
stay compatible; v1 data with missing/inconsistent binding returns 409. Existing permission
checks run first, so a denied requester receives 403 without corrupt fields or details.

Focused verification: 24 passed in 12.17s (11 new audit tests + 13 existing history tests).
New synthetic real TestClient/SQLite scenarios cover field tamper without rehashing, full
report and citation transplant, stripped version/binding, changed snapshot owner, review
before/after tamper, legitimate regeneration then corrupted parent history, audit permission
denial, and legacy history absence. Initial implementation used a nonexistent ORM
snapshot_ref attribute; fixed to read existing audit line metadata before final tests.

Independent full-suite acceptance is pending. Earlier expanded baseline/candidate each had
50 passes and 59 failures with exactly matching failed node IDs. Root causes have NOT been
individually established; this follow-up does not claim the entire suite passes. Real
browser, real model/HFACS, SSO, production performance and recommendation archive roundtrip
remain unverified/blocked. Hashes are consistency checks, not authentication/signatures;
coordinated edits of payload/digest/context are outside that guarantee. Current role headers
are still self-reported. No automatic retries, cleanup, merge or deployment.

Expanded selected regression: 140 passed in 43.05s (regression.txt), comprising new audit
integrity, source history, original cause provenance, report sources, W162 access, attachment
access and font coverage tests. This is a selected suite, not the entire repository. No
frontend code changed; browser checks were not performed in this follow-up.
