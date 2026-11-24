# W19 read-card explanation lifecycle
Base: 80d558101f9fa9fec628dd518e40fbec5faf165c (parent f24ef201dc21bb5987bb89ad481b6924551ef235). 15 copied web files verified against fixed Git blobs before changes.

Only product change: existing KnowledgeCard renders SearchReason only when applied search status matches card status, and keys that disclosure by card ID, content digest, status and applied search scalar fields. Changing these identities closes the old explanation. No new route, data fetch, source permission, approval or write logic. Existing body disclosure already keys card ID/digest/status, so it is reused unchanged. Existing search abort/cancel, request-context checks, clear-on-read/error and parsePage status rejection are also reused.

Observed fixed backend at service/mcis_service/knowledge/router.py: search filters status (non-Published requires internal role); detail hides non-Published from external roles; review requires LeadInvestigator, expectedDigest and current state; Withdrawn only from Published. No update-card/version-replacement endpoint exists in this inspected module. This test does NOT execute publish/withdraw or invent a version-update API.

## Reproduce
Existing deps only:
    node tests_acceptance/W19-read-lifecycle/run.cjs
For a checkout elsewhere set MCIS_NODE_MODULES to existing React/esbuild modules and MCIS_HAPPY_DOM_PATH to file:///.../happy-dom/lib/index.js. Defaults are this Linux workspace's existing installations; no download.

Optional baseline negative:
    git show 80d558101f9fa9fec628dd518e40fbec5faf165c:web/src/pages/KnowledgePage.tsx > /tmp/w19-fixed-page.tsx
    MCIS_BASELINE_PAGE=/tmp/w19-fixed-page.tsx node tests_acceptance/W19-read-lifecycle/run.cjs
The runner verifies original blob 98efab8c9626c011a881075b5e616d62847a79b3. Baseline exits 1 at the first version-change disclosure assertion; patched exits 0 with 35 assertions.

Fixture uses existing version_binding/fixture.json two developer-visible synthetic texts combined with existing model.sample, canonical content digests and fixed 2030-06-04 timestamp. It does not create old benchmark evidence or source authority. No business dataset, model or new fixture prose.

## Actual coverage
Real KnowledgeCard, KnowledgePage, knowledge/api and parsePage run in React/HappyDOM. Synthetic GET transport supplies controlled responses; all non-GET/unexpected paths and storage writes throw. Verify same component version/card/query change closes explanation and source disclosure; mismatched card/search status hides explanation; expansion makes zero new source requests. Verify unsubmitted filter retains old applied reason, submitted search clears old card, successful new version contains only new source text, failures clear reason/source, retry recovers, withdrawal represented by empty Published result stays absent on repeated re-read, a malformed Withdrawn item in Published query is refused, unmount ignores a late reply.

35 assertions exit 0. Existing knowledge-w191.test.tsx: 27 assertions exit 0; knowledge-w192.test.tsx: preview/binding/no-model/no-save checks exit 0. One early harness run printed success but timed out on Node event-loop retention; explicit exit after unmount/HappyDOM cleanup corrected the harness. Baseline-plugin build initially used unsupported sync API; switched to esbuild async build before actual negative reproduction.

## Wording / limits
Returned reasons describe the completed query's literal/tag filters, NOT similarity, verified support or a live publication-status guarantee. Card/quote content is already loaded; opening a disclosure does not reauthorize or read the original. Withdrawal is learned on explicit re-read/context change, not pushed live. Tests simulate the response after withdrawal; no actual backend SQLite authorization/withdrawal test or browser was run here. Earlier production permissions, approval and archival untouched.

Manual inspection: open reason and body; explicitly re-read a changed/removed card; confirm prior explanation and source text disappear while loading and on error. For a newly returned version both disclosures start closed. No score/threshold changes. No commit/push/CI.
