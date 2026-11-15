# In-system public-text location: readiness assessment

Base: current remote main 94d5e38c926fda232bb987b60fa9145e4bcf01a7,
fetched for this assessment. PR103 head 435f1ba remains separate; no implementation
from that branch or historical-integrity candidates is included here.

## Decision

Do not wire a new internal viewer to the current legacy content endpoint yet.
Source bytes exist; the blocker is consistent protected, version-bound delivery,
not absence of the public text. This branch contains characterization tests and
an implementation proposal only. No permission/runtime/UI changes.

## Current code and observed behavior

- seed/yangze22.py registers EV-201 at raw/public/report.txt with pinned SHA256
  bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2.
  No PDF is registered by this seed. Existing cases are not backfilled on restart.
- reports/public_text.py reads the repository copy, verifies that pinned digest,
  then provides LF line/page intervals. reports/sources.py checks registration
  against item.sha256, not an atomic read of the current evidence bytes. The
  structured citation's sourceRef is the source-text version, not a versioned
  evidence-object receipt.
- Normal HTTP GET /cases/{case}/evidence/EV-201/content returns the actual public
  text, and X-Sha256 equals the response hash. Metadata contains sha256 and
  currentSha256; these are separate requests. GET records Access and leaves
  status Unverified. A 200 or matching response header is not a Verify event.
- GET /cases/{case}/evidence/EV-201/intake returns 404 INTAKE_NOT_FOUND. The newer
  intake integrity/receipt flow cannot be substituted for this seeded item;
  manufacturing or silently migrating a receipt would be incorrect.
- Wrong-case EV-201 lookup returns 404; Public-role content read returns 403.
  These ordinary tests do not establish production identity authentication:
  common/context.py still obtains role from the caller's header/default.

## Code-level prerequisites (not newly executed exploit probes)

In evidence/router.py get_content, current main reads p.read_bytes(), derives
currentSha256 for Access, and returns a newly computed X-Sha256. There is no
comparison of response bytes to the registration/current digest in that path.
The metadata endpoint uses filter_evidence, including evidence.restricted Remove;
the content endpoint instead checks confidentiality/testimony and does not call
that same filter. A UI guard or client digest check cannot repair server policy
consistency or certify the current-version binding. Path-safe bounded reads are
also not supplied by this legacy p.read_bytes() path. These are source observations,
not claims of a newly demonstrated remote exploit.

Previously saved safety-chain commits exist on separate remote branches (e.g.
1759643 on origin/codex/content-base64-integration-review and successors); current
main is not their descendant. Do not import their whole stack or assume historical
review constitutes acceptance on today's main. Coordinate their minimal relevant
policy/reader/version-binding prerequisites before wiring the viewer. No restricted
historical report-integrity test or denied protection query was attempted here.

## Minimal follow-up after prerequisites are independently accepted

1. Reuse one protected server read operation that checks case/evidence policy,
   current registration/custody digest and bounded source bytes under the existing
   transaction semantics. Preserve Access audit and fail on missing files, missing
   trusted digest, mismatch, malformed UTF-8 or unsupported versions. Do not relax
   permission or release the revocation lock merely for speed.
2. Accept a declared expected source SHA and line interval. Require response-byte
   digest to match that version; if the current stored version differs, report
   version unavailable/mismatch. Do not fall back to repository text or GitHub and
   label it current evidence. Bind returned case/id/hash/interval explicitly.
3. Render escaped text in a local dialog/view with numbered LF lines, preserve
   form feeds, validate the 53-page ceiling/EOF from PR103, and select by line
   interval rather than searching text. On case switch, denial, stale response,
   mismatch or decoding failure clear the prior content and success indicator.
4. Labels must distinguish: byte equality to the declared text version; a current
   evidence version checked at read time (not forever); PDF-page metadata, not a
   PDF viewer; no automatic quotation-truth or investigator-conclusion check.
5. Test public real text plus explicitly synthetic missing/mismatch/invalid UTF-8,
   denial, cross-case, rollback, concurrent revocation and stale UI responses only
   after the server prerequisites are approved. Keep browser and real-identity
   acceptance separate. Do not retest restricted historical-integrity work.

## Validation

Command (service):
.venv/bin/pytest -q tests/test_internal_text_location_readiness.py tests/test_reports_w161_public_text.py tests/test_reports_w162_access.py

Four new normal HTTP characterizations use temporary SQLite/blob storage and the
existing real public source. No private data/model/OCR/browser, no file-tampering,
symlink or historical-integrity probes. First run: 2 passed/2 failed because test
assertions incorrectly assumed nested detail.code; the app actually emits top-level
code. Assertions corrected to the real response contract, not product behavior.
Final combined results recorded in ROADMAP. These are developer self-tests, not
independent acceptance, a full security suite or a production deployment verdict.
