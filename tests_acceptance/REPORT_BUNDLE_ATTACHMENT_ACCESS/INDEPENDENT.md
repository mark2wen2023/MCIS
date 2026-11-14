# Independent review: copied report ZIP byte-delivery gate

Reviewed only the new `report_output/attachment_access.py` helper and the two live
evidence download changes against `contracts/report-bundle-attachment-access.md`.
No implementation or PR61 filename files were changed by this reviewer.

Command:

```
service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/REPORT_BUNDLE_ATTACHMENT_ACCESS/test_independent.py
```

Result on2026-11-14: **30 passed, zero skipped, 9.68 s**. One existing Starlette/httpx
deprecation warning. HTTP uses real in-process FastAPI routes and temporary SQLite;
case and file fixtures are synthetic, not real investigative records.

Independent coverage:

- Both routes reject each of12 permission categories individually set to Deny,
  return403/no-store, expose no fixture bytes and add no Access event.
- Giving Investigator all12 ReadOnly permissions does not override applicable field
  redaction rules. Clearing those rules permits exact bytes and one Access event.
- During container classification, a second physical SQLite connection attempts
  BEGIN IMMEDIATE with timeout0 and gets `database is locked` for both routes.
  This verifies the route has already reserved the database writer, including
  against another process that does not share Python WRITE_LOCK. It is a deterministic
  reservation check, not a long-running scheduler or distributed concurrency stress test.
- Injected classifier exceptions return500 without exception details or Access events;
  these are explicit fault-injection tests, not claims of real infrastructure faults.

Code review found no blocker within the stated narrow guard. Classification depends
on bytes rather than filename/category, covers leadingPK and EOCD-recognized prefixed
ZIPs, and performs no member extraction. The existing full-content checker is reused;
policy reads and successful audit occur within the same reserved transaction. The
historical route is unchanged and already uses full-content authorization.

Limits remain material: all ZIP containers (including DOCX) receive the stricter gate;
non-ZIP report copies and unrecognized transformed/damaged files remain outside this
fix. This does not add general DLP, authenticated production identity, reportId binding,
automatic persistence, signature validation or a complete source-policy closure.
Reviewer did not independently rerun the implementer's pre-fix reproduction or full
regression suite; their results must be reported separately. No deployment or merge.
