# W20 developer-only disputed review presenter
Fixed parent: e419ffe66c8418261e2a6af163debaaee2721128.
AgentOverviewPage only re-exports the named component test entry AgentOverviewSyntheticReview. It does NOT mount this export. No production binding or default synthetic rows exist.
Two visible invented claims concern one disputed question in the Lily/Mary synthetic case and the same draft revision. Each has its own declared item ID, seat ID, source ID, line range and quote. A separate frozen test control specifies the entire expected item and two source line arrays.
Allowlisted own data fields are compared explicitly, with primitive type checks. Key order is irrelevant; functions/accessors, duplicate or unknown IDs, invalid arrays, case/revision/text mismatch fail closed. Exact quote equality checks only a selected local synthetic slice; it does not authenticate the complete source, semantics, causation, independence or human review authority.
From candidate checkout, using existing JS dependencies only:
node research/w20_dispute_presenter/run.cjs web /absolute/path/to/existing/node_modules
The runner verifies six imported application blobs against the fixed parent. It bundles in memory and exercises the actual named React export with SSR. It does not mount the application or start HTTP/browser. Module-import localStorage reads return null; writes and fetch throw. This is an explicit test boundary, not identity authentication.
27 checks passed, including opposing rows retaining separate quotes/sources, unresolved/pending status, no controls, no default rows, case/revision/quote/ID/line mismatch, complete side retention, mutation, property-order equivalence and no toJSON/accessor invocation.
No model, real case, queue, approval, archival, production data, browser interaction or real four-expert deliberation is covered.
Workflow inspection before handoff: parent contains no workflows; main 94d5e38c926fda232bb987b60fa9145e4bcf01a7 has only route-classification, triggered by pull_request or push to main. Candidate push is separate; no PR, merge or workflow dispatch.

Version follow-up: Source.sha256 and Item.sourceSha256 are required. The component compares a held full-source version with the fixture-host current digest; it does not compute source hashes or authenticate client control. Full-byte canonicalization and stale neighboring-line integration are tested in research/w20_dispute_cross_language. Still unmounted and test-only.
