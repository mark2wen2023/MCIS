# Deferred request writers and restore hold: bounded source review

Inspected code parent: `5870138a98c6a8b12306273b6bfc1a83e0422425`, research/restore-normal-case-registration, 2026-11-18. This adds concrete threadpool paths to [the access inventory](archive-access-entry-inventory.md); it does not repeat the publication protocol or claim that protocol is installed. No task, subprocess, model, recovery, service or test was executed. No production behavior changed.

## What “can write during hold” means here

The product has no unified research hold gate. The paths below do not consult the research readiness classification. Consequently, marking a case held only in that research protocol would not, by itself, fence these writers. This is a static integration gap, **not an observed write during a real recovery**, permission bypass, or proof that any runtime task is currently active.

`run_in_threadpool` delegates synchronous request work; it is not evidence of an autonomous background scheduler. Concrete OS thread IDs, disconnect/cancellation behavior and descendant process ownership were not measured. `db.py:37` defines a process-local `threading.RLock`; `Database.session` (67-75) commits on context exit. Neither provides cross-process publication ownership.

## Additional concrete writers

Paths are relative to `service/mcis_service`; line numbers refer to the inspected parent.

| Entry and execution | Persistence targets and checks | Missing restore integration |
| --- | --- | --- |
| `manual_interviews/router.py:create` 170-172 / `append` 203-205 delegate to `create_sync` / `append_sync` in a request threadpool | Each opens a DB session (175,208), checks content access and case existence; append checks expected document digest and source state. `save` 157-167 writes `InterviewRow`, case audit and `InterviewRequestReceiptRow` together. No original-file writes in these helpers. | No readiness admission/final-write check. A pre-request gate alone would not cover queued work. Receipt replay and audit-producing writes require the same case-state decision without replacing existing permissions. |
| `tracks_import/router.py:commit_input` 216-223 delegates to `commit_sync` 225-292 | Process-local lock and transaction; reauthorizes, checks preview/receipt/vessel and existing points. Writes two `EvidenceRow` records, `TrackPointRow`, custody, case audit, `LocalReceipt`; exclusive file writes target `raw/track-imports/<digest>/source.csv` and `report.json` (`rels` 80-85). Files are written before session exit. Exception path attempts removal of files recorded as created by this attempt. | No publication ownership/readiness binding. A future hold gate must cover file and DB work through completion, not just preview. Existing cleanup is code behavior, not a verified crash-safe compensation protocol; this review did not exercise it or infer the outcome of an uncertain commit. |
| `hfacs_drafts/router.py:save_sync` 210-241, called by threadpool at 280 | First session snapshots sources/context and checks replay; outside that session `run_core(validate)` invokes synchronous CLI subprocess (`run_core` 145 onward, timeout30s). Final lock/session rechecks context, sources, expected worksheet digest and document access; writes `HfacsWorksheetRow`, revision/audit via `append_revision`, and `HfacsRequestRow`. | Existing context checks are not restore-state fencing. Both pre-subprocess admission and final write need defined hold semantics; cannot infer worker/descendant termination or ownership from timeout. No HFACS execution was performed. |

### Existing HFACS retry wording versus proposed recovery policy

Static follow-up at `769396b374eb00e7625a326c6499f4759cac1d13`: `hfacs_drafts/router.py:save` (282) catches a generic exception and returns HTTP 503 / `HFACS_SAVE_FAILED` with “保存失败，未确认完成；可用原requestId重试”. Thus the current endpoint explicitly permits retry with the original requestId; `save_sync` checks the saved request receipt before and after core validation. This is existing behavior, not evidence that every ambiguous failure is resolved or that a client automatically retries. The proposed unknown-outcome inspection/no-automatic-retry rule below is a **future recovery-protocol constraint**, not a description of this endpoint's current error contract. Aligning those contracts remains unimplemented and was not tested.

## Already-covered writers, now identified as threadpool boundaries

- `report_output/router.py:create` 264-273 delegates initial gate and `generate` separately. `generate` 218-257 snapshots, renders outside the session/lock, then rechecks report/policy and appends report operation/audits before returning an assembled response. The output ZIP is assembled for the response here; this is not evidence of a persisted ZIP artifact. The previous inventory already identified its final recheck gap.
- `package_intake/router.py:commit` 172-175 delegates `commit_sync`; its staged files, receipt, publication and commit windows are covered by [the publication plan](archive-publication-restart-plan.md). Threadpool execution does not solve those windows.
- Agent extraction and its success/failure audit paths are already covered by the access inventory. This report does not rerun or independently verify their execution.

## Do not misclassify these paths

- `human_factors_preview/router.py` 269-278, `bowtie_preview/router.py` 227-235 and `nomoto_preview/router.py` 221-230 run a core in a threadpool between context snapshots and return `persisted:false`. The inspected endpoint bodies do not persist case records. `timeline/align_preview.py:preview_alignment` likewise returns a nonpersistent preview. Pre-computation/content release may require readiness policy, but they must not be reported as proven case DB writers merely because they cross sessions. Transitive core filesystem effects were not exhaustively audited or executed.
- `knowledge_archive/router.py:save` 60-70 separately delegates `prepare_save` and `commit`. `commit` 50-59 writes global `Archive.raw_bytes` and import metadata under lock/BEGIN IMMEDIATE. It does not hydrate a live case. A held case must not automatically hide all global knowledge archives: archive retention authority and any future live-case extraction need separate classification. `prepare_save` (44-48) invokes `gate(ctx)` (also invoked while reading the body); `commit` itself does **not** repeat that gate. It checks existing bytes against the supplied bytes and saved operator/role against the request context, then validates the stored record. These consistency checks must not be described as a fresh authorization check. This bounded source observation alone does not establish a permission bypass; no alternate caller, concurrent revocation, or runtime exploit was tested. Existing role checks remain unchanged.

## Minimal next step and unverified scope

Before implementing gating, define a case-scoped admission/ownership token that remains valid through final file publication and DB commit, with an explicit handoff to ordinary writers. Enumerate final writes, replay returns, failure audits and read-side audits, including paths queued before hold. A DB state check is necessary but not a substitute for cross-process ownership; it cannot recall an already-sent model request. Unknown outcomes require inspection, not automatic retry/deletion or a success response.

A future ordinary synthetic verification can first validate token/state transition contracts and legitimate old/new cases without invoking cores or file compensation. Actual cancellation, process ownership, file publication durability and unknown SQLite commit outcomes require separately approved, specifically bounded validation; none is established here. Do not reactivate paused tests or write-refusal probes to fill these gaps.

This list is not exhaustive: other synchronous routes and their transitive helpers, external operators, multiple service processes, and the independent image/audio candidate executors remain outside this pass. Those candidate trees must be inspected at their own fixed SHAs. Product restore remains unchanged; no experimental format is enabled, no whitelist expanded, and no normal case is newly hidden.
