# W12 selected-pair version policy — isolated experiment

Base: fa0754dc5a82012c6254c602fe287a1f2064b523.
Pin shape reviewed at c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24:
- tests_acceptance/registered-trajectory-pair/raw_two_times.py
- service/mcis_service/trajectory_exchange/registered_pair.py::_read_registered_pair
- service/mcis_service/trajectory_exchange/registered_query.py::_query_registered_pair

Those readers require server-selected pins and perform original reads/Access;
they do not provide an authoritative current-pair selection store. This test
NEVER invokes them. It copies the existing caseId/evidenceId/requestDigest/
sourceSha256 shape, with ordered vesselId from the verified original projection.
No revision counter, latest-by-time lookup or new trajectory representation.

Run with the standard library only:

```sh
python -I -B tests_acceptance/analysis-pair-version-policy/check.py
```

The sole decision entry is compare_versions(case_id, ordered_vessel_ids,
selected=Pair-or-None, receipt=GenerationReceipt-or-None). freeze_pair copies
only identity fields into frozen dataclasses; it is NOT authorization. Every
comparison revalidates both sides, even if one is absent. Malformed, cross-case,
wrong-vessel/order and duplicate-original inputs raise InvalidBinding. There is
no partial decision on error.

- current: exact equality of both ordered vessels and all four pin fields.
- historical: same case and vessel ordering, but at least one pin field changed.
- unknown: valid available inputs, but selection or generation receipt absent.

These are source-version equality decisions, not measured accuracy, valid
geometry/time coverage, authorization, causality or live recomputation.
GenerationReceipt is an experimental immutable in-memory input contract, NOT an
existing production receipt, signed object, persistence mechanism or issuer.
Synthetic tests explicitly construct it; there is no real selection provider.
Only a future trusted server caller may obtain both records and use the policy.
Browser JSON, UI labels, hashes alone or a passing freeze_pair never establish
trust. Reauthorization and concurrent selection changes still need integration.

The historical seed GET on this base has no such receipt. Its seedSha256 and
seedVerified cannot be used as one; the test rejects that substitution. An
absent receipt returns unknown. Existing AnalysisView already labels offline
results. No route/schema/seed/UI change or automatic production import is made.

Seven synthetic tests exercise A v1 -> v2 with B fixed, old vs new immutable
receipts, each independent pin field (including same bytes/new receipt), absent
inputs, swapped/wrong/duplicate vessels or originals, malformed hashes and
revalidation of constructed dataclasses. New generation input is constructed by
the fixture, not an actual calculation. No async caller currently carries a
trusted selected pair, so no late-response or cancellation integration is claimed.
Future delivery must compare against the then-current trusted selection, not
capture the selection used when starting a calculation.

Missing next product dependency: authoritative selected pair plus a generation
receipt captured from the actual analysis inputs, with existing access checks
and a defined selection/read transaction boundary. Then the product caller can
refuse current rendering for historical/unknown and reject late responses.

No service, DB, original Access, browser, model, report save/export, shared
contract, permissions, .NET or Actions executed. Not the W12 product closure.
