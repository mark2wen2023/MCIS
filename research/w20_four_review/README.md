# Follow-up: row-bound manual review questions
Base 28594e2e37484824ddce4aff9711df45845edb60. No new card, input schema,
FourChair protocol, model, ledger, queue, permission or product route.
Existing project(receipt, host) now appends reviewQuestions and an explicit
fixed_guidance_not_seat_or_human_answer origin marker to each accepted row.
Questions are selected from the existing declared label, not inferred semantics.
Conflicted rows ask for both statements and their sources plus scope/time differences;
insufficient rows ask which basis is missing and which unknowns must remain;
supported rows still ask whether an observation is being overextended to causation.
Questions do not request tools, authorize new source reads, record answers or resolve votes.
Original quotes, rationale, uncertainty, source and draft bindings are retained unchanged.
Same item shared across seats still does NOT mean independent supporting evidence.

Actual Linux: existing check.py command below exit 0, 26 checks (22 existing + 4 new).
12 same-case rows retain conflicting and insufficient opinions simultaneously.
New checks cover per-row prompt attribution, coexistence, original/source preservation
and isolated output copies. Existing 15 rejection cases remain.
Existing FourChair executes in simulation; packet loader, ledger and OS file handles
remain explicit test doubles. Source locator and fixed byte validation actually run.
No human answer, professional judgment, live meeting, model or real ledger is claimed.

## Existing projection and replay boundaries
# Four-seat pending review projection — research only

Parent: c94de84c9a4fa2b694672753605a3dc37d240479.
Only this new research directory changes. No FourChair/PR91 schema, production
route, model, queue, permission, ledger or report writer is changed.

project(receipt, host) is a pure, copy-producing function for exactly four accepted,
source-bound first-round opinions from the existing simulated FourChair. It retains
role, round, attempt/context identity, original draft binding/generation, each quote,
rationale, uncertainty and selected source bytes/locator. The summary is checked
against per-seat labels; agreement is not consensus and disagreement is not resolved.

The separate host argument is an in-process TEST-host capture of actual issued
tickets, selected registry, same draft binding/generation and meeting ID. It is NOT
accepted from a submitting seat, NOT an authenticated host interface and NOT a
credential. The fixture host first runs the existing pinned source locator and
checks each source's case ID. The projector itself does not read originals.

## Explicit unavailable-evidence blocker

No trusted product host receipt for case/round/version-bound evidence unavailability
exists here. The projector therefore ALWAYS emits:
- status=pending_human_review
- hostEvidenceAvailability=BLOCKED_NO_INTERFACE
- stopRequested=false
- identityAuthenticated/modelExecutionVerified/consensusComputed/factActivated=false

No input can enable an evidence-unavailability signal: extra receipt/host fields
are rejected. Unknown IDs remain rejected by both projector and existing chair.
Rejected unknown selection is NOT reinterpreted as unavailable evidence.
A real unavailable signal needs a separately defined trusted-host integration;
this candidate does not introduce it. It also rejects partial/later-round receipt
shapes instead of silently projecting them into this narrow first-round view.

## Offline replay

Python standard library only. From this candidate checkout:
```sh
python3 -I -B research/w20_four_review/check.py \
  --ecfc-package /path/to/fixed-6996/research/ecfc_pending_handoff \
  --locator /path/to/fixed-d1c1/research/w19_case_ranking/source_traceability/check.py
sha256sum -c research/w20_four_review/SHA256SUMS
```
Add --view to print the actual synthetic pending projection to stdout; no file,
report or meeting is saved. Default output is a deterministic test summary.

Dependencies (explicit existing Git exports; no network/download in execution):
- c94de84c9a4fa2b694672753605a3dc37d240479: FourChair, ledger module, packet validator;
  their blobs are checked before construction. They are inherited, not copied here.
- 6996fa05cd8a0df6af4312f308e7ad69e023846c: ecfc_pending_handoff/FROZEN.sha256
  (SHA256 e91d31f34678ee2af880fb9931813677b93706332a03e96a0846943ef50235dd),
  plus every listed file. Only one same synthetic case, three fixed excerpts.
- d1c1d378f8ec21e3cf8a01fe446df81770395a9e: source_traceability/check.py,
  blob 44fc5d82279db5fa3a3c748161f3122708e85668.

Actual FourChair issue/submit_simulated/receipt, packet._validate and locator run.
Constructor packet loader, Ledger and file open/close use the existing synthetic
test seam's mocks. No default public report packet is read; no real ledger is written.
Protocol packetSha256 is retained as the original protocol identifier, not claimed
as the synthetic source digest; synthetic source identities are separately bound.

## Executed coverage

22 checks, exit 0: actual same-case four-seat projection (12 item opinions),
opposed labels/uncertainty and exact source/binding preservation, pending without
invented stop, no input mutation or additional mock-ledger settlement; wrong schema,
packet identity, duplicate seat, wrong case/generation/evidence digest/locator,
unknown source, wrong round/ticket, quote borrowed from another excerpt, fact upgrade,
invented unavailable receipt/host signal and missing opinion rejected; output copy
isolation and unchanged chair unknown-ID rejection.

The candidate is not snapshot replay/authentication, semantic support validation,
real expert deliberation or human approval. Only declared synthetic labels are
shown. Host input integrity is a caller boundary, not established by this function.
No UI/browser or production use is accepted. No merge/deployment.
