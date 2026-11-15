# Independent report cause-label provenance review

Verdict: scoped PASS for generation-time disclosure of unresolved registered labels, not causal evidence or archive closure. Read AGENTS.md/handoff, frozen contract, source diff, sentence/citation constructors and专项 tests. Parent HEAD4585016. Product diff is limited to reports/sources.py's additional generated sentence.

Fresh independent execution:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_report_cause_provenance.py service/tests/test_reports_w16_sources.py
sha256sum -c logs/report-cause-provenance-impl-hashes-frozen.txt
```

**17 passed in5.38s** (5 new +12 related sources tests), independent-tests.txt;3/3 frozen hashes matched, independent-hashes.txt. Real local TestClient/SQLite with synthetic recommendation labels; no model or external-source call. These tests are not browser or external-source authenticity verification.

Code adds one separate recommendation-causes-{id} sentence using json.dumps(original labels,ensure_ascii=False), preserving order/duplicates/spaces and escaped controls. Both languages explicitly disclaim verified evidence links/causality. _sentence initializes Draft with null reviewer/time and empty reviews; sourceStatus is RegisteredLabelsUnresolved. Its sole citation is the current recommendation register with needsReview=true, not guessed evidence/rule links. 'registered' describes the record only. The source URL is current navigation, not revision/digest-pinned provenance. Later existing human-review controls can change workflow state; generation does not confirm it.

Tests verify original JSON label text including evidence-shaped and markup-like strings, single recommendation citation, Draft/unreviewed state, old report remains unchanged after register edit while new report reflects edit, true DOCX export preserves text and caveat, missing historical labels remain null/missing rather than inferred, Investigator403 and report+recommendation archive409 with unchanged database snapshot. The new paragraph is a saved generation snapshot, not live synchronization or an evidence resolver. No stored report migration, permission grant, archive allowlist expansion or identity upgrade appears in the diff.

Coordinator after.txt inspected:95 passed/2 failed in17.73s. Both failures are existing public-report font tests failing on their Investigator permissions; coordinator main-control.txt retains the same two failures on unchanged main in0.74s. These are inspected evidence, not independent reruns here; my17-case result does not resolve them. Do not present the wider run as fully green or count overlapping runs additively.

No new blocker found within this bounded disclosure scope. Missing/null labels do not mean facts established, and nonempty labels can remain unresolved or false. Actual browser/layout, PDF font workflow failures, authenticated identity and safe report+recommendation archive restoration remain outside this pass. Reviewer changed only acceptance/disposition evidence, no frozen implementation, push, merge or deployment.
