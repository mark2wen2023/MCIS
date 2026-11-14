# Evidence intake refresh recovery — isolated QA

Parent/unchanged HEAD d1a442474aed81265227b24014516facc2bbbc6c. Local branch local/evidence-refresh-recovery. No backend/identity/archive changes, no push/merge/deployment. Only evidence panel/session recovery helper, targeted test and request/roadmap/freeze notes.

## Existing mechanism and actual gap

Current backend binds requestDigest to caseId, exact source bytes, metadata, filename and role/operator. Commit checks existing registration; receipt GET requires current case policy and validates original file, Register record and Evidence binding. Archived records return history-only, corrupt/incomplete states409, missing receipt404. None of these are a global guarantee that an earlier request did not commit. Role headers are still caller labels. Existing WRITE_LOCK is not a demonstrated cross-host idempotency mechanism.

Parent UI kept unknown state only in React memory; close/reset/reload discarded it and allowed new content submission. The improvement preserves only caseId/requestDigest/sourceSha256/byteLength in sessionStorage before dispatch. There is no file, metadata text, operator or credential persisted. Storage is explicitly not an authority or audit record.

## Behavior

Before POST, write a minimal marker and read it back. If blocked, malformed, overwritten or unavailable, do not dispatch. Existing marker prevents replacement. Closing/reopening or refreshing then opening this case panel reloads the marker and disables new registration; no POST is replayed. Explicit GET checks parseReceipt, case/digest/SHA/length, then compare-before-clear removes only the corresponding marker. A verified successful commit response follows the same clear rule. Exact known first-attempt pre-registration errors may clear this attempt's marker; unknown/history/conflict/network/bad response/404/403 remain locked. A changed marker cannot be cleared by a late result. UI lifecycle guards continue suppressing late results after navigation/identity changes, retaining the marker for later query.

No uncertain file is deleted. Removing a matched browser marker after verified receipt or known prewrite refusal is not deleting evidence. Existing Register/custody/audit data are unchanged. No new Access audit is added by receipt GET, consistent with existing service semantics.

## Actual validation

- TypeScript and targeted oxlint passed after stabilizing callback dependencies.
- Existing W4.2 model/API/render88 assertions passed.
- New pending-storage unit suite passed: minimal four-field persistence, no overwrite, scoped keys, compare-before-clear, corrupt/blocked storage and byte limits.
- Independent60 assertions passed: additional read/quota/silent-write-loss/remove failures, cross-case and previous-unknown guards. Independent reviewer inspected dispatch ordering, receipt matching and late-result protection; did NOT independently run browser.
- Actual Chromium+Vite+Uvicorn with temporary SQLite/synthetic data: original existing-registration409 remains locked; second case real commit200 followed by deliberately dropped response; reload restores marker only with empty disabled file/form; injected recovery404 retains marker; real policy revoke returns403 and retains marker; restoring policy then real GET recovers receipt and removes marker. Exactly one commit and one Register for that case, no resubmission. Policy changes create their normal audit events; Register chain remains one event.
- No full Python regression rerun this turn: backend is unchanged. Parent84passed1.NETskip is historical evidence, not this run. Full-suite baseline issues/.NET absence unresolved.

## Browser QA evidence

Browser plugin unavailable; existing regular Playwright/system Python and /usr/bin/chromium, no dependencies installed. URL127.0.0.1:15942/#/evidence; API127.0.0.1:18942; desktop1440x1000. Page title/meaningful evidence workbench verified, no Vite error overlay or pageerror. Console records expected409/403, injected network failure and injected404 plus one pre-existing unattributed404; not a console-clean claim. after.json includes observations; refresh-404.png actually captures the later real403 still-locked state; unknown.png shows pre-refresh uncertainty. Screenshots are supporting evidence, DOM/request counts establish no resend. Mobile/cross-browser not tested.

## Limits / conservative failure modes

SessionStorage covers same-tab same-origin navigation/reload, not other tabs/devices, tab closure or user-cleared storage. Opening a duplicate tab may copy session markers, not establish a shared lock. A browser script/user can edit/remove storage; it is not trusted authorization. Existing default role headers, shared browser privacy and server multi-worker races are unchanged. Hashes/case IDs remain potentially sensitive operational metadata even though no raw content is stored.

Crash after marker write but before network dispatch leaves a conservative pending marker; recovery404 does not clear it automatically, so manual support may be needed. There is deliberately no discard/force retry UI. Browser crash/session restoration durability is not guaranteed. Case-ID reuse, restored databases and missing trusted incarnation/identity are not solved; the marker follows existing backend case+request digest namespace rather than proving the same physical transaction across store epochs. Do not call this server durable idempotency or true SSO/revocation protection.

Raw request data is lost on reload by design. Only a currently authorized, structurally validated matching receipt can produce the normal verified-receipt UI; local marker alone never reports success. Preserve server records for manual investigation where recovery remains denied/unknown.

Reproduction: run pending test via esbuild/node, bash web/tests/run-evidence-intake-w42.sh, tsc/oxlint. browser.py uses an absolute isolated ROOT and fresh synthetic temp data; adjust ROOT when reviewing elsewhere. independent/ contains separately produced tests/report. No production endpoint or model call used.

## Remote-review packaging update

Independent push candidate uses codex/evidence-refresh-recovery-review with unchanged direct parentd1a4424. REVIEW.md/environment.json record actual browser version/start commands and dependency chain. browser.py now uses repo-relative root and MCIS_QA_OUT (default fresh temp output); independent test imports are portable. Final-parent source checks and real Chromium flow rerun before push; images/after.json updated from that run. Earlier no-push wording describes initial local study, not the subsequently authorized review publication.
