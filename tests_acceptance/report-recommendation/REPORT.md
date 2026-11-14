# Report + safety recommendation closure investigation

## Base and scope

Fetched latest origin/main is f2eff95dfb1bbf6afd92036ec589a1513f0b8840. Verified remote feature/report-timeline-web-v1 is aeb8cf1dfb18b2fd723a6d98112e550b83054801, descended through fe36587 from that main. This isolated research/report-recommendation-closure branch starts at aeb8cf1. No production code, existing schema, policy, format acceptance, frontend or stored data changed.

## Concrete evidence and meaning

1. `recommendation.schema.json` requires nonempty causeNodeIds array, describes ECFC/HFACS/COLREG cause IDs, but stores strings without typed source/case/revision identity. `recommendations/router.py` create/patch does not resolve them. The real UI RecommendationsPage uses free comma-separated labels with default COLREG-R19. Current C# board code filters blanks/duplicates, but Python API accepts even ['','']; this is a source-inspected parity discrepancy plus an actual Python API reproduction, not a C# execution result.
2. Fresh synthetic case, actual API: ['NO-SUCH-CAUSE'], ['COLREG-R19'] and ['',''] each create201 and persist exactly while case-scoped COLREG/HFACS/timeline rows are absent. This does NOT prove the original human had no external source, and is not a cross-case leak; it proves no local typed closure can be inferred from these labels alone. No arbitrary mapping from a label prefix to a source kind is justified.
3. Creating a report after a Draft or Issued recommendation generates registered recommendation citations. Registered here means the recommendation register contains that ID; it does not prove causal-source truth. Current working archive citations validator rejects this source kind and actual mixed-case export409. Authoritative rows and audit snapshot stay unchanged. Investigator export403 also leaves them unchanged.
4. Legacy recommendation-only1.0 export/import still succeeds and restores RecommendationRow. A subsequent explicitly authorized Lead transition to Issued and response to Responded succeeds. Import does not itself issue/respond automatically; it restores active editable workflow state rather than an inert history object. This must be an explicit contract choice in any future profile.
5. Same raw legacy recommendation-only package sent to new intake commit is422, no new case/rows/directory. Removing whitelist checks alone would not add cause resolution, registered-citation closure, safe historical-state interpretation or validated restoration.
6. Revoked recommendations permission returns403; nondefault ReadOnly recommendation policy returns409 even when content-readable. Both preserve full database snapshot. The policy gate and default-policy restrictions remain unchanged.

## Actual tests

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q -s tests_acceptance/report-recommendation/test_closure.py
```

**10 passed, one dependency warning /3.36s**. Tests use actual local ASGI handlers, separate SQLite databases and synthetic documents. They verify labels/current model, report/citation boundary, Draft and Issued mixed-case refusal, preserved full SQL snapshots, role/default-policy refusal, legacy active restoration, new-intake zero-write rejection, future1.5 rejection, and explicitly injected safetyrec.create audit failure returning500 with row/audit rollback. Initial fault-probe expectation assumed a raised exception; actual NoStoreRoute correctly returns sanitized500, so the test was corrected to assert that response and preserved snapshot. No implementation changed to make it pass.

These10 passes establish current behavior and rollback boundaries only. They are **not**10 passing tests of a new recommendation archive and not a successful report+recommendation roundtrip. No process-crash/uncertain-commit proof, numerical model call, private case, browser attempt or production identity validation.

## Disposition

A safe active subset cannot simply omit causes: at least one cause label is required, and even Draft carries the unresolved association. A bounded new extension would need explicit typed cause binding or a separately designed read-only historical mode, plus citation/source routing and workflow semantics. Neither exists in this candidate. Therefore **no new successful format or whitelist relaxation is enabled**. The detailed reviewable draft is DESIGN-DRAFT.md; proposed future1.5 remains unknown/rejected and is not a released format.

Keep report+recommendation export409 until those prerequisites are implemented and validated together. Existing1.4 and earlier restrictions, authenticated-identity absence, long locks/memory/DB-filesystem crash boundary and prior browser sandbox blocker remain. No merge/deployment; this branch is evidence/design, not a release candidate for added restoration capability.

## Main advanced during parallel integration review

Remote main advanced to4a6e729 (#75 exact AIS sample metadata and #76 environment fixture correction). The isolated combination in /workspace/mcis-aeb-main-integration preserves those main changes and applies exact aeb8cf1 production files. Running these same10 probes against that combination produced10 passed/5.66s (latest-main-combination.txt). This is additional coordinator evidence, not the earlier independent run or a newly implemented recommendation archive.
