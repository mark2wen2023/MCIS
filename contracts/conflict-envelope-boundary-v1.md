# Experimental conflict envelope boundary v1 (offline only)

This is a validation seam, not an enabled package export or restoration profile.
`working_records_archive.conflict_envelope.inspect_envelope` accepts exact ZIP bytes
and an explicitly supplied expected_sha256. The checksum may be caller-declared: it
is transport consistency, not authentication. Return type BoundaryInspection always
has restore_ready=false; it contains counts/case/digest only and is NOT ParsedPackage.
There is no route, exporter, importer, persistence or authorization wiring.

## Experimental scope

Manifest packageFormat=MCIS-MCASE; packageVersion=1.5.0-draft.conflicts.1. This tag is
only for synthetic/offline inspection, not allocation of a stable1.5 product version.
Normal package readers continue to reject it. Existing1.0–1.4 readers are unchanged.

Required members: manifest.json, case.json, case.ext.json, vessels.json,
evidence/index.json, audit/audit.jsonl, audit/custody.jsonl, access-policy.json,
conflicts/records.v1.json, analysis/time-alignment.json. Additionally only uniquely
registered raw/* evidence files and the existing explicitly EMPTY timeline/COLREG/
recommendation/consultation/agent sections are accepted. Working-record/history/HFACS/
track/timeline extensions and all unknown files are refused in this narrow seam.
No wider combination is claimed. This is deliberately narrower than the future
combined-profile plan; it does not downgrade an existing live product allowance.

Use existing bounded ZIP reader: duplicate/case-alias/traversal/special members and
member/count/compressed/expanded budgets retain existing rejection. Validate exact
manifest fields, roles, sizes and SHA256 of every member; inventory must equal the
actual non-manifest file set. Manifest is bound through the whole-ZIP checksum and
is not self-listed. Missing, duplicated, unlisted or differing members fail.

Validate base case/extension schema and identity, vessel/evidence IDs, default policy
as required by current intake, and registration metadata/custody links. Every evidence
path must point to a unique included raw member whose actual packaged bytes match its
registration digest. This check does not establish original-world provenance or verify
unavailable historical originals. Active intake-history markers are refused without
their not-yet-supported receipt archive. Replaced-original custody history remains
refused, just as the current outer package reader refuses it.

Pass exact member/audit/custody/evidence dependencies from these same ZIP bytes to the
isolated conflict member parser; accept no external substituted dependency list.
Mirror analysis/time-alignment.json must exactly equal the validated current documents
(including order, absent/null and values), with no extra fields. The member parser
preserves captured revisions, audit/source associations and legacy unknown coverage;
registryDocSha256 remains an unverified historical declaration, bytesVerified=false.
No normalization, dropping history or rehashing input to make validation succeed.

## Failure and limitations

Failure raises ConflictArchiveInvalid with no partial return. No case file/DB changes
occur (checked-in schema files can be loaded). The caller still needs current server
permission checks and a complete trusted export inventory; a supplied package cannot
prove that its producer omitted no unknown database state. Hash consistency is not
identity authentication. This function must never be treated as import permission.

Failure injection tests exercise existing normal supported-case transaction rollback
if this validator raises after rows were inserted but before publication. They do not
connect a new restore path and do not prove crash/unknown-commit atomicity. No conflict
restoration, complete available-history roundtrip, second export or browser acceptance
exists yet. Those plus compatibility and unsupported-combination tests are required
before contemplating any change to conflict export refusal.
