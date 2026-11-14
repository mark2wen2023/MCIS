# Report + timeline archive — independent disposition

Frozen candidate at parent f2eff95: **scoped API acceptance passes**. Independent execution: **33 passed /17.56s** (26 supplied +7 independent), all nine frozen hashes verified. See [full independent report](../tests_acceptance/report-timeline-independent/REPORT.md), logs and added tests.

Version1.4 requires working-v1 plus exact timeline extension/mirror. Row/source/case validation, preserved timestamps/doc/flags, legacy entry rejection, unknown-table rejection, injected rollback and actual SQLite revoke ordering passed the selected tests. Submillisecond values follow existing API formatting without modifying stored timeSec.

Limits remain: frontend rejects1.4, so no workbench completion claim; track-history+timeline and other unsupported tables are still refused. Historical flags are unverified originals, not approvals. Full regression has coordinator-reported HFACS failures reproduced on parent; not fixed or independently rerun in this acceptance. Long-lock/memory/identity/FS–DB crash-atomicity boundaries remain. No product edits, push, merge or deployment by reviewer.

Final coordinator combined frozen selection: **171 passed /2 failed /60.11s**, recorded in final-regression.txt; both named HFACS nodes retain parent reproduction evidence. This is separate from the independent33-pass run, not full-suite success.
