# Conflict revision archive: dependency assessment (not enabled)

Base be93cfa0d273bb9a0120c97f8ca2994643dcf51f, branch research/conflict-revision-archive.
Remote main checked this turn:94d5e38c926fda232bb987b60fa9145e4bcf01a7.
The base includes the unmerged bounded1.4/revision/CAS/UI stack; it is not main.
Only this proposal and ordinary synthetic tests are added. No archive version reserved,
serializer enabled, permission change, merge, push or deployment.

## What is now available, and what remains missing

- timeline/revisions.py capture stores full before/after, coverage, original auditSeq/
  auditLineSha256, previous revision SHA, actor declarations and source bindings.
  The tests check three versions and original audit row links, with no historical
  mutation probes. This fixes the old current-only prerequisite, not archive support.
- working_records_archive/service.py reject_unsupported_tables still rejects both
  conflicts and conflict_revisions. It must continue until a whole validated profile
  exists. package_intake/parser.py accepts versions1.0–1.4 and requires empty
  analysis/time-alignment.json. Nonempty conflict restore is not supported.
- package/mcase.py import_case has an older current-conflict loop using put_doc:
  merely allowing the mirror would neither restore exact row timestamps nor journal.
  A new profile must bypass that loop and insert exact rows via its validated restorer.
- Audit and custody raw lines are already restored verbatim by append_raw_line /
  custody reconstruction, then package.import is appended. This offers a usable
  mechanism; original sequences/hashes must remain stable and new import audit must
  not be represented as another human conflict review.
- The journal's registryDocSha256 is a digest, not a stored registry preimage.
  Current registry evolution can leave the historical digest unequal to today's doc.
  The new synthetic fixture demonstrates this through explicit ORM fixture evolution,
  NOT a claim that an existing endpoint changes titles this way. afterSources retains
  the original binding and bytesVerified=false. Old original bytes/registry preimages
  cannot be reconstructed from hashes. Archive can preserve these declarations, but
  cannot claim to supply or verify every historical original. A digest mismatch with
  the current registry alone must not be called tampering.
- The existing history() is a live reader, not a complete untrusted-package validator:
  it does not implement a closed schema for every revision/source field. Reusing it
  alone on imported JSON would be insufficient. Current-row access alone also does
  not authorize every historical referenced evidence item.

## Bounded format proposal (not an implemented contract)

Allocate a new explicit profile, tentatively1.5 after version review. Keep1.0–1.4
unchanged; old readers reject the new profile. Start with working-records v1 plus
optional bounded timeline v1 and conflict history; track-history v2 combinations,
recommendations, consultations, agent drafts, COLREG and commands remain refused.

Add conflicts/records.v1.json with exact format/version/caseId and records. Each record
contains key/createdUtc/updatedUtc/current doc, coverage and ordered complete captured
revision docs. Preserve absent versus null, text, timestamps, original hashes and actor
claims. The existing time-alignment mirror must equal only current docs exactly.
No history truncation to fit budgets: use existing package/member limits and reject
whole packages above documented new record/revision limits (limits still need design).

Coverage is either captured-from-creation or unknown-before-capture. A legacy record
with no journal remains unknown with an empty array; one with later revisions retains
its unknown prefix and beforeSources=null. Do not invent an origin/actor/earlier source.
This is complete preservation of available history, NOT complete lifetime history.
Unknown-history backup must be explicitly described in preview/UI. It need not be
forbidden simply because information was absent before capture.

Strict validation must establish:
1. Unique case/record IDs and row envelopes, supported conflict schema, exact current
   mirror, journal ordinals and canonical digest/preimage chain, terminal after=current.
2. Every journal auditSeq maps to the exact original raw audit line; action, entity,
   actor declaration and timestamp agree. Validate original audit/custody chains first.
3. Each registered source's evidenceId is in the same-case package; declared historical
   hash and custody anchor are preserved. Validate an anchor if present against its
   original line and correct evidence, without replacing it with the latest version.
   Null anchors and unavailable historical preimages stay explicitly unverified.
   Unresolved referenced IDs require a defined refusal policy, not auto-registration.
4. Export uses existing full_content gate AND existing source visibility for every
   before/after historical reference under the existing transaction; no client role
   widening. Import/recovery uses existing package gates and restored policy. Reading
   history after restore must continue to recheck current permissions.
5. Reject orphan journals, competing authorities, unknown fields/versions and unsupported
   other tables. Only the exact new profile admits the two conflict tables after
   validation; never add them globally to ALLOWED_TABLES.

Restore inserts current rows and immutable journals once in the existing staged DB
transaction, with original audit lines. Do not replay POST/PATCH or disable append-only
triggers. No new conflict.add/update, actor authentication, active request receipt or
human approval is manufactured. Existing-case imports remain refused. Subsequent
normal edits use existing CAS and append a new revision. Existing file/DB crash and
unknown-commit limitations are not made atomic by this design.

## Required ordinary acceptance before enabling

Three stores: create A→B→C including long Unicode notes and two declared source versions;
export→restore→export→restore; compare exact current row envelopes, all journal docs,
original audit/custody prefixes, policy and retained source bindings. Only legitimate
package.import audit additions and archive lineage may differ. Then edit using a fresh
CAS read and verify the chain extends. Include legacy empty/partial journals, explicit
unknown preview, historical sources differing from current registry, unsupported-state
refusal, existing empty/1.0/1.2/1.4 compatibility and injected transactional rollback.
Permission regressions must be ordinary allowed tests, not restricted prior probes.
Frontend parser/preview must explicitly support the new bounded profile and unknown
coverage before any claim of product restoration. Browser/real-case acceptance remains
separate. No production enablement until these checks are implemented and reviewed.

## Tests actually run

`service/.venv/bin/pytest -q service/tests/test_conflict_archive_dependencies.py`
Final:3 passed in0.82s. First run:2 passed/1 failed because a test expected a localized
phrase rather than the actual ARCHIVE_RESTORE_UNSUPPORTED error code; corrected to
that exact code and reran. Covers multi-version/audit associations plus export409 with
unchanged DB/files, registry-only binding limitation, and legacy unknown prefix.
All synthetic; source test uses actual ordinary evidence/interview/report fixture APIs
plus an explicitly constructed registry evolution. No private data or original probe.

No successful conflict export/restore exists in this candidate. No runtime edits,
full suite, browser, model, production or independent acceptance. No restricted security
or ECFC tests. Missing strict archive schema/parser/restorer, source availability semantics,
limits and preview contract prevent claiming safe complete restoration now. This is an
implementable plan, not proof that conflict archives are fundamentally impossible.
