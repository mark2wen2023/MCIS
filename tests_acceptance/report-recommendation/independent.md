# Independent recommendation-closure research review

Reviewed `/workspace/mcis-report-recommendation` at `aeb8cf1dfb18b2fd723a6d98112e550b83054801`; git confirms f2eff95 ancestry. Read AGENTS/handoff, REPORT, DESIGN-DRAFT, frozen tests and related schema/API/validator/UI/C# source. No product changes relative to the research parent; no reviewer changes to tests, frozen draft, implementation or existing contract. No push, merge or deployment.

## Executed evidence

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q -s \
 tests_acceptance/report-recommendation/test_closure.py
sha256sum -c logs/report-recommendation-research-frozen.txt
```

**10 passed, one dependency deprecation warning, 3.51 seconds**, recorded in `independent-results.txt`. Both frozen files match (`independent-hash-check.txt`). These tests execute existing API handlers, SQLite and synthetic documents. The one audit failure is explicitly injected. They do not exercise a new archive profile, production identity, C# execution or a browser.

## Claims checked and necessary qualifications

* Arbitrary/missing-looking labels and duplicate blank strings are accepted and retained by the Python create API. The tested COLREG/HFACS/timeline case rows are absent. This establishes lack of enforced local typed resolution in those paths, **not** absence of an external human source, a false recommendation, cross-case disclosure or a guarantee that every possible cause source was enumerated. UI free labels/default COLREG-R19 and schema string storage support the report's stated model limitation. C# source filtering is corroborated by inspection, not runtime execution.
* Both Draft and Issued recommendations appear as registered report citations. “Registered” identifies membership of the recommendation register; it does not validate underlying causal truth, typed source, revision binding or historical approval. The archive citation validator explicitly rejects registered recommendation sources; actual mixed export409 and Investigator403 leave all captured user-table rows unchanged.
* Legacy recommendation-only package import restores its original active row. **Separate subsequent Lead API requests** perform Issued transition and response/Responded, with response audit present. Import itself does not automatically issue, respond, send external messages or publish anything. The report/draft correctly make this distinction.
* Same legacy bytes are rejected by new Intake commit with422 and unchanged DB snapshot/no case directory. Proposed1.5 preview also rejects. No new version is enabled by these passing tests. ReadOnly nondefault policy refusal and Deny403 remain intact.
* The injected safetyrec.create audit exception returns sanitized500 and rolls back captured rows. Snapshot helper captures all current non-sqlite_* SQL tables/rows, stronger than row-count-only checking, but does not compare SQLite internal metadata, physical file state, process-crash behavior or uncertain commits. The research correctly does not claim crash atomicity.

## Design assessment

The blocked draft does not guess a typed case/revision identity from causeNodeIds or equate recommendation registration with causal-source validation. It keeps original labels, requires an explicit source binding/resolver before active restoration, and distinguishes active Draft from a separately designed inert historical representation. That distinction is necessary because current RecommendationRow endpoints remain actionable; a document label alone would not disable transitions.

A Draft-only envelope is a proposed scope, not evidence of an implemented safe subset. Empty responses/history/zero progress do not eliminate required cause identity. Future active restoration needs validated reference closure and workflow/source semantics together; a read-only alternative needs separate authoritative storage/routing and mutation rejection. Neither can be achieved by simply relaxing ALLOWED_TABLES or accepting registered recommendation citations based solely on ID existence.

No independent evidence here certifies a future profile's completeness, all source kinds, full state graph, historical authority or destination authentication. Version allocation, resolver implementation and positive multi-generation restoration remain absent. Broader frontend integration/browser sandbox blockers and parent archive resource/identity limitations remain separate unresolved work.

## Disposition

**Accept this root-cause evidence and explicitly blocked design draft within scope.** No material overclaim found; summaries must retain the qualifications above. Keep report+recommendation export409 and future version rejection until a separately reviewed source/restoration contract is implemented and tested. Ten passed means current behavior/rollback probes passed, **not** successful report+recommendation restoration or release acceptance.
