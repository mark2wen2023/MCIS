# Human-selected focus → four independent Pi experts (synthetic experiment)

This isolated increment combines the existing PR45 workflow with actual four Pi Agent objects from PR49. Previously workflow only attached an issue label after calling an expert; now the manually selected issue reaches that expert's Pi prompt, with host-bound meeting ID, case, draft version and optional source/version refs. Application code binds the result to focus, not model metadata.

## Experimental contract proposal
- createPanel additionally accepts trusted host sessionId; frozen snapshot carries version.
- panel.challenge(role, target, focus) takes optional focus {sessionId, caseId, snapshotVersion, id, title, sources:[{id,version}]}.
- Supplied focus must match panel session/case/version; each source must be granted to speaker and frozen at that version. Invalid focus fails before model dispatch.
- Legacy two-argument calls retained for regression comparison, not a secure API. Integrated workflow always supplies focus after human agenda selection.
- Workflow owns issue/target metadata, captures configuration snapshot on creation, and uses separate Pi Agent objects through panelFactory:createPanel.
- These are in-process trusted-host contracts, NOT authenticated HTTP endpoints. Do not expose constructors or legacy calls to untrusted clients.

## Verification
Run: node test.mjs && node test-interleavings.mjs && node test-focus.mjs
Real Pi agent-core 1.5.2 uses local scripted providers: zero LLM/network.
Coverage: blind independent reviews then actual focus delivery; focus switching; frozen draft version; human pause/resume/end; case/source/version guards; foreign session rejection before dispatch; controlled-provider busy/cancel; separate panels. Source receipt does NOT establish factual citation support.

## Scope and limits
Not imported into MCIS; no production change, merge, deploy, NuGet or browser.
No real model, real case data, durable store, authenticated user/session ACL, semantic injection protection, token/wallclock budget, forced cancellation of non-cooperative providers, per-suggestion human adoption, or interactive UI. PR45 renderer remains a static snapshot. This increment closes an adapter gap instead of adding another mock UI.
The model can ignore focus; scripted tests prove delivery, not reasoning quality.
Existing conservative peer grant filtering remains; no authentic identity is claimed.
Dependencies reused locally, not uploaded. No credentials or .env included.

Independent acceptance reran all three suites plus review-probe.mjs and review-cancel-probe.mjs. Missing/empty/null/numeric snapshot version now denied. Focused challenge cancellation across cooperative provider await rejects late output. Unknown fields are stripped and returned contexts deep-copied. Workflow currently sends an empty focus sources list; direct panel interface supports validated refs.
