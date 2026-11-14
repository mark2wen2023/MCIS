# EXPERTREVIEWPLAN: human questions in existing offline review export

Remote refs checked2026-11-14: main73fc800, PR81de4729d, PR84head56edd5c.
PR81 is ancestor of PR84 (3 subsequent commits). Candidate directly based56edd5c;
it does not claim either PR merged into main or release execution HOLD.

review_plan(snapshot) first validates the meeting via citation_view, then emits
three pending tasks for the fixed public packet. Task ID binds exact snapshot
SHA256 and item ID; each task retains packet/source bindings, locator, fixed report
citation, human-authored claim marker, and current-round opinion ticket IDs,
labels, reasons, uncertainties and selected quotations. Values are fresh copies.
This is a deterministic projection, not an authenticated task database.

Current round means last started round (0 if none). Previous-round opinions remain
in the existing HTML history but do not fill current missing roles. Questions are
triggered by absence, declared label differences, declared insufficient material,
and an always-present human review requirement. A label is a declaration, not a
semantic verdict. Matching labels can still hide disagreements in reasoning;
no automatic inference of agreement or sufficient evidence is made. Empty or
failed/unknown/stopped/timed-out meetings do not invent missing responses.

Existing citation_html.render adds a read-only question section, preserving source
cards, uncertainty, phase/mode and no-execution warnings. Each task stays
pending_human_review even when protocol rounds finish. No checkboxes, task closure,
expert impersonation, identity authentication, approvals, case changes, persistence,
model prompts or automatic calls. All dynamic HTML remains escaped. Static HTML
can be edited and is not a signed source of truth; regenerate from original input.
Task IDs change when snapshot bytes change; do not restore annotations across
snapshots without a separate explicit binding/migration protocol (not implemented).

This is workflow preparation: humans must decide what additional materials and
reviews are appropriate. Generated questions neither certify that the public URL
is authentic nor determine claim truth. All examples use synthetic opinions on
the existing frozen public packet; no answer key or private cases are added.

Validation command: PYTHONPATH=. with supported service venv pytest
--import-mode=importlib on research/expert_meeting and tests_acceptance folders
EXPERTRECEIPT, EXPERTDEADLINE, EXPERTCOORDINATION, EXPERTCOORDINTEGRATED,
EXPERTCITATIONHTML.154 tests pass including5 new workflow cases. These are offline
protocol/HTML parser checks, not actual browser, human-expert or DeepSeek validation.
Real model calls0/HOLD; no deployment or environment configuration changes.
