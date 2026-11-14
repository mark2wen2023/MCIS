# Full-suite parent/candidate comparison

Independent parent worktree: `/workspace/mcis-idem-parent-baseline`, detached at `fe3fb05515898cbde380af9bf819afcb344a28eb`. Created from git without product modifications; only linked `service/.venv` to the same `/workspace/mcis/service/.venv` used by candidate. Environment/worktree facts recorded in `environment.json`. No remote change or test filtering. One transient exec transport disconnect occurred; read-only checks recovered and confirmed the original run continued. Tests were not restarted.

## Actual full results

| Run | Command scope | Result |
|---|---|---|
| Independent parent | `PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests` | **180 failed, 1563 passed, 11 skipped, 104 errors; 522.01 s** |
| Coordinator candidate | Same service suite plus `tests_acceptance/server-idempotency-independent/test_boundaries.py`; candidate also has 17 research cases | **180 failed, 1585 passed, 11 skipped, 104 errors; 524.45 s** |

Parent output: `parent-full-tests.txt`; exit code **1**, recorded in `exit-code.txt`. Candidate output read from `tests_acceptance/server-idempotency/full-review-tests.txt`. Candidate run was executed by coordinator; parent was executed by this reviewer. These are actual complete runs, not inferred from the focused 22-case success.

`compare.py` mechanically extracts final FAILED/ERROR node IDs and compares sets/types; `comparison.json` records all nodes and summaries:

* **284 common failed/error nodes** (180 failures + 104 errors).
* **0 candidate-only failures/errors**, **0 parent-only failures/errors**.
* **0 changed FAILED-vs-ERROR classifications** for shared nodes.
* Candidate has **22 additional passes**, matching 17 research cases plus five independent probes.

This supports **no newly observed failing/error node in this candidate full run relative to the tested parent**. It does not imply the suite passes, establish causality for every inherited error, prove absence of behavioral regressions outside assertions, or repair the baseline.

## Inherited and environmental distinctions

The earlier “five baseline failures” belonged to a smaller selected suite and is **not applicable here**. The full scope contains many additional inherited failures/errors.

Failure concentrations include reports_w16_direct (47), reports_w16 (41), consultation_input_w73 (15), environment_w92 (12), interview_compare_w5 (11), reports_w161_snapshot (11), bowtie_preview (9), human_factors_preview (6). All 104 ERROR nodes are in hfacs_drafts (50), agents_w20 (31), hfacs_package_extension (23). Their setup assertion failures include service responses denying full interview content (403); fixture/setup errors must not be counted as passes or omitted from the result.

There is explicit environment evidence too: parent log includes FileNotFoundError for missing `tools/mcis-core/out/mcis-core.dll`. Other CLI/build-dependent failures may share environmental causes, but this review has not diagnosed all 180 failures. Logs also include response-shape TypeErrors and policy-related assertions; do not relabel every inherited failure as merely missing .NET. Both runs show 11 skips; this invocation does not print individual skip reasons, so this report does not claim all 11 are .NET skips.

## Disposition

Full regression is **not green**. Candidate adds no failed/error node under this same-environment comparison and its 22 added research/independent cases pass. Baseline failures, fixture errors and environment limitations remain open and must be carried into any review/publication note. This comparison neither broadens the research prototype into production identity/file registration nor authorizes merge/deployment. Parent product code remains unchanged.
