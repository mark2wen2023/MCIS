# Timeline-only archive format selection

Branch fix/timeline-only-archive-profile, exact parent
b23c7b6d1f7091e4a4acab8e20fa947ca6a60f2b, dependent on e68bacc -> 2cb43812 ->
main94d5e38. Remote main and existing candidate head checked unchanged this turn.
Local candidate only; no push, merge or deployment in this task.

## Before: ordinary exact-commit comparison

Ran the same synthetic HTTP script against a detached complete b23c7b6 checkout
and exact parent e68bacc checkout. Create a minimal synthetic case through existing
test fixture, add just TE-01 through POST timeline/events as LeadInvestigator (using
existing HEAD test headers), GET export, then commit bytes to a fresh temporary app.
Both versions returned:
- export200, manifest1.0.0, nonempty analysis/timeline.json included;
- restore422 PACKAGE_INTAKE_INVALID: 暂不支持非空业务内容：analysis/timeline.json;
- destination database/files snapshot unchanged.
No report or other working records were added. This is an inherited format-selection
bug, not evidence that every main case is affected. Temporary script location was
/tmp/mcis_timeline_only_probe.py; durable regression is the test below.

has_history did not inspect timeline_events. Thus export_case took the legacy branch
rather than the existing1.4 path that prevalidates restoration before returning bytes.

## Minimal fix and compatibility

Add two production lines to has_history to detect a nonempty TimelineEventRow for
this case. Existing bounded assembly emits1.4 with working-v1 and exact timeline rows,
including when report/interview lists are empty. Existing full-content authorization,
reference checks, unknown-state refusal, rollback, timeline+track-history refusal,
row bounds and all version validation remain unchanged. No whitelist or parser edits.
This changes timeline-only export format from1.0 to1.4; old clients rejecting1.4
continue to reject, and earlier nonempty legacy1.0 packages are not newly accepted.
Empty cases still export1.0 and restore. It does not broaden complex-case support.

## Developer verification

```
service/.venv/bin/pytest -q service/tests/test_timeline_only_archive.py service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
**91 passed in26.67s**, no skips/failures in this selected set. Four new ordinary
synthetic tests verify:
1. No report rows; export -> restore -> export -> restore -> export. Exact original
   timeline rows survive, source digest changes to latest import, original row digest
   remains equal, both source packages retained and audit prefixes/chain preserved.
2. Timeline plus unsupported recommendation state returns409 with no ZIP/no writes.
3. Investigator and Public still receive403/no writes for full-package export.
4. Empty case retains1.0 export and successful restore.
Initial run had three test-fixture failures because TE-ONLY violated the existing
TE-[0-9]{2,} schema. Corrected synthetic ID to TE-01; no production schema relaxation.

No frontend changes/build/browser run this turn. Browser, independent acceptance,
real identity, load/memory/crash recovery, HFACS/LLM and full test suite not validated.
Original190 baseline failures not rerun or claimed fixed. No restricted historical
security/ECFC operations repeated. Latest-import provenance remains only recent import
membership, not full lineage or new review; old stores without bindings stay unknown.
