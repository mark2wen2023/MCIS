# EXPERTCITATION: strict attribution boundary, not semantic proof

Parent PR81 head de4729d7ac77e5ebb2890d4f949e5ebf46ffa713, based on main
73fc800. PR81 remains the dependency; this candidate does not claim its merge.
The previously reviewed meeting/packet/receipt implementation is unchanged.

`citation_view(snapshot_bytes)` first replays the existing bounded meeting
snapshot, then projects only accepted reviews. Empty/partial/stopped meetings
remain empty/partial/stopped, with no invented opinion. Input is fixed public
packet research only, not arbitrary case evidence. No keys/network/execution.

Output contract (schemaVersion1): snapshotSha256 binds exact input bytes;
packetSha256 binds the frozen source packet; each row retains round, role,
ticketId, itemId, declared response source, label, rationale and uncertainty.
Claim is explicitly human-authored test material including counterexamples.
Fixed report citation and reviewer-selected quotation are separate fields.
Source text, digest and original declared PDF locator are retained. All three
items refer to ONE report page, not three independent sources or corroborations.

Quotation locations use exact Unicode codepoint offsets (not UTF-8 bytes or JS
UTF-16 offsets). No normalization, paraphrase matching, ellipsis expansion or
case folding. All overlapping occurrences are counted; at most32 spans are
returned, with truncation explicit. Multiple occurrences mean ambiguous locations;
no first occurrence is silently chosen as the unique citation. A substring may
be wholly irrelevant to the claim: exact match never proves semantic support.
For example the single character 约 matches multiple places and can be paired
with a declared supported label; output still marks semanticSupportVerified=false.

Every row and whole projection keep semanticSupportVerified/factActivated=false.
The output keeps authenticityVerified/modelExecutionVerified/consensusComputed
false even for remote-declared complete responses. These are declarations, not
independent evidence of a call. Publicness and source locator are not authenticated;
URLs are inert metadata, never an SSRF allowlist. Existing hashes/replay prove
local consistency only. No reviewer identity or claim truth is certified.

This is a read-only Python display-data adapter, not a browser UI or provider
prompt. Future UI must render all text as text (never trusted HTML), show claim
and quotation labels separately, and convert codepoint offsets if using JS.
Do not send this projection or any per-item reference answer to a model. There
are no reference answers in this output or the packet; source labels describe
provenance categories, not correctness. Existing meeting inputs/prompts unchanged.

Reproduce: `PYTHONPATH=. service/.venv/bin/python -m pytest -q research/expert_meeting tests_acceptance/EXPERTRECEIPT`.
Tests use synthetic opinions; they do not demonstrate model judgement. No real
DeepSeek request, browser acceptance, production identity, or case integration.
True semantic entailment remains an unverified human/model review question.
