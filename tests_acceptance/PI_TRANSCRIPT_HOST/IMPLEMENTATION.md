# Pi transcript Python host implementation check

New callable and fixed fictional stdio host only. No legacy interface changed,
no model credentials, no remote requests or database writes by analysis tools.
Source/permission checks reuse the existing current-case `_snapshot` boundary.
4 model / 8 tool / 120 second limits. Tool counts include invalid attempts;
source/authority failure and timeout close the run. One model pending at a time.
Readonly tools return only redacted ranges, literal matches and checked proposals.
Final result is PendingReview, saved=false, factVerified=false, persistentAudit=false.

Local command (2026-11-14):
`python -m pytest tests/test_pi_transcript_host.py tests/test_host_extraction.py -q`
Result: **44 passed**, zero skips, 26.65 seconds. Includes 29 new host tests and
15 existing extraction-host tests. Real temporary SQLite and four actual Python
stdio subprocess cases; model responses remain fixed synthetic data.
Starlette/httpx existing deprecation warning remains.

Tests cover successful read/search/citation/final flow with SQL row counts
unchanged; mandatory private fragment masking; strict tool/protocol fields;
unknown tools; bool-as-int rejection; missing/out-of-range data; invalid proposal
schema and fabricated quote; source mutation; session revocation during inference
and during tool processing; limits; pending-model invalid tool ordering; generic
stdio failure with no traceback or secret output. The final result closes host.

This does NOT establish Pi/DeepSeek runtime acceptance, genuine inference,
production authentication/browser integration, persisted audit, CI, merge or deployment.
Parent owns Pi runtime/cross-language acceptance and independent review.
