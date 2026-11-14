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

## Recovery receipt addition (offline, not a new live pass)
The explicit local launcher now creates a unique restricted-permission JSONL
receipt under its OS temporary directory before reading credentials. It prints
the receipt location and syncs each record before dispatching a model request.
Only fixed lifecycle phases, bounded counters, a random run ID, timestamp and
allowlisted rejection category are recorded. No key, model content, source text,
request arguments, arbitrary exception or host output is recorded. Completed
and rejected runs are terminal; a started request without a terminal record is
**unknown**, not failed, and does not authorize retry. This supports recovery
from lost process output, not survival of workspace destruction/power loss or
a cryptographically authenticated audit trail. No new provider invocation was
made during this implementation.

## Independent new bounded live acceptance with recovery receipt
Run 202d715c-5123-44f0-8445-67cade98b96a (2026-11-14 UTC) used the same
explicitly authorized fixed public report and official DeepSeek model through
actual Pi. Three model rounds and two tools completed. `read_transcript_excerpt`
returned, and `validate_extraction_proposal` returned **PendingReview**. Final
model output was rejected with **MCIS_FINAL_UNVALIDATED_FORMATTING**: formatting
outside JSON strings differed from the exact validated candidate. Thus source
validation succeeded for a candidate but the full end-to-end final delivery
still did NOT pass. No approval or business-record save. The strict final-text
rule was not relaxed. Sanitized durable phase/counter/terminal receipt is at
receipts/public-probe-202d715c.jsonl; candidate text and key are not captured.
Historical fourth-run state remains unknown and is not rewritten by this run.
A separate launcher attempt had closed stdin and ended MCIS_KEY_TIMEOUT before
host startup or any external request; it was not a provider retry.

## Latest complete bounded live acceptance
After separately reviewed strict presentation-equivalence handling, new run
be93095b-c8be-47e1-9579-f2a3788a23aa completed **accepted_pending_review**:
actual Pi1.5.2 + official DeepSeek configured model deepseek-v4-pro,4 model
rounds,3 tools (read_transcript_excerpt and2 validate_extraction_proposal),
7 proposals and7 citations, **saved=false**. The host retained strict original
candidate bytes, exact citation validation, source/authorization rechecks and
no fact approval. Recovery receipt receipts/public-probe-be93095b.jsonl has a
terminal accepted_pending_review record. This is acceptance of one fixed public
report excerpt, not full-case accuracy, witness testimony, production identity,
UI/E2E or CI. It does not resolve the historical unknown fourth run.
The earlier failed/unknown records remain history, not the latest outcome.

Qualification: be93095b success passed Python's unchanged terminal == validated
byte check. It does not validate acceptance of presentation differences across
the complete Python path. Node structural-equivalence checks are narrower-scope
unit/fixture coverage. The server deliberately remains stricter.
