# Knowledge source snapshot freshness preview

This standalone Python callable is a non-persisting adapter, not a mounted API,
UI or publication guard. Existing review expectedDigest binds candidate content
but does not establish whether an external source has changed. This slice adds
an exact comparison utility without changing existing review behavior.

Call service/mcis_service/knowledge/freshness.py preview(body) with exact fields:
profile MCIS-KNOWLEDGE-SOURCE-FRESHNESS-1; candidateContent (JSON object with
source); expectedContentDigest (canonical full-content SHA256);
candidateSourceCapturedUtc (UTC YYYY-MM-DDTHH:MM:SSZ or null if unknown);
observation ({status: unavailable} or
{status: provided, source: {...}, capturedUtc: UTC timestamp or null}).
Timestamps are caller declarations, never verified or synthesized. Null remains
unknown, not current. Timestamp differences do not themselves prove content
changed. No clock-age threshold is applied.

Source requires type, title, locator, excerpt, rightsNote; Public also requires
url, Synthetic forbids url; all additional fields fail. This comparator does not
validate full card business schema or URL reachability. Callers must keep their
existing input, access and release validation. Limit32KiB canonical UTF8 JSON.
All source fields are compared exactly, including rightsNote and URL. No
whitespace normalization, semantic comparison, OCR or LLM calls.

Outputs changed / unchanged_snapshot / unavailable, sorted changedFields,
originalSourceDigest, observedSourceDigest (null if unavailable), content digest,
declared capture times, and comparisonScope exact_supplied_source_fields.
recheckRequired is true for changed/unavailable; even unchanged_snapshot returns
reviewRequired=true, sourceCurrentnessVerified=false, captureTimesVerified=false,
sourceAuthenticity=not_verified. Same snapshot is NOT proof the current external
source is unchanged, public, authoritative, authorized or factually correct.
Changed snapshots do NOT auto-withdraw/approve cards or infer which claim is true.
Missing required fields reject rather than return unchanged.

No network, model, database, mutation, approval or case write. No card IDs,
operators or raw excerpts in result. Synthetic tests are protocol-only.
Remaining: storage and trustworthy capture provenance, authenticated API/UI
integration, real external source retrieval, re-review workflow and production QA.
