# Offline conflict ZIP boundary v2

Experimental profiles only, not supported product .mcase versions:
- 1.5.0-draft.conflicts.1 -> conflicts/records.v1.json -> member version1.
- 1.5.0-draft.conflicts.2 -> conflicts/records.v2.json -> member version2.
Exact profile/path/member agreement required; both paths present, unknown versions
or silent downgrade reject. Old v1 schema and historical fields retain original meaning.

build_envelope accepts explicit bytes in a member map and builds a manifest/ZIP,
then validates its exact output before returning. It is not a DB exporter or file
reader. inspect_envelope accepts bytes plus expected whole-ZIP SHA256; returns
counts/member version, restore_ready=false and receipt_authorization=inactive-history.
Neither function grants access, authenticates supplied bytes or restores data.

Required manifest/case/case.ext/vessels/evidence/audit/custody/access-policy/member/
conflict-mirror entries follow the earlier bounded experimental v1 envelope. Each
manifest path, role, size and SHA must match exactly; no omitted/unlisted members.
Reuse existing bounded ZIP reader and strict JSON. Envelope max32MiB; builder also
caps supplied member bytes32MiB, member parser retains its16MiB cap. No performance
claim or lifting of existing reader budgets.

Case identity, vessel/source references, custody registration metadata and member
before/after/audit/history checked as one supplied snapshot. Every packaged evidence
file must occupy unique raw/ path and match its registered SHA. Only synthetic bytes
were tested: digest match is not historical provenance/original-authenticity proof.
Replacement-original history remains unsupported. Default policy only (existing
restriction), active intake history, nonempty other modules and unknown combinations
remain refused. Existing empty placeholders retain old behavior.

v2 delegates full member validation including all consumed and unused historical
receipts, issuance audit, captured revision/version/source bindings. All remain
inactive-history, never written to an active receipt table. Unknown legacy histories
remain unknown/empty, not inferred from current data or reconstructed retrospectively.

Preserved raw member values can be unpacked and re-enveloped without altering source
members; generated manifest timestamps/ZIP bytes need not be identical. This is not
restore/edit/re-export. Product parsers still reject both experimental ZIP profiles;
product export guards unchanged. Existing supported .mcase1.0-1.4 formats are not
accepted by this research inspector and must continue through their existing parser.
Full production old-package regression and editable recovery remain outside this step.
