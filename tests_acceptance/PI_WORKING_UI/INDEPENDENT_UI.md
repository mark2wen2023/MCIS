# Independent Pi working/archive UI boundary review

Scope: extractionWorking and workingArchive TypeScript parsers and isolated React
views. No real model call, browser engine, production session, merge or deployment.

Found and corrected before acceptance: Pi statement `kind` previously accepted
arbitrary strings, and `claim.unit:null` did not match the server contract. The
implementer added the kind enum and Pi unit type check. Duplicate source-quote
rejection was also added by the implementer. No safety rules were weakened.

Independent tests added:
- `web/tests/pi-independent-fixture.ts`: fictional UTF-16/newline citation fixture.
- `web/tests/extraction-working-pi-independent.ts`:27/27 checks. Cross-record,
  exact quote/span, aliases/copies, extra fields, source bindings, provider flags,
  arbitrary trace/verified claims, duplicate quotes, scripted/user/unspecified
  review origins, changed old origin and client-supplied origin rejected.
- `web/tests/working-archive-pi-independent.ts`:20/20 checks. Restored data remains
  untrusted/nonactivated, v1 rejects Pi, v2 provider/trace/origin retained, source
  declarations strict, export wrapper/payload version mismatch rejected.

Rerun supplied implementation/regression suites:
- Pi working parser + HappyDOM30/30; existing working24/24 and independent9/9.
- Pi archive parser + HappyDOM28/28; existing archive27/27 and independent13/13.
- Strict TypeScript for both ports/components: exit0.

All listed checks passed. Counts include overlap with earlier reports and must
not be represented as new unique full-system/CI coverage. Views correctly label
scripted_test as not human review, missing origin as unknown and user submissions
as not independently verified human identity. Remote DeepSeek is not relabeled
local; historical provider/model/trace remain unverified package claims. Existing
unknown-write retry and late-response state handling were retained.

UI only displays validated projections and retains original quote whitespace.
The archive port relies on server import validation for duplicate JSON keys and
checksums; client parsing alone does not authenticate the archive. No production
browser or genuine-model-to-UI end-to-end acceptance was performed by this reviewer.
