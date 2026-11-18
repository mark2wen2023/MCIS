# PR104 exact-head combined regression — developer evidence

Tested source: 1651b98d221611d25aca6828676e43f892da9b6d.
Remote PR104 was verified at this head; main remained94d5e38. Tracked service,
tests, contracts and web had no differences. Only existing untracked .venv link
was present; installed dependencies were reused. No installation, policy change,
production data access, merge or deployment.

## Scope and deduplication
Collection of each former selection and their union was performed on the SAME
current head with --collect-only. Node IDs, not previous pass totals, determine
membership. Collections succeeded and contained no repeated node IDs internally.
- Former367pass/1skip report selection:368 selected node IDs.
- Archive selection:191 selected node IDs; real HFACS test explicitly deselected.
- Cross-selection intersection:0 node IDs.
- Union:559 selected node IDs; exact set equality with the union was asserted.

The command lists23 selectors:21 whole files and2 specific report-output nodes.
It collects560 total items, deselecting the one named real HFACS test. CLI skip
remains a collected item, not a pass. This is NOT the complete repository suite.
Shared fixtures/semantic coverage can overlap even when node IDs differ; no claim
of559 independent product capabilities or addition of independent reviewer counts.

## Exact execution
From service/ use command.txt. union-nodeids.txt is the precise selected set;
report-nodeids.txt/archive-nodeids.txt record membership and overlap-nodeids.txt
is empty. versions.json records the actual project .venv, not system Python.

Collection bookkeeping initially omitted the first report selector because of a
script slicing error (314 instead of368 report nodes). That incomplete attempt
was interrupted, not counted as a pass or product failure. Its local artifacts
are retained under /tmp/mcis-pr104-combined-1651/initial-interrupted. The corrected
runner asserts group counts and set equality before launching the final run.

## Boundaries
The named HFACS test was not executed, mocked or repaired; it remains unavailable.
The existing real CLI requirement may skip its existing test; no new skip/xfail
was introduced. Ordinary synthetic adapter fixtures do not demonstrate real
HFACS/LLM/AIS. PDF/DOCX output checks exercise real renderers but are not browser
or visual acceptance. Actual browser was not attempted; previous controlled-tool
and sandbox limitations have not been resolved or bypassed. No previously restricted
historical-report-integrity/ECFC operation or denied protection query was retried.
No fresh frontend/CI/full-environment or production identity validation this turn.
The earlier191 and367 results are superseded only for this explicit combined
selection, not evidence for any excluded tests or system release.

## Final observed result
**558 passed, 1 skipped, 1 deselected in145.24s**, pytest exit0. Zero failures.
Skip: tests/test_align_preview_w41.py::test_real_cli_csv_preview, existing
`real CLI SDK required` at line66. Deselection: the named real HFACS test.
Thus559 selected items executed as558passes plus1skip; the excluded560th item
is not counted as successful. This is one deduplicated run on1651b98, not sums
of earlier separate runs. No skipped/unexecuted dependency was substituted.

The recording branch contains only these acceptance materials. Remote PR104
remains1651b98 and main94d5e38; Draft/HOLD continues. No remote mutation, merge
or deployment performed. Independent combined rerun remains pending.
