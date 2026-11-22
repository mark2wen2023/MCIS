# W20 internal synthetic PendingReview queue candidate

Parent c94de84c9a4fa2b694672753605a3dc37d240479. Independent research only.
No public HTTP registration, generic POST, role/permission change, real database,
model, human signature, report write or ECFC save. Existing FourChair is unchanged.

## Trusted host and unique reference
FrozenSyntheticContext loads ONLY the fixed 6996fa05 synthetic ECFC package:
manifest SHA e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd,
all listed source bytes, and fixed locator blob
44fc5d82279db5fa3a3c748161f3122708e85668. It calls actual locate() and checks
each statement's case. The queue reconstructs this context from pinned files;
caller-modified context dictionaries are not treated as source verification.

The same-process host owns the actual c94de84 FourChair, current draft binding,
generation and accepted receipt. enqueue requires exact live receipt equality,
same frozen case/version/draft/source-set digest, generation, four distinct issued
attempts and the four round-one roles. Each selected source must exactly match
the independently rebuilt registry. The existing _validate checks quotes again.
This is a trusted synthetic process, not authentication or a signed capability.

A reference identifies original SHA-256 + exact line + locator, excerpt SHA-256,
quote start/length (Unicode code points) and quote SHA-256. The quote must occur
exactly once within the selected excerpt; ambiguous positions reject the whole
handoff. referenceId hashes this metadata. Readback resolves all three references
against the fixed original excerpts, without placing text in the queue.

## Minimal stored record, not a bare payload
The internal record has an explicit research schema, case/draft/version/generation,
meeting and handoff digest, four attributed opinions with item/label/referenceId/
reviewDigest, and a reference map. Status is PendingReview; reviewedBy/reviewedUtc
remain null and factVerified=false. No source excerpt, quote, rationale, uncertainty
free text, candidate causal claim, targetEntityType or arbitrary payload is stored.
Original text stays in the trusted local source context for future authorized review.

This reuses AgentDraftRow's SQL table, NOT the public agent-draft HTTP DTO/schema.
The record is deliberately never submitted to formal read/review endpoints.
It is not a fully usable investigator review UI or a production queue migration.
Only citation-place counts are reported; source independence/weight is not inferred.

## Storage and atomicity
TemporaryPendingQueue accepts no database URL or existing DB. It owns and deletes
a fresh TemporaryDirectory SQLite file. Only the original AgentDraftRow and
AuditEventRow tables are created; no cases/reports/ECFC business tables exist.
Original Database.session commit/rollback, get_doc/put_doc and audit.append execute
against real SQLAlchemy/SQLite. Original append-only audit protection is installed.
BEGIN IMMEDIATE is single-writer only; no multi-process/concurrency certification.

Identity key = meeting + draft binding + generation. An exact duplicate reads the
existing document and corresponding audit, creates neither a second row nor audit.
Changed duplicate content rejects. Failed validation occurs before storage.
Audit failure after the real append has flushed rolls back both rows in the original
session. A retry starts with audit seq=1, with no phantom successful handoff.

Audit operator is explicitly synthetic-four-chair-host; action is
agent.synthetic_pending, not a human review. Test document/audit UTC is fixed
2026-02-01T12:02:04Z. No human receipt or actual authorization proof is fabricated.
No confirm/review function is provided; production review permissions are NOT tested.

## Reproduce
Use an already installed MCIS Python environment containing SQLAlchemy; do not install.
From this candidate checkout:
```sh
/path/to/existing/mcis/service/.venv/bin/python -I -B research/w20_pending_queue/check.py \
  --ecfc-package /path/to/verified-6996fa05/research/ecfc_pending_handoff \
  --locator /path/to/verified-431d9d5/research/w19_case_ranking/source_traceability/check.py \
  --temp-root /path/to/isolated/writable/temp-directory
sha256sum -c logs/W20_PENDING_QUEUE-impl-hashes-frozen.txt
```
These paths can reference verified Git exports. No download/install occurs.
Dependencies are reused, not copied into the candidate commit. Check.py pins the
actual chair/packet/database/model/audit support blobs before exercising the queue.
The test reads only fixed synthetic material; no W19 blind answers.

## Actual coverage (2026-11-22, exit 0)
- Fresh connection reopens one same-case PendingReview record + corresponding real
  audit event; chain valid; four opinions and three uniquely resolvable references.
- Exact duplicate leaves document/audit counts and contents unchanged.
- Wrong case, old version/generation, wrong locator/quote/role: zero success rows.
- A live chair on another version rejects; a live chair using unverified positions
  rejects even when caller context fields were also edited.
- Actual audit append flush followed by an injected ordinary Python exception:
  zero draft/audit rows after fresh reconnect, then successful clean retry.
- Source/free-review text absent from persisted document and audit strings.
- Only the two allowed tables exist; temporary databases are deleted after tests.

REAL: original queue DB/session, AgentDraftRow, AuditEventRow, audit append/readback/
chain, fixed-source locator, FourChair methods and quote validator.
MOCKED: FourChair constructor's own reservation ledger/file creation and packet
loader (synthetic only); one audit failure wrapper invokes the real append then raises.
NOT VERIFIED: real expert/model output, production source/identity/authorization,
human sign-off, public queue UI, formal cases/ECFC, multi-writer recovery/deployment.
Pending independent review. No merge or deployment.
