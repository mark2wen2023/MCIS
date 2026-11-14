# Independent recommendation cause-label review

Verdict: PASS for the bounded input-validation change, not a typed cause resolver or archive closure. Read AGENTS.md/handoff, frozen contract, product diff, input models, create/PATCH flow and all15 tests.

Fresh independent commands:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_recommendation_cause_links.py
sha256sum -c logs/recommendation-cause-links-impl-hashes-frozen.txt
```

**15 passed in4.65s**, independent-tests.txt; **3/3 frozen hashes match**, independent-hashes.txt. These use actual local HTTP/TestClient routes and SQLite, synthetic content/role headers, no model calls. Coordinator's earlier12-case baseline inspected:8 failed/4 passed in3.93s. That baseline and the coordinator's wider89-pass run were not independently rerun here and are not added to this15-case result.

The helper rejects supplied None or a list with no string outside existing _core_blank semantics. Pydantic retains list/string shape and min_length checks. Create calls it after permission, ID/duplicate and due-date checks, before row/audit writes. PATCH calls it only when causeNodeIds is explicitly present, after permission and existing lifecycle/progress checks, before updating/storing the row. Thus well-shaped unauthorized requests keep403; non-Draft content changes keep409. Structural validation still precedes handler permission as usual; the contract appropriately limits its403 statement to well-shaped requests.

The helper does not trim/filter/deduplicate/mutate the supplied list. Mixed blank/nonblank labels, order, duplicate and spaced labels are retained exactly. An unrelated patch to a historical blank-only row does not revalidate or rewrite labels. Explicit null PATCH now fails422. Existing _core_blank semantics are deliberately narrower than all visually blank Unicode: e.g.U+200B or U+001C are not newly treated as whitespace; this is not a universal invisible-character filter.

Tests confirm create/PATCH blank-only422 with all mapped-table snapshot hashes unchanged; exact mixed values through create/PATCH/GET; permission-first403 for three restricted roles; null422 and non-Draft409; historical row compatibility; and report+recommendation export still409 ARCHIVE_RESTORE_UNSUPPORTED with unchanged DB hash. The archive format/schema/import paths and label resolver are unchanged. No filesystem snapshot/crash guarantee, SSO or genuine .NET execution is established by these tests.

A nonblank label may be unknown, cross-context or stale: this change does not validate existence, case/revision/digest, causal truth or provenance. Registration is not evidence authenticity. The contract explicitly retains this boundary and acknowledges tightened blank-only input compatibility for unknown external clients. Safe report+recommendation roundtrip remains blocked pending its separate versioned dependency/restore design; no allowlist was relaxed.

No new blocking defect found within the stated input-only scope. Reviewer changed only acceptance/disposition artifacts, no frozen implementation. No push, merge or deployment.
