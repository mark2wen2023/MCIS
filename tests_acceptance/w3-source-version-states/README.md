# PR56 W3 protected source-state UI slice

Base: 254167e3e957784fd9d2d136a275731f33314d9b. Combined patch includes v2 backend plus existing model/IssueWorkspace integration. No new host protocol, endpoint, permission, storage, approval or archival. Not default mounted. No push/CI.

## Read-only trial proposal
Each protected history reference may carry sourceVersionStates with only evidenceId/status. Server compares immutable snapshots with a request-local current-source result, at most once per case/source per read. Final authorization remains. Python host explicitly allowlists those two fields; no historical SHA/incarnation delivery is added. Existing authorized raw journal snapshots unchanged.

Existing hostPort calls model.parse, which now retains and validates status: exact array coverage of event source IDs, no duplicates/foreign IDs/unknown values/extra keys. Missing field is old-response compatibility, displayed as 未核对, never current. Invalid provided fields reject the entire read. Read-time state is omitted from append-only equality comparisons; notes, sequence and references remain protected. Existing save response does not assert fresh state.

Current = 当前（本次读取核对）, needs_review = 待复核, unavailable = 不可用. All say 不代表事实已确认. Starting reads clears old state; history refresh clears history while pending. Source-read failure hides history. Existing layout-effect epoch invalidation handles case/context/prop card change; card selection clears state. Late replies cannot repopulate a different epoch. No automatic background revocation notification: revocation is observed on a protected operation or host context change.

## Local commands (existing Linux dependencies, no installs)
    node w3-pr56-version-ui-20261124/run-version-ui.cjs
    mcis-work/service/.venv/bin/python -I -B w3-pr56-version-ui-20261124/check-version-states.py
    node w3-pr56-version-ui-20261124/run-ui.cjs

Results: 86 React/TS/stdio/ASGI/temporary SQLite assertions, exit 0; 14 backend groups, exit 0; original full UI integration PASS, exit 0. React uses HappyDOM, NOT a real browser. Legacy/malformed/delayed envelopes are labelled transport controls around actual responses. Fault/reopen/revoke/unavailable are fixed test-host controls only, never product endpoints. Source mutation is temporary-file fault injection, not a legitimate replacement-registration API. Unavailable control removes one temporary incarnation, not authority. Temp data cleans up on EOF.

## Apply and independently replay
In an isolated checkout of the fixed base:
    git apply --check /path/to/combined.patch
    git apply /path/to/combined.patch
    /existing/python -I -B tests_acceptance/w3-source-version-states/check.py "$PWD/service"
    MCIS_SOURCE_ROOT="$PWD" MCIS_NODE_MODULES=/existing/node_modules MCIS_HOST_PYTHON=/existing/python MCIS_HAPPY_DOM_PATH=file:///existing/happy-dom/lib/index.js node tests_acceptance/w3-source-version-states/run-version-ui.cjs

Runner uses existing esbuild/React/ReactDOM and HappyDOM. No download or listener. Original UI test can be bundled with the same existing automatic JSX configuration, replacing entryPoint with web/tests/issue-host-integration.tsx and omitting MCIS_VERSION_HOST override. Test-only host imports only specified exported service path. It cannot accept caller-selected real cases/files.

## Human-review replay checklist (component simulation, not production workflow)
Run the integration command and inspect web/tests/issue-version-integration.tsx in action order:
1. Read card A: EV-001 当前, note 假设甲待核; no approval inferred.
2. Fixed test fault changes source A bytes. Re-read A: 待复核 with original note. Switch B: previous content absent until explicit read; EV-002 remains 当前.
3. Close/reopen SQLite connection and host; re-read A still 待复核.
4. Old parent response without states: 未核对. Invalid state response: history/status hidden. Valid subsequent read recovers.
5. Hold a read reply, switch to B, release old reply: old A status stays absent. Explicit B read restores only B.
6. Switch FOREIGN: no history. Return authorized case and read; remove A local identity through test control: 不可用; B unchanged.
7. Revoke actual synthetic membership; read fails, note and state hidden. No persistence or approval controls added. Existing trial append controls are unchanged and follow original read/write authorization.

Do not use testControl commands as a product contract. Browser focus/paint, production mounting/login, legitimate evidence replacement and push-style revocation remain unverified/out of scope.

## P2 draft recovery correction
After a failed current-source read on an existing card, keep the unsent text read-only, clear history/source selection, and offer two non-writing controls: 重读历史以恢复草稿 and 放弃未提交文字. Authorized history re-read unlocks editing without restoring source selections; failed/unauthorized retry keeps text but no history. Discard clears only text, leaves readBlocked until authorized re-read. Normal save/approval contracts unchanged. Test uses real local membership revoke/restore and asserts history receipts are unchanged, then checks editing resumes and explicit discard works.
Manual reproduction: read B, type unsent text, revoke fixture membership, click 读取当前来源; verify locked text and recovery controls. Retry while revoked: no history. Restore fixture membership and retry: editing resumes, no preselected sources. Repeat failure and choose 放弃未提交文字: empty text, no writes, ordinary authorized re-read required. There is no production role switch UI or new authentication route.

## P2 fixed draft judgment target
Verification/discussion draft target is fixed in local component state when that draft kind/text is established, and save uses that fixed seq rather than recalculating latest(history). Authorized recovery compares it with the newly read latest judgment. If changed, preserve original text/kind, show original/current judgment numbers, keep editing/submission locked, disable recovery retry and allow only explicit discard followed by re-read. No automatic rebind. Ordinary judgment drafts have no againstJudgment target and retain the previous recovery behavior.

The fixed temporary test host provisions a SECOND synthetic subject/session through original identity and grant functions. That actor independently reads/appends a judgment through IssueHostClient/ASGI/SQLite while the first actor is revoked. Three mounted cases cover supports, refutes and discussion (the latter receives its required prior verification through that same second authorized actor). After recovery, assertions check old/new seq, unchanged draft text/kind, zero first-actor save messages and no corresponding stored event; discard/re-read returns editing. A same-target verification recovery remains editable with unchanged history. These are actual local synthetic identities, not production identity certification. Final original integration also passes its normal judgment/verification/discussion saves.

Manual extension: select verification of judgment #1, select supports or refutes, type an unsent note. Fail current-source read via temporary membership revoke; have second fixed test actor append next judgment; restore membership and recover. Observe old/new numbers and disabled submission, retained note, explicit discard. Repeat discussion only after a verification exists for its original judgment. Do not interpret history revision as judgment number: tests use actual judgment event seq (discussion setup adds a separate verification event).
