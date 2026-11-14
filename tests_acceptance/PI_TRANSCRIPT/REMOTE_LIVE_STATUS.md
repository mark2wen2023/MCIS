# Real-provider status, bounded public excerpt

Source: Shanghai MSA YANGZE22/VEGA DREAM public accident report,
https://www.sh.msa.gov.cn/sgdc/104170.jhtml ; printed page1/PDF page3.
Excerpt SHA256 c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748.
Input is a public report excerpt, NOT witness testimony or a complete case.
Model selected: deepseek-v4-pro; official endpoint only. Credentials were
supplied through non-echoing stdin into process memory, never repository files.

## Observed outcomes
1. First live attempt: one model_request; PI_DEEPSEEK_OUTPUT_INVALID before any tool.
2. Bounded structural diagnostic attempt: same rejection. Diagnostic records only
   field names/types/lengths showed non-stream tool_calls carry an index field.
   No source/model text or credentials were captured by that diagnostic.
3. After independently verified strict index normalization: real Pi performed
   three model_request rounds and executed read_transcript_excerpt and
   validate_extraction_proposal through the authorized Python host. A subsequent
   model reply was received, but final delivery failed MCIS_FINAL_UNVALIDATED.
   This proves real tool-loop execution, NOT an accepted final proposal.
4. A further run added only safe error/status classification. Its execution
   session was lost before the final result could be collected. Recovery found
   no node/python process, and no terminal result artifact exists. **Outcome
   unknown**; do not count this run as passed or automatically repeat it.

No run is recorded as accepted PendingReview; no official fact, proposal record
or database write was made by these read-only tools. In-memory/temporary test
state is not production persistence. The result remains a draft engineering
checkpoint; no merge, deployment, full case analysis, UI or CI pass is claimed.

## Verification scope
Final combined Python local regression after compatibility change:148/148,
zero skipped,49.06s. Node34/34; independent remote63/63 confirms strict index,
canonical history and absolute deadline cancellation. These mocked tests are
separate from the live outcomes above. Final recovery review is recorded in
FINAL_REVIEW.md when completed.

## Remaining work
Diagnose whether the prior rejected final had no valid proposal or changed a
validated candidate (including JSON-only formatting differences). The runtime
now distinguishes these cases without accepting any formerly rejected output.
Do not weaken source quotes, JSON schemas, call IDs or approval checks to pass a
live test. Add recovery-safe non-secret result receipts before another explicit
live acceptance run; a lost process response cannot be inferred from code tests.
