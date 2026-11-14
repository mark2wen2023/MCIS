# Independent research-note export review

Scope: new `export_review.py`, based on existing semantic evaluator and HTML renderer. Native independent subagent; no model/API calls, no deployment or Git push.

## Result
No blocking issue found in the bounded CLI workflow. Independent 10 cases pass; combined primary16 + independent10 =26/26 in0.48s. This is Python/CLI/HTML parsing, not browser visual or CSP enforcement acceptance.

Independent checks cover:
- Every supplied note is literal HTML text; closing tags, scripts, image/event injection remain escaped. No new network/navigation/script/form elements or pre-ticked fields appear.
- Reordered worksheet items bind by exact ID; original corpus, predictions and worksheet objects remain unchanged.
- Unexpected factVerified/reviewerId/approved/label fields reject rather than importing authority.
- Any changed prediction file bytes invalidate a worksheet's captured predictions digest.
- Duplicate JSON keys reject before output creation and do not echo sensitive sentinel text.
- Actual CLI export with socket construction prohibited writes mode0600, emits no model/case update claim, and matches independently generated expected bytes with the actual worksheet file digest.
- Output budget rejection.

## Boundaries and residual limitations
This is explicit local file export, not authenticated review storage, a signature, production UI, browser form saving, or an official case record. Existing blank controls remain temporary and do not populate the snapshot; top/bottom notices explain this. User must explicitly edit the generated JSON and run export. False flags mean unmarked, not verified.

Raw-byte SHA binding is a local consistency check only; arbitrary callers can fabricate input files and hashes. The CLI computes hashes from loaded bytes. Pure Python functions accept supplied digest arguments and are not a remote security boundary.

Exclusive output creation rejects existing files/symlinks. A write/fsync failure can leave a partial newly created file; no success is emitted. This is not a transactional durable storage protocol. No browser render/print interaction or OS crash persistence is claimed.
