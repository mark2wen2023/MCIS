# Public two-role Pi research flow v1

Research-only, not a professional human expert panel or a production case workflow.
Two separate Pi1.5.2 sessions review exactly the pinned public-packet.json, derived
without reference labels/rationales from the YANGZE22 public report oil-loss section
(PDF28/printed26). The packet/source/PDF hashes are declarations inherited from the
recorded source; this slice does not fetch or independently authenticate the PDF.

Roles source_attribution and uncertainty_boundary have code-owned fixed prompts,
independent provider histories and no access to each other's opinions. Tools only
read_packet and validate_review; no filesystem/shell/URL/production tools. For every
item, each role returns label, exact source quote, rationale and explicit uncertainty.
All items exactly once; no facts or consensus activated even when labels match.
Source text, qualifiers and source locators stay visible alongside both opinions.

Limits: at most4 model attempts/8 tools/120seconds each; at most8 attempts/16 tools/
240seconds total, sequential sessions. No retries, model substitution or fixture
fallback. Canonical host history/callIds and validated completion references prevent
model/child-supplied state from replacing accepted proposals. Timeout/cancellation/
partial failures stop later work and retain incomplete states; unknown provider
outcomes cannot be displayed as completed or automatically rerun.

Fixture means actual Pi loop with scripted provider responses, zero provider network
requests and no credential access. It must remain clearly labeled everywhere. Real
mode uses only the fixed official DeepSeek HTTPS endpoint and approved model; raw
credentials reach Python host through bounded non-echoed stdin, never Node, argv,
artifacts or logs. CLI disclosure binds packet, roles/prompts/version and budgets;
explicit digest approval is a scope acknowledgment, not verified human identity.

Artifacts are explicit local exports to a newly created0700 directory:0600 receipt
JSONL, result JSON and static comparison HTML, plus a final completion.json binding all three by SHA256. The result artifactPolicy always requires this final marker; --verify-dir checks hashes, receipt terminal and run binding. A complete export can contain an unsuccessful run, never promote its status. Receipt is metadata-only, hash chained
and flushed before model attempts; it is local tamper evidence, not a signature or
provider/model identity authentication. Errors are generic. Existing paths must never
be overwritten. Partial receipt/result may remain after failure; absent or invalid completion.json means incomplete export even when an inner run status finished.
HTML has no scripts/active links/network resources and escapes all source/model text.

Native-browser behavior and real-model quality require separate actual acceptance.
Offline tests cannot establish those. No production route, authenticated identity,
case database, evidence-file semantics, timeline or hypothesis archive are modified.
